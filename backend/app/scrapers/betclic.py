import re
import json
import logging
from datetime import datetime
import httpx
from dateutil import parser
from .base import BaseBookmakerScraper, ScrapedMatch, ScrapedOddsItem
from ..engine.normalizer import normalize_team_name

logger = logging.getLogger(__name__)

BETCLIC_LEAGUES = {
    # Principais Ligas Europeias
    "Premier League": "https://www.betclic.pt/futebol-s1/premier-league-c4",
    "La Liga": "https://www.betclic.pt/futebol-s1/la-liga-c7",
    "Serie A": "https://www.betclic.pt/futebol-s1/serie-a-c6",
    "Bundesliga": "https://www.betclic.pt/futebol-s1/bundesliga-c5",
    "Ligue 1": "https://www.betclic.pt/futebol-s1/ligue-1-mcdonalds-c3",
    "Liga Portugal": "https://www.betclic.pt/futebol-s1/liga-portugal-c32",
    "Champions League": "https://www.betclic.pt/futebol-s1/liga-dos-campeoes-c8",
    "Europa League": "https://www.betclic.pt/futebol-s1/liga-europa-c9",
    "Conference League": "https://www.betclic.pt/futebol-s1/liga-conferencia-c3822",
    # Ligas Árabes
    "Saudi Pro League": "https://www.betclic.pt/futebol-s1/arabia-saudita-primeira-divisao-c89",
    "UAE Pro League": "https://www.betclic.pt/futebol-s1/emirados-arabes-unidos-pro-league-c214",
    "Qatar Stars League": "https://www.betclic.pt/futebol-s1/catar-stars-league-c215",
    # Todas as outras competições do dia na Betclic
    "Geral Futebol": "https://www.betclic.pt/futebol-s1",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"
}

class BetclicScraper(BaseBookmakerScraper):
    @property
    def bookmaker_name(self) -> str:
        return "Betclic"

    async def fetch_league_matches(self, league_name: str) -> list[ScrapedMatch]:
        url = BETCLIC_LEAGUES.get(league_name)
        if not url:
            # Check if generic football page can be used
            url = BETCLIC_LEAGUES["Geral Futebol"]

        results = []
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.error(f"Betclic returned status {resp.status_code} for {league_name}")
                    return []

                html = resp.text
                m = re.search(r'<script id="ng-state" type="application/json">(.*?)</script>', html, re.DOTALL)
                if not m:
                    logger.warning(f"Could not find ng-state for Betclic {league_name}")
                    return []

                state = json.loads(m.group(1))
                matches_data = []
                for k, v in state.items():
                    if "grpc" in k and isinstance(v, dict):
                        payload = v.get("response", {}).get("payload", {})
                        if isinstance(payload, dict) and "matches" in payload:
                            matches_data = payload.get("matches", [])
                            if matches_data:
                                break

                for match in matches_data:
                    contestants = match.get("contestants", [])
                    if len(contestants) < 2:
                        name_parts = match.get("name", "").split(" - ")
                        if len(name_parts) == 2:
                            home_team = name_parts[0].strip()
                            away_team = name_parts[1].strip()
                        else:
                            continue
                    else:
                        home_team = contestants[0].get("name", "").strip()
                        away_team = contestants[1].get("name", "").strip()

                    match_date_str = match.get("matchDateUtc")
                    if not match_date_str:
                        continue
                    kickoff = parser.isoparse(match_date_str)

                    comp_name = match.get("competition", {}).get("name") or league_name

                    odds_items: list[ScrapedOddsItem] = []
                    market = match.get("market", {})
                    selections = market.get("mainSelections", [])

                    if len(selections) >= 3:
                        o1 = float(selections[0].get("odds", 0.0))
                        ox = float(selections[1].get("odds", 0.0))
                        o2 = float(selections[2].get("odds", 0.0))

                        if o1 > 1.0 and ox > 1.0 and o2 > 1.0:
                            # 1X2 market
                            odds_items.append(ScrapedOddsItem(market_type="1X2", selection="1", odds=o1))
                            odds_items.append(ScrapedOddsItem(market_type="1X2", selection="X", odds=ox))
                            odds_items.append(ScrapedOddsItem(market_type="1X2", selection="2", odds=o2))

                            # Synthetic Dupla Chance from 1X2 bookmaker margin
                            o_1x = round((o1 * ox) / (o1 + ox), 2)
                            o_x2 = round((ox * o2) / (ox + o2), 2)
                            o_12 = round((o1 * o2) / (o1 + o2), 2)

                            if o_1x > 1.05:
                                odds_items.append(ScrapedOddsItem(market_type="DOUBLE_CHANCE", selection="1X", odds=o_1x))
                            if o_x2 > 1.05:
                                odds_items.append(ScrapedOddsItem(market_type="DOUBLE_CHANCE", selection="X2", odds=o_x2))
                            if o_12 > 1.05:
                                odds_items.append(ScrapedOddsItem(market_type="DOUBLE_CHANCE", selection="12", odds=o_12))

                    if odds_items:
                        results.append(ScrapedMatch(
                            bookmaker=self.bookmaker_name,
                            home_team=normalize_team_name(home_team),
                            away_team=normalize_team_name(away_team),
                            league=comp_name,
                            kickoff=kickoff,
                            odds=odds_items,
                            raw_data={"betclic_match_id": match.get("matchId")}
                        ))
        except Exception as e:
            logger.error(f"Error scraping Betclic for {league_name}: {e}")

        return results
