import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Portuguese AI Betting Companion"
    VERSION: str = "1.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'data', 'betting_companion.db')}")
    
    # Paper Trading & Quantitative Value Bounds
    INITIAL_BANKROLL: float = 1000.0   # Fictional 1,000.00 EUR
    MIN_EV_THRESHOLD: float = 0.035    # 3.5% positive expected value minimum
    MIN_ODDS: float = 1.40             # Minimum odds (eliminates low-value short odds traps)
    MAX_ODDS: float = 4.50             # Maximum odds (eliminates high-variance lottery underdogs)
    MIN_PROBABILITY: float = 0.22      # Minimum model probability (ensures genuine statistical support)
    KELLY_FRACTION: float = 0.20       # Conservative 1/5th Kelly criterion for controlled variance
    MAX_BET_PERCENTAGE: float = 0.04   # Max 4% bankroll per single wager
    MAX_ACTIVE_EXPOSURE_PERCENT: float = 0.25  # Max 25% bankroll in active pending wagers
    
    # Automation & Cron
    AUTO_BET_ENABLED: bool = True      # Automatically place simulated bets on good opportunities
    CRON_INTERVAL_MINUTES: int = 30    # 30-minute recurring inspection
    DISCORD_WEBHOOK_URL: str | None = os.getenv("DISCORD_WEBHOOK_URL", None)
    RESPONSIBLE_GAMBLING_MSG: str = "Aposta com responsabilidade (+18, Linha SICAD 1414)"
    
    # Priority & Monitored Football Leagues
    TARGET_LEAGUES: list[str] = [
        # Principais Ligas Europeias
        "Premier League",
        "La Liga",
        "Serie A",
        "Bundesliga",
        "Ligue 1",
        "Liga Portugal",
        "Champions League",
        "Europa League",
        "Conference League",
        # Principais Ligas Árabes de Primeiro Nível
        "Saudi Pro League",
        "UAE Pro League",
        "Qatar Stars League"
    ]
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
