
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import threading

from config import TELEGRAM_BOT_TOKEN, MAX_IMAGE_SIZE_MB, ALLOW_DUPLICATE_SCREENSHOTS, user_sessions, logger
from database import DatabaseManager
from vision_gemini import GeminiVisionEngine
from memory_engine import QuantitativeEngine
from server import start_web_server

db = DatabaseManager()
vision = GeminiVisionEngine()
quant = QuantitativeEngine(db)

KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🧠 Start Training Mode"), KeyboardButton("🎯 Live Signal Engine")],
        [KeyboardButton("🔒 Lock Memory Database"), KeyboardButton("📊 System Status")]
    ],
    resize_keyboard=True
)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id] = {"state": 0, "1d_data": None}
    msg = (
        "🏛 **Quotex Institutional Quant Engine v5.0**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**নিয়মাবলী:**\n"
        "1️⃣ **1-Hour Timeframe System**\n"
        "2️⃣ **Training Mode:** ছবি পাঠালে Gemini AI চার্ট এনালাইসিস করে ডাটাবেজে রিয়েল নোড যুক্ত করবে।\n"
        "3️⃣ **Live Signal:** প্রথমে 1D এবং তারপর 1H স্ক্রিনশট দিতে হবে।"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=KEYBOARD)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_sessions:
        user_sessions[user_id] = {"state": 0, "1d_data": None}

    if text == "🧠 Start Training Mode":
        user_sessions[user_id]["state"] = 1
        await update.message.reply_text("📥 **Training Mode Engaged:** অতীতের চার্টের স্ক্রিনশট পাঠানো শুরু করুন। AI লাইভ প্রসেস করবে।")

    elif text == "🔒 Lock Memory Database":
        user_sessions[user_id]["state"] = 0
        total = db.get_total_nodes()
        await update.message.reply_text(f"🔒 **Training Locked!** মোট AI-প্রসেসড নোড: `{total}`", parse_mode="Markdown")

    elif text == "🎯 Live Signal Engine":
        user_sessions[user_id]["state"] = 2
        user_sessions[user_id]["1d_data"] = None
        await update.message.reply_text("📸 **Step 1:** লাইভ মার্কেটের **১ দিনের (1D)** চার্ট স্ক্রিনশট দিন।")

    elif text == "📊 System Status":
        total = db.get_total_nodes()
        await update.message.reply_text(f"📊 **Database Analytics:**\n• Total Stored AI Nodes: `{total}`", parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {"state": 0, "1d_data": None}

    session = user_sessions[user_id]
    state = session["state"]

    if state == 0:
        await update.message.reply_text("⚠️ দয়া করে আগে **'🎯 Live Signal Engine'** অথবা **'🧠 Start Training Mode'** বাটন নির্বাচন করুন।")
        return

    photo = update.message.photo[-1]
    if photo.file_size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(f"❌ ছবির সাইজ {MAX_IMAGE_SIZE_MB}MB-এর বেশি।")
        return

    file_obj = await photo.get_file()
    img_bytes = await file_obj.download_as_bytearray()

    is_dup, img_hash = db.check_duplicate_image(img_bytes)
    if is_dup and not ALLOW_DUPLICATE_SCREENSHOTS and state == 1:
        await update.message.reply_text("⚠️ এই ছবিটি ডাটাবেজে যুক্ত আছে! নতুন স্ক্রিনশট দিন।")
        return

    await update.message.reply_text("⏳ **Gemini AI Analyzing Chart Structure...**")

    # State 1: Training Mode AI Process
    if state == 1:
        ai_result = vision.analyze_chart_screenshot(img_bytes, timeframe="1H")
        if ai_result and db.insert_pattern(img_hash, "1H", ai_result):
            total = db.get_total_nodes()
            await update.message.reply_text(
                f"✅ **AI Training Node Saved!**\n"
                f"• Trend: `{ai_result.get('primary_trend')}`\n"
                f"• Rejection: `{ai_result.get('rejection_zone')}`\n"
                f"• Total Database Nodes: `{total}`", 
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Gemini AI অ্যানালাইসিসে সমস্যা হয়েছে। আবার চেষ্টা করুন।")

    # State 2: Live Signal 1D
    elif state == 2:
        ai_1d = vision.analyze_chart_screenshot(img_bytes, timeframe="1D")
        if ai_1d:
            session["1d_data"] = ai_1d
            session["state"] = 3
            await update.message.reply_text("✅ **1D Trend Extracted!**\n📸 **Step 2:** এখন **১ ঘণ্টার (1H)** স্ক্রিনশট দিন।")
        else:
            await update.message.reply_text("❌ 1D চার্ট প্রসেস করতে ব্যর্থ হয়েছে। স্পষ্ট চার্ট দিন।")

    # State 3: Live Signal 1H & Compute Signal
    elif state == 3:
        ai_1h = vision.analyze_chart_screenshot(img_bytes, timeframe="1H")
        if ai_1h:
            res = quant.evaluate_multi_timeframe(session["1d_data"], ai_1h)

            card = (
                "🎯 **QUOTEX OTC QUANT SIGNAL** 🎯\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 **Decision:** `{res['decision']}`\n"
                f"🧪 **Research Score:** `{res['research_score']}/100`\n"
                f"📈 **Hist. Win Rate:** `{res['historical_frequency']}%`\n"
                f"⏱ **Timeframe:** `1 HOUR`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 **1D Bias:** `{res['trend_1d']}`\n"
                f"⏳ **1H Structure:** `{res['trend_1h']}`\n"
                f"🧱 **1H Rejection:** `{res['rejection_1h']}`\n"
                f"🧠 **Matching Historical Patterns:** `{res['matched_historical_samples']}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ *১ ঘণ্টার ক্যান্ডেল ওপেনিংয়ে সঠিক মনি ম্যানেজমেন্ট নিয়ে ট্রেড করুন।*"
            )
            session["state"] = 0
            session["1d_data"] = None
            await update.message.reply_text(card, parse_mode="Markdown", reply_markup=KEYBOARD)
        else:
            await update.message.reply_text("❌ 1H চার্ট প্রসেস করতে ব্যর্থ হয়েছে। স্পষ্ট চার্ট দিন।")

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing!")
        return

    # Start Light Web Server in Thread
    t = threading.Thread(target=start_web_server, daemon=True)
    t.start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Bot Online with Full Dynamic Gemini Vision Logic...")
    app.run_polling()

if __name__ == "__main__":
    main()
