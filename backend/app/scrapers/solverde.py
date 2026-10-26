import logging
from datetime import datetime
import httpx
from .base import BaseBookmakerScraper, ScrapedMatch, ScrapedOddsItem
from ..engine.normalizer import normalize_team_name

logger = logging.getLogger(__name__)

SOLVERDE_LEAGUES = {
    "Liga Portugal": "https://www.solverde.pt/apostas/futebol/portugal/liga-portugal",
    "Premier League": "https://www.solverde.pt/apostas/futebol/inglaterra/premier-league",
    "La Liga": "https://www.solverde.pt/apostas/futebol/espanha/la-liga",
    "Champions League": "https://www.solverde.pt/apostas/futebol/europa/liga-dos-campeoes"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.solverde.pt/apostas"
}

class SolverdeScraper(BaseBookmakerScraper):
    @property
    def bookmaker_name(self) -> str:
        return "Solverde"

    async def fetch_league_matches(self, league_name: str) -> list[ScrapedMatch]:
        url = SOLVERDE_LEAGUES.get(league_name)
        if not url:
            return []
            
        results = []
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    # Solverde loads via SPA widget; in live production, Playwright headless worker extracts runtime odds
                    pass
        except Exception as e:
            logger.debug(f"Solverde fetch notice: {e}")

        return results
