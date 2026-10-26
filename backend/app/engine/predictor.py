import math
import numpy as np
from scipy.stats import poisson

LEAGUE_GOAL_MEANS = {
    "Liga Portugal": {"home": 1.48, "away": 1.12},
    "Premier League": {"home": 1.62, "away": 1.30},
    "La Liga": {"home": 1.45, "away": 1.15},
    "Serie A": {"home": 1.50, "away": 1.20},
    "Bundesliga": {"home": 1.75, "away": 1.42},
    "Champions League": {"home": 1.65, "away": 1.32},
}

# Team Elo / Relative Strength modifiers (Attack rating, Defense rating multiplier)
# 1.0 is league average; > 1.0 means stronger attack or leakier defense
TEAM_STRENGTH_MODIFIERS = {
    # Liga Portugal
    "SL Benfica": {"att": 1.55, "def": 0.65},
    "Sporting CP": {"att": 1.60, "def": 0.60},
    "FC Porto": {"att": 1.50, "def": 0.68},
    "SC Braga": {"att": 1.30, "def": 0.85},
    "Vitória SC": {"att": 1.15, "def": 0.90},
    "Santa Clara": {"att": 0.90, "def": 1.10},
    "Casa Pia AC": {"att": 0.85, "def": 1.15},
    "Moreirense FC": {"att": 0.95, "def": 1.05},
    "GD Estoril Praia": {"att": 1.00, "def": 1.25},
    "Rio Ave FC": {"att": 0.88, "def": 1.12},
    "FC Famalicão": {"att": 0.95, "def": 1.00},
    "Gil Vicente FC": {"att": 0.92, "def": 1.18},
    "CF Estrela Amadora": {"att": 0.85, "def": 1.25},
    "FC Arouca": {"att": 0.95, "def": 1.10},
    "CD Nacional": {"att": 0.82, "def": 1.30},
    "AVS Futebol SAD": {"att": 0.80, "def": 1.35},
    "SC Farense": {"att": 0.80, "def": 1.30},
    "Boavista FC": {"att": 0.85, "def": 1.28},

    # Premier League
    "Manchester City": {"att": 1.65, "def": 0.65},
    "Arsenal": {"att": 1.55, "def": 0.60},
    "Liverpool": {"att": 1.60, "def": 0.65},
    "Chelsea": {"att": 1.35, "def": 0.90},
    "Aston Villa": {"att": 1.30, "def": 0.95},
    "Tottenham Hotspur": {"att": 1.35, "def": 1.05},
    "Newcastle United": {"att": 1.25, "def": 0.95},
    "Manchester United": {"att": 1.20, "def": 1.05},

    # La Liga
    "Real Madrid": {"att": 1.65, "def": 0.65},
    "FC Barcelona": {"att": 1.68, "def": 0.68},
    "Atlético Madrid": {"att": 1.35, "def": 0.70},
    "Sevilla FC": {"att": 1.05, "def": 1.05},
    "Villarreal CF": {"att": 1.25, "def": 1.00},
    "CA Osasuna": {"att": 0.95, "def": 1.05},
    "RCD Espanyol": {"att": 0.90, "def": 1.20},
}

class MatchPredictor:
    @staticmethod
    def remove_bookmaker_margin(odds_1x2: list[float]) -> list[float]:
        if not odds_1x2 or any(o <= 1.0 for o in odds_1x2):
            return [0.333, 0.333, 0.333]
        raw_probs = [1.0 / o for o in odds_1x2]
        margin = sum(raw_probs)
        return [p / margin for p in raw_probs]

    @classmethod
    def calculate_poisson_probs(cls, league: str, home_team: str, away_team: str, max_goals: int = 7) -> dict[str, float]:
        means = LEAGUE_GOAL_MEANS.get(league, {"home": 1.50, "away": 1.20})
        
        home_mod = TEAM_STRENGTH_MODIFIERS.get(home_team, {"att": 1.0, "def": 1.0})
        away_mod = TEAM_STRENGTH_MODIFIERS.get(away_team, {"att": 1.0, "def": 1.0})

        # Expected goals lambda and mu
        lambda_home = means["home"] * home_mod["att"] * away_mod["def"]
        mu_away = means["away"] * away_mod["att"] * home_mod["def"]

        # Clamp between 0.35 and 4.5 goals for numerical safety
        lambda_home = max(0.35, min(4.5, lambda_home))
        mu_away = max(0.35, min(4.5, mu_away))

        prob_matrix = np.zeros((max_goals + 1, max_goals + 1))
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                prob_matrix[h, a] = poisson.pmf(h, lambda_home) * poisson.pmf(a, mu_away)

        prob_home = float(np.sum(np.tril(prob_matrix, -1)))
        prob_draw = float(np.sum(np.diag(prob_matrix)))
        prob_away = float(np.sum(np.triu(prob_matrix, 1)))

        total = prob_home + prob_draw + prob_away
        return {
            "1": prob_home / total,
            "X": prob_draw / total,
            "2": prob_away / total,
            "exp_home_goals": round(lambda_home, 2),
            "exp_away_goals": round(mu_away, 2)
        }

    @classmethod
    def estimate_probabilities(
        cls,
        league: str,
        home_team: str,
        away_team: str,
        multi_odds_1x2: list[list[float]]
    ) -> dict[str, float]:
        """
        Combines our Poisson statistical model (40% weight) with multi-bookmaker consensus (60% weight).
        This blended probability model spots when a bookmaker has shaded or mispriced an underdog/favorite.
        """
        poisson_res = cls.calculate_poisson_probs(league, home_team, away_team)

        if multi_odds_1x2:
            all_fair_probs = [cls.remove_bookmaker_margin(odds) for odds in multi_odds_1x2 if len(odds) == 3]
            if all_fair_probs:
                market_p1 = float(np.mean([p[0] for p in all_fair_probs]))
                market_px = float(np.mean([p[1] for p in all_fair_probs]))
                market_p2 = float(np.mean([p[2] for p in all_fair_probs]))

                # Weighted ensemble: 40% Poisson statistical edge + 60% market consensus
                blend_p1 = (0.40 * poisson_res["1"]) + (0.60 * market_p1)
                blend_px = (0.40 * poisson_res["X"]) + (0.60 * market_px)
                blend_p2 = (0.40 * poisson_res["2"]) + (0.60 * market_p2)

                total_blend = blend_p1 + blend_px + blend_p2
                return {
                    "1": blend_p1 / total_blend,
                    "X": blend_px / total_blend,
                    "2": blend_p2 / total_blend
                }

        return {"1": poisson_res["1"], "X": poisson_res["X"], "2": poisson_res["2"]}
