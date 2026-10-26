import logging
from datetime import datetime
import httpx
from ..core.config import settings

logger = logging.getLogger(__name__)

class DiscordNotifier:
    @staticmethod
    async def send_webhook_message(embed: dict, content: str = "") -> bool:
        webhook_url = settings.DISCORD_WEBHOOK_URL
        if not webhook_url:
            logger.info("Discord Webhook URL not configured. Skipping Discord notification.")
            return False

        payload = {
            "username": "AI Betting Companion PT",
            "avatar_url": "https://img.icons8.com/color/96/football2--v1.png",
            "content": content,
            "embeds": [embed]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(webhook_url, json=payload)
                if res.status_code in (200, 204):
                    logger.info("Successfully sent Discord webhook notification.")
                    return True
                else:
                    logger.error(f"Failed to send Discord webhook: HTTP {res.status_code} - {res.text}")
                    return False
        except Exception as e:
            logger.error(f"Error dispatching Discord webhook: {e}")
            return False

    @classmethod
    async def notify_value_bet(
        cls,
        home_team: str,
        away_team: str,
        league: str,
        kickoff: datetime,
        odds_by_bookmaker: dict[str, dict[str, float]], # {"Betclic": {"1": 8.75, "X": 5.4, "2": 1.31}, "Betano": {...}}
        selection: str,
        best_bookmaker: str,
        best_odds: float,
        model_prob: float,
        fair_odds: float,
        ev_percent: float,
        recommended_stake: float,
        auto_bet_placed: bool = False
    ) -> bool:
        # Format odds table comparison across all casinos
        comparison_lines = []
        for bookie, odds in odds_by_bookmaker.items():
            o1 = f"{odds.get('1', 0.0):.2f}" if "1" in odds else "-"
            ox = f"{odds.get('X', 0.0):.2f}" if "X" in odds else "-"
            o2 = f"{odds.get('2', 0.0):.2f}" if "2" in odds else "-"
            
            icon = "🔴" if "betclic" in bookie.lower() else "🟠" if "betano" in bookie.lower() else "🟢"
            comparison_lines.append(f"{icon} **{bookie}** — `1:` **{o1}** | `X:` **{ox}** | `2:` **{o2}**")

        odds_comparison_text = "\n".join(comparison_lines) if comparison_lines else "Odds comparison not available"

        kickoff_str = kickoff.strftime("%Y-%m-%d %H:%M UTC")

        embed = {
            "title": f"🎯 High Value Bet Alert: {home_team} vs {away_team}",
            "description": (
                f"**Competition:** `{league}`\n"
                f"**Kickoff:** `{kickoff_str}`\n\n"
                f"### 🎰 Odds Comparison by Casino\n"
                f"{odds_comparison_text}\n\n"
                f"### 💡 AI Value Recommendation\n"
                f"• **Recommended Pick:** Selection **`{selection}`**\n"
                f"• **Best Market Odds:** **`{best_odds:.2f}`** at **{best_bookmaker}**\n"
                f"• **Fair Model Odds:** **`{fair_odds:.2f}`** ({model_prob * 100:.1f}% True Prob)\n"
                f"• **Expected Value (+EV):** **`+{ev_percent:.1f}%`**\n"
                f"• **Recommended Stake:** **`{recommended_stake:.2f} €`** (Fractional Kelly)\n"
            ),
            "color": 0x10b981, # Emerald green
            "fields": [
                {
                    "name": "⚡ Auto-Bet Status",
                    "value": "✅ **Simulated Paper Bet Placed!** Fictional stake deducted." if auto_bet_placed else "ℹ️ Manual bet simulation available on dashboard.",
                    "inline": False
                }
            ],
            "footer": {
                "text": "Portuguese AI Betting Companion • 30-min Cron Monitor"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        return await cls.send_webhook_message(embed=embed)

    @classmethod
    async def send_test_notification(cls, webhook_url: str | None = None) -> tuple[bool, str]:
        url = webhook_url or settings.DISCORD_WEBHOOK_URL
        if not url:
            return False, "No webhook URL provided"

        embed = {
            "title": "✅ AI Betting Companion: Discord Alerts Active",
            "description": "Your 30-minute betting opportunity cron monitor has successfully connected to this channel!",
            "color": 0x10b981,
            "fields": [
                {"name": "Status", "value": "🟢 Online & Monitoring", "inline": True},
                {"name": "Target Bookmakers", "value": "Betclic.pt • Betano.pt • Solverde.pt", "inline": True},
                {"name": "Scan Frequency", "value": f"Every {settings.CRON_INTERVAL_MINUTES} minutes", "inline": True},
            ],
            "footer": {
                "text": "Portuguese AI Betting Companion"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        payload = {
            "username": "AI Betting Companion PT",
            "embeds": [embed]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code in (200, 204):
                    return True, "Notification sent successfully!"
                else:
                    return False, f"HTTP Error {res.status_code}: {res.text}"
        except Exception as e:
            return False, str(e)
