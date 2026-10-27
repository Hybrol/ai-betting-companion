import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from .core.config import settings
from .core.database import Base, engine, SessionLocal
from .models.schema import PaperBet, Match, BetStatus
from .api.router import api_router
from .engine.paper_trader import PaperTrader
from .engine.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    
    # Auto-migrate any new SQLite columns
    try:
        with engine.begin() as conn:
            res = conn.exec_driver_sql("PRAGMA table_info(predictions)").fetchall()
            cols = [r[1] for r in res]
            if "confidence" not in cols:
                conn.exec_driver_sql("ALTER TABLE predictions ADD COLUMN confidence VARCHAR(32) DEFAULT 'MÉDIA'")
            if "reasoning" not in cols:
                conn.exec_driver_sql("ALTER TABLE predictions ADD COLUMN reasoning TEXT")

            res_b = conn.exec_driver_sql("PRAGMA table_info(paper_bets)").fetchall()
            cols_b = [r[1] for r in res_b]
            if "confidence" not in cols_b:
                conn.exec_driver_sql("ALTER TABLE paper_bets ADD COLUMN confidence VARCHAR(32) DEFAULT 'MÉDIA'")
            if "reasoning" not in cols_b:
                conn.exec_driver_sql("ALTER TABLE paper_bets ADD COLUMN reasoning TEXT")
            if "is_multiple" not in cols_b:
                conn.exec_driver_sql("ALTER TABLE paper_bets ADD COLUMN is_multiple BOOLEAN DEFAULT 0")
            if "multiple_legs" not in cols_b:
                conn.exec_driver_sql("ALTER TABLE paper_bets ADD COLUMN multiple_legs TEXT")
    except Exception as e:
        logger.debug(f"Auto-migration note: {e}")

    # Initialize bankroll if empty and clean up any future pending bets
    db = SessionLocal()
    try:
        br = PaperTrader.get_or_create_bankroll(db)

        # Release exposure from any pending bets placed on matches scheduled for future dates
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        future_bets = db.query(PaperBet).join(Match).filter(
            PaperBet.status == BetStatus.PENDING,
            func.date(Match.kickoff) > today_str
        ).all()
        if future_bets:
            refunded_total = 0.0
            for fb in future_bets:
                refunded_total += fb.stake
                br.current_balance += fb.stake
                br.total_staked -= fb.stake
                br.total_bets -= 1
                db.delete(fb)
            db.commit()
            logger.info(
                f"Cleaned up {len(future_bets)} future pending paper bets. "
                f"Refunded {refunded_total:.2f}€ to bankroll for today's matches."
            )
    except Exception as e:
        logger.warning(f"Startup future bets cleanup notice: {e}")
    finally:
        db.close()

    # Automatic Match & Prediction Deduplication
    db_cleanup = SessionLocal()
    try:
        from .engine.normalizer import create_match_key, normalize_team_name, normalize_league_name
        from .models.schema import BookmakerOdds, Prediction
        from collections import defaultdict

        all_matches = db_cleanup.query(Match).all()
        by_canon_key = defaultdict(list)

        for m in all_matches:
            c_key = create_match_key(m.home_team, m.away_team, m.kickoff.isoformat())
            by_canon_key[c_key].append(m)

        for c_key, group in by_canon_key.items():
            if len(group) <= 1:
                m = group[0]
                m.match_key = c_key
                m.home_team = normalize_team_name(m.home_team)
                m.away_team = normalize_team_name(m.away_team)
                m.league = normalize_league_name(m.league)
                continue

            # Group has duplicates! Pick best primary match
            def sort_key(m_item):
                pb_count = db_cleanup.query(PaperBet).filter(PaperBet.match_id == m_item.id).count()
                has_exact_key = 1 if m_item.match_key == c_key else 0
                odds_count = db_cleanup.query(BookmakerOdds).filter(BookmakerOdds.match_id == m_item.id).count()
                return (pb_count, has_exact_key, odds_count, m_item.id)

            group.sort(key=sort_key, reverse=True)
            primary = group[0]
            duplicates = group[1:]

            for dup in duplicates:
                logger.info(f"[DEDUP] Merging duplicate Match #{dup.id} ({dup.home_team} vs {dup.away_team}) into Match #{primary.id}")
                dup.match_key = f"dup_{dup.id}_{c_key}"
                db_cleanup.flush()

                db_cleanup.query(PaperBet).filter(PaperBet.match_id == dup.id).update({"match_id": primary.id})

                dup_odds = db_cleanup.query(BookmakerOdds).filter(BookmakerOdds.match_id == dup.id).all()
                for d_odd in dup_odds:
                    exists = db_cleanup.query(BookmakerOdds).filter(
                        BookmakerOdds.match_id == primary.id,
                        BookmakerOdds.bookmaker == d_odd.bookmaker,
                        BookmakerOdds.market_type == d_odd.market_type,
                        BookmakerOdds.selection == d_odd.selection
                    ).first()
                    if exists:
                        if d_odd.odds > exists.odds:
                            exists.odds = d_odd.odds
                        db_cleanup.delete(d_odd)
                    else:
                        d_odd.match_id = primary.id

                db_cleanup.query(Prediction).filter(Prediction.match_id == dup.id).delete()
                db_cleanup.delete(dup)
                db_cleanup.flush()

            primary.match_key = c_key
            primary.home_team = normalize_team_name(primary.home_team)
            primary.away_team = normalize_team_name(primary.away_team)
            primary.league = normalize_league_name(primary.league)
            db_cleanup.flush()

        db_cleanup.commit()
        logger.info("[DEDUP] Automatic match deduplication completed.")
    except Exception as e:
        db_cleanup.rollback()
        logger.error(f"[DEDUP] Error during match deduplication: {e}")
    finally:
        db_cleanup.close()
        
    # Start the 30-minute recurring scheduler
    logger.info(f"Starting 30-minute betting inspection scheduler (interval: {settings.CRON_INTERVAL_MINUTES}m)...")
    start_scheduler()
    
    yield
    
    logger.info("Shutting down background scheduler...")
    stop_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Enable CORS for full-stack Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "auto_bet_enabled": settings.AUTO_BET_ENABLED,
        "cron_interval_minutes": settings.CRON_INTERVAL_MINUTES,
        "discord_configured": bool(settings.DISCORD_WEBHOOK_URL),
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }
