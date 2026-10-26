from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..engine.paper_trader import PaperTrader

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Returns high-level bankroll KPIs, Greens vs Reds, ROI, and balance timeline.
    """
    return PaperTrader.get_analytics(db)
