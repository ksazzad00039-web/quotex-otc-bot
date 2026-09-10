import os
import logging

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger("OTC_Quant_Engine")

# Authentication Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Infrastructure & System
DATABASE_FILE = os.getenv("DATABASE_FILE", "data/research.db")
DATABASE_WAL_MODE = int(os.getenv("DATABASE_WAL_MODE", "1"))
PORT = int(os.getenv("PORT", "10000"))
TZ = os.getenv("TZ", "Asia/Dhaka")

# Image & Analysis Limits
MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
ALLOW_DUPLICATE_SCREENSHOTS = int(os.getenv("ALLOW_DUPLICATE_SCREENSHOTS", "0"))
VISION_TIMEOUT_SECONDS = int(os.getenv("VISION_TIMEOUT_SECONDS", "60"))
VISION_MAX_RETRIES = int(os.getenv("VISION_MAX_RETRIES", "3"))

# Quant Statistical Rules
MIN_PATTERN_SAMPLES = int(os.getenv("MIN_PATTERN_SAMPLES", "30"))
MIN_HISTORICAL_FREQUENCY = float(os.getenv("MIN_HISTORICAL_FREQUENCY", "0.80"))

user_sessions = {}

