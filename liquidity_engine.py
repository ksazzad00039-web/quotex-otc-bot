import logging
from typing import Dict, Any, Tuple, Optional

# Fallback Configuration Logging Setup
try:
    from config import logger
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("OTC_Enterprise_Quant.LiquidityEngine")


class LiquidityEngine:
    """
    Enterprise Institutional Smart Money Concepts (SMC) & ICT Order Flow Engine.
    Evaluates Liquidity Sweeps, Imbalance (FVG), Order Block Mitigation, 
    Market Structure Shift (MSS), and Pricing Zones for Strict 1-Hour Chart Evaluation.
    """

    def __init__(self):
        # Quant Confluence Weights
        self.weight_fvg = 18.0
        self.weight_sweep = 22.0
        self.weight_ob = 18.0
        self.weight_mss = 15.0
        self.weight_pricing_zone = 12.0

    def evaluate_fvg(self, fvg_present: bool, fvg_type: str, trade_direction: str) -> Tuple[float, str]:
        """Evaluates Fair Value Gap (Imbalance) structural alignment."""
        if not fvg_present or fvg_type == "NONE":
            return 0.0, "NO_FVG_DETECTED"

        if fvg_type == "BULLISH_FVG" and trade_direction == "UP":
            return self.weight_fvg, "BULLISH_FVG_ALIGNED"
        elif fvg_type == "BEARISH_FVG" and trade_direction == "DOWN":
            return self.weight_fvg, "BEARISH_FVG_ALIGNED"
        elif (fvg_type == "BULLISH_FVG" and trade_direction == "DOWN") or \
             (fvg_type == "BEARISH_FVG" and trade_direction == "UP"):
            return -12.0, "COUNTER_FVG_WARNING_RETAIL_TRAP"

        return 0.0, "NEUTRAL_FVG"

    def evaluate_liquidity_sweep(self, sweep_detected: bool, sweep_side: str, trade_direction: str) -> Tuple[float, str]:
        """
        Evaluates Liquidity Sweeps (Stop Hunts).
        Sweep of Sell-Side Liquidity (SSL) provides bullish reversal momentum.
        Sweep of Buy-Side Liquidity (BSL) provides bearish reversal momentum.
        """
        if not sweep_detected or sweep_side == "NONE":
            return 0.0, "NO_LIQUIDITY_SWEEP"

        if sweep_side == "SELL_SIDE_LIQUIDITY" and trade_direction == "UP":
            return self.weight_sweep, "SSL_SWEPT_HIGH_CONFLUENCE_BULLISH"
        elif sweep_side == "BUY_SIDE_LIQUIDITY" and trade_direction == "DOWN":
            return self.weight_sweep, "BSL_SWEPT_HIGH_CONFLUENCE_BEARISH"
        elif (sweep_side == "SELL_SIDE_LIQUIDITY" and trade_direction == "DOWN") or \
             (sweep_side == "BUY_SIDE_LIQUIDITY" and trade_direction == "UP"):
            return -15.0, "COUNTER_LIQUIDITY_SWEEP_TRAP"

        return 0.0, "NEUTRAL_SWEEP"

    def evaluate_order_block(self, ob_active: bool, ob_zone: str, trade_direction: str) -> Tuple[float, str]:
        """Validates Institutional Order Block (OB) mitigation zones."""
        if not ob_active or ob_zone == "NONE":
            return 0.0, "NO_ORDER_BLOCK"

        if ob_zone == "BULLISH_ORDER_BLOCK" and trade_direction == "UP":
            return self.weight_ob, "BULLISH_ORDER_BLOCK_MITIGATION"
        elif ob_zone == "BEARISH_ORDER_BLOCK" and trade_direction == "DOWN":
            return self.weight_ob, "BEARISH_ORDER_BLOCK_MITIGATION"
        elif (ob_zone == "BULLISH_ORDER_BLOCK" and trade_direction == "DOWN") or \
             (ob_zone == "BEARISH_ORDER_BLOCK" and trade_direction == "UP"):
            return -10.0, "COUNTER_ORDER_BLOCK_RISK"

        return 0.0, "NEUTRAL_ORDER_BLOCK"

    def evaluate_market_structure_shift(self, mss_detected: bool, mss_type: str, trade_direction: str) -> Tuple[float, str]:
        """Evaluates Market Structure Shift (MSS) / Break of Structure (BOS)."""
        if not mss_detected or mss_type == "NONE":
            return 0.0, "NO_STRUCTURE_SHIFT"

        if mss_type == "BULLISH_MSS" and trade_direction == "UP":
            return self.weight_mss, "BULLISH_STRUCTURE_SHIFT_CONFIRMED"
        elif mss_type == "BEARISH_MSS" and trade_direction == "DOWN":
            return self.weight_mss, "BEARISH_STRUCTURE_SHIFT_CONFIRMED"

        return -8.0, "COUNTER_STRUCTURE_SHIFT"

    def evaluate_pricing_zone(self, pricing_zone: str, trade_direction: str) -> Tuple[float, str]:
        """
        Evaluates Premium vs. Discount Pricing Arrays.
        Buy in Discount Zone, Sell in Premium Zone.
        """
        if pricing_zone == "DISCOUNT" and trade_direction == "UP":
            return self.weight_pricing_zone, "DISCOUNT_ZONE_OPTIMAL_BUY"
        elif pricing_zone == "PREMIUM" and trade_direction == "DOWN":
            return self.weight_pricing_zone, "PREMIUM_ZONE_OPTIMAL_SELL"
        elif pricing_zone == "PREMIUM" and trade_direction == "UP":
            return -10.0, "BUYING_IN_PREMIUM_HIGH_RISK"
        elif pricing_zone == "DISCOUNT" and trade_direction == "DOWN":
            return -10.0, "SELLING_IN_DISCOUNT_HIGH_RISK"

        return 0.0, "EQUILIBRIUM_NEUTRAL_ZONE"

    def analyze_liquidity_confluence(
        self,
        data_1h: Dict[str, Any],
        predicted_direction: str
    ) -> Dict[str, Any]:
        """
        Master Institutional Liquidity Confluence Pipeline.
        Calculates total Smart Money Concepts (SMC) Score and validates execution safety.
        """
        try:
            fvg_present = data_1h.get("fvg_detected", False)
            fvg_type = data_1h.get("fvg_type", "NONE")

            sweep_detected = data_1h.get("liquidity_sweep", False)
            sweep_side = data_1h.get("sweep_side", "NONE")

            ob_active = data_1h.get("order_block_detected", False)
            ob_zone = data_1h.get("order_block_zone", "NONE")

            mss_detected = data_1h.get("mss_detected", False)
            mss_type = data_1h.get("mss_type", "NONE")

            pricing_zone = data_1h.get("pricing_zone", "EQUILIBRIUM")

            base_liquidity_score = 45.0  # Base Neutral Confluence Score

            # 1. Fair Value Gap Evaluation
            fvg_score, fvg_status = self.evaluate_fvg(fvg_present, fvg_type, predicted_direction)
            base_liquidity_score += fvg_score

            # 2. Liquidity Sweep Evaluation
            sweep_score, sweep_status = self.evaluate_liquidity_sweep(sweep_detected, sweep_side, predicted_direction)
            base_liquidity_score += sweep_score

            # 3. Order Block Evaluation
            ob_score, ob_status = self.evaluate_order_block(ob_active, ob_zone, predicted_direction)
            base_liquidity_score += ob_score

            # 4. Market Structure Shift Evaluation
            mss_score, mss_status = self.evaluate_market_structure_shift(mss_detected, mss_type, predicted_direction)
            base_liquidity_score += mss_score

            # 5. Pricing Array Evaluation
            pricing_score, pricing_status = self.evaluate_pricing_zone(pricing_zone, predicted_direction)
            base_liquidity_score += pricing_score

            # Clamp Score between 0.0 and 100.0
            final_smc_score = round(max(0.0, min(base_liquidity_score, 100.0)), 2)

            # Determine Institutional Order Flow Bias
            if final_smc_score >= 75.0:
                institutional_bias = "HIGH_INSTITUTIONAL_CONFLUENCE"
            elif final_smc_score <= 40.0:
                institutional_bias = "HIGH_RISK_RETAIL_TRAP"
            else:
                institutional_bias = "MODERATE_LIQUIDITY_CONFLUENCE"

            logger.info(f"SMC Liquidity Pipeline Processed | Final Score: [{final_smc_score}%] | Bias: [{institutional_bias}]")

            return {
                "liquidity_score": final_smc_score,
                "institutional_bias": institutional_bias,
                "fvg_status": fvg_status,
                "sweep_status": sweep_status,
                "order_block_status": ob_status,
                "mss_status": mss_status,
                "pricing_status": pricing_status,
                "metrics": {
                    "fvg_score": fvg_score,
                    "sweep_score": sweep_score,
                    "ob_score": ob_score,
                    "mss_score": mss_score,
                    "pricing_score": pricing_score
                }
            }

        except Exception as e:
            logger.error(f"Error in Liquidity Engine execution: {str(e)}")
            return {
                "liquidity_score": 50.0,
                "institutional_bias": "NEUTRAL_FALLBACK",
                "fvg_status": "ERROR_FALLBACK",
                "sweep_status": "ERROR_FALLBACK",
                "order_block_status": "ERROR_FALLBACK",
                "mss_status": "ERROR_FALLBACK",
                "pricing_status": "ERROR_FALLBACK",
                "metrics": {}
            }


# Global Engine Instance Export
liquidity_engine = LiquidityEngine()
# Class Alias for Flexible Imports
SMCLiquidityEngine = LiquidityEngine

if __name__ == "__main__":
    print("SMC Liquidity Engine Ready.")

