import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Portuguese AI Betting Companion"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./backend/data/betting_companion.db"
    
    # Paper Trading Defaults
    INITIAL_BANKROLL: float = 1000.0  # Fictional 1,000.00 EUR
    MIN_EV_THRESHOLD: float = 0.03    # 3% positive expected value minimum
    KELLY_FRACTION: float = 0.25      # Quarter-Kelly for risk mitigation
    MAX_BET_PERCENTAGE: float = 0.05  # Max 5% bankroll per single wager
    
    # Scraping Configuration
    POLL_INTERVAL_MINUTES: int = 15
    TARGET_LEAGUES: list[str] = [
        "Liga Portugal",
        "Premier League",
        "La Liga",
        "Serie A",
        "Bundesliga",
        "Champions League"
    ]
    
    class Config:
        case_sensitive = True

settings = Settings()
