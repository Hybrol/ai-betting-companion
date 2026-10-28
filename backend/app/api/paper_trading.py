import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.schema import PaperBet, Match, Bankroll, BankrollHistory, BetStatus
from ..engine.paper_trader import PaperTrader
from ..core.config import settings

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])

class PlaceBetRequest(BaseModel):
    match_id: int
    bookmaker: str
    market_type: str = "1X2"
    selection: str
    odds: float
    stake: float
    prediction_id: int | None = None
    confidence: str = "MÉDIA"
    reasoning: str | None = None
    stats_analysis: dict | None = None

class ResolveMatchRequest(BaseModel):
    match_id: int
    home_score: int
    away_score: int

class ResetBankrollRequest(BaseModel):
    initial_balance: float = 1000.0

@router.post("/bet")
def place_paper_bet(req: PlaceBetRequest, db: Session = Depends(get_db)):
    """
    Simulate placing a bet using fictional bankroll.
    """
    try:
        bet = PaperTrader.place_bet(
            db=db,
            match_id=req.match_id,
            bookmaker=req.bookmaker,
            market_type=req.market_type,
            selection=req.selection,
            odds=req.odds,
            stake=req.stake,
            prediction_id=req.prediction_id,
            confidence=req.confidence,
            reasoning=req.reasoning,
            stats_analysis=req.stats_analysis
        )
        return {
            "message": "Bet placed successfully",
            "bet_id": bet.id,
            "status": bet.status.value,
            "potential_payout": bet.potential_payout
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/bets")
def list_paper_bets(status: str | None = None, db: Session = Depends(get_db)):
    """
    List virtual bets (Greens, Reds, and PENDING).
    """
    query = db.query(PaperBet).join(Match)
    if status:
        query = query.filter(PaperBet.status == status)

    bets = query.order_by(PaperBet.placed_at.desc()).all()

    results = []
    for b in bets:
        is_mult = getattr(b, "is_multiple", False)
        legs_data = None
        stats_data = None
        if is_mult and b.multiple_legs:
            try:
                legs_data = json.loads(b.multiple_legs)
            except Exception:
                legs_data = []
        elif not is_mult:
            if getattr(b, "stats_analysis", None):
                try:
                    stats_data = json.loads(b.stats_analysis)
                except Exception:
                    stats_data = None
            if not stats_data:
                p = b.prediction
                ev = p.ev_percent if p else 8.5
                model_prob = round(p.model_prob * 100, 1) if p else round((1.0 / (b.odds * 0.9)) * 100, 1)
                fair_odds = p.fair_odds if p else round(100.0 / model_prob, 2)
                stats_data = {
                    "home": {
                        "name": b.match.home_team,
                        "rank": "Competidor",
                        "points": "-",
                        "record": "Forma Regular",
                        "goal_diff": "-",
                        "form": "D-W-L-W-D",
                        "last_matches": []
                    },
                    "away": {
                        "name": b.match.away_team,
                        "rank": "Competidor",
                        "points": "-",
                        "record": "Forma Regular",
                        "goal_diff": "-",
                        "form": "W-D-W-L-W",
                        "last_matches": []
                    },
                    "dixon_coles": {
                        "xg_home": 1.45,
                        "xg_away": 1.25,
                        "xg_total": 2.70,
                        "ev_percent": round(ev, 1),
                        "market_odds": b.odds,
                        "fair_odds": fair_odds,
                        "model_prob": model_prob,
                        "kelly_stake_percent": round((b.stake / 1000.0) * 100, 1)
                    },
                    "dossier_text": b.reasoning or ""
                }

        results.append({
            "id": b.id,
            "match_id": b.match_id,
            "home_team": "💎 Múltipla de Valor" if is_mult else b.match.home_team,
            "away_team": f"{len(legs_data)} Seleções" if is_mult and legs_data else (b.match.away_team if not is_mult else ""),
            "league": "Múltipla SRIJ" if is_mult else b.match.league,
            "home_score": None if is_mult else b.match.home_score,
            "away_score": None if is_mult else b.match.away_score,
            "match_status": "PENDING" if is_mult else b.match.status.value,
            "bookmaker": b.bookmaker,
            "market_type": b.market_type,
            "selection": b.selection,
            "odds": b.odds,
            "stake": b.stake,
            "potential_payout": b.potential_payout,
            "status": b.status.value,
            "profit_loss": b.profit_loss,
            "confidence": getattr(b, "confidence", "ALTA" if is_mult else "MÉDIA") or "MÉDIA",
            "reasoning": getattr(b, "reasoning", "") or "",
            "is_multiple": is_mult,
            "multiple_legs": legs_data,
            "stats_analysis": stats_data,
            "placed_at": b.placed_at.isoformat(),
            "resolved_at": b.resolved_at.isoformat() if b.resolved_at else None
        })

    return results

@router.post("/resolve")
def resolve_match(req: ResolveMatchRequest, db: Session = Depends(get_db)):
    """
    Settle all wagers for a match and update bankroll with GREEN or RED.
    """
    resolved_bets = PaperTrader.resolve_match_bets(
        db=db,
        match_id=req.match_id,
        home_score=req.home_score,
        away_score=req.away_score
    )
    return {
        "message": f"Settled {len(resolved_bets)} bets for match {req.match_id}",
        "home_score": req.home_score,
        "away_score": req.away_score,
        "settled_count": len(resolved_bets)
    }

@router.post("/reset")
def reset_bankroll(req: ResetBankrollRequest, db: Session = Depends(get_db)):
    """
    Resets fictional bankroll and clears previous bet records.
    """
    db.query(PaperBet).delete()
    db.query(BankrollHistory).delete()
    db.query(Bankroll).delete()
    db.commit()

    br = Bankroll(
        current_balance=req.initial_balance,
        initial_balance=req.initial_balance,
        total_staked=0.0,
        total_pnl=0.0,
        total_bets=0,
        greens=0,
        reds=0,
        voids=0
    )
    db.add(br)

    hist = BankrollHistory(
        balance=req.initial_balance,
        pnl_delta=0.0,
        description=f"Bankroll reset to {req.initial_balance:.2f}€"
    )
    db.add(hist)
    db.commit()

    return {"message": "Bankroll reset successfully", "new_balance": req.initial_balance}
