from pydantic import BaseModel
from ..core.config import settings

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

class ValueFinder:
    @staticmethod
    def calculate_ev(prob: float, odds: float) -> float:
        """
        Calculates Expected Value: (P * Decimal_Odds) - 1
        Returns float, e.g., 0.054 for +5.4%
        """
        return (prob * odds) - 1.0

    @staticmethod
    def calculate_kelly_stake(prob: float, odds: float, bankroll: float) -> tuple[float, float]:
        """
        Calculates fractional Kelly Criterion stake.
        f = (p * (b) - q) / b, where b = odds - 1, q = 1 - p
        Returns (stake_percentage, recommended_amount)
        """
        if odds <= 1.0 or prob <= 0.0:
            return 0.0, 0.0

        b = odds - 1.0
        q = 1.0 - prob
        full_kelly = (prob * b - q) / b

        if full_kelly <= 0.0:
            return 0.0, 0.0

        # Apply fractional Kelly (e.g., quarter Kelly for safety)
        fractional_kelly = full_kelly * settings.KELLY_FRACTION
        
        # Cap stake at maximum bankroll exposure percentage
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
        odds_by_selection: dict[str, list[tuple[str, float]]], # {"1": [("Betclic", 1.8), ("Betano", 1.85)]}
        model_probs: dict[str, float],                         # {"1": 0.58, "X": 0.25, "2": 0.17}
        current_bankroll: float
    ) -> list[ValueOpportunity]:
        opportunities = []

        for selection, odds_list in odds_by_selection.items():
            if not odds_list or selection not in model_probs:
                continue

            # Find best available odds across bookmakers
            best_bookmaker, best_odds = max(odds_list, key=lambda item: item[1])
            prob = model_probs[selection]
            fair_odds = round(1.0 / prob, 2) if prob > 0 else 999.0

            ev = cls.calculate_ev(prob, best_odds)

            # Check if exceeds threshold (e.g. +3% or better)
            if ev >= settings.MIN_EV_THRESHOLD:
                stake_pct, stake_amt = cls.calculate_kelly_stake(prob, best_odds, current_bankroll)
                if stake_amt > 0:
                    opportunities.append(ValueOpportunity(
                        match_id=match_id,
                        home_team=home_team,
                        away_team=away_team,
                        league=league,
                        market_type="1X2",
                        selection=selection,
                        best_bookmaker=best_bookmaker,
                        best_odds=best_odds,
                        model_prob=round(prob, 4),
                        fair_odds=fair_odds,
                        ev_percent=round(ev * 100, 2),
                        kelly_stake_percent=stake_pct,
                        recommended_stake=stake_amt
                    ))

        return opportunities
