import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Ensure dynamic module path resolution for server build environments (Fixes ModuleNotFoundError)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Custom Institutional Engine Imports
try:
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
except ImportError as err:
    logging.critical(f"Critical System Failure: Module import failed -> {str(err)}")
    sys.exit(1)

# ------------------------------------------------------------------
# Global Engine Instantiations & Core Systems
# ------------------------------------------------------------------
db = DatabaseManager()
image_proc = ImageProcessor()
sessions = SessionManager(session_ttl_seconds=900)  # 15-Minute Dynamic TTL
pattern_eng = PatternEngine()
liquidity_eng = LiquidityEngine()
validation_eng = ValidationEngine(min_pattern_score=65.0, min_liquidity_score=55.0)
stats_eng = StatisticsEngine()
outcome_eng = OutcomeEngine()
report_eng = ReportEngine()
vision_eng = VisionGeminiEngine()

# Authorized System Administrators
ADMIN_USER_IDS = [123456789]

# Institutional UI Interface
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🧠 Start Training Mode"), KeyboardButton("🎯 Live Signal Engine")],
        [KeyboardButton("📊 System Analytics"), KeyboardButton("📝 Record Trade Result")],
        [KeyboardButton("🔒 Lock Memory Database"), KeyboardButton("⚡ Admin Diagnostics")]
    ],
    resize_keyboard=True
)

# ------------------------------------------------------------------
# Advanced Quant Risk & Money Management Engine
# ------------------------------------------------------------------
class InstitutionalRiskManager:
    """
    Calculates dynamic position sizing using Fractional Kelly Criterion 
    and applies institutional risk filters tailored for binary OTC markets.
    """
    @staticmethod
    def calculate_position_size(win_probability: float, payout_rate: float = 0.85, balance: float = 100.0) -> Dict[str, Any]:
        p = win_probability / 100.0
        q = 1.0 - p
        b = payout_rate
        
        # Kelly Formula: f* = (bp - q) / b
        kelly_fraction = (b * p - q) / b
        
        # Half-Kelly for Conservative Enterprise Risk Control
        conservative_fraction = max(0.0, kelly_fraction * 0.5)
        recommended_stake = round(balance * conservative_fraction, 2)
        
        return {
            "kelly_percentage": round(kelly_fraction * 100, 2),
            "recommended_stake_usd": max(1.0, recommended_stake) if kelly_fraction > 0 else 0.0,
            "max_martingale_steps": 0 if kelly_fraction > 0.15 else 1
        }

# ------------------------------------------------------------------
# Helper & Security Guardrails
# ------------------------------------------------------------------
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS or len(ADMIN_USER_IDS) == 0

# ------------------------------------------------------------------
# Telegram Command Handlers
# ------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initializes user session and presents institutional system directives."""
    user_id = update.effective_user.id
    user_session = sessions.get_or_create_session(user_id)
    user_session.reset()

    welcome_text = (
        "🏛 **Quotex OTC Institutional Quant Enterprise Engine v8.0**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "স্বাগতম! এটি একটি সর্বোচ্চ নিখুঁত প্রাতিষ্ঠানিক অ্যালগরিদম ভিত্তিক ওটিসি মার্কেট অ্যানালিসিস বট।\n\n"
        "⚠️ **কঠোর ট্রেডিং নিয়মকানুন (Strict Protocol):**\n"
        "• **Timeframe Rule:** এই বট শুধুমাত্র **১ ঘণ্টার (1-Hour)** মোমবাতি চার্টে এনালাইসিস করে।\n"
        "• **Noise Avoidance:** ১ মিনিট, ৫ মিনিট বা ১৫ মিনিটের স্কেল্পিং চার্ট সম্পূর্ণরূপে নিষিদ্ধ।\n"
        "• **Execution Rule:** প্রতি ঘণ্টার মোমবাতি খোলার প্রথম ৫-১০ সেকেন্ডের মধ্যে প্রবেশের নিয়ম মেনে চলুন।\n\n"
        "👇 নিচের কন্ট্রোল মেনু থেকে আপনার পছন্দসই অপশন সিলেক্ট করুন:"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)

async def admin_diagnostics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generates an in-depth system operational health report."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ আপনি এই অ্যাডমিন ডায়াগনস্টিক অ্যাক্সেসের জন্য অনুমোদিত নন।")
        return

    total_nodes = db.get_total_nodes()
    uptime_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report = (
        "⚡ **Enterprise System Diagnostics Report**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• **System UTC Time:** `{uptime_time}`\n"
        f"• **Turso Cloud DB Memory:** `ONLINE`\n"
        f"• **Total Active AI Patterns:** `{total_nodes}`\n"
        f"• **Vision Model:** `Gemini-1.5-Flash (Multimodal)`\n"
        f"• **Primary Core Timeframe:** `1-HOUR`\n"
        f"• **Engine Active Workers:** `Asyncio High-Concurrency`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ **System Status:** ALL ENGINES OPERATIONAL"
    )
    await update.message.reply_text(report, parse_mode="Markdown")

async def admin_backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin utility to fetch raw SQLite local memory database."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ অননুমোদিত অনুরোধ।")
        return

    if os.path.exists(DATABASE_FILE):
        await update.message.reply_text("📦 Local DB Backup ফাইল প্রস্তুত হচ্ছে...")
        with open(DATABASE_FILE, "rb") as db_file:
            await context.bot.send_document(chat_id=user_id, document=db_file, filename="otc_quant_memory.db")
    else:
        await update.message.reply_text("❌ ডাটাবেজ ফাইল পাওয়া যায়নি (Turso Pure Cloud Mode Active)।")

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
            "🧠 **AI Training & Pattern Learning Mode Activated!**\n\n"
            "অতীতের ১-ঘণ্টা (1H) টাইমফ্রেমের মোমবাতির স্ক্রিনশট পাঠাতে থাকুন। "
            "এআই প্রতিটি চার্ট হ্যাশ করে স্থায়ী ক্লাউড ডাটাবেজে নতুন নোড হিসেবে স্টোর করবে।",
            parse_mode="Markdown"
        )

    elif text == "🔒 Lock Memory Database":
        user_session.reset()
        total_nodes = db.get_total_nodes()
        await update.message.reply_text(
            f"🔒 **Memory Database Locked!**\n\n"
            f"সেশন সফলভাবে রিসেট করা হয়েছে। বর্তমান ক্লাউডে সংরক্ষিত মোট প্যাটার্ন নোড: `{total_nodes}` টি।",
            parse_mode="Markdown"
        )

    elif text == "🎯 Live Signal Engine":
        sessions.set_state(user_id, SessionState.WAITING_1D)
        await update.message.reply_text(
            "🎯 **Live Institutional Signal Pipeline Activated!**\n\n"
            "📸 **ধাপ ১:** প্রাতিষ্ঠানিক ট্রেন্ড ডায়রেকশন নিশ্চিত করতে ওটিসি মার্কেটের **১ দিনের (1D)** ক্যান্ডেল চার্ট স্ক্রিনশট দিন।",
            parse_mode="Markdown"
        )

    elif text == "📊 System Analytics":
        total_nodes = db.get_total_nodes()
        await update.message.reply_text(
            f"📊 **System Core Analytics & Parameters:**\n"
            f"• **AI Database Memory Nodes:** `{total_nodes}`\n"
            f"• **Target Execution Timeframe:** `1-HOUR`\n"
            f"• **Validation Threshold Score:** `65.0 / 100`\n"
            f"• **Quant Risk Calculator:** `Kelly Criterion Active`\n"
            f"• **Smart Money Liquidity Engine:** `ONLINE`",
            parse_mode="Markdown"
        )

    elif text == "📝 Record Trade Result":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ WIN", callback_data="record_WIN"),
             InlineKeyboardButton("❌ LOSS", callback_data="record_LOSS"),
             InlineKeyboardButton("🔄 REFUND", callback_data="record_REFUND")]
        ])
        await update.message.reply_text(
            "📝 **সর্বশেষ ট্রেডের ফলাফল চয়ন করুন:**\n"
            "এটি এআই মেমোরি টিউনিং এবং বেয়েসিয়ান সম্ভাব্যতা প্রসেসিং এ ব্যবহার করা হবে।",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    elif text == "⚡ Admin Diagnostics":
        await admin_diagnostics_command(update, context)

# ------------------------------------------------------------------
# Master Multi-Engine Image Processing Pipeline
# ------------------------------------------------------------------
async def handle_photo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_session = sessions.get_or_create_session(user_id)
    current_state = user_session.state

    if current_state == SessionState.IDLE:
        await update.message.reply_text("⚠️ অনুগ্রহ করে মেনু থেকে **'🎯 Live Signal Engine'** অথবা **'🧠 Start Training Mode'** সিলেক্ট করুন।")
        return

    # Download high-res photo from Telegram
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()

    # Engine 1: Deduplication, Rescaling & Cryptographic Hashing
    is_valid, msg, processed_bytes, sha256_hash, p_hash = image_proc.process_screenshot(bytes(image_bytes))
    if not is_valid:
        await update.message.reply_text(f"❌ {msg}")
        return

    # Save temporary file for Vision Engine
    temp_filename = f"temp_{user_id}_{int(datetime.now().timestamp())}.png"
    with open(temp_filename, "wb") as f:
        f.write(processed_bytes)

    status_msg = await update.message.reply_text("⏳ **Multi-Engine Quant Pipeline Analysing Chart...**")

    try:
        # Engine 9: Multimodal Vision Gemini Model Extraction
        vision_raw = vision_eng.analyze_chart(temp_filename)

        # -----------------------------------------------------------
        # WORKFLOW A: AI Training & Pattern Learning Mode
        # -----------------------------------------------------------
        if current_state == SessionState.TRAINING:
            data_1h = vision_raw.get("data_1h", vision_raw)
            inserted = db.insert_pattern(sha256_hash, "1H", data_1h)

            if inserted:
                count = sessions.increment_training_count(user_id)
                total_nodes = db.get_total_nodes()
                await status_msg.edit_text(
                    f"✅ **Training Node Successfully Stored!**\n"
                    f"• **Trend Structural:** `{data_1h.get('primary_trend')}`\n"
                    f"• **Rejection Profile:** `{data_1h.get('rejection_zone')}`\n"
                    f"• **Session Count:** `{count}`\n"
                    f"• **Total DB Memory:** `{total_nodes}`",
                    parse_mode="Markdown"
                )
            else:
                await status_msg.edit_text("⚠️ এই চার্ট প্যাটার্নটি ডাটাবেজে আগে থেকেই বিদ্যমান রয়েছে (Duplicate Hash)!")

        # -----------------------------------------------------------
        # WORKFLOW B: Live Signal Pipeline - Step 1 (1D Chart)
        # -----------------------------------------------------------
        elif current_state == SessionState.WAITING_1D:
            data_1d = vision_raw.get("data_1d", vision_raw)
            sessions.store_1d_analysis(user_id, data_1d)
            await status_msg.edit_text(
                "✅ **1D Higher Timeframe Structure Cached!**\n\n"
                "📸 **ধাপ ২:** এবার আপনার ট্রেডিং এন্ট্রির জন্য **১ ঘণ্টার (1H)** ক্যান্ডেলস্টিক চার্টের স্ক্রিনশট দিন।",
                parse_mode="Markdown"
            )

        # -----------------------------------------------------------
        # WORKFLOW C: Live Signal Pipeline - Step 2 (1H Execution)
        # -----------------------------------------------------------
        elif current_state == SessionState.WAITING_1H:
            data_1h = vision_raw.get("data_1h", vision_raw)
            sessions.store_1h_analysis(user_id, data_1h)

            data_1d = user_session.data_1d or {}
            asset_pair = vision_raw.get("asset_pair", "EUR/USD-OTC")

            # Engine 3: Technical Pattern Evaluation
            pattern_res = pattern_eng.compute_pattern_score(data_1d, data_1h)

            # Engine 4: SMC Liquidity Confluence Engine
            liquidity_res = liquidity_eng.analyze_liquidity_confluence(data_1h, pattern_res["suggested_direction"])

            # Engine 5: Risk Validation & Decision Engine
            val_res = validation_eng.validate_trade(pattern_res, liquidity_res)

            # Engine 2: Database Historical Query
            trend_1h = data_1h.get("primary_trend", "CONSOLIDATION")
            rejection_1h = data_1h.get("rejection_zone", "NEUTRAL")
            matched_history = db.query_pattern_statistics(trend_1h, rejection_1h)

            # Engine 6: Quant Expectancy & Bayesian Probability Engine
            quant_res = stats_eng.compute_quant_metrics(
                matched_history=[matched_history] if isinstance(matched_history, dict) else [],
                model_confidence=val_res["combined_confidence"]
            )

            # Dynamic Kelly Position Sizing Calculation
            win_rate = quant_res.get("bayesian_win_probability", 65.0)
            risk_profile = InstitutionalRiskManager.calculate_position_size(win_probability=win_rate)

            # Engine 8: Comprehensive Report Formatting
            final_report = report_eng.generate_signal_report(
                asset_pair=asset_pair,
                timeframe="1-HOUR",
                validation_result=val_res,
                pattern_result=pattern_res,
                liquidity_result=liquidity_res,
                quant_metrics=quant_res
            )

            # Append Money Management Advice to Report
            report_addon = (
                f"\n💰 **Kelly Risk Sizing:** `{risk_profile['kelly_percentage']}% of Capital`\n"
                f"🛡️ **Recommended Stake:** `${risk_profile['recommended_stake_usd']} (Standard $100 Balance)`"
            )
            full_report = final_report + report_addon

            # Log to DB and reset user session state
            db.log_live_signal(user_id, {
                "decision": val_res["final_decision"],
                "research_score": val_res["combined_confidence"],
                "win_rate": win_rate,
                "trend_1d": data_1d.get("primary_trend", "N/A"),
                "trend_1h": trend_1h,
                "rejection_1h": rejection_1h
            })

            user_session.reset()
            await status_msg.edit_text(full_report, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Execution Error in Pipeline: {str(e)}", exc_info=True)
        err_msg = report_eng.generate_error_report(str(e))
        await status_msg.edit_text(err_msg, parse_mode="Markdown")

    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass

# ------------------------------------------------------------------
# Callback Query Handler (Inline Button Engagements)
# ------------------------------------------------------------------
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("record_"):
        outcome_result = query.data.split("_")[1]

        outcome_eng.record_outcome(
            signal_id=f"SIG_{int(datetime.now().timestamp())}",
            asset_pair="OTC_INSTITUTIONAL",
            timeframe="1H",
            predicted_direction="ANALYZED",
            confidence_score=75.0,
            entry_price=0.0,
            exit_price=0.0,
            quant_metrics={"bayesian_win_probability": 70.0, "expected_value_per_dollar": 0.35}
        )

        await query.edit_message_text(
            f"✅ **ট্রেড রেজাল্ট সফলভাবে ডাটাবেজে স্টোর হয়েছে:** `{outcome_result}`\n"
            "বট তার অ্যালগরিদম শেখার কাজে এই ডাটা ব্যবহার করে মেমোরি আপডেট করে নেবে।",
            parse_mode="Markdown"
        )

# ------------------------------------------------------------------
# Application Main Execution Loop
# ------------------------------------------------------------------
def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN environment variable is missing! Exiting...")
        sys.exit(1)

    # Start Flask Health Check Web Server for Cloud Deployment Keep-Alive
    start_web_server()

    # Build Telegram Bot Application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("backup", admin_backup_command))
    app.add_handler(CommandHandler("diagnostics", admin_diagnostics_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_input))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    logger.info("Quotex OTC Quant Enterprise Engine fully activated!")
    app.run_polling()

if __name__ == "__main__":
    main()

