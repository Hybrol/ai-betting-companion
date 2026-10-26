from datetime import datetime
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.schema import Match, BookmakerOdds, Prediction, MatchStatus
from ..engine.scheduler import execute_betting_cycle

router = APIRouter(prefix="/matches", tags=["Matches"])

async def run_sync_task(db: Session, target_league: str | None = None):
    await execute_betting_cycle(target_league)

@router.get("/")
def list_matches(
    league: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Match)
    if league:
        query = query.filter(Match.league == league)
    if status:
        query = query.filter(Match.status == status)

    matches = query.order_by(Match.kickoff.asc()).all()

    result = []
    for m in matches:
        odds_list = []
        for o in m.odds:
            odds_list.append({
                "bookmaker": o.bookmaker,
                "market_type": o.market_type,
                "selection": o.selection,
                "odds": o.odds
            })

        preds_list = []
        for p in m.predictions:
            preds_list.append({
                "id": p.id,
                "market_type": p.market_type,
                "selection": p.selection,
                "model_prob": p.model_prob,
                "fair_odds": p.fair_odds,
                "best_bookmaker": p.best_bookmaker,
                "best_odds": p.best_odds,
                "ev_percent": p.ev_percent,
                "recommended_stake": p.recommended_stake,
                "confidence": getattr(p, "confidence", "MÉDIA") or "MÉDIA",
                "reasoning": getattr(p, "reasoning", "") or ""
            })

        result.append({
            "id": m.id,
            "home_team": m.home_team,
            "away_team": m.away_team,
            "league": m.league,
            "kickoff": m.kickoff.isoformat(),
            "status": m.status.value,
            "home_score": m.home_score,
            "away_score": m.away_score,
            "odds": odds_list,
            "predictions": preds_list
        })

    return result

@router.post("/sync")
async def trigger_sync(
    league: str | None = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Triggers an on-demand scrape and value analysis for Portuguese sportsbooks.
    """
    await run_sync_task(db, league)
    return {"message": "Sync complete", "league": league or "All Leagues"}
