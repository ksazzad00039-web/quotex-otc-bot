import sqlite3
import os
import hashlib
import json
from config import DATABASE_FILE, DATABASE_WAL_MODE, logger

class DatabaseManager:
    def __init__(self):
        dir_name = os.path.dirname(DATABASE_FILE)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            
        self.conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        if DATABASE_WAL_MODE == 1:
            cursor.execute("PRAGMA journal_mode=WAL;")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_hash TEXT UNIQUE,
                timeframe TEXT,
                primary_trend TEXT,
                support_resistance_count INTEGER,
                volatility_score REAL,
                rejection_zone TEXT,
                suggested_direction TEXT,
                raw_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def check_duplicate_image(self, image_bytes):
        img_hash = hashlib.sha256(image_bytes).hexdigest()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM training_patterns WHERE image_hash = ?", (img_hash,))
        return cursor.fetchone() is not None, img_hash

    def insert_pattern(self, img_hash, timeframe, ai_data):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO training_patterns 
                (image_hash, timeframe, primary_trend, support_resistance_count, volatility_score, rejection_zone, suggested_direction, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                img_hash,
                timeframe,
                ai_data.get("primary_trend", "CONSOLIDATION"),
                ai_data.get("support_resistance_count", 0),
                ai_data.get("volatility_score", 50.0),
                ai_data.get("rejection_zone", "NEUTRAL"),
                ai_data.get("recommended_direction", "NO_TRADE"),
                json.dumps(ai_data)
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def query_pattern_statistics(self, trend_1h, rejection_zone):
        cursor = self.conn.cursor()
        # Find matches for same trend and rejection pattern
        cursor.execute("""
            SELECT suggested_direction, COUNT(*) 
            FROM training_patterns 
            WHERE primary_trend = ? AND rejection_zone = ?
            GROUP BY suggested_direction
        """, (trend_1h, rejection_zone))
        
        results = cursor.fetchall()
        total_matched = sum([row[1] for row in results])
        
        if total_matched == 0:
            return {"total_samples": 0, "win_rate": 0.0, "dominant_direction": "NO_TRADE"}
            
        direction_counts = {row[0]: row[1] for row in results}
        up_count = direction_counts.get("UP", 0)
        down_count = direction_counts.get("DOWN", 0)
        
        if up_count >= down_count:
            dominant = "UP"
            historical_prob = round((up_count / total_matched) * 100, 2)
        else:
            dominant = "DOWN"
            historical_prob = round((down_count / total_matched) * 100, 2)

        return {
            "total_samples": total_matched,
            "win_rate": historical_prob,
            "dominant_direction": dominant
        }

    def get_total_nodes(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM training_patterns")
        return cursor.fetchone()[0]

