import logging
import json
import urllib.request
import asyncio
from datetime import datetime
from .base import BaseBookmakerScraper, ScrapedMatch, ScrapedOddsItem
from ..engine.normalizer import normalize_team_name

logger = logging.getLogger(__name__)

BETANO_LEAGUE_IDS = {
    "Premier League": "1",
    "La Liga": "5",
    "Serie A": "1635",
    "Bundesliga": "216",
    "Ligue 1": "215",
    "Liga Portugal": "17083",
    "Champions League": "16839",
    "Europa League": "16840",
    "Conference League": "10016",
    "Saudi Pro League": "18925",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
    "Referer": "https://www.betano.pt/sport/futebol/"
}

def _fetch_betano_sync(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

class BetanoScraper(BaseBookmakerScraper):
    @property
    def bookmaker_name(self) -> str:
        return "Betano"

    async def fetch_league_matches(self, league_name: str) -> list[ScrapedMatch]:
        league_id = BETANO_LEAGUE_IDS.get(league_name)
        if not league_id:
            logger.debug(f"League '{league_name}' not in Betano mapping.")
            return []

        url = f"https://www.betano.pt/api/sports/FOOT/hot/trending/leagues/{league_id}/events"
        results = []
        try:
            data = await asyncio.to_thread(_fetch_betano_sync, url)
            events = data.get("data", {}).get("events", [])

            for ev in events:
                name = ev.get("name", "")
                parts = name.split(" - ")
                if len(parts) < 2:
                    continue

                home_raw = parts[0].strip()
                away_raw = parts[1].strip()

                start_time_ms = ev.get("startTime")
                if not start_time_ms:
                    continue
                kickoff = datetime.fromtimestamp(start_time_ms / 1000.0)

                odds_items: list[ScrapedOddsItem] = []
                markets = ev.get("markets", [])

                for m in markets:
                    m_name = m.get("name", "").lower()

                    # 1X2 / Resultado Final
                    if "resultado final" in m_name:
                        for sel in m.get("selections", []):
                            s_name = sel.get("name", "").strip().upper()
                            price = float(sel.get("price", 0.0))
                            if price > 1.0:
                                odds_items.append(ScrapedOddsItem(market_type="1X2", selection=s_name, odds=price))

                    # Dupla Chance / Hipótese Dupla
                    elif "hipótese dupla" in m_name or "hipotese dupla" in m_name:
                        for sel in m.get("selections", []):
                            s_name = sel.get("name", "").strip().upper()
                            price = float(sel.get("price", 0.0))
                            if price > 1.0 and s_name in ("1X", "X2", "12"):
                                odds_items.append(ScrapedOddsItem(market_type="DOUBLE_CHANCE", selection=s_name, odds=price))

                    # Total de Golos Mais/Menos
                    elif "total de golos mais/menos" in m_name and "1ª parte" not in m_name:
                        for sel in m.get("selections", []):
                            s_name = sel.get("name", "").lower()
                            price = float(sel.get("price", 0.0))
                            if price <= 1.0:
                                continue

                            if "2.5" in s_name:
                                sel_type = "OVER" if "mais" in s_name else "UNDER"
                                odds_items.append(ScrapedOddsItem(market_type="OVER_UNDER_2_5", selection=sel_type, odds=price))
                            elif "1.5" in s_name:
                                sel_type = "OVER" if "mais" in s_name else "UNDER"
                                odds_items.append(ScrapedOddsItem(market_type="OVER_UNDER_1_5", selection=sel_type, odds=price))
                            elif "3.5" in s_name:
                                sel_type = "OVER" if "mais" in s_name else "UNDER"
                                odds_items.append(ScrapedOddsItem(market_type="OVER_UNDER_3_5", selection=sel_type, odds=price))

                    # Ambas as Equipas Marcam (BTTS)
                    elif "ambas as equipas marcam" in m_name:
                        for sel in m.get("selections", []):
                            s_name = sel.get("name", "").lower()
                            price = float(sel.get("price", 0.0))
                            if price > 1.0:
                                if "sim" in s_name:
                                    odds_items.append(ScrapedOddsItem(market_type="BTTS", selection="YES", odds=price))
                                elif "n" in s_name:
                                    odds_items.append(ScrapedOddsItem(market_type="BTTS", selection="NO", odds=price))

                if odds_items:
                    results.append(ScrapedMatch(
                        bookmaker=self.bookmaker_name,
                        home_team=normalize_team_name(home_raw),
                        away_team=normalize_team_name(away_raw),
                        league=league_name,
                        kickoff=kickoff,
                        odds=odds_items,
                        raw_data={"betano_event_id": ev.get("id")}
                    ))
        except Exception as e:
            logger.error(f"Error scraping Betano for {league_name}: {e}")

        return results
