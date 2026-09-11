import os
import sys
import json
import logging
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# ============================================================
# PATH
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)


# ============================================================
# TELEGRAM
# ============================================================

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# ============================================================
# CUSTOM MODULES
# ============================================================

try:
    from config import (
        TELEGRAM_BOT_TOKEN,
        DATABASE_FILE,
        logger,
    )

    from database import DatabaseManager
    from image_processor import ImageProcessor
    from session_manager import SessionManager, SessionState
    from pattern_engine import PatternEngine
    from liquidity_engine import LiquidityEngine
    from validation_engine import ValidationEngine
    from statistics_engine import StatisticsEngine
    from outcome_engine import OutcomeEngine
    from report_engine import ReportEngine
    from vision_gemini import VisionGeminiEngine
    from server import start_web_server

except ImportError as err:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger("LiquidityResearchBot")

    logger.critical(
        "Module import failure: %s",
        str(err),
    )

    TELEGRAM_BOT_TOKEN = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        ""
    )

    DATABASE_FILE = os.getenv(
        "DATABASE_FILE",
        "data/research.db"
    )

    DatabaseManager = None
    ImageProcessor = None
    SessionManager = None
    SessionState = None
    PatternEngine = None
    LiquidityEngine = None
    ValidationEngine = None
    StatisticsEngine = None
    OutcomeEngine = None
    ReportEngine = None
    VisionGeminiEngine = None

    def start_web_server():
        return None


# ============================================================
# GLOBAL ENGINES
# ============================================================

db = (
    DatabaseManager()
    if DatabaseManager
    else None
)

image_proc = (
    ImageProcessor()
    if ImageProcessor
    else None
)

sessions = (
    SessionManager(session_ttl_seconds=1800)
    if SessionManager
    else None
)

pattern_eng = (
    PatternEngine()
    if PatternEngine
    else None
)

liquidity_eng = (
    LiquidityEngine()
    if LiquidityEngine
    else None
)

validation_eng = (
    ValidationEngine(
        min_pattern_score=60.0,
        min_liquidity_score=50.0,
    )
    if ValidationEngine
    else None
)

stats_eng = (
    StatisticsEngine()
    if StatisticsEngine
    else None
)

outcome_eng = (
    OutcomeEngine()
    if OutcomeEngine
    else None
)

report_eng = (
    ReportEngine()
    if ReportEngine
    else None
)

vision_eng = (
    VisionGeminiEngine()
    if VisionGeminiEngine
    else None
)


# ============================================================
# CONCURRENCY
# ============================================================

batch_processing_lock = asyncio.Lock()


# ============================================================
# ADMIN
# ============================================================

# নিজের Telegram user ID এখানে দিতে পারো।
# খালি list দিলে diagnostics সবার জন্য open হবে।
ADMIN_USER_IDS = []


def is_admin(user_id: int) -> bool:
    return (
        not ADMIN_USER_IDS
        or user_id in ADMIN_USER_IDS
    )


# ============================================================
# USER SESSION MEMORY
# ============================================================

# 1D এবং 1H screenshot একই analysis session-এ রাখার জন্য।
#
# Structure:
#
# {
#   user_id: {
#       "1D": {
#           "path": "...",
#           "hash": "...",
#           "created_at": "..."
#       },
#       "1H": {
#           ...
#       }
#   }
# }

pending_charts: Dict[int, Dict[str, Dict[str, Any]]] = {}


# ============================================================
# TELEGRAM KEYBOARD
# ============================================================

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            KeyboardButton("🧠 Training Mode"),
            KeyboardButton("🔎 1D + 1H Research"),
        ],
        [
            KeyboardButton("📊 Statistics"),
            KeyboardButton("📝 Record Outcome"),
        ],
        [
            KeyboardButton("🔒 Lock Memory"),
            KeyboardButton("⚡ System Health"),
        ],
        [
            KeyboardButton("❓ Help"),
        ],
    ],
    resize_keyboard=True,
)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_user_id(update: Update) -> Optional[int]:

    if not update.effective_user:
        return None

    return update.effective_user.id


def clean_old_session(user_id: int) -> None:

    if user_id in pending_charts:
        pending_charts[user_id].clear()


def calculate_file_hash(file_path: str) -> str:

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        while True:

            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def safe_json(value: Any) -> Dict[str, Any]:

    if isinstance(value, dict):
        return value

    if isinstance(value, str):

        try:
            parsed = json.loads(value)

            if isinstance(parsed, dict):
                return parsed

        except Exception:
            pass

    return {}


def normalize_bias(value: Any) -> str:

    if not value:
        return "MIXED"

    text = str(value).upper()

    if "BULL" in text:
        return "BULLISH"

    if "BEAR" in text:
        return "BEARISH"

    if "UP" in text:
        return "BULLISH"

    if "DOWN" in text:
        return "BEARISH"

    return "MIXED"


def extract_liquidity_text(result: Dict[str, Any]) -> str:

    possible_fields = [
        "liquidity",
        "liquidity_zone",
        "liquidity_analysis",
        "liquidity_structure",
        "liquidity_observation",
    ]

    for field in possible_fields:

        value = result.get(field)

        if value:
            return str(value)

    return "No clear liquidity information returned."


def extract_structure_text(result: Dict[str, Any]) -> str:

    possible_fields = [
        "structure",
        "market_structure",
        "price_action",
        "candle_structure",
        "candle_anatomy",
    ]

    for field in possible_fields:

        value = result.get(field)

        if value:
            return str(value)

    return "No clear structure information returned."


# ============================================================
# VISION ANALYSIS
# ============================================================

async def analyze_single_chart(
    image_path: str,
    timeframe: str,
) -> Dict[str, Any]:

    if not vision_eng:
        return {
            "timeframe": timeframe,
            "bias": "MIXED",
            "liquidity": "Vision engine unavailable.",
            "structure": "Vision engine unavailable.",
        }

    try:

        # Existing engine support
        if hasattr(
            vision_eng,
            "analyze_chart"
        ):

            result = vision_eng.analyze_chart(
                image_path
            )

            # Async engine support
            if asyncio.iscoroutine(result):
                result = await result

            result = safe_json(result)

            result["timeframe"] = timeframe

            return result

        logger.warning(
            "VisionGeminiEngine has no analyze_chart method."
        )

    except Exception as exc:

        logger.error(
            "Vision analysis failed for %s: %s",
            timeframe,
            str(exc),
            exc_info=True,
        )

    return {
        "timeframe": timeframe,
        "bias": "MIXED",
        "liquidity": "Analysis unavailable.",
        "structure": "Analysis unavailable.",
    }


# ============================================================
# CROSS TIMEFRAME RESEARCH
# ============================================================

def combine_timeframes(
    daily: Dict[str, Any],
    hourly: Dict[str, Any],
) -> Dict[str, Any]:

    daily_bias = normalize_bias(
        daily.get("bias")
        or daily.get("direction")
        or daily.get("trend")
    )

    hourly_bias = normalize_bias(
        hourly.get("bias")
        or hourly.get("direction")
        or hourly.get("trend")
    )

    # --------------------------------------------------------
    # Alignment
    # --------------------------------------------------------

    if (
        daily_bias == hourly_bias
        and daily_bias in [
            "BULLISH",
            "BEARISH",
        ]
    ):
        alignment = "ALIGNED"

        research_bias = daily_bias

    elif (
        daily_bias in [
            "BULLISH",
            "BEARISH",
        ]
        and hourly_bias in [
            "BULLISH",
            "BEARISH",
        ]
        and daily_bias != hourly_bias
    ):
        alignment = "CONFLICT"

        research_bias = "MIXED"

    else:
        alignment = "UNCLEAR"

        research_bias = "MIXED"

    return {
        "research_bias": research_bias,
        "daily_bias": daily_bias,
        "hourly_bias": hourly_bias,
        "alignment": alignment,
    }


# ============================================================
# FORMAT RESEARCH REPORT
# ============================================================

def build_research_report(
    daily: Dict[str, Any],
    hourly: Dict[str, Any],
) -> str:

    combined = combine_timeframes(
        daily,
        hourly,
    )

    bias = combined["research_bias"]

    alignment = combined["alignment"]

    daily_liquidity = extract_liquidity_text(
        daily
    )

    hourly_liquidity = extract_liquidity_text(
        hourly
    )

    daily_structure = extract_structure_text(
        daily
    )

    hourly_structure = extract_structure_text(
        hourly
    )

    report = (
        "🔬 **MULTI-TIMEFRAME LIQUIDITY RESEARCH**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "📅 **1D CONTEXT**\n"
        f"• Research Bias: `{combined['daily_bias']}`\n"
        f"• Liquidity: {daily_liquidity}\n"
        f"• Structure: {daily_structure}\n\n"

        "⏱️ **1H STRUCTURE**\n"
        f"• Research Bias: `{combined['hourly_bias']}`\n"
        f"• Liquidity: {hourly_liquidity}\n"
        f"• Structure: {hourly_structure}\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        "🧩 **1D → 1H RELATIONSHIP**\n"
        f"• Alignment: `{alignment}`\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        f"🧭 **RESEARCH CLASSIFICATION:** `{bias}`\n\n"

        "⚠️ এটি historical/chart research classification।\n"
        "এটি কোনো নিশ্চিত next-candle prediction, "
        "win probability বা real-money execution instruction নয়।"
    )

    return report


# ============================================================
# /START
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    user_id = get_user_id(update)

    if user_id is None:
        return

    clean_old_session(user_id)

    if sessions:

        try:

            session = sessions.get_or_create_session(
                user_id
            )

            session.reset()

        except Exception as exc:

            logger.warning(
                "Session reset failed: %s",
                str(exc),
            )

    welcome = (
        "🔬 **Liquidity Research Bot**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "এই bot historical/chart research-এর জন্য "
        "1D এবং 1H chart structure বিশ্লেষণ করতে পারে।\n\n"

        "📌 **Workflow**\n"
        "1️⃣ Training Mode নির্বাচন করুন\n"
        "2️⃣ 1D screenshot দিন\n"
        "3️⃣ 1H screenshot দিন\n"
        "4️⃣ Bot দুই timeframe-এর liquidity context "
        "compare করবে\n"
        "5️⃣ Research classification দেখাবে\n\n"

        "🔎 Research classification:\n"
        "• BULLISH\n"
        "• BEARISH\n"
        "• MIXED\n"
        "• SKIP\n\n"

        "⚠️ কোনো classification-কে নিশ্চিত ভবিষ্যৎ "
        "candle result হিসেবে ধরা যাবে না।"
    )

    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )


# ============================================================
# HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    text = (
        "❓ **HELP**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "🧠 **Training Mode**\n"
        "Historical chart screenshot memory/research-এর "
        "জন্য ব্যবহার করুন।\n\n"

        "🔎 **1D + 1H Research**\n"
        "প্রথমে 1D এবং পরে 1H screenshot দিন।\n\n"

        "📝 **Record Outcome**\n"
        "Historical sample-এর পরে actual outcome "
        "record করার জন্য।\n\n"

        "📊 **Statistics**\n"
        "Stored research samples-এর statistics দেখাবে।\n\n"

        "🔒 **Lock Memory**\n"
        "Current image session বন্ধ করবে।"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
    )


# ============================================================
# DIAGNOSTICS
# ============================================================

async def diagnostics_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    user_id = get_user_id(update)

    if user_id is None:
        return

    if not is_admin(user_id):

        await update.message.reply_text(
            "⛔ Diagnostics access restricted."
        )

        return

    try:

        total_nodes = (
            db.get_total_nodes()
            if db and hasattr(
                db,
                "get_total_nodes"
            )
            else 0
        )

    except Exception:

        total_nodes = 0

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    report = (
        "⚡ **SYSTEM HEALTH**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• UTC: `{timestamp}`\n"
        f"• Database nodes: `{total_nodes}`\n"
        f"• Vision Engine: `{'READY' if vision_eng else 'MISSING'}`\n"
        f"• Liquidity Engine: `{'READY' if liquidity_eng else 'MISSING'}`\n"
        f"• Pattern Engine: `{'READY' if pattern_eng else 'MISSING'}`\n"
        f"• Outcome Engine: `{'READY' if outcome_eng else 'MISSING'}`\n"
        f"• Statistics Engine: `{'READY' if stats_eng else 'MISSING'}`\n"
        "• Mode: `HISTORICAL / RESEARCH`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ System check completed."
    )

    await update.message.reply_text(
        report,
        parse_mode="Markdown",
    )


# ============================================================
# TEXT MENU
# ============================================================

async def handle_text_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    user_id = get_user_id(update)

    if user_id is None:
        return

    text = (
        update.message.text.strip()
        if update.message
        and update.message.text
        else ""
    )

    # --------------------------------------------------------
    # TRAINING
    # --------------------------------------------------------

    if text in [
        "🧠 Training Mode",
        "🧠 Deep Pattern Training Mode",
    ]:

        clean_old_session(user_id)

        if sessions and SessionState:

            try:
                sessions.set_state(
                    user_id,
                    SessionState.TRAINING,
                )
            except Exception as exc:

                logger.warning(
                    "Training state failed: %s",
                    str(exc),
                )

        await update.message.reply_text(
            "🧠 **TRAINING MODE ACTIVE**\n\n"
            "Historical 1D অথবা 1H chart screenshot পাঠান।\n\n"
            "প্রথম screenshot-এর আগে লিখুন:\n"
            "`1D`\n\n"
            "তারপর দ্বিতীয় screenshot-এর আগে লিখুন:\n"
            "`1H`\n\n"
            "Bot দুইটি chart একই research session-এ রাখবে।",
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # RESEARCH
    # --------------------------------------------------------

    elif text in [
        "🔎 1D + 1H Research",
        "🎯 Deep 1H Signal Engine",
    ]:

        clean_old_session(user_id)

        if sessions and SessionState:

            try:
                sessions.set_state(
                    user_id,
                    SessionState.ANALYZING_1H,
                )
            except Exception:
                pass

        await update.message.reply_text(
            "🔎 **1D + 1H RESEARCH MODE**\n\n"
            "প্রথমে `1D` লিখে 1D screenshot পাঠান।\n"
            "তারপর `1H` লিখে 1H screenshot পাঠান।\n\n"
            "দুই timeframe-এর liquidity structure "
            "compare করা হবে।",
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # LOCK
    # --------------------------------------------------------

    elif text in [
        "🔒 Lock Memory",
        "🔒 Lock Memory Core",
    ]:

        clean_old_session(user_id)

        if sessions:

            try:
                sessions.clear_session(
                    user_id
                )
            except Exception:
                pass

        await update.message.reply_text(
            "🔒 **Research Session Locked**\n\n"
            "Current 1D/1H screenshot session cleared."
        )

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    elif text in [
        "📊 Statistics",
        "📊 Advanced Market Diagnostics",
    ]:

        try:

            total_nodes = (
                db.get_total_nodes()
                if db
                and hasattr(
                    db,
                    "get_total_nodes"
                )
                else 0
            )

        except Exception:

            total_nodes = 0

        await update.message.reply_text(
            "📊 **RESEARCH STATISTICS**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Stored nodes: `{total_nodes}`\n"
            "Mode: `Historical Research`\n\n"
            "বেশি historical samples জমা হলে "
            "statistics আরও meaningful হবে।",
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # OUTCOME
    # --------------------------------------------------------

    elif text in [
        "📝 Record Outcome",
        "📝 Record Trade Outcome",
    ]:

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🟢 BULLISH",
                        callback_data="outcome_BULLISH",
                    ),
                    InlineKeyboardButton(
                        "🔴 BEARISH",
                        callback_data="outcome_BEARISH",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "⚪ MIXED",
                        callback_data="outcome_MIXED",
                    ),
                ],
            ]
        )

        await update.message.reply_text(
            "📝 **Historical Outcome Record**\n\n"
            "পরবর্তী historical candle-এর actual "
            "direction দেখে outcome নির্বাচন করুন।",
            reply_markup=keyboard,
        )

    # --------------------------------------------------------
    # HEALTH
    # --------------------------------------------------------

    elif text in [
        "⚡ System Health",
        "⚡ System Health Check",
    ]:

        await diagnostics_command(
            update,
            context,
        )

    # --------------------------------------------------------
    # HELP
    # --------------------------------------------------------

    elif text == "❓ Help":

        await help_command(
            update,
            context,
        )

    # --------------------------------------------------------
    # 1D / 1H LABEL
    # --------------------------------------------------------

    elif text.upper() in [
        "1D",
        "1H",
    ]:

        timeframe = text.upper()

        if user_id not in pending_charts:

            pending_charts[user_id] = {}

        pending_charts[user_id]["requested_timeframe"] = {
            "timeframe": timeframe,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        await update.message.reply_text(
            f"✅ `{timeframe}` selected.\n\n"
            f"এখন {timeframe} chart screenshot পাঠান।",
            parse_mode="Markdown",
        )


# ============================================================
# PHOTO HANDLER
# ============================================================

async def handle_photo_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    user_id = get_user_id(update)

    if user_id is None:
        return

    # --------------------------------------------------------
    # RATE LIMIT
    # --------------------------------------------------------

    if sessions:

        try:

            allowed, rate_msg = (
                sessions.validate_request_rate(
                    user_id
                )
            )

            if not allowed:

                await update.message.reply_text(
                    rate_msg
                )

                return

        except Exception as exc:

            logger.warning(
                "Rate validation failed: %s",
                str(exc),
            )

    # --------------------------------------------------------
    # TIMEFRAME
    # --------------------------------------------------------

    requested = (
        pending_charts
        .get(user_id, {})
        .get("requested_timeframe")
    )

    if not requested:

        await update.message.reply_text(
            "⚠️ আগে `1D` অথবা `1H` লিখে timeframe নির্বাচন করুন।"
        )

        return

    timeframe = requested["timeframe"]

    status_msg = await update.message.reply_text(
        f"🔍 **{timeframe} chart received.**\n"
        "Liquidity research চলছে...\n"
        "⏳ একটু অপেক্ষা করুন...",
        parse_mode="Markdown",
    )

    temp_filename = None

    try:

        # ----------------------------------------------------
        # LOCK
        # ----------------------------------------------------

        async with batch_processing_lock:

            # ------------------------------------------------
            # DOWNLOAD
            # ------------------------------------------------

            photo = update.message.photo[-1]

            photo_file = await photo.get_file()

            image_bytes = (
                await photo_file.download_as_bytearray()
            )

            # ------------------------------------------------
            # TEMP FILE
            # ------------------------------------------------

            temp_filename = os.path.join(
                CURRENT_DIR,
                (
                    f"temp_{user_id}_"
                    f"{timeframe}_"
                    f"{int(datetime.now().timestamp())}.jpg"
                ),
            )

            with open(
                temp_filename,
                "wb",
            ) as file:

                file.write(image_bytes)

            # ------------------------------------------------
            # HASH
            # ------------------------------------------------

            image_hash = calculate_file_hash(
                temp_filename
            )

            # ------------------------------------------------
            # DUPLICATE CHECK
            # ------------------------------------------------

            existing = (
                pending_charts
                .get(user_id, {})
                .get(timeframe)
            )

            if (
                existing
                and existing.get("hash")
                == image_hash
            ):

                await status_msg.edit_text(
                    "⚠️ একই screenshot আবার পাঠানো হয়েছে।"
                )

                return

            # ------------------------------------------------
            # VISION
            # ------------------------------------------------

            result = await analyze_single_chart(
                temp_filename,
                timeframe,
            )

            # ------------------------------------------------
            # STORE SESSION
            # ------------------------------------------------

            if user_id not in pending_charts:

                pending_charts[user_id] = {}

            pending_charts[user_id][timeframe] = {
                "path": temp_filename,
                "hash": image_hash,
                "result": result,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            # requested flag remove
            pending_charts[user_id].pop(
                "requested_timeframe",
                None,
            )

            # ------------------------------------------------
            # RESPONSE
            # ------------------------------------------------

            available = pending_charts[
                user_id
            ]

            if (
                "1D" in available
                and "1H" in available
            ):

                daily_result = available[
                    "1D"
                ]["result"]

                hourly_result = available[
                    "1H"
                ]["result"]

                report = build_research_report(
                    daily_result,
                    hourly_result,
                )

                await status_msg.edit_text(
                    report,
                    parse_mode="Markdown",
                )

            else:

                missing = (
                    "1H"
                    if timeframe == "1D"
                    else "1D"
                )

                await status_msg.edit_text(
                    f"✅ **{timeframe} analysis stored.**\n\n"
                    f"এখন `{missing}` screenshot দিন।\n\n"
                    "তারপর 1D + 1H cross-timeframe "
                    "research report তৈরি হবে।",
                    parse_mode="Markdown",
                )

    except Exception as exc:

        logger.error(
            "Photo pipeline error: %s",
            str(exc),
            exc_info=True,
        )

        await status_msg.edit_text(
            "❌ **Analysis failed.**\n\n"
            "Screenshot পরিষ্কারভাবে পাঠান এবং "
            "সঠিক timeframe নির্বাচন করুন।",
            parse_mode="Markdown",
        )

    finally:

        # ----------------------------------------------------
        # IMPORTANT:
        # We do NOT delete the temp file immediately if
        # it is being held for 1D+1H comparison.
        # Old files can be cleaned later.
        # ----------------------------------------------------

        pass


# ============================================================
# CALLBACK
# ============================================================

async def handle_callback_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    query = update.callback_query

    await query.answer()

    data = query.data or ""

    if data.startswith(
        "outcome_"
    ):

        outcome = data.split(
            "_",
            1
        )[1]

        # ----------------------------------------------------
        # Optional database integration
        # ----------------------------------------------------

        saved = False

        if db:

            possible_methods = [
                "record_outcome",
                "save_outcome",
                "add_outcome",
            ]

            for method_name in possible_methods:

                if hasattr(
                    db,
                    method_name
                ):

                    try:

                        method = getattr(
                            db,
                            method_name
                        )

                        method(
                            user_id=query.from_user.id,
                            outcome=outcome,
                        )

                        saved = True

                        break

                    except TypeError:

                        # Different signature.
                        # Do not crash the bot.
                        continue

                    except Exception as exc:

                        logger.warning(
                            "Outcome save failed: %s",
                            str(exc),
                        )

                        break

        status = (
            "saved to research database"
            if saved
            else "recorded for the current session"
        )

        await query.edit_message_text(
            "📝 **Historical Outcome Recorded**\n\n"
            f"Outcome: `{outcome}`\n"
            f"Status: `{status}`\n\n"
            "এই data পরে historical error/statistics "
            "analysis-এ ব্যবহার করা যাবে।",
            parse_mode="Markdown",
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    logger.error(
        "Telegram handler error: %s",
        context.error,
        exc_info=True,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    token = (
        TELEGRAM_BOT_TOKEN
        or os.getenv(
            "BOT_TOKEN",
            ""
        )
    )

    if not token:

        logger.critical(
            "TELEGRAM_BOT_TOKEN is missing."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # WEB SERVER
    # --------------------------------------------------------

    try:

        start_web_server()

    except Exception as exc:

        logger.warning(
            "Web server failed to start: %s",
            str(exc),
        )

    # --------------------------------------------------------
    # TELEGRAM APP
    # --------------------------------------------------------

    application = (
        ApplicationBuilder()
        .token(token)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "diagnostics",
            diagnostics_command,
        )
    )

    # Text menu
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_text_menu,
        )
    )

    # Photos
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo_input,
        )
    )

    # Buttons
    application.add_handler(
        CallbackQueryHandler(
            handle_callback_query
        )
    )

    # Errors
    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Liquidity Research Bot started."
    )

    # --------------------------------------------------------
    # POLLING
    # --------------------------------------------------------

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
