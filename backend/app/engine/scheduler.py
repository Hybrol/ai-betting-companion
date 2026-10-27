import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..core.config import settings
from ..core.database import SessionLocal
from ..models.schema import Match, BookmakerOdds, Prediction, MatchStatus, PaperBet, BetStatus
from ..engine.normalizer import create_match_key, get_canonical_stem
from ..engine.predictor import MatchPredictor
from ..engine.value_finder import ValueFinder, ValueOpportunity
from ..engine.paper_trader import PaperTrader
from ..engine.auto_bettor import AutoBettor
from ..engine.discord_notifier import DiscordNotifier
from ..scrapers.betclic import BetclicScraper
from ..scrapers.betano import BetanoScraper
from ..scrapers.solverde import SolverdeScraper

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Multiple notification cache: tracks signature and timestamp of last dispatched multiple
LAST_MULTIPLE_NOTIFICATION: dict = {
    "signature": None,
    "date": None,
    "timestamp": None
}

def get_multiple_signature(multiple: dict) -> str:
    legs = multiple.get("legs", [])
    stubs = []
    for leg in legs:
        match_str = leg.get("match", "")
        parts = match_str.split(" vs ")
        if len(parts) == 2:
            m_key = f"{get_canonical_stem(parts[0])}_vs_{get_canonical_stem(parts[1])}"
        else:
            m_key = get_canonical_stem(match_str)
        market = leg.get("market", "")
        selection = leg.get("selection", "")
        stubs.append(f"{m_key}:{market}:{selection}")
    stubs.sort()
    return "__".join(stubs)

async def execute_betting_cycle(target_league: str | None = None):
    """
    Elite Quantitative Betting Cycle (runs every 30 minutes):
    1. Scrapes legal Portuguese sportsbooks (Betclic, Betano, Solverde) across European & Arab leagues.
    2. Runs Dixon-Coles goal expectation modeling and consensus market de-vigging.
    3. Evaluates multi-market edges (1X2, Dupla Chance, Over/Under 1.5/2.5/3.5, Ambas Marcam).
    4. Enforces professional odds bounds (1.40 - 4.50, min 22% prob, +3.5% EV min).
    5. Deduplicates bets (max 1 bet per match across all houses) with 25% portfolio exposure ceiling.
    6. Assembles daily curated Múltipla de Valor and dispatches rich Portuguese alerts.
    """
    logger.info("=== [CRON] Starting Elite AI Betting Inspection Cycle ===")
    db: Session = SessionLocal()

    try:
        scrapers = [BetclicScraper(), BetanoScraper(), SolverdeScraper()]
        leagues = [target_league] if target_league else settings.TARGET_LEAGUES

        br = PaperTrader.get_or_create_bankroll(db)
        current_bankroll = br.current_balance

        all_cycle_opportunities: list[ValueOpportunity] = []
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
                    logger.debug(f"[CRON] Scraper {scraper.bookmaker_name} note on {league}: {e}")

            for sm in all_scraped:
                m_key = create_match_key(sm.home_team, sm.away_team, sm.kickoff.isoformat())
                match = db.query(Match).filter(Match.match_key == m_key).first()

                if not match:
                    match = Match(
                        match_key=m_key,
                        home_team=sm.home_team,
                        away_team=sm.away_team,
                        league=sm.league or league,
                        kickoff=sm.kickoff,
                        status=MatchStatus.SCHEDULED
                    )
                    db.add(match)
                    db.flush()

                # Upsert all scraped odds
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

                # Retrieve all match odds across all markets
                all_odds = db.query(BookmakerOdds).filter(
                    BookmakerOdds.match_id == match.id
                ).all()

                odds_by_market: dict[str, dict[str, list[tuple[str, float]]]] = {}
                odds_by_bookie_1x2: dict[str, dict[str, float]] = {}

                for o in all_odds:
                    odds_by_market.setdefault(o.market_type, {}).setdefault(o.selection, []).append((o.bookmaker, o.odds))
                    if o.market_type == "1X2":
                        odds_by_bookie_1x2.setdefault(o.bookmaker, {})[o.selection] = o.odds

                multi_1x2 = [
                    [b_odds.get("1", 0), b_odds.get("X", 0), b_odds.get("2", 0)]
                    for b_odds in odds_by_bookie_1x2.values()
                    if "1" in b_odds and "X" in b_odds and "2" in b_odds
                ]

                # Run Dixon-Coles goal expectation & consensus model across markets
                model_results = MatchPredictor.compute_all_market_probabilities(
                    match.league, match.home_team, match.away_team, multi_1x2
                )
                metrics = model_results.get("metrics", {})

                # Scan for genuine +EV value across all markets
                values = ValueFinder.scan_for_value(
                    match_id=match.id,
                    home_team=match.home_team,
                    away_team=match.away_team,
                    league=match.league,
                    odds_by_market=odds_by_market,
                    model_probs_by_market=model_results,
                    current_bankroll=current_bankroll,
                    metrics=metrics
                )

                # Update prediction table
                db.query(Prediction).filter(Prediction.match_id == match.id).delete()

                # Sort by highest expected value (+EV)
                values.sort(key=lambda x: (1 if x.confidence == "ALTA" else 0, x.ev_percent), reverse=True)

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
                        recommended_stake=v.recommended_stake,
                        confidence=v.confidence,
                        reasoning=v.reasoning
                    )
                    db.add(p)
                    db.flush()
                    if best_prediction is None:
                        best_prediction = p

                    all_cycle_opportunities.append(v)
                    total_new_opportunities += 1

                db.commit()

                # Process strictly the single highest-value pick for this match to avoid duplicate match gambling
                # Only auto-bet on matches occurring TODAY that have not started yet
                now_utc = datetime.utcnow()
                if best_prediction and match.kickoff.date() == now_utc.date() and match.kickoff > now_utc:
                    auto_placed = await AutoBettor.process_value_opportunity(
                        db=db,
                        match=match,
                        prediction=best_prediction
                    )
                    if auto_placed:
                        total_auto_bets += 1

                # Yield control to event loop to keep API responsive
                await asyncio.sleep(0.01)

        # Curated Múltipla de Valor (strictly using today's upcoming matches)
        now_utc = datetime.utcnow()
        today_str = now_utc.strftime("%Y-%m-%d")
        today_preds = db.query(Prediction).join(Match).filter(
            func.date(Match.kickoff) == today_str,
            Match.kickoff >= now_utc,
            Prediction.ev_percent >= 3.5,
            Prediction.best_odds >= 1.35,
            Prediction.best_odds <= 2.80
        ).order_by(Prediction.ev_percent.desc()).all()

        today_opps = [
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
            for p in today_preds
        ]

        curated_multiple = ValueFinder.build_curated_multiple(
            opportunities=today_opps,
            max_legs=3,
            current_bankroll=current_bankroll
        )

        if curated_multiple:
            # 1. Enrich every leg with comprehensive pre-match statistical analysis
            from .team_analyzer import TeamStatsAnalyzer
            curated_multiple = await TeamStatsAnalyzer.enrich_multiple(curated_multiple)

            now_utc = datetime.utcnow()
            today_str = now_utc.strftime("%Y-%m-%d")

            # 2. Place curated multiple in Paper Trading (Strictly 1 multiple per day)
            if settings.AUTO_BET_ENABLED:
                existing_today_multiple = db.query(PaperBet).filter(
                    PaperBet.is_multiple == True,
                    func.date(PaperBet.placed_at) == today_str
                ).first()

                if not existing_today_multiple:
                    try:
                        placed_mb = PaperTrader.place_multiple_bet(
                            db=db,
                            curated_multiple=curated_multiple
                        )
                        logger.info(
                            f"[AUTO-BET MULTIPLE PLACED] {placed_mb.stake:.2f}€ on curated multiple #{placed_mb.id} "
                            f"({curated_multiple['legs_count']} legs @ {placed_mb.odds:.2f}, potential payout: {placed_mb.potential_payout:.2f}€)"
                        )
                        total_auto_bets += 1
                    except Exception as e:
                        logger.error(f"[AUTO-BET MULTIPLE ERROR] Could not place multiple: {e}")

            # 3. Discord Webhook Notification with deduplication
            if settings.DISCORD_WEBHOOK_URL:
                multi_sig = get_multiple_signature(curated_multiple)

                last_sig = LAST_MULTIPLE_NOTIFICATION.get("signature")
                last_date = LAST_MULTIPLE_NOTIFICATION.get("date")
                last_time = LAST_MULTIPLE_NOTIFICATION.get("timestamp")

                is_same_signature = (multi_sig == last_sig)
                is_same_day = (last_date == today_str)

                should_notify_multiple = False
                if not is_same_day:
                    should_notify_multiple = True
                elif not is_same_signature:
                    # Selections changed today: allow re-dispatch only if at least 2 hours elapsed
                    if last_time is None or (now_utc - last_time).total_seconds() >= 7200:
                        should_notify_multiple = True
                    else:
                        logger.info(
                            f"[DISCORD SKIPPED] Curated multiple changed but cooldown active "
                            f"({int((now_utc - last_time).total_seconds())}s / 7200s)."
                        )
                else:
                    logger.info(
                        f"[DISCORD SKIPPED] Curated multiple already dispatched for today ({today_str}) "
                        f"with identical selections: {multi_sig}."
                    )

                if should_notify_multiple:
                    sent = await DiscordNotifier.notify_curated_multiple(curated_multiple)
                    if sent:
                        LAST_MULTIPLE_NOTIFICATION["signature"] = multi_sig
                        LAST_MULTIPLE_NOTIFICATION["date"] = today_str
                        LAST_MULTIPLE_NOTIFICATION["timestamp"] = now_utc
                        logger.info(f"[DISCORD] Curated multiple successfully dispatched: {multi_sig}")

        logger.info(
            f"=== [CRON] Elite Cycle Completed! Found {total_new_opportunities} quality +EV opportunities, "
            f"Placed {total_auto_bets} automated paper bets ==="
        )
    except Exception as e:
        logger.error(f"[CRON] Error during inspection cycle: {e}", exc_info=True)
    finally:
        db.close()

def start_scheduler():
    """Starts the 30-minute background cron job and 1-minute live score settler."""
    if not scheduler.running:
        trigger = IntervalTrigger(minutes=settings.CRON_INTERVAL_MINUTES)
        scheduler.add_job(
            execute_betting_cycle,
            trigger=trigger,
            id="betting_companion_cron",
            name="30-min Betting Companion Cron",
            replace_existing=True
        )

        # 60-second live score tracking and automated paper bet settlement
        from .live_score_resolver import LiveScoreResolver
        live_trigger = IntervalTrigger(seconds=60)
        scheduler.add_job(
            LiveScoreResolver.check_and_resolve_live_matches,
            trigger=live_trigger,
            id="live_score_resolver",
            name="1-min ESPN Live Score & Auto-Settler",
            replace_existing=True
        )

        scheduler.start()
        logger.info(
            f"Background scheduler started: 30-minute betting cycle & 60-second ESPN live score auto-settler active."
        )

def stop_scheduler():
    """Stops the scheduler safely."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped.")
