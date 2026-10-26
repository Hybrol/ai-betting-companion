from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.schema import Prediction, Match
from ..engine.value_finder import ValueFinder, ValueOpportunity
from ..engine.paper_trader import PaperTrader

router = APIRouter(prefix="/predictions", tags=["Predictions"])

@router.get("/value-bets")
def get_value_bets(
    min_ev: float = Query(3.5, description="Minimum EV percentage"),
    league: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns AI-identified value bets with confidence level and expert tipster rationale.
    """
    query = db.query(Prediction).join(Match).filter(Prediction.ev_percent >= min_ev)
    if league:
        query = query.filter(Match.league == league)

    preds = query.order_by(Prediction.ev_percent.desc()).all()

    results = []
    for p in preds:
        results.append({
            "id": p.id,
            "match_id": p.match_id,
            "home_team": p.match.home_team,
            "away_team": p.match.away_team,
            "league": p.match.league,
            "kickoff": p.match.kickoff.isoformat(),
            "market_type": p.market_type,
            "selection": p.selection,
            "model_prob": p.model_prob,
            "fair_odds": p.fair_odds,
            "best_bookmaker": p.best_bookmaker,
            "best_odds": p.best_odds,
            "ev_percent": p.ev_percent,
            "kelly_stake_percent": p.kelly_stake_percent,
            "recommended_stake": p.recommended_stake,
            "confidence": getattr(p, "confidence", "MÉDIA") or "MÉDIA",
            "reasoning": getattr(p, "reasoning", "") or ""
        })

    return results

@router.get("/curated-multiple")
def get_curated_multiple(db: Session = Depends(get_db)):
    """
    Returns the daily curated Múltipla de Valor (Acca).
    """
    br = PaperTrader.get_or_create_bankroll(db)
    preds = db.query(Prediction).join(Match).filter(
        Prediction.ev_percent >= 3.5,
        Prediction.best_odds >= 1.35,
        Prediction.best_odds <= 2.80
    ).order_by(Prediction.ev_percent.desc()).all()

    opps = [
        ValueOpportunity(
            match_id=p.match_id,
            home_team=p.match.home_team,
            away_team=p.match.away_team,
            league=p.match.league,
            market_type=p.market_type,
            selection=p.selection,
            best_bookmaker=p.best_bookmaker,
            best_odds=p.best_odds,
            model_prob=p.model_prob,
            fair_odds=p.fair_odds,
            ev_percent=p.ev_percent,
            kelly_stake_percent=p.kelly_stake_percent,
            recommended_stake=p.recommended_stake,
            confidence=getattr(p, "confidence", "MÉDIA") or "MÉDIA",
            reasoning=getattr(p, "reasoning", "") or ""
        )
        for p in preds
    ]

    multiple = ValueFinder.build_curated_multiple(opps, max_legs=3, current_bankroll=br.current_balance)
    return multiple or {"message": "Nenhuma múltipla de valor qualificada no momento."}
