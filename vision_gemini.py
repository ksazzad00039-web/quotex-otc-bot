import os
import io
import json
import time
import logging
from typing import Dict, Any, Union, Optional

import PIL.Image
import google.generativeai as genai


# ============================================================
# CONFIG
# ============================================================

try:
    from config import (
        GEMINI_API_KEY,
        GEMINI_MODEL,
        logger,
    )

except ImportError:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(
        "LiquidityResearchBot.Vision"
    )

    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY"
    )

    GEMINI_MODEL = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash",
    )


# ============================================================
# VISION ENGINE
# ============================================================

class VisionGeminiEngine:
    """
    Gemini multimodal engine for historical/chart liquidity research.

    Supported:
        - 1D chart analysis
        - 1H chart analysis
        - Candle anatomy
        - Liquidity mapping
        - High/Low liquidity
        - Equal High / Equal Low
        - Swing liquidity
        - Internal / External liquidity
        - Sweep observation
        - Rejection / continuation
        - Range liquidity
        - Multi-timeframe context

    This engine does NOT produce:
        - guaranteed next-candle predictions
        - real-money trade instructions
        - staking recommendations
        - fake probability scores
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):

        self.api_key = (
            api_key
            or GEMINI_API_KEY
        )

        self.model_name = (
            model_name
            or GEMINI_MODEL
        )

        self.model = None

        self._bootstrap()


    # ========================================================
    # BOOTSTRAP
    # ========================================================

    def _bootstrap(self) -> None:

        if not self.api_key:

            logger.warning(
                "GEMINI_API_KEY is missing. "
                "Vision engine will remain unavailable."
            )

            return

        try:

            genai.configure(
                api_key=self.api_key
            )

            self.model = (
                genai.GenerativeModel(
                    self.model_name
                )
            )

            logger.info(
                "Gemini Vision initialized: %s",
                self.model_name,
            )

        except Exception as exc:

            logger.error(
                "Gemini initialization failed: %s",
                str(exc),
                exc_info=True,
            )

            self.model = None


    # ========================================================
    # PROMPT
    # ========================================================

    def _build_research_prompt(
        self,
        timeframe_context: str,
    ) -> str:

        timeframe = (
            timeframe_context
            .strip()
            .upper()
        )

        return f"""
You are a chart-vision research assistant.

Analyze the supplied candlestick chart screenshot
strictly as HISTORICAL / EDUCATIONAL MARKET-STRUCTURE
research.

Chart timeframe:
{timeframe}

IMPORTANT:

Do not claim to know any private broker algorithm.

Do not assume that a synthetic/OTC market has a known
manipulation algorithm.

Do not give a guaranteed future candle direction.

Do not provide betting instructions.

Do not provide stake size.

Do not provide Kelly calculations.

Do not invent probability or accuracy percentages.

Only describe what is visually observable or reasonably
inferable from the supplied chart.

============================================================
LIQUIDITY ANALYSIS
============================================================

Analyze these categories when visible:

1. Previous High
2. Previous Low
3. Recent Swing High
4. Recent Swing Low
5. Equal Highs
6. Equal Lows
7. Range High
8. Range Low
9. Internal Liquidity
10. External Liquidity
11. Buy-side liquidity observation
12. Sell-side liquidity observation
13. Possible liquidity sweep
14. Sweep direction
15. Wick rejection
16. Candle close location
17. Breakout
18. Failed breakout
19. Rejection
20. Continuation
21. Liquidity void / thin area
22. Compression before expansion
23. Expansion after compression
24. High-volatility candle behaviour
25. Low-volatility/choppy behaviour

============================================================
CANDLE ANATOMY
============================================================

Observe:

- body size
- upper wick
- lower wick
- body-to-range relationship
- close location
- consecutive bullish candles
- consecutive bearish candles
- inside candle if visible
- engulfing behaviour if clearly visible
- rejection candle if clearly visible

Do NOT invent a named candlestick pattern when the
screenshot does not clearly support it.

============================================================
LIQUIDITY EVENT CLASSIFICATION
============================================================

Classify the visible situation as one of:

CLEAR_SWEEP
POSSIBLE_SWEEP
BREAKOUT
FAILED_BREAKOUT
REJECTION
CONTINUATION
RANGE
UNCLEAR

============================================================
RESEARCH BIAS
============================================================

Based ONLY on the visible structure, classify:

BULLISH
BEARISH
MIXED
SKIP

This is a CURRENT CHART RESEARCH BIAS.

It is NOT a guaranteed prediction of the next candle.

============================================================
VISUAL QUALITY
============================================================

Determine:

GOOD
FAIR
POOR

If the chart is too blurry, cropped, or missing important
price information, use SKIP rather than guessing.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use exactly this structure:

{{
    "asset_pair": "UNKNOWN",
    "timeframe": "{timeframe}",
    "visual_quality": "GOOD / FAIR / POOR",

    "primary_structure":
        "TREND / RANGE / TRANSITION / UNCLEAR",

    "research_bias":
        "BULLISH / BEARISH / MIXED / SKIP",

    "liquidity_event":
        "CLEAR_SWEEP / POSSIBLE_SWEEP / BREAKOUT / FAILED_BREAKOUT / REJECTION / CONTINUATION / RANGE / UNCLEAR",

    "liquidity_side":
        "BUY_SIDE / SELL_SIDE / BOTH / NONE",

    "previous_high":
        "VISIBLE / NOT_VISIBLE",

    "previous_low":
        "VISIBLE / NOT_VISIBLE",

    "swing_high":
        "VISIBLE / NOT_VISIBLE",

    "swing_low":
        "VISIBLE / NOT_VISIBLE",

    "equal_highs":
        "VISIBLE / NOT_VISIBLE",

    "equal_lows":
        "VISIBLE / NOT_VISIBLE",

    "range_high":
        "VISIBLE / NOT_VISIBLE",

    "range_low":
        "VISIBLE / NOT_VISIBLE",

    "internal_liquidity":
        "VISIBLE / NOT_VISIBLE / UNCLEAR",

    "external_liquidity":
        "VISIBLE / NOT_VISIBLE / UNCLEAR",

    "sweep_observation":
        "Detailed visual observation",

    "rejection_observation":
        "Detailed wick/close observation",

    "breakout_observation":
        "Detailed breakout or failed-breakout observation",

    "candle_anatomy": {{
        "body":
            "SMALL / MEDIUM / LARGE / UNCLEAR",

        "upper_wick":
            "SHORT / MEDIUM / LONG / UNCLEAR",

        "lower_wick":
            "SHORT / MEDIUM / LONG / UNCLEAR",

        "close_location":
            "UPPER_RANGE / MIDDLE / LOWER_RANGE / UNCLEAR"
    }},

    "liquidity_zones": [
        {{
            "type":
                "PREVIOUS_HIGH / PREVIOUS_LOW / SWING_HIGH / SWING_LOW / EQUAL_HIGH / EQUAL_LOW / RANGE_HIGH / RANGE_LOW / OTHER",

            "side":
                "BUY_SIDE / SELL_SIDE / UNKNOWN",

            "observation":
                "What is visibly present"
        }}
    ],

    "market_behaviour":
        "TRENDING / RANGING / CHOPPY / EXPANDING / COMPRESSING / UNCLEAR",

    "research_notes":
        [
            "Observation 1",
            "Observation 2",
            "Observation 3"
        ]
}}
"""


    # ========================================================
    # IMAGE LOADER
    # ========================================================

    def _load_image(
        self,
        image_input: Union[bytes, str],
    ):

        if isinstance(
            image_input,
            bytes,
        ):

            image = PIL.Image.open(
                io.BytesIO(image_input)
            )

        elif isinstance(
            image_input,
            str,
        ):

            if not os.path.exists(
                image_input
            ):

                raise FileNotFoundError(
                    f"Image not found: {image_input}"
                )

            image = PIL.Image.open(
                image_input
            )

        else:

            raise TypeError(
                "image_input must be bytes "
                "or a file path."
            )

        # Convert unusual image modes
        if image.mode not in [
            "RGB",
            "RGBA",
        ]:

            image = image.convert(
                "RGB"
            )

        return image


    # ========================================================
    # JSON SANITIZER
    # ========================================================

    def _sanitize_json(
        self,
        raw_text: str,
    ) -> str:

        if not raw_text:

            raise ValueError(
                "Gemini returned empty response."
            )

        text = raw_text.strip()

        # Remove markdown fences
        if text.startswith(
            "```json"
        ):

            text = text[
                len("```json"):
            ]

        elif text.startswith(
            "```"
        ):

            text = text[
                len("```"):
            ]

        if text.endswith(
            "```"
        ):

            text = text[
                :-3
            ]

        text = text.strip()

        # Handle accidental prose around JSON
        first = text.find("{")
        last = text.rfind("}")

        if (
            first >= 0
            and last >= 0
            and last > first
        ):

            text = text[
                first:last + 1
            ]

        return text.strip()


    # ========================================================
    # NORMALIZER
    # ========================================================

    def _normalize_result(
        self,
        data: Dict[str, Any],
        timeframe: str,
    ) -> Dict[str, Any]:

        if not isinstance(
            data,
            dict,
        ):

            return self._fallback(
                "Invalid Gemini object.",
                timeframe,
            )

        # --------------------------------------------
        # Research bias
        # --------------------------------------------

        bias = str(
            data.get(
                "research_bias",
                "SKIP",
            )
        ).upper()

        allowed_bias = {
            "BULLISH",
            "BEARISH",
            "MIXED",
            "SKIP",
        }

        if bias not in allowed_bias:
            bias = "SKIP"

        data[
            "research_bias"
        ] = bias

        # --------------------------------------------
        # Timeframe
        # --------------------------------------------

        data[
            "timeframe"
        ] = timeframe.upper()

        # --------------------------------------------
        # Visual quality
        # --------------------------------------------

        quality = str(
            data.get(
                "visual_quality",
                "FAIR",
            )
        ).upper()

        if quality not in {
            "GOOD",
            "FAIR",
            "POOR",
        }:

            quality = "FAIR"

        data[
            "visual_quality"
        ] = quality

        # --------------------------------------------
        # Ensure arrays
        # --------------------------------------------

        if not isinstance(
            data.get(
                "liquidity_zones"
            ),
            list,
        ):

            data[
                "liquidity_zones"
            ] = []

        if not isinstance(
            data.get(
                "research_notes"
            ),
            list,
        ):

            data[
                "research_notes"
            ] = []

        # --------------------------------------------
        # Candle anatomy
        # --------------------------------------------

        anatomy = data.get(
            "candle_anatomy"
        )

        if not isinstance(
            anatomy,
            dict,
        ):

            anatomy = {}

        data[
            "candle_anatomy"
        ] = anatomy

        return data


    # ========================================================
    # ANALYZE
    # ========================================================

    def analyze_chart(
        self,
        image_input: Union[bytes, str],
        timeframe_hint: str = "1H",
        max_retries: int = 3,
    ) -> Dict[str, Any]:

        timeframe = (
            timeframe_hint
            .strip()
            .upper()
        )

        if not self.model:

            return self._fallback(
                "Gemini Vision engine unavailable.",
                timeframe,
            )

        image = None
        raw_text = ""

        try:

            image = self._load_image(
                image_input
            )

            prompt = (
                self._build_research_prompt(
                    timeframe
                )
            )

            # ----------------------------------------
            # Retry loop
            # ----------------------------------------

            for attempt in range(
                1,
                max_retries + 1,
            ):

                try:

                    logger.info(
                        "Gemini chart research "
                        "attempt %s/%s | %s",
                        attempt,
                        max_retries,
                        timeframe,
                    )

                    response = (
                        self.model.generate_content(
                            [
                                prompt,
                                image,
                            ]
                        )
                    )

                    raw_text = (
                        getattr(
                            response,
                            "text",
                            "",
                        )
                        or ""
                    ).strip()

                    if raw_text:

                        break

                except Exception as api_error:

                    logger.warning(
                        "Gemini attempt failed: %s",
                        str(api_error),
                    )

                    if attempt >= max_retries:

                        raise

                    time.sleep(
                        min(
                            2 ** (attempt - 1),
                            5,
                        )
                    )

            # ----------------------------------------
            # Parse
            # ----------------------------------------

            clean_json = (
                self._sanitize_json(
                    raw_text
                )
            )

            parsed = json.loads(
                clean_json
            )

            result = self._normalize_result(
                parsed,
                timeframe,
            )

            logger.info(
                "Chart research completed | "
                "TF=%s | Bias=%s | Event=%s",
                timeframe,
                result.get(
                    "research_bias"
                ),
                result.get(
                    "liquidity_event"
                ),
            )

            return result

        except json.JSONDecodeError as exc:

            logger.error(
                "Gemini JSON parsing failed: %s | "
                "Raw=%s",
                str(exc),
                raw_text[:300],
            )

            return self._fallback(
                "Invalid JSON returned by Gemini.",
                timeframe,
            )

        except Exception as exc:

            logger.error(
                "Vision analysis failed: %s",
                str(exc),
                exc_info=True,
            )

            return self._fallback(
                str(exc),
                timeframe,
            )


    # ========================================================
    # FALLBACK
    # ========================================================

    def _fallback(
        self,
        error_details: str,
        timeframe: str,
    ) -> Dict[str, Any]:

        return {

            "asset_pair":
                "UNKNOWN",

            "timeframe":
                timeframe.upper(),

            "visual_quality":
                "POOR",

            "primary_structure":
                "UNCLEAR",

            "research_bias":
                "SKIP",

            "liquidity_event":
                "UNCLEAR",

            "liquidity_side":
                "NONE",

            "previous_high":
                "NOT_VISIBLE",

            "previous_low":
                "NOT_VISIBLE",

            "swing_high":
                "NOT_VISIBLE",

            "swing_low":
                "NOT_VISIBLE",

            "equal_highs":
                "NOT_VISIBLE",

            "equal_lows":
                "NOT_VISIBLE",

            "range_high":
                "NOT_VISIBLE",

            "range_low":
                "NOT_VISIBLE",

            "internal_liquidity":
                "UNCLEAR",

            "external_liquidity":
                "UNCLEAR",

            "sweep_observation":
                "Unavailable.",

            "rejection_observation":
                "Unavailable.",

            "breakout_observation":
                "Unavailable.",

            "candle_anatomy": {
                "body":
                    "UNCLEAR",

                "upper_wick":
                    "UNCLEAR",

                "lower_wick":
                    "UNCLEAR",

                "close_location":
                    "UNCLEAR",
            },

            "liquidity_zones":
                [],

            "market_behaviour":
                "UNCLEAR",

            "research_notes": [
                "Vision analysis unavailable.",
                str(error_details),
            ],
        }


# ============================================================
# GLOBAL INSTANCE
# ============================================================

vision_engine = VisionGeminiEngine()

# Backward compatibility
GeminiVisionEngine = VisionGeminiEngine


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Liquidity Research Vision Engine initialized."
    )

    print(
        f"Model: {GEMINI_MODEL}"
        )
