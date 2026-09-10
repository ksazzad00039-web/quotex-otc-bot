import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("OTC_Enterprise_Quant.PatternEngine")

class PatternEngine:
    """
    Algorithmic Price Action & Technical Pattern Evaluation Engine.
    Processes structured vision output to identify high-probability institutional candle patterns,
    trend alignments, wick rejections, and structural strength for OTC markets.
    """

    def __init__(self):
        # Weightage matrix for structural trend alignment
        self.trend_weights = {
            "STRONG_BULLISH": 1.0,
            "WEAK_BULLISH": 0.5,
            "CONSOLIDATION": 0.0,
            "WEAK_BEARISH": -0.5,
            "STRONG_BEARISH": -1.0
        }

    def evaluate_trend_alignment(self, trend_1d: str, trend_1h: str) -> Tuple[float, str]:
        """
        Calculates higher timeframe (1D) vs current execution timeframe (1H) alignment score.
        Returns: (alignment_score, alignment_status)
        """
        weight_1d = self.trend_weights.get(trend_1d, 0.0)
        weight_1h = self.trend_weights.get(trend_1h, 0.0)

        # Perfect directional alignment
        if weight_1d > 0 and weight_1h > 0:
            return 25.0, "PERFECT_BULLISH_ALIGNMENT"
        elif weight_1d < 0 and weight_1h < 0:
            return 25.0, "PERFECT_BEARISH_ALIGNMENT"
        
        # Mixed or conflicting trends
        if (weight_1d > 0 and weight_1h < 0) or (weight_1d < 0 and weight_1h > 0):
            return -15.0, "COUNTER_TREND_CONFLICT"

        # Consolidation or weak trend state
        return 5.0, "NEUTRAL_CONSOLIDATION"

    def analyze_rejection_confluence(self, rejection_zone: str, primary_trend: str) -> Tuple[float, str]:
        """
        Evaluates wick rejection dynamics against current timeframe trend bias.
        Upper wicks indicate selling pressure; lower wicks indicate buying pressure.
        """
        score = 0.0
        status = "NO_REJECTION_CONFLUENCE"

        if rejection_zone == "UPPER_REJECTION":
            if "BEARISH" in primary_trend:
                score += 20.0
                status = "STRONG_UPPER_WICK_BEARISH_REJECTION"
            else:
                score += 5.0
                status = "WEAK_UPPER_REJECTION"

        elif rejection_zone == "LOWER_REJECTION":
            if "BULLISH" in primary_trend:
                score += 20.0
                status = "STRONG_LOWER_WICK_BULLISH_REJECTION"
            else:
                score += 5.0
                status = "WEAK_LOWER_REJECTION"

        return score, status

    def evaluate_volatility_and_levels(self, volatility_score: float, sr_count: int) -> Tuple[float, Dict[str, Any]]:
        """
        Assesses key Support/Resistance level density and volatility index.
        Ideal trading environment requires clear key levels and stable (non-erratic) volatility.
        """
        score = 0.0
        metrics = {
            "volatility_status": "STABLE",
            "level_density": "LOW"
        }

        # Key Level Density
        if sr_count >= 3:
            score += 15.0
            metrics["level_density"] = "HIGH"
        elif sr_count >= 1:
            score += 8.0
            metrics["level_density"] = "MEDIUM"

        # Volatility Assessment (0 to 100 scale)
        if 30.0 <= volatility_score <= 70.0:
            score += 10.0
            metrics["volatility_status"] = "OPTIMAL_VOLATILITY"
        elif volatility_score > 85.0:
            score -= 10.0
            metrics["volatility_status"] = "EXTREME_VOLATILITY_NOISY"
        elif volatility_score < 20.0:
            score -= 5.0
            metrics["volatility_status"] = "DEAD_LOW_VOLATILITY"

        return score, metrics

    def compute_pattern_score(self, data_1d: Dict[str, Any], data_1h: Dict[str, Any]) -> Dict[str, Any]:
        """
        Master method aggregating all technical, pattern, and structural confluence metrics.
        Returns detailed scoring breakdown and recommended trade direction.
        """
        trend_1d = data_1d.get("primary_trend", "CONSOLIDATION")
        trend_1h = data_1h.get("primary_trend", "CONSOLIDATION")
        rejection_1h = data_1h.get("rejection_zone", "NEUTRAL")
        volatility_1h = float(data_1h.get("volatility_score", 50.0))
        sr_count_1h = int(data_1h.get("support_resistance_count", 0))

        # Base technical setup score
        base_score = 50.0

        # 1. Trend Alignment Score
        trend_score, trend_status = self.evaluate_trend_alignment(trend_1d, trend_1h)
        base_score += trend_score

        # 2. Rejection Confluence Score
        rejection_score, rejection_status = self.analyze_rejection_confluence(rejection_1h, trend_1h)
        base_score += rejection_score

        # 3. Volatility & Levels Score
        vol_score, vol_metrics = self.evaluate_volatility_and_levels(volatility_1h, sr_count_1h)
        base_score += vol_score

        # Clamp final pattern score between 10.0 and 99.0
        final_pattern_score = round(max(10.0, min(base_score, 99.0)), 1)

        # Direction Determination Logic
        if "BULLISH" in trend_status:
            direction = "UP"
        elif "BEARISH" in trend_status:
            direction = "DOWN"
        else:
            if rejection_1h == "LOWER_REJECTION":
                direction = "UP"
            elif rejection_1h == "UPPER_REJECTION":
                direction = "DOWN"
            else:
                direction = data_1h.get("recommended_direction", "NO_TRADE")

        return {
            "pattern_score": final_pattern_score,
            "suggested_direction": direction,
            "trend_alignment_status": trend_status,
            "rejection_status": rejection_status,
            "volatility_metrics": vol_metrics,
            "raw_inputs": {
                "trend_1d": trend_1d,
                "trend_1h": trend_1h,
                "rejection_1h": rejection_1h,
                "volatility": volatility_1h,
                "sr_count": sr_count_1h
            }
        }
