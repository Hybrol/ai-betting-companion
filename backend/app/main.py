import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.database import Base, engine, SessionLocal
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
    except Exception as e:
        logger.debug(f"Auto-migration note: {e}")

    # Initialize bankroll if empty
    db = SessionLocal()
    try:
        PaperTrader.get_or_create_bankroll(db)
    finally:
        db.close()
        
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
