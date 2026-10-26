from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from datetime import datetime

class ScrapedOddsItem(BaseModel):
    market_type: str  # "1X2", "OVER_UNDER_2_5", "BTTS"
    selection: str    # "1", "X", "2", "OVER", "UNDER", "YES", "NO"
    odds: float

class ScrapedMatch(BaseModel):
    bookmaker: str
    home_team: str
    away_team: str
    league: str
    kickoff: datetime
    odds: list[ScrapedOddsItem]
    raw_data: dict[str, Any] = {}

class BaseBookmakerScraper(ABC):
    @property
    @abstractmethod
    def bookmaker_name(self) -> str:
        pass

    @abstractmethod
    async def fetch_league_matches(self, league_name: str) -> list[ScrapedMatch]:
        pass
