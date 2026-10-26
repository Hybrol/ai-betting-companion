import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from ..core.config import settings
from ..engine.discord_notifier import DiscordNotifier
from ..engine.scheduler import execute_betting_cycle

router = APIRouter(prefix="/settings", tags=["Settings & Scheduler"])

def _persist_settings_to_env():
    """Writes updated configuration to the .env file so it persists across service restarts."""
    env_path = os.path.join(settings.BASE_DIR, ".env")
    lines = []
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            lines = []

    env_map = {
        "AUTO_BET_ENABLED": str(settings.AUTO_BET_ENABLED),
        "DISCORD_WEBHOOK_URL": settings.DISCORD_WEBHOOK_URL or "",
        "MIN_EV_THRESHOLD": str(settings.MIN_EV_THRESHOLD),
    }

    written_keys = set()
    new_lines = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in env_map:
                new_lines.append(f"{k}={env_map[k]}\n")
                written_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in env_map.items():
        if k not in written_keys:
            new_lines.append(f"{k}={v}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception:
        pass

class UpdateSettingsRequest(BaseModel):
    auto_bet_enabled: bool | None = None
    discord_webhook_url: str | None = None
    min_ev_threshold: float | None = None

class TestDiscordRequest(BaseModel):
    webhook_url: str | None = None

@router.get("")
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

@router.post("")
@router.post("/")
def update_settings(req: UpdateSettingsRequest):
    """Updates auto-betting or Discord webhook preferences dynamically."""
    if req.auto_bet_enabled is not None:
        settings.AUTO_BET_ENABLED = req.auto_bet_enabled
    if req.discord_webhook_url is not None:
        settings.DISCORD_WEBHOOK_URL = req.discord_webhook_url.strip() if req.discord_webhook_url else None
    if req.min_ev_threshold is not None:
        settings.MIN_EV_THRESHOLD = req.min_ev_threshold

    _persist_settings_to_env()

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
