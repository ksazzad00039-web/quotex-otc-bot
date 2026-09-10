import os
import sys
import logging
from dataclasses import dataclass
from typing import Optional

# ------------------------------------------------------------------
# Institutional Logging Configuration Setup
# ------------------------------------------------------------------
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("OTC_Enterprise_Quant")


# ------------------------------------------------------------------
# System Enterprise Configuration Engine
# ------------------------------------------------------------------
@dataclass(frozen=True)
class EnterpriseConfig:
    """
    Centralized Institutional Configuration Data Structure.
    Enforces strict typing, environment dynamic loading, and safety checks.
    """
    # Telegram Security Architecture
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Multimodal Vision Gemini Engine
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Turso Cloud SQLite & Local Storage Infrastructure
    DATABASE_FILE: str = os.getenv("DATABASE_FILE", "data/research.db")
    TURSO_DATABASE_URL: Optional[str] = os.getenv("TURSO_DATABASE_URL")
    TURSO_AUTH_TOKEN: Optional[str] = os.getenv("TURSO_AUTH_TOKEN")

    # Web Server & Keep-Alive Settings
    PORT: int = int(os.getenv("PORT", "10000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Trading Execution Strategy Parameters
    TIMEFRAME_RULE: str = "1-HOUR"
    STRICT_OTC_MODE: bool = True
    MIN_CONFIDENCE_THRESHOLD: float = 65.0
    KELLY_RISK_FRACTION: float = 0.5  # Half-Kelly Policy
    DEFAULT_PAYOUT_RATE: float = 0.85

    # System Safety & Environment Flags
    RESEARCH_MODE: bool = os.getenv("RESEARCH_MODE", "1") == "1"
    PAPER_TRADING: bool = os.getenv("PAPER_TRADING", "1") == "1"
    LIVE_TRADING: bool = os.getenv("LIVE_TRADING", "0") == "1"

    def validate_environment(self) -> None:
        """Runs pre-flight validation on essential enterprise configurations."""
        logger.info("Initializing Enterprise Pre-Flight System Validation...")

        if not self.TELEGRAM_BOT_TOKEN:
            logger.critical("SECURITY ALERT: 'TELEGRAM_BOT_TOKEN' environment variable is NOT set!")
        else:
            logger.info("Telegram Bot Authentication Token: LOADED")

        if not self.GEMINI_API_KEY:
            logger.critical("AI CORE ALERT: 'GEMINI_API_KEY' environment variable is NOT set!")
        else:
            logger.info(f"Gemini Multimodal Model Engine ({self.GEMINI_MODEL}): LOADED")

        # Local Data Directory Assurance
        db_dir = os.path.dirname(self.DATABASE_FILE)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Local storage directory created successfully at: '{db_dir}'")
            except Exception as e:
                logger.error(f"Failed to create local storage directory '{db_dir}': {str(e)}")

        # Turso Cloud Connection Check
        if self.TURSO_DATABASE_URL and self.TURSO_AUTH_TOKEN:
            logger.info("Database Mode: TURSO CLOUD SQLITE (Persistent Sync Active)")
        else:
            logger.info("Database Mode: LOCAL SQLITE FALLBACK (Data lost on container wipe if disk unmounted)")

        logger.info(f"System Mode -> Research: {self.RESEARCH_MODE} | Paper: {self.PAPER_TRADING} | Live: {self.LIVE_TRADING}")


# ------------------------------------------------------------------
# Global Instantiation
# ------------------------------------------------------------------
config = EnterpriseConfig()
config.validate_environment()

# Dynamic Top-Level Export Variables (Maintains Full Backwards Compatibility)
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
GEMINI_API_KEY = config.GEMINI_API_KEY
GEMINI_MODEL = config.GEMINI_MODEL
DATABASE_FILE = config.DATABASE_FILE
TURSO_DATABASE_URL = config.TURSO_DATABASE_URL
TURSO_AUTH_TOKEN = config.TURSO_AUTH_TOKEN
PORT = config.PORT
RESEARCH_MODE = config.RESEARCH_MODE
PAPER_TRADING = config.PAPER_TRADING
LIVE_TRADING = config.LIVE_TRADING

