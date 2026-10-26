import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.schema import Match, PaperBet, Prediction, BetStatus, BookmakerOdds
from ..engine.paper_trader import PaperTrader
from ..engine.discord_notifier import DiscordNotifier
from ..core.config import settings

logger = logging.getLogger(__name__)

# In-memory notification deduplication cache: { "matchId_selection": last_notified_datetime }
NOTIFIED_CACHE: dict[str, datetime] = {}

class AutoBettor:
    @classmethod
    async def process_value_opportunity(
        cls,
        db: Session,
        match: Match,
        prediction: Prediction,
        odds_by_bookmaker: dict[str, dict[str, float]]
    ) -> bool:
        """
        Evaluates a single value opportunity:
        1. Auto-bets on it if AUTO_BET_ENABLED and not already placed.
        2. Sends a Discord notification if DISCORD_WEBHOOK_URL is set and not already notified recently.
        """
        cache_key = f"{match.id}_{prediction.selection}"
        now = datetime.utcnow()

        # Check if already bet on this match and selection
        existing_bet = db.query(PaperBet).filter(
            PaperBet.match_id == match.id,
            PaperBet.selection == prediction.selection,
            PaperBet.status == BetStatus.PENDING
        ).first()

        auto_bet_placed = False

        # 1. Automated Paper Bet Placement
        if settings.AUTO_BET_ENABLED and not existing_bet:
            try:
                br = PaperTrader.get_or_create_bankroll(db)
                stake = prediction.recommended_stake
                
                # Check bankroll availability
                if stake > 0 and br.current_balance >= stake:
                    PaperTrader.place_bet(
                        db=db,
                        match_id=match.id,
                        bookmaker=prediction.best_bookmaker,
                        market_type=prediction.market_type,
                        selection=prediction.selection,
                        odds=prediction.best_odds,
                        stake=stake,
                        prediction_id=prediction.id
                    )
                    auto_bet_placed = True
                    logger.info(
                        f"[AUTO-BET PLACED] {stake:.2f}€ on {match.home_team} vs {match.away_team} "
                        f"(Pick: {prediction.selection} @ {prediction.best_odds:.2f} via {prediction.best_bookmaker})"
                    )
                else:
                    logger.warning(
                        f"[AUTO-BET SKIPPED] Insufficient bankroll ({br.current_balance:.2f}€) for stake {stake:.2f}€"
                    )
            except Exception as e:
                logger.error(f"[AUTO-BET ERROR] Could not place bet: {e}")

        # 2. Discord Notification (with 4-hour deduplication window)
        last_notified = NOTIFIED_CACHE.get(cache_key)
        should_notify = (last_notified is None) or (now - last_notified > timedelta(hours=4))

        if should_notify and settings.DISCORD_WEBHOOK_URL:
            try:
                sent = await DiscordNotifier.notify_value_bet(
                    home_team=match.home_team,
                    away_team=match.away_team,
                    league=match.league,
                    kickoff=match.kickoff,
                    odds_by_bookmaker=odds_by_bookmaker,
                    selection=prediction.selection,
                    best_bookmaker=prediction.best_bookmaker,
                    best_odds=prediction.best_odds,
                    model_prob=prediction.model_prob,
                    fair_odds=prediction.fair_odds,
                    ev_percent=prediction.ev_percent,
                    recommended_stake=prediction.recommended_stake,
                    auto_bet_placed=auto_bet_placed
                )
                if sent:
                    NOTIFIED_CACHE[cache_key] = now
            except Exception as e:
                logger.error(f"[DISCORD ERROR] Failed to send value bet alert: {e}")

        return auto_bet_placed
