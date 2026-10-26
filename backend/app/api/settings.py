from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from ..core.config import settings
from ..engine.discord_notifier import DiscordNotifier
from ..engine.scheduler import execute_betting_cycle

router = APIRouter(prefix="/settings", tags=["Settings & Scheduler"])

class UpdateSettingsRequest(BaseModel):
    auto_bet_enabled: bool | None = None
    discord_webhook_url: str | None = None
    min_ev_threshold: float | None = None

class TestDiscordRequest(BaseModel):
    webhook_url: str | None = None

@router.get("/")
def get_settings():
    """Returns current automation and notification configurations."""
    return {
        "auto_bet_enabled": settings.AUTO_BET_ENABLED,
        "cron_interval_minutes": settings.CRON_INTERVAL_MINUTES,
        "discord_configured": bool(settings.DISCORD_WEBHOOK_URL),
        "discord_webhook_preview": (
            settings.DISCORD_WEBHOOK_URL[:30] + "..." if settings.DISCORD_WEBHOOK_URL else None
        ),
        "min_ev_threshold": settings.MIN_EV_THRESHOLD,
        "kelly_fraction": settings.KELLY_FRACTION,
        "max_bet_percentage": settings.MAX_BET_PERCENTAGE,
        "target_leagues": settings.TARGET_LEAGUES
    }

@router.post("/")
def update_settings(req: UpdateSettingsRequest):
    """Updates auto-betting or Discord webhook preferences dynamically."""
    if req.auto_bet_enabled is not None:
        settings.AUTO_BET_ENABLED = req.auto_bet_enabled
    if req.discord_webhook_url is not None:
        settings.DISCORD_WEBHOOK_URL = req.discord_webhook_url.strip() if req.discord_webhook_url else None
    if req.min_ev_threshold is not None:
        settings.MIN_EV_THRESHOLD = req.min_ev_threshold

    return {
        "message": "Settings updated successfully",
        "auto_bet_enabled": settings.AUTO_BET_ENABLED,
        "discord_configured": bool(settings.DISCORD_WEBHOOK_URL)
    }

@router.post("/test-discord")
async def test_discord_webhook(req: TestDiscordRequest):
    """Sends a test embed message to verify the Discord Webhook connection."""
    url = req.webhook_url or settings.DISCORD_WEBHOOK_URL
    if not url:
        raise HTTPException(status_code=400, detail="No Discord webhook URL provided.")

    success, msg = await DiscordNotifier.send_test_notification(url)
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    return {"message": "Test Discord notification sent successfully!", "detail": msg}

@router.post("/run-cycle")
async def trigger_cycle_now(background_tasks: BackgroundTasks):
    """Runs the 30-minute betting & odds analysis cycle immediately."""
    background_tasks.add_task(execute_betting_cycle)
    return {"message": "30-minute betting inspection cycle initiated in the background."}
