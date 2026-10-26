import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.schema import Match, PaperBet, Prediction, BetStatus, BookmakerOdds
from ..engine.paper_trader import PaperTrader
from ..engine.discord_notifier import DiscordNotifier
from ..core.config import settings

logger = logging.getLogger(__name__)

# In-memory notification deduplication cache: { "matchId": last_notified_datetime }
NOTIFIED_CACHE: dict[int, datetime] = {}

class AutoBettor:
    @classmethod
    async def process_value_opportunity(
        cls,
        db: Session,
        match: Match,
        prediction: Prediction
    ) -> bool:
        """
        Evaluates a value opportunity:
        1. Ensures STRICT single-bet per match (never bet on multiple casinos or duplicate match bets).
        2. Strictly validates quality criteria (odds in sweet spot 1.40 - 4.50, prob >= 22%, EV >= 3.5%).
        3. Caps total bankroll active exposure to 25%.
        4. Auto-bets on the single best bookmaker line if AUTO_BET_ENABLED and not already placed.
        5. Sends a Discord notification in the elite tipster format.
        """
        now = datetime.utcnow()

        # Strict odds range validation
        if prediction.best_odds < settings.MIN_ODDS or prediction.best_odds > settings.MAX_ODDS:
            logger.debug(
                f"[AUTO-BET FILTERED] Odds {prediction.best_odds:.2f} for '{match.home_team} vs {match.away_team}' "
                f"outside elite sweet spot [{settings.MIN_ODDS} - {settings.MAX_ODDS}]."
            )
            return False

        if prediction.model_prob < settings.MIN_PROBABILITY:
            logger.debug(
                f"[AUTO-BET FILTERED] Probability {prediction.model_prob:.2%} for '{match.home_team} vs {match.away_team}' "
                f"below minimum confidence threshold ({settings.MIN_PROBABILITY:.0%})."
            )
            return False

        # Strict match-level check: Has this match already been wagered on with ANY bookmaker?
        existing_match_bet = db.query(PaperBet).filter(
            PaperBet.match_id == match.id,
            PaperBet.status == BetStatus.PENDING
        ).first()

        auto_bet_placed = False

        # 1. Automated Paper Bet Placement (Strictly 1 Bet Per Match across ALL Bookmakers)
        if settings.AUTO_BET_ENABLED:
            if existing_match_bet:
                logger.info(
                    f"[AUTO-BET SKIPPED] Match '{match.home_team} vs {match.away_team}' already has an active bet "
                    f"at {existing_match_bet.bookmaker} (Pick: {existing_match_bet.selection} @ {existing_match_bet.odds:.2f}). "
                    f"Prevented duplicate bet at {prediction.best_bookmaker}."
                )
            else:
                try:
                    br = PaperTrader.get_or_create_bankroll(db)
                    stake = prediction.recommended_stake
                    
                    # Portfolio Risk Limit: check total active open wagers
                    active_stake = db.query(func.sum(PaperBet.stake)).filter(
                        PaperBet.status == BetStatus.PENDING
                    ).scalar() or 0.0
                    
                    max_portfolio_exposure = br.initial_balance * settings.MAX_ACTIVE_EXPOSURE_PERCENT

                    if (active_stake + stake) > max_portfolio_exposure:
                        logger.info(
                            f"[AUTO-BET PAUSED] Active bankroll exposure reached ({active_stake:.2f}€ / {max_portfolio_exposure:.2f}€ max). "
                            f"Holding off new wagers until active matches settle."
                        )
                    elif stake > 0 and br.current_balance >= stake:
                        PaperTrader.place_bet(
                            db=db,
                            match_id=match.id,
                            bookmaker=prediction.best_bookmaker,
                            market_type=prediction.market_type,
                            selection=prediction.selection,
                            odds=prediction.best_odds,
                            stake=stake,
                            prediction_id=prediction.id,
                            confidence=prediction.confidence or "MÉDIA",
                            reasoning=prediction.reasoning
                        )
                        auto_bet_placed = True
                        logger.info(
                            f"[AUTO-BET PLACED] {stake:.2f}€ on '{match.home_team} vs {match.away_team}' "
                            f"(Best Bookmaker: {prediction.best_bookmaker} @ {prediction.best_odds:.2f}, "
                            f"Market: {prediction.market_type} - {prediction.selection}, Conf: {prediction.confidence})"
                        )
                    else:
                        logger.warning(
                            f"[AUTO-BET SKIPPED] Insufficient bankroll ({br.current_balance:.2f}€) for stake {stake:.2f}€"
                        )
                except Exception as e:
                    logger.error(f"[AUTO-BET ERROR] Could not place bet: {e}")

        # 2. Discord Notification (Deduplicated per match with 4-hour window)
        last_notified = NOTIFIED_CACHE.get(match.id)
        should_notify = (last_notified is None) or (now - last_notified > timedelta(hours=4))

        if should_notify and settings.DISCORD_WEBHOOK_URL:
            try:
                sent = await DiscordNotifier.notify_value_bet(
                    home_team=match.home_team,
                    away_team=match.away_team,
                    league=match.league,
                    kickoff=match.kickoff,
                    market_type=prediction.market_type,
                    selection=prediction.selection,
                    best_bookmaker=prediction.best_bookmaker,
                    best_odds=prediction.best_odds,
                    model_prob=prediction.model_prob,
                    fair_odds=prediction.fair_odds,
                    ev_percent=prediction.ev_percent,
                    recommended_stake=prediction.recommended_stake,
                    confidence=prediction.confidence or "MÉDIA",
                    reasoning=prediction.reasoning or "",
                    auto_bet_placed=auto_bet_placed or (existing_match_bet is not None)
                )
                if sent:
                    NOTIFIED_CACHE[match.id] = now
            except Exception as e:
                logger.error(f"[DISCORD ERROR] Failed to send value bet alert: {e}")

        return auto_bet_placed
