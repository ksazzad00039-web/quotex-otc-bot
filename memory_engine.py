from config import MIN_PATTERN_SAMPLES, MIN_HISTORICAL_FREQUENCY, logger

class QuantitativeEngine:
    def __init__(self, db_manager):
        self.db = db_manager

    def evaluate_multi_timeframe(self, data_1d, data_1h):
        # 1. Compute Synthetic Research Score (Technical Metric)
        research_score = 50.0
        
        trend_1d = data_1d.get("primary_trend", "CONSOLIDATION")
        trend_1h = data_1h.get("primary_trend", "CONSOLIDATION")
        rejection_1h = data_1h.get("rejection_zone", "NEUTRAL")

        if "BULLISH" in trend_1d and "BULLISH" in trend_1h:
            research_score += 25.0
            technical_dir = "UP"
        elif "BEARISH" in trend_1d and "BEARISH" in trend_1h:
            research_score += 25.0
            technical_dir = "DOWN"
        else:
            research_score += 10.0
            technical_dir = "DOWN" if rejection_1h == "UPPER_REJECTION" else "UP"

        if rejection_1h != "NEUTRAL":
            research_score += 15.0

        research_score = min(research_score, 98.0)

        # 2. Query Actual Historical Database Frequency (Real Math)
        db_stats = self.db.query_pattern_statistics(trend_1h, rejection_1h)

        return {
            "decision": db_stats["dominant_direction"] if db_stats["total_samples"] > 0 else technical_dir,
            "research_score": round(research_score, 1),
            "historical_frequency": db_stats["win_rate"],
            "matched_historical_samples": db_stats["total_samples"],
            "min_samples_met": db_stats["total_samples"] >= MIN_PATTERN_SAMPLES,
            "trend_1d": trend_1d,
            "trend_1h": trend_1h,
            "rejection_1h": rejection_1h
        }

