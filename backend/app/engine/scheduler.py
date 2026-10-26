import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from ..core.config import settings
from ..core.database import SessionLocal
from ..models.schema import Match, BookmakerOdds, Prediction, MatchStatus
from ..engine.normalizer import create_match_key
from ..engine.predictor import MatchPredictor
from ..engine.value_finder import ValueFinder
from ..engine.paper_trader import PaperTrader
from ..engine.auto_bettor import AutoBettor
from ..scrapers.betclic import BetclicScraper
from ..scrapers.betano import BetanoScraper
from ..scrapers.solverde import SolverdeScraper

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def execute_betting_cycle(target_league: str | None = None):
    """
    Core inspection cycle executed every 30 minutes:
    1. Scrapes odds from Betclic, Betano, and Solverde across leagues.
    2. Runs AI Poisson + market consensus predictive modeling.
    3. Identifies +EV value bets with Kelly stakes.
    4. Auto-places simulated paper wagers on top opportunities.
    5. Dispatches Discord notifications with side-by-side odds across each casino.
    """
    logger.info("=== [CRON] Starting 30-Minute AI Betting Inspection Cycle ===")
    db: Session = SessionLocal()

    try:
        scrapers = [BetclicScraper(), BetanoScraper(), SolverdeScraper()]
        leagues = [target_league] if target_league else settings.TARGET_LEAGUES

        br = PaperTrader.get_or_create_bankroll(db)
        current_bankroll = br.current_balance

        total_new_opportunities = 0
        total_auto_bets = 0

        for league in leagues:
            logger.info(f"[CRON] Inspecting {league}...")
            all_scraped = []
            for scraper in scrapers:
                try:
                    matches = await scraper.fetch_league_matches(league)
                    all_scraped.extend(matches)
                except Exception as e:
                    logger.error(f"[CRON] Scraper {scraper.bookmaker_name} failed on {league}: {e}")

            for sm in all_scraped:
                m_key = create_match_key(sm.home_team, sm.away_team, sm.kickoff.isoformat())
                match = db.query(Match).filter(Match.match_key == m_key).first()

                if not match:
                    match = Match(
                        match_key=m_key,
                        home_team=sm.home_team,
                        away_team=sm.away_team,
                        league=league,
                        kickoff=sm.kickoff,
                        status=MatchStatus.SCHEDULED
                    )
                    db.add(match)
                    db.flush()

                # Upsert odds
                for odd_item in sm.odds:
                    existing_odd = db.query(BookmakerOdds).filter(
                        BookmakerOdds.match_id == match.id,
                        BookmakerOdds.bookmaker == sm.bookmaker,
                        BookmakerOdds.market_type == odd_item.market_type,
                        BookmakerOdds.selection == odd_item.selection
                    ).first()

                    if existing_odd:
                        existing_odd.odds = odd_item.odds
                        existing_odd.timestamp = datetime.utcnow()
                    else:
                        new_odd = BookmakerOdds(
                            match_id=match.id,
                            bookmaker=sm.bookmaker,
                            market_type=odd_item.market_type,
                            selection=odd_item.selection,
                            odds=odd_item.odds
                        )
                        db.add(new_odd)

                db.commit()

                # Gather all 1X2 odds for AI prediction and comparison
                all_odds = db.query(BookmakerOdds).filter(
                    BookmakerOdds.match_id == match.id,
                    BookmakerOdds.market_type == "1X2"
                ).all()

                odds_by_sel: dict[str, list[tuple[str, float]]] = {"1": [], "X": [], "2": []}
                odds_by_bookie: dict[str, dict[str, float]] = {}

                for o in all_odds:
                    odds_by_sel.setdefault(o.selection, []).append((o.bookmaker, o.odds))
                    odds_by_bookie.setdefault(o.bookmaker, {})[o.selection] = o.odds

                multi_1x2 = [
                    [b_odds.get("1", 0), b_odds.get("X", 0), b_odds.get("2", 0)]
                    for b_odds in odds_by_bookie.values()
                    if "1" in b_odds and "X" in b_odds and "2" in b_odds
                ]

                # Run AI goal expectation & market consensus model
                probs = MatchPredictor.estimate_probabilities(
                    league, match.home_team, match.away_team, multi_1x2
                )

                # Scan for +EV value opportunities
                values = ValueFinder.scan_for_value(
                    match.id, match.home_team, match.away_team, match.league,
                    odds_by_sel, probs, current_bankroll
                )

                # Update prediction table
                db.query(Prediction).filter(Prediction.match_id == match.id).delete()
                
                # Sort values by highest Expected Value (+EV)
                values.sort(key=lambda x: x.ev_percent, reverse=True)

                best_prediction = None
                for v in values:
                    p = Prediction(
                        match_id=match.id,
                        market_type=v.market_type,
                        selection=v.selection,
                        model_prob=v.model_prob,
                        fair_odds=v.fair_odds,
                        best_bookmaker=v.best_bookmaker,
                        best_odds=v.best_odds,
                        ev_percent=v.ev_percent,
                        kelly_stake_percent=v.kelly_stake_percent,
                        recommended_stake=v.recommended_stake
                    )
                    db.add(p)
                    db.flush()
                    if best_prediction is None:
                        best_prediction = p

                    total_new_opportunities += 1

                db.commit()

                # Strictly process ONLY the single highest-value pick for this match to avoid duplicate gambling
                if best_prediction:
                    auto_placed = await AutoBettor.process_value_opportunity(
                        db=db,
                        match=match,
                        prediction=best_prediction,
                        odds_by_bookmaker=odds_by_bookie
                    )
                    if auto_placed:
                        total_auto_bets += 1

        logger.info(
            f"=== [CRON] Cycle Completed! Found {total_new_opportunities} +EV opportunities, "
            f"Placed {total_auto_bets} automated paper bets ==="
        )
    except Exception as e:
        logger.error(f"[CRON] Error during inspection cycle: {e}", exc_info=True)
    finally:
        db.close()

def start_scheduler():
    """Starts the 30-minute background cron job."""
    if not scheduler.running:
        trigger = IntervalTrigger(minutes=settings.CRON_INTERVAL_MINUTES)
        scheduler.add_job(
            execute_betting_cycle,
            trigger=trigger,
            id="betting_companion_cron",
            name="30-min Betting Companion Cron",
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"Background scheduler started: running every {settings.CRON_INTERVAL_MINUTES} minutes.")

def stop_scheduler():
    """Stops the scheduler safely."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped.")
