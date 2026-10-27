from difflib import SequenceMatcher
from pydantic import BaseModel
from ..core.config import settings
from .predictor import MatchPredictor
from .normalizer import get_canonical_stem

class ValueOpportunity(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    league: str
    market_type: str
    selection: str
    best_bookmaker: str
    best_odds: float
    model_prob: float
    fair_odds: float
    ev_percent: float
    kelly_stake_percent: float
    recommended_stake: float
    confidence: str
    reasoning: str

class ValueFinder:
    @staticmethod
    def calculate_ev(prob: float, odds: float) -> float:
        """
        Calculates Expected Value: (P * Decimal_Odds) - 1.0
        Returns float, e.g., 0.065 for +6.5% EV
        """
        return (prob * odds) - 1.0

    @staticmethod
    def calculate_kelly_stake(prob: float, odds: float, bankroll: float) -> tuple[float, float]:
        """
        Calculates fractional Kelly Criterion stake.
        f = (p * (b) - q) / b, where b = odds - 1, q = 1 - p
        """
        if odds <= 1.0 or prob <= 0.0:
            return 0.0, 0.0

        b = odds - 1.0
        q = 1.0 - prob
        full_kelly = (prob * b - q) / b

        if full_kelly <= 0.0:
            return 0.0, 0.0

        # Apply conservative fractional Kelly for variance control
        fractional_kelly = full_kelly * settings.KELLY_FRACTION
        stake_pct = min(fractional_kelly, settings.MAX_BET_PERCENTAGE)
        stake_amount = round(bankroll * stake_pct, 2)

        return round(stake_pct * 100, 2), stake_amount

    @classmethod
    def scan_for_value(
        cls,
        match_id: int,
        home_team: str,
        away_team: str,
        league: str,
        odds_by_market: dict[str, dict[str, list[tuple[str, float]]]],
        # Format: {"1X2": {"1": [("Betclic", 1.8), ("Betano", 1.9)]}, "DOUBLE_CHANCE": {...}, ...}
        model_probs_by_market: dict[str, dict[str, float]],
        # Format: {"1X2": {"1": 0.55, ...}, "DOUBLE_CHANCE": {"1X": 0.78, ...}, ...}
        current_bankroll: float,
        metrics: dict | None = None
    ) -> list[ValueOpportunity]:
        opportunities = []
        metrics = metrics or {}
        lam = metrics.get("exp_home_goals", 1.5)
        mu = metrics.get("exp_away_goals", 1.2)

        for market_type, selections_dict in odds_by_market.items():
            market_probs = model_probs_by_market.get(market_type, {})
            if not market_probs:
                continue

            for selection, odds_list in selections_dict.items():
                if not odds_list or selection not in market_probs:
                    continue

                best_bookmaker, best_odds = max(odds_list, key=lambda item: item[1])
                prob = market_probs[selection]

                # STRICT QUALITY & VALUE FILTERS
                # 1. Filter out odds outside the professional sweet spot (1.40 - 4.50)
                if best_odds < settings.MIN_ODDS or best_odds > settings.MAX_ODDS:
                    continue

                # 2. Filter out extreme lottery probabilities (< 22%)
                if prob < settings.MIN_PROBABILITY:
                    continue

                # 3. Calculate Expected Value
                ev = cls.calculate_ev(prob, best_odds)

                # 4. Filter by minimum positive edge threshold (>= 3.5%)
                if ev >= settings.MIN_EV_THRESHOLD:
                    fair_odds = round(1.0 / prob, 2) if prob > 0 else 9.99
                    stake_pct, stake_amt = cls.calculate_kelly_stake(prob, best_odds, current_bankroll)

                    if stake_amt > 0:
                        conf, reason = MatchPredictor.generate_tipster_reasoning(
                            home_team=home_team,
                            away_team=away_team,
                            market_type=market_type,
                            selection=selection,
                            best_odds=best_odds,
                            best_bookmaker=best_bookmaker,
                            model_prob=prob,
                            ev_percent=round(ev * 100, 2),
                            lam=lam,
                            mu=mu
                        )

                        opportunities.append(ValueOpportunity(
                            match_id=match_id,
                            home_team=home_team,
                            away_team=away_team,
                            league=league,
                            market_type=market_type,
                            selection=selection,
                            best_bookmaker=best_bookmaker,
                            best_odds=best_odds,
                            model_prob=round(prob, 4),
                            fair_odds=fair_odds,
                            ev_percent=round(ev * 100, 2),
                            kelly_stake_percent=stake_pct,
                            recommended_stake=stake_amt,
                            confidence=conf,
                            reasoning=reason
                        ))

        return opportunities

    @classmethod
    def build_curated_multiple(
        cls,
        opportunities: list[ValueOpportunity],
        max_legs: int = 3,
        current_bankroll: float = 1000.0
    ) -> dict | None:
        """
        Builds a curated Múltipla de Valor (Acca) from 2 to 3 highest-confidence,
        independent value opportunities from different matches.
        """
        if len(opportunities) < 2:
            return None

        # Prioritize ALTA confidence first, then highest EV
        sorted_opps = sorted(
            opportunities,
            key=lambda x: (1 if x.confidence == "ALTA" else 0, x.ev_percent),
            reverse=True
        )

        selected_legs: list[ValueOpportunity] = []
        seen_matches = set()
        seen_team_stems: set[str] = set()

        for opp in sorted_opps:
            if opp.best_odds < 1.35 or opp.best_odds > 2.80:
                continue

            if opp.match_id in seen_matches:
                continue

            h_stem = get_canonical_stem(opp.home_team)
            a_stem = get_canonical_stem(opp.away_team)

            # Prevent duplicate matches or teams across different bookmakers/match records
            is_duplicate = False
            for seen in seen_team_stems:
                if h_stem == seen or a_stem == seen:
                    is_duplicate = True
                    break
                if (len(h_stem) >= 4 and h_stem in seen) or (len(seen) >= 4 and seen in h_stem):
                    is_duplicate = True
                    break
                if (len(a_stem) >= 4 and a_stem in seen) or (len(seen) >= 4 and seen in a_stem):
                    is_duplicate = True
                    break
                if SequenceMatcher(None, h_stem, seen).ratio() >= 0.80 or SequenceMatcher(None, a_stem, seen).ratio() >= 0.80:
                    is_duplicate = True
                    break

            if is_duplicate:
                continue

            selected_legs.append(opp)
            seen_matches.add(opp.match_id)
            seen_team_stems.add(h_stem)
            seen_team_stems.add(a_stem)

            if len(selected_legs) >= max_legs:
                break

        if len(selected_legs) < 2:
            return None

        combined_odds = 1.0
        combined_prob = 1.0
        for leg in selected_legs:
            combined_odds *= leg.best_odds
            combined_prob *= leg.model_prob

        combined_odds = round(combined_odds, 2)
        combined_prob = round(combined_prob, 4)
        combined_ev = round(((combined_prob * combined_odds) - 1.0) * 100, 2)
        fair_combined_odds = round(1.0 / combined_prob, 2) if combined_prob > 0 else 99.0

        # Small controlled stake on multiples (e.g. 1.0% to 1.5% bankroll)
        multiple_stake = round(min(15.0, current_bankroll * 0.012), 2)
        potential_payout = round(multiple_stake * combined_odds, 2)

        return {
            "legs_count": len(selected_legs),
            "total_odds": combined_odds,
            "fair_odds": fair_combined_odds,
            "combined_ev_percent": combined_ev,
            "combined_prob_percent": round(combined_prob * 100, 1),
            "recommended_stake": multiple_stake,
            "potential_payout": potential_payout,
            "legs": [
                {
                    "match": f"{leg.home_team} vs {leg.away_team}",
                    "league": leg.league,
                    "market": leg.market_type,
                    "selection": leg.selection,
                    "bookmaker": leg.best_bookmaker,
                    "odds": leg.best_odds,
                    "confidence": leg.confidence,
                    "reasoning": leg.reasoning
                }
                for leg in selected_legs
            ]
        }
