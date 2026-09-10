import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("OTC_Enterprise_Quant.LiquidityEngine")

class LiquidityEngine:
    """
    Smart Money Concepts (SMC) & Institutional Order Flow Engine.
    Analyzes Liquidity Sweeps, Fair Value Gaps (FVG), Order Blocks, 
    and Buy/Sell Side Liquidity levels to validate trade setups.
    """

    def __init__(self):
        # Base confidence multiplier for liquidity setups
        self.fvg_weight = 15.0
        self.sweep_weight = 20.0
        self.ob_weight = 15.0

    def evaluate_fvg(self, fvg_present: bool, fvg_type: str, trade_direction: str) -> Tuple[float, str]:
        """
        Evaluates Fair Value Gap (Imbalance) alignment with predicted direction.
        Returns: (score_delta, fvg_status)
        """
        if not fvg_present:
            return 0.0, "NO_FVG_DETECTED"

        if fvg_type == "BULLISH_FVG" and trade_direction == "UP":
            return self.fvg_weight, "BULLISH_FVG_ALIGNED"
        elif fvg_type == "BEARISH_FVG" and trade_direction == "DOWN":
            return self.fvg_weight, "BEARISH_FVG_ALIGNED"
        elif (fvg_type == "BULLISH_FVG" and trade_direction == "DOWN") or \
             (fvg_type == "BEARISH_FVG" and trade_direction == "UP"):
            return -10.0, "COUNTER_FVG_WARNNING"

        return 0.0, "NEUTRAL_FVG"

    def evaluate_liquidity_sweep(self, sweep_detected: bool, sweep_side: str, trade_direction: str) -> Tuple[float, str]:
        """
        Evaluates Liquidity Sweeps (Stop Hunts).
        A sweep of Sell-Side Liquidity (SSL) fuels UP moves.
        A sweep of Buy-Side Liquidity (BSL) fuels DOWN moves.
        """
        if not sweep_detected:
            return 0.0, "NO_SWEEP_DETECTED"

        if sweep_side == "SELL_SIDE_LIQUIDITY" and trade_direction == "UP":
            return self.sweep_weight, "SSL_SWEPT_BULLISH_REVERSAL"
        elif sweep_side == "BUY_SIDE_LIQUIDITY" and trade_direction == "DOWN":
            return self.sweep_weight, "BSL_SWEPT_BEARISH_REVERSAL"
        
        return -15.0, "UNFAVORABLE_LIQUIDITY_SWEEP"

    def evaluate_order_block(self, ob_active: bool, ob_zone: str, trade_direction: str) -> Tuple[float, str]:
        """
        Validates institutional Order Block (OB) mitigation zones.
        """
        if not ob_active:
            return 0.0, "NO_ORDER_BLOCK"

        if ob_zone == "BULLISH_ORDER_BLOCK" and trade_direction == "UP":
            return self.ob_weight, "BULLISH_OB_MITIGATION"
        elif ob_zone == "BEARISH_ORDER_BLOCK" and trade_direction == "DOWN":
            return self.ob_weight, "BEARISH_OB_MITIGATION"

        return 0.0, "NEUTRAL_ORDER_BLOCK"

    def analyze_liquidity_confluence(
        self, 
        data_1h: Dict[str, Any], 
        predicted_direction: str
    ) -> Dict[str, Any]:
        """
        Master Liquidity Analysis Pipeline.
        Calculates total Institutional Order Flow Score and returns SMC metrics.
        """
        fvg_present = data_1h.get("fvg_detected", False)
        fvg_type = data_1h.get("fvg_type", "NONE")
        
        sweep_detected = data_1h.get("liquidity_sweep", False)
        sweep_side = data_1h.get("sweep_side", "NONE")
        
        ob_active = data_1h.get("order_block_detected", False)
        ob_zone = data_1h.get("order_block_zone", "NONE")

        total_liquidity_score = 50.0  # Base Liquidity Neutral Score

        # 1. Fair Value Gap Check
        fvg_score, fvg_status = self.evaluate_fvg(fvg_present, fvg_type, predicted_direction)
        total_liquidity_score += fvg_score

        # 2. Liquidity Sweep Check
        sweep_score, sweep_status = self.evaluate_liquidity_sweep(sweep_detected, sweep_side, predicted_direction)
        total_liquidity_score += sweep_score

        # 3. Order Block Mitigation Check
        ob_score, ob_status = self.evaluate_order_block(ob_active, ob_zone, predicted_direction)
        total_liquidity_score += ob_score

        # Clamping score between 0.0 and 100.0
        final_liquidity_score = round(max(0.0, min(total_liquidity_score, 100.0)), 1)

        # Determine overall institutional bias
        if final_liquidity_score >= 70.0:
            institutional_bias = "HIGH_INSTITUTIONAL_CONFLUENCE"
        elif final_liquidity_score <= 35.0:
            institutional_bias = "HIGH_RISK_RETAIL_TRAP"
        else:
            institutional_bias = "MODERATE_LIQUIDITY_CONFLUENCE"

        return {
            "liquidity_score": final_liquidity_score,
            "institutional_bias": institutional_bias,
            "fvg_status": fvg_status,
            "sweep_status": sweep_status,
            "order_block_status": ob_status,
            "metrics": {
                "fvg_score": fvg_score,
                "sweep_score": sweep_score,
                "ob_score": ob_score
            }
        }
