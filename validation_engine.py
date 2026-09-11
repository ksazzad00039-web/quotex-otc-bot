import logging
from typing import Dict, Any, Tuple, Optional

# Fallback Configuration Logging Setup
try:
    from config import logger, MIN_PATTERN_SCORE, MIN_LIQUIDITY_SCORE, MIN_COMBINED_CONFIDENCE
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("OTC_Enterprise_Quant.ValidationEngine")
    MIN_PATTERN_SCORE = 65.0
    MIN_LIQUIDITY_SCORE = 55.0
    MIN_COMBINED_CONFIDENCE = 70.0


class ValidationEngine:
    """
    Master Enterprise Risk & Multi-Timeframe Trade Verification Engine.
    Specially engineered for Quotex OTC binary markets.
    Validates 1D Macro Trend Direction alongside 1H Execution Signals to guarantee high-probability setups.
    """

    def __init__(
        self, 
        min_pattern_score: float = MIN_PATTERN_SCORE, 
        min_liquidity_score: float = MIN_LIQUIDITY_SCORE,
        min_combined_confidence: float = MIN_COMBINED_CONFIDENCE
    ):
        self.min_pattern_score = min_pattern_score
        self.min_liquidity_score = min_liquidity_score
        self.min_combined_confidence = min_combined_confidence

    def validate_multi_timeframe_bias(
        self, 
        macro_1d_bias: str, 
        execution_1h_signal: str
    ) -> Tuple[bool, str, float]:
        """
        Validates 1D Higher Timeframe Bias against 1H Execution Signal.
        Returns: (is_aligned, reason, alignment_score_bonus)
        """
        macro_bias = str(macro_1d_bias).upper()
        signal_1h = str(execution_1h_signal).upper()

        if macro_bias == "BULLISH" and signal_1h == "UP":
            return True, "PERFECT_CONFLUENCE: 1D Bullish Bias aligns with 1H UP Signal.", 100.0
        elif macro_bias == "BEARISH" and signal_1h == "DOWN":
            return True, "PERFECT_CONFLUENCE: 1D Bearish Bias aligns with 1H DOWN Signal.", 100.0
        elif macro_bias in ["NEUTRAL", "SIDEWAYS", "RANGING"]:
            return True, "NEUTRAL_MACRO: 1D chart is ranging; relying strictly on 1H SMC levels.", 70.0
        else:
            return False, f"COUNTER_TREND_VETO: 1D Macro Bias is {macro_bias} but 1H Signal suggests {signal_1h}.", 0.0

    def evaluate_risk_factors(
        self, 
        pattern_data: Dict[str, Any], 
        liquidity_data: Dict[str, Any],
        macro_1d_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Hard Risk Gatekeeper: Evaluates strict market rules to veto unsafe trading conditions.
        """
        trend_status = pattern_data.get("trend_alignment_status", "")
        liquidity_bias = liquidity_data.get("institutional_bias", "")
        volatility_metrics = pattern_data.get("volatility_metrics", {})
        vol_status = volatility_metrics.get("volatility_status", "")
        suggested_direction = pattern_data.get("suggested_direction", "NO_TRADE")

        # 1. 1D vs 1H Trend Alignment Check
        if macro_1d_data:
            macro_bias = macro_1d_data.get("macro_bias", "NEUTRAL")
            is_aligned, align_reason, _ = self.validate_multi_timeframe_bias(macro_bias, suggested_direction)
            if not is_aligned:
                return False, align_reason

        # 2. Instant Veto on Counter-Trend Conflict Flags
        if trend_status == "COUNTER_TREND_CONFLICT":
            return False, "VETO: Higher Timeframe structure conflicts with local 1H candle momentum."

        # 3. Instant Veto on Retail Traps
        if liquidity_bias == "HIGH_RISK_RETAIL_TRAP":
            return False, "VETO: High-risk retail liquidity trap detected near support/resistance level."

        # 4. Instant Veto on Extreme / Erratic Volatility
        if vol_status == "EXTREME_VOLATILITY_NOISY":
            return False, "VETO: Market volatility is dangerously erratic for 1-Hour candle predictions."

        # 5. Instant Veto on Dead / Low Liquidity Volume
        if vol_status == "DEAD_LOW_VOLATILITY":
            return False, "VETO: Market volume is insufficient; risk of flat candle output."

        return True, "PASSED_ALL_RISK_GATES"

    def calculate_combined_confidence(
        self, 
        pattern_score: float, 
        liquidity_score: float,
        alignment_score: float = 70.0,
        bayesian_prob: float = 50.0
    ) -> float:
        """
        Computes composite multi-engine confidence score:
        • 40% Weight: 1H Price Action & Pattern Score
        • 30% Weight: SMC Liquidity & Order Block Validation
        • 20% Weight: 1D Macro Trend Confluence Score
        • 10% Weight: Bayesian Statistical Win Probability
        """
        weighted_score = (
            (pattern_score * 0.40) + 
            (liquidity_score * 0.30) + 
            (alignment_score * 0.20) + 
            (bayesian_prob * 0.10)
        )
        return round(weighted_score, 1)

    def determine_stake_recommendation(self, confidence: float) -> str:
        """Calculates dynamic Kelly risk allocation recommendation."""
        if confidence >= 85.0:
            return "AGGRESSIVE_HIGH_CONVICTION (Stake: 3% - 5%)"
        elif confidence >= 75.0:
            return "STANDARD_STAKE (Stake: 2% - 3%)"
        elif confidence >= 70.0:
            return "CONSERVATIVE_HALF_STAKE (Stake: 1% - 1.5%)"
        return "NO_STAKE (0%)"

    def validate_trade(
        self, 
        pattern_result: Dict[str, Any], 
        liquidity_result: Dict[str, Any],
        macro_1d_result: Optional[Dict[str, Any]] = None,
        stats_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Master Multi-Timeframe Trade Validation Pipeline.
        Evaluates 1D context, 1H price action, SMC liquidity, and statistical win-rate.
        """
        pattern_score = float(pattern_result.get("pattern_score", 0.0))
        liquidity_score = float(liquidity_result.get("liquidity_score", 0.0))
        suggested_direction = str(pattern_result.get("suggested_direction", "NO_TRADE")).upper()

        macro_bias = "NEUTRAL"
        if macro_1d_result:
            macro_bias = macro_1d_result.get("macro_bias", "NEUTRAL")

        _, align_msg, alignment_score = self.validate_multi_timeframe_bias(macro_bias, suggested_direction)

        bayesian_prob = 50.0
        if stats_result:
            bayesian_prob = float(stats_result.get("bayesian_win_probability", 50.0))

        # 1. Evaluate Hard Risk Gates
        is_safe, risk_msg = self.evaluate_risk_factors(pattern_result, liquidity_result, macro_1d_result)
        if not is_safe:
            logger.info(f"Trade Validation Veto Triggered: {risk_msg}")
            return {
                "is_approved": False,
                "final_decision": "NO_TRADE",
                "reason": risk_msg,
                "combined_confidence": 0.0,
                "pattern_score": pattern_score,
                "liquidity_score": liquidity_score,
                "macro_1d_bias": macro_bias,
                "stake_recommendation": "NO_STAKE"
            }

        # 2. Compute Composite Multi-Timeframe Confidence
        combined_confidence = self.calculate_combined_confidence(
            pattern_score, liquidity_score, alignment_score, bayesian_prob
        )

        # 3. Check Confidence & Score Thresholds
        if (pattern_score >= self.min_pattern_score and 
            liquidity_score >= self.min_liquidity_score and 
            combined_confidence >= self.min_combined_confidence and 
            suggested_direction in ["UP", "DOWN"]):

            stake_rec = self.determine_stake_recommendation(combined_confidence)
            logger.info(
                f"Trade Approved! Direction: [{suggested_direction}], "
                f"1D Bias: [{macro_bias}], Confidence: [{combined_confidence}%]"
            )
            return {
                "is_approved": True,
                "final_decision": suggested_direction,
                "reason": f"High-probability setup validated (1D {macro_bias} + 1H {suggested_direction}) with {combined_confidence}% confidence.",
                "combined_confidence": combined_confidence,
                "pattern_score": pattern_score,
                "liquidity_score": liquidity_score,
                "macro_1d_bias": macro_bias,
                "stake_recommendation": stake_rec
            }

        # 4. Threshold Unmet Fallback
        reason = (
            f"Composite confidence threshold unmet. (Combined: {combined_confidence}%, "
            f"Min Required: {self.min_combined_confidence}%)"
        )
        logger.info(f"Trade Validation Rejected: {reason}")

        return {
            "is_approved": False,
            "final_decision": "NO_TRADE",
            "reason": reason,
            "combined_confidence": combined_confidence,
            "pattern_score": pattern_score,
            "liquidity_score": liquidity_score,
            "macro_1d_bias": macro_bias,
            "stake_recommendation": "NO_STAKE"
        }


# Global Engine Instance Export
validation_engine = ValidationEngine()
# Class Alias for Flexible Import
MasterValidationEngine = ValidationEngine

if __name__ == "__main__":
    print("Master Multi-Timeframe Validation Engine Ready.")
