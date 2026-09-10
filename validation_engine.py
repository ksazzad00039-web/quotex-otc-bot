import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("OTC_Enterprise_Quant.ValidationEngine")

class ValidationEngine:
    """
    Risk & Trade Verification Engine.
    Filters out high-risk trades, noisy market conditions, and conflicting setups.
    Generates final execution approvals or 'NO_TRADE' decisions based on quant thresholds.
    """

    def __init__(
        self, 
        min_pattern_score: float = 65.0, 
        min_liquidity_score: float = 55.0,
        min_combined_confidence: float = 70.0
    ):
        self.min_pattern_score = min_pattern_score
        self.min_liquidity_score = min_liquidity_score
        self.min_combined_confidence = min_combined_confidence

    def evaluate_risk_factors(
        self, 
        pattern_data: Dict[str, Any], 
        liquidity_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Hard Risk Gatekeeper: Evaluates safety rules to instantly veto risky trades.
        Returns: (is_safe, failure_reason)
        """
        trend_status = pattern_data.get("trend_alignment_status", "")
        liquidity_bias = liquidity_data.get("institutional_bias", "")
        volatility_metrics = pattern_data.get("volatility_metrics", {})
        vol_status = volatility_metrics.get("volatility_status", "")

        # Rule 1: Instant Veto on Counter Trend Conflicts
        if trend_status == "COUNTER_TREND_CONFLICT":
            return False, "VETO: Higher timeframe (1D) and execution timeframe (1H) trends are in direct conflict."

        # Rule 2: Instant Veto on High Risk Retail Traps
        if liquidity_bias == "HIGH_RISK_RETAIL_TRAP":
            return False, "VETO: High risk of retail trap detected around liquidity pools."

        # Rule 3: Instant Veto on Extreme/Noisy Volatility
        if vol_status == "EXTREME_VOLATILITY_NOISY":
            return False, "VETO: Market volatility is dangerously high and erratic."

        # Rule 4: Instant Veto on Dead Low Volatility
        if vol_status == "DEAD_LOW_VOLATILITY":
            return False, "VETO: Market volume/volatility is extremely low."

        return True, "PASSED_RISK_CHECKS"

    def calculate_combined_confidence(
        self, 
        pattern_score: float, 
        liquidity_score: float
    ) -> float:
        """
        Calculates weighted composite confidence score.
        60% weight on Price Action Pattern + 40% weight on SMC Liquidity.
        """
        weighted_score = (pattern_score * 0.60) + (liquidity_score * 0.40)
        return round(weighted_score, 1)

    def validate_trade(
        self, 
        pattern_result: Dict[str, Any], 
        liquidity_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Master Trade Validation Pipeline.
        Evaluates risk gates and threshold metrics to return the final execution mandate.
        """
        pattern_score = float(pattern_result.get("pattern_score", 0.0))
        liquidity_score = float(liquidity_result.get("liquidity_score", 0.0))
        suggested_direction = pattern_result.get("suggested_direction", "NO_TRADE")

        # 1. Check Hard Risk Gates
        is_safe, risk_msg = self.evaluate_risk_factors(pattern_result, liquidity_result)
        if not is_safe:
            logger.info(f"Trade Validation Failed: {risk_msg}")
            return {
                "is_approved": False,
                "final_decision": "NO_TRADE",
                "reason": risk_msg,
                "combined_confidence": 0.0,
                "pattern_score": pattern_score,
                "liquidity_score": liquidity_score
            }

        # 2. Compute Composite Confidence
        combined_confidence = self.calculate_combined_confidence(pattern_score, liquidity_score)

        # 3. Check Threshold Criteria
        if (pattern_score >= self.min_pattern_score and 
            liquidity_score >= self.min_liquidity_score and 
            combined_confidence >= self.min_combined_confidence and 
            suggested_direction in ["UP", "DOWN"]):

            logger.info(f"Trade Approved! Direction: {suggested_direction}, Confidence: {combined_confidence}%")
            return {
                "is_approved": True,
                "final_decision": suggested_direction,
                "reason": f"High probability setup validated with {combined_confidence}% confidence.",
                "combined_confidence": combined_confidence,
                "pattern_score": pattern_score,
                "liquidity_score": liquidity_score
            }

        # If thresholds are not met
        reason = (
            f"Score threshold unmet. (Combined: {combined_confidence}%, "
            f"Min required: {self.min_combined_confidence}%)"
        )
        logger.info(f"Trade Validation Reject: {reason}")
        
        return {
            "is_approved": False,
            "final_decision": "NO_TRADE",
            "reason": reason,
            "combined_confidence": combined_confidence,
            "pattern_score": pattern_score,
            "liquidity_score": liquidity_score
        }
