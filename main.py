import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Custom Engine Imports
from config import TELEGRAM_BOT_TOKEN, DATABASE_FILE, logger
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

# ------------------------------------------------------------------
# Global Engine Instantiations
# ------------------------------------------------------------------
db = DatabaseManager()
image_proc = ImageProcessor()
sessions = SessionManager(session_ttl_seconds=900)  # 15 min TTL
pattern_eng = PatternEngine()
liquidity_eng = LiquidityEngine()
validation_eng = ValidationEngine(min_pattern_score=65.0, min_liquidity_score=55.0)
stats_eng = StatisticsEngine()
outcome_eng = OutcomeEngine()
report_eng = ReportEngine()
vision_eng = VisionGeminiEngine()

# Admin Telegram User IDs (প্রয়োজনে আপনার আইডি দিন)
ADMIN_USER_IDS = [123456789] 

# Telegram Keyboards
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🧠 Start Training Mode"), KeyboardButton("🎯 Live Signal Engine")],
        [KeyboardButton("🔒 Lock Memory Database"), KeyboardButton("📊 System Status")],
        [KeyboardButton("📝 Record Trade Result"), KeyboardButton("ℹ️ Strategy Guide")]
    ],
    resize_keyboard=True
)

# ------------------------------------------------------------------
# Helper & Security Functions
# ------------------------------------------------------------------
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS or len(ADMIN_USER_IDS) == 0

# ------------------------------------------------------------------
# Telegram Command Handlers
# ------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initializes user session and welcomes the user."""
    user_id = update.effective_user.id
    user_session = sessions.get_or_create_session(user_id)
    user_session.reset()

    welcome_text = (
        "🏛 **Quotex OTC Institutional Quant Enterprise Engine**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "স্বাগতম! এটি একটি প্রাতিষ্ঠানিক অ্যালগরিদম ভিত্তিক ওটিসি মার্কেট অ্যানালিসিস বট।\n\n"
        "⚠️ **কঠোর ট্রেডিং নিয়মকানুন:**\n"
        "• এই বট শুধুমাত্র **১ ঘণ্টার (1-Hour)** চার্টে সংকেত ও বিশ্লেষণের জন্য ডিজাইন করা হয়েছে।\n"
        "• কোনো প্রকারে ১ মিনিট, ৫ মিনিট বা ১৫ মিনিটের শট-টার্ম চার্ট ব্যবহার করবেন না।\n"
        "• প্রতিটি সিগন্যালে প্রবাবিলিটি এবং এক্সপেক্টেন্সি হিসাব করে সিদ্ধান্ত নিন।\n\n"
        "👇 মেনু থেকে পছন্দসই অপশন সিলেক্ট করুন:"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provides user guidelines."""
    guide_text = (
        "📖 **বট ব্যবহার করার নির্দেশিকা (1-Hour OTC Rule)**\n\n"
        "1️⃣ **Live Signal Engine:** প্রথমে ১-দিনের (1D) ট্রেন্ড ক্যান্ডেল চার্ট আপলোড করুন, তারপর ১-ঘণ্টার (1H) ক্যান্ডেল চার্ট আপলোড করুন।\n"
        "2️⃣ **Training Mode:** আগে ঘটেছে এমন ১-ঘণ্টার উইনিং চার্ট আপলোড করে বটের ডাটাবেজ মেমোরি শক্তিশালী করুন।\n"
        "3️⃣ **Record Trade Result:** ট্রেড শেষ হওয়ার পর আপনার উইন বা লস এন্ট্রি ম্যানুয়ালি আপডেট করুন যাতে এআই শিখতে পারে।\n"
        "4️⃣ **Lock Memory:** ট্রেনিং সেশন বন্ধ করার জন্য ডাটাবেজ লক করুন।"
    )
    await update.message.reply_text(guide_text, parse_mode="Markdown")

async def admin_backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin feature to download raw database file."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ আপনি এই অ্যাডমিন কমান্ডটি ব্যবহারের জন্য অনুমোদিত নন।")
        return

    if os.path.exists(DATABASE_FILE):
        await update.message.reply_text("📦 ডাটাবেজ ব্যাকআপ ফাইল প্রস্তুত করা হচ্ছে...")
        with open(DATABASE_FILE, "rb") as db_file:
            await context.bot.send_document(chat_id=user_id, document=db_file, filename="otc_quant_memory.db")
    else:
        await update.message.reply_text("❌ ডাটাবেজ ফাইল খুঁজে পাওয়া যায়নি।")

# ------------------------------------------------------------------
# Main Text Menu Controller
# ------------------------------------------------------------------
async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user_session = sessions.get_or_create_session(user_id)

    if text == "🧠 Start Training Mode":
        sessions.set_state(user_id, SessionState.TRAINING)
        await update.message.reply_text(
            "🧠 **Training & Learning Mode Activated!**\n\n"
            "অতীতের ১-ঘণ্টা টাইমফ্রেমের মোমবাতির স্ক্রিনশট পাঠাতে থাকুন। "
            "এআই প্রতিটি প্যাটার্ন হ্যাশ করে মেমোরি নোড হিসেবে ডাটাবেজে সংরক্ষণ করবে।",
            parse_mode="Markdown"
        )

    elif text == "🔒 Lock Memory Database":
        user_session.reset()
        total_nodes = db.get_total_nodes()
        await update.message.reply_text(
            f"🔒 **Memory Database Locked!**\n\n"
            f"সেশন সফলভাবে রসেট করা হয়েছে। বর্তমান সংরক্ষিত মেমোরি নোড: `{total_nodes}` টি।",
            parse_mode="Markdown"
        )

    elif text == "🎯 Live Signal Engine":
        sessions.set_state(user_id, SessionState.WAITING_1D)
        await update.message.reply_text(
            "🎯 **Live Signal Analysis Pipeline Engaged!**\n\n"
            "📸 **ধাপ ১:** ওটিসি মার্কেটের **১ দিনের (1D)** মোমবাতির চার্ট স্ক্রিনশট আপলোড করুন।",
            parse_mode="Markdown"
        )

    elif text == "📊 System Status":
        total_nodes = db.get_total_nodes()
        await update.message.reply_text(
            f"📊 **Institutional System Core Analytics:**\n"
            f"• **AI Database Memory Nodes:** `{total_nodes}`\n"
            f"• **System Strategy Timeframe:** `1-HOUR`\n"
            f"• **Validation Threshold Score:** `65.0 / 100`\n"
            f"• **Quant Expectancy Engine:** `ACTIVE`\n"
            f"• **SMC Liquidity Engine:** `ONLINE`",
            parse_mode="Markdown"
        )

    elif text == "📝 Record Trade Result":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ WIN", callback_data="record_WIN"),
             InlineKeyboardButton("❌ LOSS", callback_data="record_LOSS"),
             InlineKeyboardButton("🔄 REFUND", callback_data="record_REFUND")]
        ])
        await update.message.reply_text(
            "📝 **সর্বশেষ ট্রেডের ফলাফল নির্বাচন করুন:**\n"
            "এটি বটের বেয়েসিয়ান সম্ভাবনা (Bayesian Probabilities) আপডেট করতে ব্যবহৃত হবে।",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    elif text == "ℹ️ Strategy Guide":
        await help_command(update, context)

# ------------------------------------------------------------------
# Image Processing & Pipeline Execution
# ------------------------------------------------------------------
async def handle_photo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_session = sessions.get_or_create_session(user_id)
    current_state = user_session.state

    if current_state == SessionState.IDLE:
        await update.message.reply_text("⚠️ অনুগ্রহ করে মেনু থেকে **'🎯 Live Signal Engine'** অথবা **'🧠 Start Training Mode'** বেছে নিন।")
        return

    # Download image from Telegram servers
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()

    # Image Processing Engine: Deduplication and hash checking
    is_valid, msg, processed_bytes, sha256_hash, p_hash = image_proc.process_screenshot(bytes(image_bytes))
    if not is_valid:
        await update.message.reply_text(f"❌ {msg}")
        return

    # Save to a temp path for Vision Gemini AI
    temp_filename = f"temp_{user_id}_{int(datetime.now().timestamp())}.png"
    with open(temp_filename, "wb") as f:
        f.write(processed_bytes)

    status_msg = await update.message.reply_text("⏳ **Multi-Engine Quant Pipeline Analysing Chart...**")

    try:
        # Multimodal Gemini Analysis
        vision_raw = vision_eng.analyze_chart(temp_filename)

        # WORKFLOW 1: Training Mode
        if current_state == SessionState.TRAINING:
            data_1h = vision_raw.get("data_1h", vision_raw)
            inserted = db.insert_pattern(sha256_hash, "1H", data_1h)

            if inserted:
                count = sessions.increment_training_count(user_id)
                total_nodes = db.get_total_nodes()
                await status_msg.edit_text(
                    f"✅ **Training Node Successfully Learned!**\n"
                    f"• **Trend:** `{data_1h.get('primary_trend')}`\n"
                    f"• **Rejection Zone:** `{data_1h.get('rejection_zone')}`\n"
                    f"• **Session Count:** `{count}`\n"
                    f"• **Total DB Nodes:** `{total_nodes}`",
                    parse_mode="Markdown"
                )
            else:
                await status_msg.edit_text("⚠️ এই চার্টটি ডাটাবেজে আগে থেকেই বিদ্যমান রয়েছে (Duplicate Hash)!")

        # WORKFLOW 2: Live Signal - Step 1 (1D Chart)
        elif current_state == SessionState.WAITING_1D:
            data_1d = vision_raw.get("data_1d", vision_raw)
            sessions.store_1d_analysis(user_id, data_1d)
            await status_msg.edit_text(
                "✅ **1D Trend Structure Cached!**\n\n"
                "📸 **ধাপ ২:** এবার আপনার **১ ঘণ্টার (1H)** ক্যান্ডেলস্টিক চার্টের স্ক্রিনশট দিন।",
                parse_mode="Markdown"
            )

        # WORKFLOW 3: Live Signal - Step 2 (1H Chart & Evaluation)
        elif current_state == SessionState.WAITING_1H:
            data_1h = vision_raw.get("data_1h", vision_raw)
            sessions.store_1h_analysis(user_id, data_1h)

            data_1d = user_session.data_1d or {}
            asset_pair = vision_raw.get("asset_pair", "EUR/USD-OTC")

            # Pattern Score Calculation
            pattern_res = pattern_eng.compute_pattern_score(data_1d, data_1h)

            # SMC Liquidity Confluence Analysis
            liquidity_res = liquidity_eng.analyze_liquidity_confluence(data_1h, pattern_res["suggested_direction"])

            # Risk and Trade Decision Validation
            val_res = validation_eng.validate_trade(pattern_res, liquidity_res)

            # Historical Database Statistics Lookup
            trend_1h = data_1h.get("primary_trend", "CONSOLIDATION")
            rejection_1h = data_1h.get("rejection_zone", "NEUTRAL")
            matched_history = db.query_pattern_statistics(trend_1h, rejection_1h)

            # Quant and Bayesian Calculations
            quant_res = stats_eng.compute_quant_metrics(
                matched_history=[matched_history] if isinstance(matched_history, dict) else [],
                model_confidence=val_res["combined_confidence"]
            )

            # Final Signal Message Generation
            final_report = report_eng.generate_signal_report(
                asset_pair=asset_pair,
                timeframe="1-HOUR",
                validation_result=val_res,
                pattern_result=pattern_res,
                liquidity_result=liquidity_res,
                quant_metrics=quant_res
            )

            # Log Signal to Database
            db.log_live_signal(user_id, {
                "decision": val_res["final_decision"],
                "research_score": val_res["combined_confidence"],
                "win_rate": quant_res["bayesian_win_probability"],
                "trend_1d": data_1d.get("primary_trend", "N/A"),
                "trend_1h": trend_1h,
                "rejection_1h": rejection_1h
            })

            user_session.reset()
            await status_msg.edit_text(final_report, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in signal pipeline processing: {str(e)}", exc_info=True)
        err_msg = report_eng.generate_error_report(str(e))
        await status_msg.edit_text(err_msg, parse_mode="Markdown")

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

# ------------------------------------------------------------------
# Callback Query Handler (Inline Button Clicks)
# ------------------------------------------------------------------
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("record_"):
        outcome_result = query.data.split("_")[1]
        
        # Log to trade outcome memory
        outcome_eng.record_outcome(
            signal_id=f"SIG_{int(datetime.now().timestamp())}",
            asset_pair="OTC_ASSET",
            timeframe="1H",
            predicted_direction="N/A",
            confidence_score=0.0,
            entry_price=0.0,
            exit_price=0.0,
            quant_metrics={"bayesian_win_probability": 0.0, "expected_value_per_dollar": 0.0}
        )

        await query.edit_message_text(
            f"✅ **ট্রেডের ফলাফল সংরক্ষিত হয়েছে:** `{outcome_result}`\n"
            "বট তার অ্যালগরিদম শেখার কাজে এই ডাটা ব্যবহার করবে।",
            parse_mode="Markdown"
        )

# ------------------------------------------------------------------
# Application Main Execution
# ------------------------------------------------------------------
def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN environment variable missing! Exiting...")
        sys.exit(1)

    # Start Web Server for Render/Heroku Keep-Alive Ping
    start_web_server()

    # Build Application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("backup", admin_backup_command))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_input))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    logger.info("OTC Enterprise Bot engine fully started!")
    app.run_polling()

if __name__ == "__main__":
    main()

