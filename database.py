import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List

import libsql_experimental as libsql


# ============================================================
# PATH
# ============================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

if CURRENT_DIR not in sys.path:
    sys.path.insert(
        0,
        CURRENT_DIR
    )


# ============================================================
# CONFIG
# ============================================================

try:

    from config import (
        DATABASE_FILE,
        TURSO_DATABASE_URL,
        TURSO_AUTH_TOKEN,
        logger,
    )

except ImportError:

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s - "
            "%(name)s - "
            "%(levelname)s - "
            "%(message)s"
        ),
    )

    logger = logging.getLogger(
        "LiquidityResearchBot.Database"
    )

    DATABASE_FILE = os.getenv(
        "DATABASE_FILE",
        "data/research.db",
    )

    TURSO_DATABASE_URL = os.getenv(
        "TURSO_DATABASE_URL"
    )

    TURSO_AUTH_TOKEN = os.getenv(
        "TURSO_AUTH_TOKEN"
    )


# ============================================================
# DATABASE MANAGER
# ============================================================

class DatabaseManager:
    """
    Historical Liquidity Research Database.

    Stores:

    - 1D / 1H chart observations
    - Liquidity events
    - Liquidity zones
    - Candle anatomy
    - Research bias
    - Historical outcomes
    - Session information
    - Research statistics

    This database does NOT store:
    - stake recommendations
    - Kelly sizing
    - real-money execution
    - guaranteed predictions
    """


    # ========================================================
    # INIT
    # ========================================================

    def __init__(self):

        self.local_db_path = (
            DATABASE_FILE
        )

        self.turso_url = (
            TURSO_DATABASE_URL
        )

        self.turso_token = (
            TURSO_AUTH_TOKEN
        )

        self.conn = None

        self.using_turso = False

        self._initialize_connection()

        self._bootstrap_schema()


    # ========================================================
    # TURSO URL
    # ========================================================

    def _format_turso_url(
        self,
        url: Optional[str],
    ) -> str:

        if not url:
            return ""

        url = url.strip()

        if url.startswith(
            "libsql://"
        ):

            return url.replace(
                "libsql://",
                "https://",
                1,
            )

        if url.startswith(
            "wss://"
        ):

            return url.replace(
                "wss://",
                "https://",
                1,
            )

        return url


    # ========================================================
    # CONNECTION
    # ========================================================

    def _initialize_connection(
        self,
    ) -> None:

        # ----------------------------------------------------
        # Local directory
        # ----------------------------------------------------

        db_dir = os.path.dirname(
            self.local_db_path
        )

        if (
            db_dir
            and not os.path.exists(db_dir)
        ):

            try:

                os.makedirs(
                    db_dir,
                    exist_ok=True,
                )

                logger.info(
                    "Database directory created: %s",
                    db_dir,
                )

            except Exception as exc:

                logger.warning(
                    "Could not create database directory: %s",
                    exc,
                )


        # ----------------------------------------------------
        # Turso
        # ----------------------------------------------------

        if (
            self.turso_url
            and self.turso_token
        ):

            formatted_url = (
                self._format_turso_url(
                    self.turso_url
                )
            )

            try:

                logger.info(
                    "Connecting to Turso..."
                )

                self.conn = (
                    libsql.connect(
                        database=formatted_url,
                        auth_token=self.turso_token,
                    )
                )

                self.using_turso = True

                logger.info(
                    "Turso connection established."
                )

                return

            except Exception as exc:

                logger.warning(
                    "Turso connection failed: %s",
                    exc,
                )

                self.conn = None


        # ----------------------------------------------------
        # Local SQLite fallback
        # ----------------------------------------------------

        logger.info(
            "Using local SQLite database: %s",
            self.local_db_path,
        )

        try:

            self.conn = (
                libsql.connect(
                    database=self.local_db_path
                )
            )

            self.using_turso = False

            logger.info(
                "Local SQLite connection established."
            )

        except Exception as exc:

            logger.critical(
                "Database initialization failed: %s",
                exc,
                exc_info=True,
            )

            raise


    # ========================================================
    # EXECUTE HELPER
    # ========================================================

    def _execute(
        self,
        sql: str,
        params: tuple = (),
        commit: bool = False,
    ):

        cursor = self.conn.cursor()

        cursor.execute(
            sql,
            params,
        )

        if commit:
            self.conn.commit()

        return cursor


    # ========================================================
    # SCHEMA
    # ========================================================

    def _bootstrap_schema(
        self,
    ) -> None:

        try:

            cursor = self.conn.cursor()


            # =================================================
            # CHART ANALYSIS
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                chart_analysis (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    user_id INTEGER,

                    image_hash TEXT NOT NULL,

                    timeframe TEXT NOT NULL,

                    asset_pair TEXT,

                    visual_quality TEXT,

                    primary_structure TEXT,

                    research_bias TEXT,

                    liquidity_event TEXT,

                    liquidity_side TEXT,

                    previous_high TEXT,

                    previous_low TEXT,

                    swing_high TEXT,

                    swing_low TEXT,

                    equal_highs TEXT,

                    equal_lows TEXT,

                    range_high TEXT,

                    range_low TEXT,

                    internal_liquidity TEXT,

                    external_liquidity TEXT,

                    sweep_observation TEXT,

                    rejection_observation TEXT,

                    breakout_observation TEXT,

                    candle_anatomy TEXT,

                    liquidity_zones TEXT,

                    market_behaviour TEXT,

                    research_notes TEXT,

                    raw_json TEXT,

                    created_at
                        TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE (
                        image_hash,
                        timeframe
                    )
                )
                """
            )


            # =================================================
            # HISTORICAL OUTCOME
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                historical_outcomes (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    analysis_id INTEGER,

                    user_id INTEGER,

                    actual_outcome TEXT NOT NULL,

                    bars_forward INTEGER,

                    notes TEXT,

                    created_at
                        TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (
                        analysis_id
                    )
                    REFERENCES chart_analysis(id)
                )
                """
            )


            # =================================================
            # RESEARCH SESSIONS
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                research_sessions (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    user_id INTEGER NOT NULL,

                    session_key TEXT UNIQUE,

                    status TEXT DEFAULT 'OPEN',

                    started_at
                        TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP,

                    locked_at TIMESTAMP
                )
                """
            )


            # =================================================
            # SYSTEM EVENTS
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                audit_events (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    user_id INTEGER,

                    event_type TEXT NOT NULL,

                    event_data TEXT,

                    created_at
                        TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


            # =================================================
            # INDEXES
            # =================================================

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_chart_timeframe
                ON chart_analysis(timeframe)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_chart_bias
                ON chart_analysis(research_bias)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_liquidity_event
                ON chart_analysis(liquidity_event)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_chart_user
                ON chart_analysis(user_id)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_outcome_analysis
                ON historical_outcomes(analysis_id)
                """
            )


            self.conn.commit()

            logger.info(
                "Liquidity research database schema ready."
            )

        except Exception as exc:

            logger.error(
                "Schema bootstrap failed: %s",
                exc,
                exc_info=True,
            )

            raise


    # ========================================================
    # INSERT CHART ANALYSIS
    # ========================================================

    def insert_chart_analysis(
        self,
        user_id: int,
        image_hash: str,
        analysis: Dict[str, Any],
    ) -> Optional[int]:

        try:

            timeframe = str(
                analysis.get(
                    "timeframe",
                    "UNKNOWN",
                )
            ).upper()

            cursor = self.conn.cursor()

            cursor.execute(
                """
                INSERT OR IGNORE INTO
                chart_analysis (

                    user_id,
                    image_hash,
                    timeframe,
                    asset_pair,
                    visual_quality,
                    primary_structure,
                    research_bias,
                    liquidity_event,
                    liquidity_side,
                    previous_high,
                    previous_low,
                    swing_high,
                    swing_low,
                    equal_highs,
                    equal_lows,
                    range_high,
                    range_low,
                    internal_liquidity,
                    external_liquidity,
                    sweep_observation,
                    rejection_observation,
                    breakout_observation,
                    candle_anatomy,
                    liquidity_zones,
                    market_behaviour,
                    research_notes,
                    raw_json

                )

                VALUES (

                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,

                (
                    user_id,

                    image_hash,

                    timeframe,

                    analysis.get(
                        "asset_pair",
                        "UNKNOWN",
                    ),

                    analysis.get(
                        "visual_quality",
                        "UNKNOWN",
                    ),

                    analysis.get(
                        "primary_structure",
                        "UNCLEAR",
                    ),

                    analysis.get(
                        "research_bias",
                        "SKIP",
                    ),

                    analysis.get(
                        "liquidity_event",
                        "UNCLEAR",
                    ),

                    analysis.get(
                        "liquidity_side",
                        "NONE",
                    ),

                    analysis.get(
                        "previous_high",
                        "NOT_VISIBLE",
                    ),

                    analysis.get(
                        "previous_low",
                        "NOT_VISIBLE",
                    ),

                    analysis.get(
                        "swing_high",
                        "NOT_VISIBLE",
                    ),

                    analysis.get(
                        "swing_low",
                        "NOT_VISIBLE",
                    ),

                    analysis.get(
                        "equal_highs",
                        "NOT_VISIBLE",
                    ),

                    analysis.get(
                        "equal_lows",
                        "NOT_VISIBLE",
                    ),

                    analysis.get(
                        "range_high",
                        "NOT_VISIBLE",
                    ),

                    analysis.get(
                        "range_low",
                        "NOT_VISIBLE",
                    ),

                    analysis.get(
                        "internal_liquidity",
                        "UNCLEAR",
                    ),

                    analysis.get(
                        "external_liquidity",
                        "UNCLEAR",
                    ),

                    analysis.get(
                        "sweep_observation",
                        "",
                    ),

                    analysis.get(
                        "rejection_observation",
                        "",
                    ),

                    analysis.get(
                        "breakout_observation",
                        "",
                    ),

                    json.dumps(
                        analysis.get(
                            "candle_anatomy",
                            {},
                        ),
                        ensure_ascii=False,
                    ),

                    json.dumps(
                        analysis.get(
                            "liquidity_zones",
                            [],
                        ),
                        ensure_ascii=False,
                    ),

                    analysis.get(
                        "market_behaviour",
                        "UNCLEAR",
                    ),

                    json.dumps(
                        analysis.get(
                            "research_notes",
                            [],
                        ),
                        ensure_ascii=False,
                    ),

                    json.dumps(
                        analysis,
                        ensure_ascii=False,
                    ),
                ),
            )

            self.conn.commit()

            # ------------------------------------------------
            # Get ID
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM chart_analysis
                WHERE image_hash = ?
                  AND timeframe = ?
                LIMIT 1
                """,
                (
                    image_hash,
                    timeframe,
                ),
            )

            row = cursor.fetchone()

            analysis_id = (
                int(row[0])
                if row
                else None
            )

            logger.info(
                "Chart analysis stored | id=%s | tf=%s",
                analysis_id,
                timeframe,
            )

            return analysis_id

        except Exception as exc:

            logger.error(
                "Chart analysis insertion failed: %s",
                exc,
                exc_info=True,
            )

            return None


    # ========================================================
    # COMPATIBILITY: OLD insert_pattern
    # ========================================================

    def insert_pattern(
        self,
        sha256_hash: str,
        timeframe: str,
        data_1h: Dict[str, Any],
    ) -> bool:

        analysis = dict(
            data_1h
        )

        analysis[
            "timeframe"
        ] = timeframe

        analysis_id = (
            self.insert_chart_analysis(
                user_id=0,
                image_hash=sha256_hash,
                analysis=analysis,
            )
        )

        return analysis_id is not None


    # ========================================================
    # GET TOTAL NODES
    # ========================================================

    def get_total_nodes(
        self,
    ) -> int:

        try:

            cursor = self.conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM chart_analysis
                """
            )

            row = cursor.fetchone()

            return (
                int(row[0])
                if row
                else 0
            )

        except Exception as exc:

            logger.error(
                "get_total_nodes failed: %s",
                exc,
            )

            return 0


    # ========================================================
    # GET ANALYSIS BY HASH
    # ========================================================

    def get_analysis_by_hash(
        self,
        image_hash: str,
        timeframe: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        try:

            cursor = self.conn.cursor()

            if timeframe:

                cursor.execute(
                    """
                    SELECT raw_json
                    FROM chart_analysis
                    WHERE image_hash = ?
                      AND timeframe = ?
                    LIMIT 1
                    """,
                    (
                        image_hash,
                        timeframe.upper(),
                    ),
                )

            else:

                cursor.execute(
                    """
                    SELECT raw_json
                    FROM chart_analysis
                    WHERE image_hash = ?
                    LIMIT 1
                    """,
                    (image_hash,),
                )

            row = cursor.fetchone()

            if not row:
                return None

            try:

                return json.loads(
                    row[0]
                )

            except Exception:

                return {
                    "raw_json": row[0]
                }

        except Exception as exc:

            logger.error(
                "Hash lookup failed: %s",
                exc,
            )

            return None


    # ========================================================
    # PATTERN / LIQUIDITY STATISTICS
    # ========================================================

    def query_pattern_statistics(
        self,
        trend_1h: str,
        rejection_1h: str,
    ) -> Dict[str, Any]:

        try:

            cursor = self.conn.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    research_bias
                FROM chart_analysis
                WHERE primary_structure = ?
                  AND rejection_observation LIKE ?
                GROUP BY research_bias
                """,
                (
                    trend_1h,
                    f"%{rejection_1h}%",
                ),
            )

            rows = cursor.fetchall()

            distribution = {}

            total = 0

            for row in rows:

                count = int(
                    row[0]
                )

                bias = str(
                    row[1]
                )

                distribution[
                    bias
                ] = count

                total += count

            return {
                "matched_records":
                    total,

                "bias_distribution":
                    distribution,
            }

        except Exception as exc:

            logger.error(
                "Pattern statistics failed: %s",
                exc,
            )

            return {
                "matched_records": 0,
                "bias_distribution": {},
            }


    # ========================================================
    # LIQUIDITY EVENT STATISTICS
    # ========================================================

    def get_liquidity_statistics(
        self,
        timeframe: Optional[str] = None,
    ) -> Dict[str, Any]:

        try:

            cursor = self.conn.cursor()

            if timeframe:

                cursor.execute(
                    """
                    SELECT
                        liquidity_event,
                        COUNT(*)
                    FROM chart_analysis
                    WHERE timeframe = ?
                    GROUP BY liquidity_event
                    ORDER BY COUNT(*) DESC
                    """,
                    (
                        timeframe.upper(),
                    ),
                )

            else:

                cursor.execute(
                    """
                    SELECT
                        liquidity_event,
                        COUNT(*)
                    FROM chart_analysis
                    GROUP BY liquidity_event
                    ORDER BY COUNT(*) DESC
                    """
                )

            rows = cursor.fetchall()

            return {
                str(row[0]):
                    int(row[1])
                for row in rows
            }

        except Exception as exc:

            logger.error(
                "Liquidity statistics failed: %s",
                exc,
            )

            return {}


    # ========================================================
    # RECORD HISTORICAL OUTCOME
    # ========================================================

    def record_outcome(
        self,
        user_id: int,
        outcome: str,
        analysis_id: Optional[int] = None,
        bars_forward: Optional[int] = None,
        notes: str = "",
    ) -> bool:

        try:

            outcome = str(
                outcome
            ).upper()

            allowed = {
                "BULLISH",
                "BEARISH",
                "MIXED",
                "FLAT",
                "UNKNOWN",
            }

            if outcome not in allowed:

                outcome = "UNKNOWN"

            cursor = self.conn.cursor()

            cursor.execute(
                """
                INSERT INTO
                historical_outcomes (

                    analysis_id,
                    user_id,
                    actual_outcome,
                    bars_forward,
                    notes

                )

                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    user_id,
                    outcome,
                    bars_forward,
                    notes,
                ),
            )

            self.conn.commit()

            logger.info(
                "Historical outcome recorded: %s",
                outcome,
            )

            return True

        except Exception as exc:

            logger.error(
                "Outcome recording failed: %s",
                exc,
                exc_info=True,
            )

            return False


    # ========================================================
    # COMPATIBILITY: OLD log_live_signal
    # ========================================================

    def log_live_signal(
        self,
        user_id: int,
        signal_data: Dict[str, Any],
    ) -> bool:

        """
        Backward-compatible method.

        The old live-signal table is intentionally not used.
        We record the classification as a research event instead.
        """

        try:

            cursor = self.conn.cursor()

            cursor.execute(
                """
                INSERT INTO audit_events (
                    user_id,
                    event_type,
                    event_data
                )
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    "RESEARCH_CLASSIFICATION",
                    json.dumps(
                        signal_data,
                        ensure_ascii=False,
                    ),
                ),
            )

            self.conn.commit()

            return True

        except Exception as exc:

            logger.error(
                "Research event logging failed: %s",
                exc,
            )

            return False


    # ========================================================
    # AUDIT EVENT
    # ========================================================

    def log_event(
        self,
        user_id: Optional[int],
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> bool:

        try:

            cursor = self.conn.cursor()

            cursor.execute(
                """
                INSERT INTO audit_events (
                    user_id,
                    event_type,
                    event_data
                )
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    event_type,
                    json.dumps(
                        event_data or {},
                        ensure_ascii=False,
                    ),
                ),
            )

            self.conn.commit()

            return True

        except Exception as exc:

            logger.error(
                "Audit event failed: %s",
                exc,
            )

            return False


    # ========================================================
    # SESSION
    # ========================================================

    def create_session(
        self,
        user_id: int,
        session_key: str,
    ) -> bool:

        try:

            cursor = self.conn.cursor()

            cursor.execute(
                """
                INSERT OR IGNORE INTO
                research_sessions (
                    user_id,
                    session_key,
                    status
                )
                VALUES (?, ?, 'OPEN')
                """,
                (
                    user_id,
                    session_key,
                ),
            )

            self.conn.commit()

            return True

        except Exception as exc:

            logger.error(
                "Session creation failed: %s",
                exc,
            )

            return False


    def lock_session(
        self,
        session_key: str,
    ) -> bool:

        try:

            cursor = self.conn.cursor()

            cursor.execute(
                """
                UPDATE research_sessions
                SET
                    status = 'LOCKED',
                    locked_at =
                        CURRENT_TIMESTAMP
                WHERE session_key = ?
                """,
                (
                    session_key,
                ),
            )

            self.conn.commit()

            return True

        except Exception as exc:

            logger.error(
                "Session lock failed: %s",
                exc,
            )

            return False


    # ========================================================
    # RECENT ANALYSES
    # ========================================================

    def get_recent_analyses(
        self,
        user_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        try:

            limit = max(
                1,
                min(
                    int(limit),
                    100,
                ),
            )

            cursor = self.conn.cursor()

            if user_id is not None:

                cursor.execute(
                    f"""
                    SELECT
                        id,
                        user_id,
                        timeframe,
                        asset_pair,
                        research_bias,
                        liquidity_event,
                        created_at
                    FROM chart_analysis
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT {limit}
                    """,
                    (
                        user_id,
                    ),
                )

            else:

                cursor.execute(
                    f"""
                    SELECT
                        id,
                        user_id,
                        timeframe,
                        asset_pair,
                        research_bias,
                        liquidity_event,
                        created_at
                    FROM chart_analysis
                    ORDER BY id DESC
                    LIMIT {limit}
                    """
                )

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "timeframe": row[2],
                    "asset_pair": row[3],
                    "research_bias": row[4],
                    "liquidity_event": row[5],
                    "created_at": row[6],
                }
                for row in rows
            ]

        except Exception as exc:

            logger.error(
                "Recent analysis query failed: %s",
                exc,
            )

            return []


# ============================================================
# GLOBAL INSTANCE
# ============================================================

db = DatabaseManager()


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Liquidity Research Database initialized."
    )

    print(
        f"Using Turso: {db.using_turso}"
    )

    print(
        f"Total chart analyses: "
        f"{db.get_total_nodes()}"
    )
