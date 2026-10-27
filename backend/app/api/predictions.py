from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
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
    today_only: bool = Query(True, description="Filter strictly for today's matches"),
    target_date: str | None = Query(None, description="Specific date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """
    Returns AI-identified value bets with confidence level and expert tipster rationale.
    By default, restricts recommendations strictly to today's matches.
    """
    query = db.query(Prediction).join(Match).filter(Prediction.ev_percent >= min_ev)
    if league:
        query = query.filter(Match.league == league)

    if target_date:
        query = query.filter(func.date(Match.kickoff) == target_date)
    elif today_only:
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        query = query.filter(func.date(Match.kickoff) == today_str)

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
def get_curated_multiple(
    today_only: bool = Query(True, description="Only legs from today's matches"),
    db: Session = Depends(get_db)
):
    """
    Returns the daily curated Múltipla de Valor (Acca), restricted to today's matches.
    """
    br = PaperTrader.get_or_create_bankroll(db)
    query = db.query(Prediction).join(Match).filter(
        Prediction.ev_percent >= 3.5,
        Prediction.best_odds >= 1.35,
        Prediction.best_odds <= 2.80
    )

    if today_only:
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        query = query.filter(
            func.date(Match.kickoff) == today_str,
            Match.kickoff >= datetime.utcnow()
        )

    preds = query.order_by(Prediction.ev_percent.desc()).all()

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
            reasoning=getattr(p, "reasoning", "") or "",
            kickoff=p.match.kickoff.isoformat()
        )
        for p in preds
    ]

    multiple = ValueFinder.build_curated_multiple(opps, max_legs=3, current_bankroll=br.current_balance)
    return multiple or {"message": "Nenhuma múltipla de valor qualificada no momento."}
