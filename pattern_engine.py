import logging
import math
from typing import Dict, Any, Tuple, Optional, List

# Fallback Configuration Logging Setup
try:
    from config import logger, MIN_COMBINED_SCORE, KELLY_RISK_FRACTION, DEFAULT_PAYOUT_RATE
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("OTC_Enterprise_Quant.PatternEngine")
    MIN_COMBINED_SCORE = 75.0
    KELLY_RISK_FRACTION = 0.5
    DEFAULT_PAYOUT_RATE = 0.85


class PatternEngine:
    """
    Ultimate Enterprise Quantitative Pattern & Price Action Analysis Engine.
    Strictly designed for Quotex OTC Binary Options on 1-Hour Chart Executions.
    Integrates Candlestick Microstructure, Wick Rejections, Macro Trend Alignment (1D),
    Support/Resistance Level Density, Exhaustion Protection, and Half-Kelly Risk Management.
    """

    def __init__(self):
        # Directional Trend Matrix
        self.trend_weights = {
            "STRONG_BULLISH": 1.0,
            "UPTREND": 1.0,
            "WEAK_BULLISH": 0.5,
            "CONSOLIDATION": 0.0,
            "NEUTRAL": 0.0,
            "WEAK_BEARISH": -0.5,
            "DOWNTREND": -1.0,
            "STRONG_BEARISH": -1.0
        }

        # Candlestick Microstructure Weight Matrix
        self.candlestick_weights = {
            "BULLISH_ENGULFING": 18.0,
            "BEARISH_ENGULFING": 18.0,
            "PIN_BAR_REJECTION": 15.0,
            "MARUBOZU_CONTINUATION": 12.0,
            "HAMMER_REVERSAL": 14.0,
            "SHOOTING_STAR": 14.0,
            "DOJI_INDECISION": -10.0
        }

    def evaluate_trend_alignment(self, trend_1d: str, trend_1h: str) -> Tuple[float, str]:
        """Calculates Macro Trend (1D) vs Micro Structure (1H) alignment."""
        w_1d = self.trend_weights.get(trend_1d.upper(), 0.0)
        w_1h = self.trend_weights.get(trend_1h.upper(), 0.0)

        if w_1d > 0 and w_1h > 0:
            return 25.0, "PERFECT_BULLISH_ALIGNMENT"
        elif w_1d < 0 and w_1h < 0:
            return 25.0, "PERFECT_BEARISH_ALIGNMENT"
        elif (w_1d > 0 and w_1h < 0) or (w_1d < 0 and w_1h > 0):
            return -18.0, "COUNTER_TREND_CONFLICT_RISK"

        return 5.0, "NEUTRAL_CONSOLIDATION_ALIGNMENT"

    def analyze_wick_rejection(self, rejection_zone: str, primary_trend: str) -> Tuple[float, str]:
        """Evaluates wick rejection dynamics against current timeframe trend bias."""
        rejection = rejection_zone.upper()
        trend = primary_trend.upper()

        if rejection in ["UPPER_REJECTION", "RESISTANCE", "TOP_WICK_REJECTION"]:
            if "BEARISH" in trend or "DOWN" in trend:
                return 22.0, "HIGH_CONFLUENCE_BEARISH_REJECTION"
            return 4.0, "WEAK_UPPER_REJECTION"

        elif rejection in ["LOWER_REJECTION", "SUPPORT", "BOTTOM_WICK_REJECTION"]:
            if "BULLISH" in trend or "UP" in trend:
                return 22.0, "HIGH_CONFLUENCE_BULLISH_REJECTION"
            return 4.0, "WEAK_LOWER_REJECTION"

        return 0.0, "NO_WICK_REJECTION"

    def evaluate_candlestick_pattern(self, pattern_type: str, trade_direction: str) -> Tuple[float, str]:
        """Evaluates candlestick microstructure formation against expected trade direction."""
        pattern = pattern_type.upper()
        direction = trade_direction.upper()

        if pattern == "NONE" or not pattern:
            return 0.0, "NO_CANDLE_PATTERN_DETECTED"

        if pattern in ["BULLISH_ENGULFING", "HAMMER_REVERSAL"] and direction == "UP":
            return self.candlestick_weights.get(pattern, 15.0), f"ALIGNED_{pattern}"
        elif pattern in ["BEARISH_ENGULFING", "SHOOTING_STAR"] and direction == "DOWN":
            return self.candlestick_weights.get(pattern, 15.0), f"ALIGNED_{pattern}"
        elif pattern == "DOJI_INDECISION":
            return -12.0, "DOJI_HIGH_VOLATILITY_RISK"

        return 0.0, "NEUTRAL_CANDLE_PATTERN"

    def evaluate_sr_density_and_volatility(self, sr_count: int, volatility_score: float) -> Tuple[float, Dict[str, Any]]:
        """Assesses S/R level cluster density and price volatility stability."""
        score = 0.0
        status = {"density": "LOW", "volatility": "STABLE"}

        if sr_count >= 3:
            score += 12.0
            status["density"] = "HIGH_KEY_LEVEL_CONFLUENCE"
        elif sr_count >= 1:
            score += 6.0
            status["density"] = "MODERATE_KEY_LEVEL"

        if 30.0 <= volatility_score <= 70.0:
            score += 10.0
            status["volatility"] = "OPTIMAL_VOLATILITY"
        elif volatility_score > 85.0:
            score -= 15.0
            status["volatility"] = "EXTREME_VOLATILITY_NOISE"
        elif volatility_score < 20.0:
            score -= 8.0
            status["volatility"] = "LOW_LIQUIDITY_STAGNANT"

        return score, status

    def calculate_kelly_stake(self, win_rate_pct: float, payout_rate: float = DEFAULT_PAYOUT_RATE) -> float:
        """Calculates Fractional Half-Kelly Risk Percentage based on win probability."""
        p = win_rate_pct / 100.0
        q = 1.0 - p
        b = payout_rate

        kelly_full = (b * p - q) / b if b > 0 else 0.0
        kelly_fractional = max(0.0, kelly_full * KELLY_RISK_FRACTION)

        return round(kelly_fractional * 100, 2)

    def compute_pattern_score(
        self,
        vision_data: Dict[str, Any],
        db_stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Master Execution Pipeline:
        Integrates Price Action, Candlestick Microstructure, S/R Density, 
        and Historical DB Analytics to generate institutional grade decisions.
        """
        if db_stats is None:
            db_stats = {}

        try:
            trend_1d = vision_data.get("timeframe_1d_trend", "CONSOLIDATION")
            trend_1h = vision_data.get("primary_trend", "CONSOLIDATION")
            rejection_1h = vision_data.get("rejection_zone", "NEUTRAL")
            candle_pattern = vision_data.get("candlestick_pattern", "NONE")
            sr_count = int(vision_data.get("sr_level_count", 0))
            volatility_score = float(vision_data.get("volatility_score", 50.0))
            ai_confidence = float(vision_data.get("confidence_score", 50.0))
            raw_prediction = vision_data.get("predicted_direction", "HOLD").upper()

            # 1. Base Confluence Aggregation
            base_score = 35.0
            trend_score, trend_status = self.evaluate_trend_alignment(trend_1d, trend_1h)
            rejection_score, rejection_status = self.analyze_wick_rejection(rejection_1h, trend_1h)
            candle_score, candle_status = self.evaluate_candlestick_pattern(candle_pattern, raw_prediction)
            sr_vol_score, sr_vol_metrics = self.evaluate_sr_density_and_volatility(sr_count, volatility_score)

            total_pattern_score = base_score + trend_score + rejection_score + candle_score + sr_vol_score

            # 2. Database History Fusion (60% AI Vision + 40% DB Memory)
            historical_matches = db_stats.get("matched_records", 0)
            historical_avg_conf = db_stats.get("historical_avg_confidence", 50.0)

            if historical_matches > 0:
                combined_score = (ai_confidence * 0.55) + (historical_avg_conf * 0.30) + (total_pattern_score * 0.15)
            else:
                combined_score = (ai_confidence * 0.65) + (total_pattern_score * 0.35)

            final_score = round(max(10.0, min(combined_score, 99.0)), 2)

            # 3. Execution Guard & Risk Sizing
            if final_score < MIN_COMBINED_SCORE or raw_prediction not in ["UP", "DOWN"]:
                decision = "HOLD"
                win_rate = 0.0
                recommended_stake_pct = 0.0
            else:
                decision = raw_prediction
                win_rate = min(96.0, max(55.0, final_score))
                recommended_stake_pct = self.calculate_kelly_stake(win_rate)

            logger.info(
                f"Master Pattern Evaluation Complete | Decision: [{decision}] | "
                f"Combined Score: [{final_score}%] | Recommended Stake: [{recommended_stake_pct}%]"
            )

            return {
                "decision": decision,
                "confidence_score": final_score,
                "win_rate_probability": win_rate,
                "kelly_risk_stake_pct": recommended_stake_pct,
                "trend_alignment_status": trend_status,
                "rejection_status": rejection_status,
                "candlestick_status": candle_status,
                "sr_volatility_metrics": sr_vol_metrics,
                "historical_matches_found": historical_matches,
                "summary": vision_data.get("analysis_summary", "")
            }

        except Exception as e:
            logger.error(f"Error in Pattern Engine evaluation: {str(e)}")
            return {
                "decision": "HOLD",
                "confidence_score": 50.0,
                "win_rate_probability": 0.0,
                "kelly_risk_stake_pct": 0.0,
                "trend_alignment_status": "ERROR_FALLBACK",
                "rejection_status": "ERROR_FALLBACK",
                "candlestick_status": "ERROR_FALLBACK",
                "sr_volatility_metrics": {},
                "historical_matches_found": 0,
                "summary": f"Fallback execution: {str(e)}"
            }


# Global Engine Instance Export
pattern_engine = PatternEngine()
# Class Alias for Flexible Importing
QuantPatternEngine = PatternEngine

if __name__ == "__main__":
    print("Master Quant Pattern Engine Ready.")
