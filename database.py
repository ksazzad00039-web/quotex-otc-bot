import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List
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
    DATABASE_FILE = os.getenv("DATABASE_FILE", "data/research.db")
    TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
    TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


class DatabaseManager:
    """
    Enterprise-Grade Hybrid Database Infrastructure.
    Provides Cloud Turso libSQL Synchronization with Local SQLite Resilient Fallback.
    Optimized for High-Precision 1-Hour OTC Market Pattern Intelligence.
    """

    def __init__(self):
        self.local_db_path = DATABASE_FILE
        self.turso_url = TURSO_DATABASE_URL
        self.turso_token = TURSO_AUTH_TOKEN
        self.conn = None

        self._initialize_connection()
        self._bootstrap_schema()

    def _initialize_connection(self) -> None:
        """Establishes robust cloud or local database connections."""
        db_dir = os.path.dirname(self.local_db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        try:
            if self.turso_url and self.turso_token:
                logger.info("Initializing Turso Hybrid Cloud Sync Engine...")
                self.conn = libsql.connect(
                    database=self.local_db_path,
                    sync_url=self.turso_url,
                    auth_token=self.turso_token
                )
                self.conn.sync()
                logger.info("Turso Cloud Sync Connected & Synchronized Successfully.")
            else:
                logger.info(f"Connecting to Local SQLite Persistent Database at '{self.local_db_path}'...")
                self.conn = libsql.connect(database=self.local_db_path)
        except Exception as e:
            logger.error(f"Primary Database Connection Error: {str(e)}. Falling back to isolated SQLite...")
            self.conn = libsql.connect(database=self.local_db_path)

    def _sync_to_cloud(self) -> None:
        """Triggers asynchronous synchronization with Turso Cloud."""
        if self.turso_url and self.turso_token and self.conn:
            try:
                self.conn.sync()
            except Exception as e:
                logger.warning(f"Turso Sync Exception: {str(e)}")

    def _bootstrap_schema(self) -> None:
        """Initializes relational tables and performance indexes for 1-Hour OTC Quants."""
        try:
            cursor = self.conn.cursor()

            # 1. Institutional Pattern Memory Repository
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

            # 2. Historical Trading Signal Execution Logs
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

            # 3. Optimization Indexes for Ultra-Fast Retrieval
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_lookup ON pattern_memory(primary_trend, rejection_zone);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_users ON signal_logs(user_id);")

            self.conn.commit()
            self._sync_to_cloud()
            logger.info("Database Schema & Indexes Verified Successfully.")
        except Exception as e:
            logger.error(f"Failed to Bootstrap Database Schema: {str(e)}")

    # ------------------------------------------------------------------
    # Core Quant Operations
    # ------------------------------------------------------------------

    def insert_pattern(self, sha256_hash: str, timeframe: str, data_1h: Dict[str, Any]) -> bool:
        """Stores structured 1-Hour candle screenshot analysis into database memory."""
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
            self._sync_to_cloud()
            logger.info(f"Pattern memory saved: Hash {sha256_hash[:8]} | Timeframe: {timeframe}")
            return True
        except Exception as e:
            logger.warning(f"Pattern Hash Collision or Save Error ({sha256_hash[:8]}): {str(e)}")
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
        """Logs user predictions for operational analysis."""
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
            self._sync_to_cloud()
            return True
        except Exception as e:
            logger.error(f"Failed to log live signal: {str(e)}")
            return False

    def get_total_nodes(self) -> int:
        """Returns total historical patterns registered in database memory."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pattern_memory")
            return cursor.fetchone()[0]
        except Exception:
            return 0


if __name__ == "__main__":
    db = DatabaseManager()
    print(f"Database Core Ready. Total Memory Nodes: {db.get_total_nodes()}")

