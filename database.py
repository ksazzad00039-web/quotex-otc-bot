import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
import libsql_experimental as libsql

# Dynamic System Path Handling
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from config import DATABASE_FILE, TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("OTC_Enterprise_Quant.Database")
    DATABASE_FILE = os.getenv("DATABASE_FILE", "otc_quant_memory.db")
    TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
    TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


class DatabaseManager:
    """
    Enterprise-Grade Hybrid Database Infrastructure for Quotex OTC Quant Analysis.
    Combines Turso Cloud DB with Local SQLite Fail-Safe Persistence.
    Enforces Strict 1-Hour Timeframe Pattern Matching & Signal Performance Analytics.
    """

    def __init__(self):
        self.local_db_path = DATABASE_FILE
        self.turso_url = TURSO_DATABASE_URL
        self.turso_token = TURSO_AUTH_TOKEN
        self.conn = None

        self._initialize_connection()
        self._bootstrap_schema()

    def _format_turso_url(self, url: str) -> str:
        """
        Converts deprecated libsql:// or wss:// URL schemes to HTTPS
        to prevent protocol handshake errors on cloud platforms like Render.
        """
        if not url:
            return ""
        if url.startswith("libsql://"):
            return url.replace("libsql://", "https://")
        if url.startswith("wss://"):
            return url.replace("wss://", "https://")
        return url

    def _initialize_connection(self) -> None:
        """Establishes fault-tolerant connection between Turso Cloud and Local SQLite."""
        db_dir = os.path.dirname(self.local_db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Database directory created at: '{db_dir}'")
            except Exception as e:
                logger.warning(f"Could not create database directory {db_dir}: {str(e)}")

        # 1. Attempt Turso Cloud DB Connection
        if self.turso_url and self.turso_token:
            formatted_url = self._format_turso_url(self.turso_url)
            try:
                logger.info(f"Connecting to Turso Cloud Database ({formatted_url[:25]}...)...")
                self.conn = libsql.connect(
                    database=formatted_url,
                    auth_token=self.turso_token
                )
                logger.info("Turso Direct Cloud Connection Established Successfully.")
                return
            except Exception as e:
                logger.warning(
                    f"Turso Remote Connection Handshake Failed ({str(e)}). "
                    f"Failing over to Local Isolated SQLite Engine..."
                )

        # 2. Local Engine Fallback
        logger.info(f"Initializing Local SQLite Engine at '{self.local_db_path}'...")
        try:
            self.conn = libsql.connect(database=self.local_db_path)
            logger.info("Local SQLite Connection Ready.")
        except Exception as e:
            logger.critical(f"Critical System Failure: Unable to initialize SQLite Connection: {str(e)}")
            raise e

    def _bootstrap_schema(self) -> None:
        """Initializes optimized relational tables and performance indexes for 1-Hour OTC Trading."""
        try:
            cursor = self.conn.cursor()

            # 1. OTC Pattern Memory Repository
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pattern_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sha256_hash TEXT UNIQUE NOT NULL,
                    timeframe TEXT NOT NULL DEFAULT '1-HOUR',
                    primary_trend TEXT NOT NULL,
                    rejection_zone TEXT NOT NULL,
                    confidence_rating REAL NOT NULL,
                    json_features TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Live Signal Execution History
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signal_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    decision TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    trend_1h TEXT NOT NULL,
                    rejection_1h TEXT NOT NULL,
                    trade_result TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Quant Performance Metrics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_key TEXT UNIQUE NOT NULL,
                    metric_value REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Performance Indexes for Faster Lookups
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_lookup ON pattern_memory(primary_trend, rejection_zone);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_users ON signal_logs(user_id);")

            self.conn.commit()
            logger.info("Database Schema & Institutional Indexes Verified Successfully.")
        except Exception as e:
            logger.error(f"Failed to Bootstrap Database Schema: {str(e)}")

    # ------------------------------------------------------------------
    # Data Query & Insertion Core
    # ------------------------------------------------------------------

    def insert_pattern(self, sha256_hash: str, timeframe: str, data_1h: Dict[str, Any]) -> bool:
        """Stores structured 1-Hour candle screenshot pattern analysis into database memory."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO pattern_memory (sha256_hash, timeframe, primary_trend, rejection_zone, confidence_rating, json_features)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sha256_hash,
                    timeframe.upper(),
                    data_1h.get("primary_trend", "CONSOLIDATION"),
                    data_1h.get("rejection_zone", "NEUTRAL"),
                    float(data_1h.get("confidence", 70.0)),
                    json.dumps(data_1h)
                )
            )
            self.conn.commit()
            logger.info(f"Pattern Hash [{sha256_hash[:8]}] stored successfully.")
            return True
        except Exception as e:
            logger.warning(f"Pattern Record Collision or Insertion Error ({sha256_hash[:8]}): {str(e)}")
            return False

    def query_pattern_statistics(self, trend_1h: str, rejection_1h: str) -> Dict[str, Any]:
        """Queries historical match frequency for current 1-Hour chart setup."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*), AVG(confidence_rating) 
                FROM pattern_memory 
                WHERE primary_trend = ? AND rejection_zone = ?
                """,
                (trend_1h, rejection_1h)
            )
            row = cursor.fetchone()
            match_count = row[0] if row else 0
            avg_confidence = row[1] if row and row[1] else 0.0

            return {
                "matched_records": match_count,
                "historical_avg_confidence": round(avg_confidence, 2)
            }
        except Exception as e:
            logger.error(f"Error querying pattern statistics: {str(e)}")
            return {"matched_records": 0, "historical_avg_confidence": 0.0}

    def log_live_signal(self, user_id: int, signal_data: Dict[str, Any]) -> bool:
        """Logs user trading predictions for backtesting and performance analytics."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO signal_logs (user_id, decision, confidence_score, win_rate, trend_1h, rejection_1h)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    signal_data.get("decision", "HOLD"),
                    float(signal_data.get("confidence", 0.0)),
                    float(signal_data.get("win_rate", 0.0)),
                    signal_data.get("trend_1h", "NEUTRAL"),
                    signal_data.get("rejection_1h", "NEUTRAL")
                )
            )
            self.conn.commit()
            logger.info(f"Signal logged for User ID [{user_id}] | Decision: {signal_data.get('decision')}")
            return True
        except Exception as e:
            logger.error(f"Failed to log signal for user {user_id}: {str(e)}")
            return False

    def get_total_nodes(self) -> int:
        """Returns total historical patterns registered in database memory."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pattern_memory")
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception:
            return 0


# Global Instantiation
db = DatabaseManager()

if __name__ == "__main__":
    print(f"Database Core Initialized Successfully. Total Patterns Stored: {db.get_total_nodes()}")
