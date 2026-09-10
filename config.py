import os
import sys
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

# ------------------------------------------------------------------
# Enterprise Logging Architecture Setup
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

logger = logging.getLogger("OTC_Enterprise_Quant.Config")


# ------------------------------------------------------------------
# Centralized Quant Enterprise Configuration Engine
# ------------------------------------------------------------------
@dataclass(frozen=True)
class EnterpriseConfig:
    """
    Centralized Configuration System for Quotex OTC Quantitative Bot.
    Enforces strict typing, environment dynamic loading, smart resolution,
    and institutional risk management rules.
    """

    # --------------------------------------------------------------
    # 1. Telegram Integration Architecture
    # --------------------------------------------------------------
    # Auto-resolves TELEGRAM_BOT_TOKEN or BOT_TOKEN to prevent deploy crashes
    TELEGRAM_BOT_TOKEN: Optional[str] = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    )

    # --------------------------------------------------------------
    # 2. AI Multimodal Vision Engine (Gemini Core)
    # --------------------------------------------------------------
    GEMINI_API_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    GEMINI_MODEL: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    )

    # --------------------------------------------------------------
    # 3. Database & Storage Infrastructure (Turso Cloud + SQLite)
    # --------------------------------------------------------------
    DATABASE_FILE: str = field(
        default_factory=lambda: os.getenv("DATABASE_FILE", "otc_quant_memory.db")
    )
    TURSO_DATABASE_URL: Optional[str] = field(
        default_factory=lambda: os.getenv("TURSO_DATABASE_URL")
    )
    TURSO_AUTH_TOKEN: Optional[str] = field(
        default_factory=lambda: os.getenv("TURSO_AUTH_TOKEN")
    )

    # --------------------------------------------------------------
    # 4. Networking & Web Diagnostics Server
    # --------------------------------------------------------------
    PORT: int = field(
        default_factory=lambda: int(os.getenv("PORT", "8080"))
    )
    HOST: str = field(
        default_factory=lambda: os.getenv("HOST", "0.0.0.0")
    )

    # --------------------------------------------------------------
    # 5. Institutional Trading Rules & Strategy Thresholds
    # --------------------------------------------------------------
    TIMEFRAME_POLICY: str = "1-HOUR ONLY"
    STRICT_OTC_MODE: bool = True
    
    # Combined score, liquidity, and pattern match thresholds
    MIN_COMBINED_SCORE: float = field(
        default_factory=lambda: float(os.getenv("MIN_COMBINED_SCORE", "70.0"))
    )
    MIN_LIQUIDITY_SCORE: float = field(
        default_factory=lambda: float(os.getenv("MIN_LIQUIDITY_SCORE", "55.0"))
    )
    MIN_PATTERN_SCORE: float = field(
        default_factory=lambda: float(os.getenv("MIN_PATTERN_SCORE", "65.0"))
    )

    # Risk Engine Rules
    KELLY_RISK_FRACTION: float = 0.5  # Fractional Half-Kelly Execution Strategy
    DEFAULT_PAYOUT_RATE: float = 0.85

    # --------------------------------------------------------------
    # 6. Safety Flags & System Modes
    # --------------------------------------------------------------
    RESEARCH_MODE: bool = field(
        default_factory=lambda: os.getenv("RESEARCH_MODE", "1") == "1"
    )
    PAPER_TRADING: bool = field(
        default_factory=lambda: os.getenv("PAPER_TRADING", "1") == "1"
    )
    LIVE_TRADING: bool = field(
        default_factory=lambda: os.getenv("LIVE_TRADING", "0") == "1"
    )

    # --------------------------------------------------------------
    # Validation & System Pre-Flight Diagnostics
    # --------------------------------------------------------------
    def validate_environment(self) -> None:
        """Executes systematic system checks before initializing the main engine."""
        logger.info("Initializing Enterprise Pre-Flight System Diagnostics...")

        # 1. Telegram Validation
        if not self.TELEGRAM_BOT_TOKEN:
            logger.critical("SECURITY ALERT: 'TELEGRAM_BOT_TOKEN' (or 'BOT_TOKEN') environment variable is NOT set!")
        else:
            logger.info("Telegram Bot Token Authentication: LOADED SUCCESSFULLY")

        # 2. Gemini AI Engine Validation
        if not self.GEMINI_API_KEY:
            logger.critical("AI CORE ALERT: 'GEMINI_API_KEY' environment variable is NOT set!")
        else:
            logger.info(f"Gemini Multimodal AI Core ({self.GEMINI_MODEL}): LOADED SUCCESSFULLY")

        # 3. Local Storage Directory Check
        db_dir = os.path.dirname(self.DATABASE_FILE)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Storage directory initialized: '{db_dir}'")
            except Exception as e:
                logger.error(f"Failed to initialize storage directory '{db_dir}': {str(e)}")

        # 4. Database Sync Mode Check
        if self.TURSO_DATABASE_URL and self.TURSO_AUTH_TOKEN:
            logger.info("Database Engine Mode: TURSO HYBRID CLOUD DB (Persistent Cloud Sync Active)")
        else:
            logger.info("Database Engine Mode: LOCAL SQLITE FALLBACK")

        # 5. Trading Policy Audit
        logger.info(f"Timeframe Enforcement: [ {self.TIMEFRAME_POLICY} ] Strategy Active")
        logger.info(f"System Operational Status -> Research: {self.RESEARCH_MODE} | Paper: {self.PAPER_TRADING} | Live: {self.LIVE_TRADING}")

    def export_summary(self) -> Dict[str, Any]:
        """Returns structured metadata for web diagnostics endpoint."""
        return {
            "timeframe_policy": self.TIMEFRAME_POLICY,
            "min_combined_score": self.MIN_COMBINED_SCORE,
            "min_pattern_score": self.MIN_PATTERN_SCORE,
            "min_liquidity_score": self.MIN_LIQUIDITY_SCORE,
            "gemini_model": self.GEMINI_MODEL,
            "turso_enabled": bool(self.TURSO_DATABASE_URL and self.TURSO_AUTH_TOKEN),
            "research_mode": self.RESEARCH_MODE,
            "paper_trading": self.PAPER_TRADING,
            "live_trading": self.LIVE_TRADING,
        }


# ------------------------------------------------------------------
# Global Instantiation & Compatibility Exports
# ------------------------------------------------------------------
config = EnterpriseConfig()
config.validate_environment()

# Dynamic Top-Level Export Variables (Ensures 100% Backwards Compatibility with All Modules)
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
GEMINI_API_KEY = config.GEMINI_API_KEY
GEMINI_MODEL = config.GEMINI_MODEL
DATABASE_FILE = config.DATABASE_FILE
TURSO_DATABASE_URL = config.TURSO_DATABASE_URL
TURSO_AUTH_TOKEN = config.TURSO_AUTH_TOKEN
PORT = config.PORT
HOST = config.HOST

MIN_COMBINED_SCORE = config.MIN_COMBINED_SCORE
MIN_LIQUIDITY_SCORE = config.MIN_LIQUIDITY_SCORE
MIN_PATTERN_SCORE = config.MIN_PATTERN_SCORE

RESEARCH_MODE = config.RESEARCH_MODE
PAPER_TRADING = config.PAPER_TRADING
LIVE_TRADING = config.LIVE_TRADING


