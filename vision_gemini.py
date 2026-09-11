import os
import io
import json
import time
import logging
import PIL.Image
from typing import Dict, Any, Union, Optional
import google.generativeai as genai

# Configuration Fallback Logging Setup
try:
    from config import GEMINI_API_KEY, GEMINI_MODEL, logger
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("OTC_Enterprise_Quant.VisionGemini")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-1.5-flash"


class VisionGeminiEngine:
    """
    Enterprise-Grade Multimodal Computer Vision Engine powered by Google Gemini.
    Specialized for Quotex OTC Binary Options Chart Analysis.
    Integrates Institutional Smart Money Concepts (SMC) & Price Action Microstructure
    for Strict 1-Hour Primary and 1-Day Macro Timeframe Evaluation.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model_name = model_name or GEMINI_MODEL
        self.model = None

        self._bootstrap_vision_engine()

    def _bootstrap_vision_engine(self) -> None:
        """Configures Gemini API credentials and initializes Generative Model safely."""
        if not self.api_key:
            logger.warning(
                "GEMINI_API_KEY environment variable missing! "
                "Vision Engine running in Resilient Offline Mode."
            )
            return

        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini Vision Engine Online | Active Core: [{self.model_name}]")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Vision Core: {str(e)}")
            self.model = None

    def _build_institutional_prompt(self, timeframe_context: str) -> str:
        """Constructs quantitative prompt instructing Gemini to return validated raw JSON."""
        return f"""
        You are an Elite OTC Quantitative Binary Options Analyst specializing in Price Action & Smart Money Concepts (SMC).
        Evaluate this OTC Candlestick Chart screenshot strictly for a target timeframe of: [{timeframe_context.upper()}].

        PERFORM DEEP TECHNICAL ANALYSIS ON THE FOLLOWING COMPONENT LAYERS:
        1. Macro & Micro Trend: Primary directional flow (STRONG_BULLISH, WEAK_BULLISH, CONSOLIDATION, WEAK_BEARISH, STRONG_BEARISH).
        2. Price Action Rejections: Upper wick vs lower wick rejection pressures.
        3. Candlestick Formations: Pin Bar, Engulfing, Doji, Marubozu, Hammer, Star setups.
        4. Smart Money Concepts (SMC):
           - Fair Value Gap (FVG): Detect BULLISH_FVG, BEARISH_FVG, or NONE.
           - Liquidity Sweeps: Track BUY_SIDE_LIQUIDITY, SELL_SIDE_LIQUIDITY, or NONE.
           - Order Blocks: Identify BULLISH_ORDER_BLOCK, BEARISH_ORDER_BLOCK, or NONE.
        5. Next Candle Prediction: Predict immediate NEXT candle direction (UP, DOWN, HOLD).
        6. Statistical Confidence Score: Rate precision probability from 50.0 to 99.0.

        CRITICAL STIPULATION:
        Output ONLY a valid, clean JSON object. Do not include markdown code block formatting (e.g., no backticks), no intro, and no extra prose outside the JSON body.

        EXPECTED PURE JSON SCHEMA:
        {{
            "asset_pair": "EUR/USD-OTC",
            "timeframe": "{timeframe_context.upper()}",
            "primary_trend": "STRONG_BULLISH / WEAK_BULLISH / CONSOLIDATION / WEAK_BEARISH / STRONG_BEARISH",
            "rejection_zone": "UPPER_REJECTION / LOWER_REJECTION / NEUTRAL",
            "volatility_score": 75.5,
            "pattern_detected": "Identified Candlestick Setup",
            "buyers_sellers_ratio": "BUYERS_DOMINANT / SELLERS_DOMINANT / BALANCED",
            "fvg_detected": true,
            "fvg_type": "BULLISH_FVG / BEARISH_FVG / NONE",
            "liquidity_sweep": false,
            "sweep_side": "BUY_SIDE_LIQUIDITY / SELL_SIDE_LIQUIDITY / NONE",
            "order_block_detected": true,
            "order_block_zone": "BULLISH_ORDER_BLOCK / BEARISH_ORDER_BLOCK / NONE",
            "confidence_score": 88.0,
            "predicted_direction": "UP / DOWN / HOLD",
            "key_support_level": "Key support level or price zone",
            "key_resistance_level": "Key resistance level or price zone",
            "analysis_summary": "1-sentence quantitative trade rationale"
        }}
        """

    def analyze_chart(
        self,
        image_input: Union[bytes, str],
        timeframe_hint: str = "1-HOUR",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Processes chart screenshots from file paths or memory bytes into quantitative JSON metrics.

        Args:
            image_input: Direct file path (str) OR raw image bytes (bytes).
            timeframe_hint: Targeted timeframe context ('1-HOUR' or '1-DAY').
            max_retries: Number of retries in case of transient API failures.

        Returns:
            Dict containing detailed SMC, trend, pattern, and directional predictions.
        """
        if not self.model:
            logger.warning("Generative Model uninitialized. Route to fallback engine.")
            return self._build_fallback_schema("Vision Engine Offline or API Key Missing", timeframe_hint)

        try:
            # Load image from file path or bytes buffer
            if isinstance(image_input, bytes):
                pil_image = PIL.Image.open(io.BytesIO(image_input))
            elif isinstance(image_input, str):
                if not os.path.exists(image_input):
                    raise FileNotFoundError(f"Chart image file not found at path: {image_input}")
                pil_image = PIL.Image.open(image_input)
            else:
                raise TypeError("Input must be raw bytes or valid string file path.")

            prompt = self._build_institutional_prompt(timeframe_hint)

            # Execution with Retry Mechanism for API stability
            raw_text = ""
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Submitting chart to Gemini Vision API (Attempt {attempt}/{max_retries})...")
                    response = self.model.generate_content([prompt, pil_image])
                    raw_text = response.text.strip()
                    if raw_text:
                        break
                except Exception as api_err:
                    logger.warning(f"API Attempt {attempt} failed: {str(api_err)}")
                    if attempt == max_retries:
                        raise api_err
                    time.sleep(1)

            clean_json = self._sanitize_json_output(raw_text)
            parsed_data = json.loads(clean_json)

            logger.info(
                f"Vision Analysis Successfully Executed | Timeframe: [{timeframe_hint}] | "
                f"Signal: [{parsed_data.get('predicted_direction')}] | Confidence: [{parsed_data.get('confidence_score')}%]"
            )
            return parsed_data

        except json.JSONDecodeError as je:
            logger.error(f"JSON Parsing Exception: {str(je)} | Raw Text Snippet: {raw_text[:120]}...")
            return self._build_fallback_schema("AI Response JSON Format Invalid", timeframe_hint)
        except Exception as e:
            logger.error(f"Unexpected Execution Error during Vision processing: {str(e)}")
            return self._build_fallback_schema(str(e), timeframe_hint)

    def _sanitize_json_output(self, raw_text: str) -> str:
        """Strips unwanted Markdown code block tags, quotes, or conversational prose."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.replace("```json", "", 1)
        elif cleaned.startswith("```"):
            cleaned = cleaned.replace("```", "", 1)

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        return cleaned.strip()

    def _build_fallback_schema(self, error_details: str, timeframe: str) -> Dict[str, Any]:
        """Provides a safe backup JSON structure if the API call is interrupted."""
        return {
            "asset_pair": "UNKNOWN_OTC",
            "timeframe": timeframe.upper(),
            "primary_trend": "CONSOLIDATION",
            "rejection_zone": "NEUTRAL",
            "volatility_score": 50.0,
            "pattern_detected": "UNCERTAIN_STRUCTURE",
            "buyers_sellers_ratio": "BALANCED",
            "fvg_detected": False,
            "fvg_type": "NONE",
            "liquidity_sweep": False,
            "sweep_side": "NONE",
            "order_block_detected": False,
            "order_block_zone": "NONE",
            "confidence_score": 50.0,
            "predicted_direction": "HOLD",
            "key_support_level": "DYNAMIC_SUPPORT",
            "key_resistance_level": "DYNAMIC_RESISTANCE",
            "analysis_summary": f"Fallback Mode Engaged. Diagnostics: {error_details}"
        }


# Global Instance Export
vision_engine = VisionGeminiEngine()
# Backward Compatibility Instance Alias
GeminiVisionEngine = VisionGeminiEngine

if __name__ == "__main__":
    print(f"Vision Engine Core Initialized. Active Core Model: {GEMINI_MODEL}")
