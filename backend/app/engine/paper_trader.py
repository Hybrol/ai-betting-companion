from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.schema import Match, PaperBet, Bankroll, BankrollHistory, BetStatus, MatchStatus
from ..core.config import settings

class PaperTrader:
    @staticmethod
    def get_or_create_bankroll(db: Session) -> Bankroll:
        br = db.query(Bankroll).first()
        if not br:
            br = Bankroll(
                current_balance=settings.INITIAL_BANKROLL,
                initial_balance=settings.INITIAL_BANKROLL,
                total_staked=0.0,
                total_pnl=0.0,
                total_bets=0,
                greens=0,
                reds=0,
                voids=0
            )
            db.add(br)
            db.commit()
            db.refresh(br)
            
            # Initial history entry
            hist = BankrollHistory(
                balance=settings.INITIAL_BANKROLL,
                pnl_delta=0.0,
                description="Initial fictional bankroll deposit"
            )
            db.add(hist)
            db.commit()

        return br

    @classmethod
    def place_bet(
        cls,
        db: Session,
        match_id: int,
        bookmaker: str,
        market_type: str,
        selection: str,
        odds: float,
        stake: float,
        prediction_id: int | None = None,
        confidence: str = "MÉDIA",
        reasoning: str | None = None
    ) -> PaperBet:
        br = cls.get_or_create_bankroll(db)

        if stake > br.current_balance:
            raise ValueError(f"Insufficient fictional funds! Balance: {br.current_balance:.2f}€, Requested: {stake:.2f}€")

        # Deduct stake from current bankroll
        br.current_balance -= stake
        br.total_staked += stake
        br.total_bets += 1

        bet = PaperBet(
            prediction_id=prediction_id,
            match_id=match_id,
            bookmaker=bookmaker,
            market_type=market_type,
            selection=selection,
            odds=odds,
            stake=stake,
            potential_payout=round(stake * odds, 2),
            status=BetStatus.PENDING,
            confidence=confidence,
            reasoning=reasoning,
            placed_at=datetime.utcnow()
        )
        db.add(bet)

        # Record bankroll history
        hist = BankrollHistory(
            balance=round(br.current_balance, 2),
            pnl_delta=-round(stake, 2),
            description=f"Placed bet: {stake:.2f}€ on {selection} @ {odds:.2f} ({bookmaker})"
        )
        db.add(hist)

        db.commit()
        db.refresh(bet)
        return bet

    @classmethod
    def resolve_match_bets(
        cls,
        db: Session,
        match_id: int,
        home_score: int,
        away_score: int
    ) -> list[PaperBet]:
        """
        Settles all pending bets for a match based on final score.
        """
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return []

        match.home_score = home_score
        match.away_score = away_score
        match.status = MatchStatus.FINISHED

        pending_bets = db.query(PaperBet).filter(
            PaperBet.match_id == match_id,
            PaperBet.status == BetStatus.PENDING
        ).all()

        br = cls.get_or_create_bankroll(db)
        resolved = []

        # Determine winning 1X2 selection
        if home_score > away_score:
            winning_1x2 = "1"
        elif home_score == away_score:
            winning_1x2 = "X"
        else:
            winning_1x2 = "2"

        total_goals = home_score + away_score

        for bet in pending_bets:
            is_win = False
            is_void = False

            if bet.market_type == "1X2":
                is_win = (bet.selection.upper() == winning_1x2)
            elif bet.market_type == "DOUBLE_CHANCE":
                sel = bet.selection.upper()
                if sel == "1X":
                    is_win = (home_score >= away_score)
                elif sel == "X2":
                    is_win = (away_score >= home_score)
                elif sel == "12":
                    is_win = (home_score != away_score)
            elif bet.market_type in ("OVER_UNDER_2_5", "OVER_UNDER"):
                is_win = (total_goals > 2.5) if bet.selection.upper() == "OVER" else (total_goals < 2.5)
            elif bet.market_type == "OVER_UNDER_1_5":
                is_win = (total_goals > 1.5) if bet.selection.upper() == "OVER" else (total_goals < 1.5)
            elif bet.market_type == "OVER_UNDER_3_5":
                is_win = (total_goals > 3.5) if bet.selection.upper() == "OVER" else (total_goals < 3.5)
            elif bet.market_type == "BTTS":
                if bet.selection.upper() in ("YES", "SIM"):
                    is_win = (home_score > 0 and away_score > 0)
                else:
                    is_win = (home_score == 0 or away_score == 0)

            if is_win:
                bet.status = BetStatus.GREEN
                bet.payout = round(bet.stake * bet.odds, 2)
                bet.profit_loss = round(bet.payout - bet.stake, 2)
                br.current_balance += bet.payout
                br.total_pnl += bet.profit_loss
                br.greens += 1

                hist = BankrollHistory(
                    balance=round(br.current_balance, 2),
                    pnl_delta=bet.profit_loss,
                    description=f"GREEN! Won {bet.profit_loss:+.2f}€ on {match.home_team} vs {match.away_team} ({bet.selection} @ {bet.odds})"
                )
                db.add(hist)
            else:
                bet.status = BetStatus.RED
                bet.payout = 0.0
                bet.profit_loss = -bet.stake
                br.total_pnl -= bet.stake
                br.reds += 1

                hist = BankrollHistory(
                    balance=round(br.current_balance, 2),
                    pnl_delta=-bet.stake,
                    description=f"RED. Lost -{bet.stake:.2f}€ on {match.home_team} vs {match.away_team} ({bet.selection})"
                )
                db.add(hist)

            bet.resolved_at = datetime.utcnow()
            resolved.append(bet)

        db.commit()
        return resolved

    @classmethod
    def get_analytics(cls, db: Session) -> dict:
        br = cls.get_or_create_bankroll(db)
        resolved_count = br.greens + br.reds
        win_rate = (br.greens / resolved_count * 100) if resolved_count > 0 else 0.0
        roi = (br.total_pnl / br.total_staked * 100) if br.total_staked > 0 else 0.0

        history = db.query(BankrollHistory).order_by(BankrollHistory.timestamp.asc()).all()
        history_points = [
            {
                "timestamp": h.timestamp.isoformat(),
                "balance": round(h.balance, 2),
                "delta": round(h.pnl_delta, 2),
                "description": h.description
            }
            for h in history
        ]

        # Calculate max drawdown on realized/settled equity
        settled_bets = db.query(PaperBet).filter(
            PaperBet.status.in_([BetStatus.GREEN, BetStatus.RED])
        ).order_by(PaperBet.resolved_at.asc()).all()

        equity_peak = br.initial_balance
        running_equity = br.initial_balance
        max_drawdown = 0.0

        for sb in settled_bets:
            running_equity += sb.profit_loss
            if running_equity > equity_peak:
                equity_peak = running_equity
            dd = (equity_peak - running_equity) / equity_peak if equity_peak > 0 else 0.0
            if dd > max_drawdown:
                max_drawdown = dd

        # Active pending wagers in play
        active_stakes = db.query(func.sum(PaperBet.stake)).filter(
            PaperBet.status == BetStatus.PENDING
        ).scalar() or 0.0
        total_equity = br.current_balance + active_stakes

        return {
            "current_balance": round(br.current_balance, 2),
            "total_equity": round(total_equity, 2),
            "active_stakes": round(active_stakes, 2),
            "initial_balance": round(br.initial_balance, 2),
            "total_staked": round(br.total_staked, 2),
            "total_pnl": round(br.total_pnl, 2),
            "roi_percent": round(roi, 2),
            "win_rate_percent": round(win_rate, 2),
            "greens": br.greens,
            "reds": br.reds,
            "voids": br.voids,
            "total_bets": br.total_bets,
            "max_drawdown_percent": round(max_drawdown * 100, 2),
            "history": history_points
        }
