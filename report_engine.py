import logging
from typing import Dict, Any

logger = logging.getLogger("OTC_Enterprise_Quant.ReportEngine")

class ReportEngine:
    """
    Telegram Message & Analysis Report Formatting Engine.
    Converts multi-engine quant data, technical analysis, and SMC liquidity metrics 
    into structured Markdown templates for user-facing Telegram signals.
    """

    def __init__(self):
        pass

    def generate_signal_report(
        self,
        asset_pair: str,
        timeframe: str,
        validation_result: Dict[str, Any],
        pattern_result: Dict[str, Any],
        liquidity_result: Dict[str, Any],
        quant_metrics: Dict[str, Any]
    ) -> str:
        """
        Generates a comprehensive signal message in Bengali with Markdown formatting.
        """
        final_decision = validation_result.get("final_decision", "NO_TRADE")
        confidence = validation_result.get("combined_confidence", 0.0)
        pattern_score = pattern_result.get("pattern_score", 0.0)
        liquidity_score = liquidity_result.get("liquidity_score", 0.0)
        
        bayesian_prob = quant_metrics.get("bayesian_win_probability", 0.0)
        ev_dollar = quant_metrics.get("expected_value_per_dollar", 0.0)
        samples = quant_metrics.get("sample_count", 0)

        # Signal Icon Logic
        if final_decision == "UP":
            direction_text = "🟢 **BUY (CALL / UP)**"
            direction_icon = "📈"
        elif final_decision == "DOWN":
            direction_text = "🔴 **SELL (PUT / DOWN)**"
            direction_icon = "📉"
        else:
            direction_text = "⚠️ **NO TRADE (মার্কেট ঝুঁকিপূর্ণ)**"
            direction_icon = "🛑"

        # Constructing the Message
        report = []
        report.append("📊 **Quotex OTC Quant Signal System**")
        report.append("═════════════════════════")
        report.append(f"<b>এসেট পেয়ার:</b> `{asset_pair}`")
        report.append(f"<b>টাইমফ্রেম:</b> `{timeframe}`")
        report.append(f"<b>ট্রেড সিদ্ধান্ত:</b> {direction_text} {direction_icon}")
        report.append(f"<b>আস্থা স্কোর (Confidence):</b> `{confidence}%`\n")

        report.append("🔍 **প্রযুক্তিগত ও SMC টেকনিক্যাল বিশ্লেষণ:**")
        report.append(f"• **Price Action Pattern Score:** `{pattern_score}/100`")
        report.append(f"• **SMC Liquidity Score:** `{liquidity_score}/100`")
        report.append(f"• **Trend Alignment:** `{pattern_result.get('trend_alignment_status', 'N/A')}`")
        report.append(f"• **Liquidity Bias:** `{liquidity_result.get('institutional_bias', 'N/A')}`\n")

        report.append("📐 **কোয়ান্ট ও স্ট্যাটিস্টিক্যাল মেট্রিক্স:**")
        report.append(f"• **Bayesian Win Prob:** `{bayesian_prob}%`")
        report.append(f"• **Expected Value (EV):** `${ev_dollar} / $1`")
        report.append(f"• **Historical Memory Samples:** `{samples} টি ট্রেড`\n")

        if final_decision != "NO_TRADE":
            report.append("⏱️ **পরামর্শ:** এক ঘণ্টার মোমবাতির শুরুতে প্রবেশের জন্য উপযুক্ত কনফার্মেশন নিন।")
        else:
            report.append(f"❌ **কারন:** {validation_result.get('reason', 'Score Threshold Unmet')}")

        report.append("═════════════════════════")
        report.append("⚠️ *রিস্ক সতর্কতা: ওটিসি মার্কেট অ্যালগরিদম ভিত্তিক। যথাযথ মানি ম্যানেজমেন্ট ব্যবহার করুন।*")

        return "\n".join(report)

    def generate_error_report(self, error_message: str) -> str:
        """
        Generates user-friendly error response on system/vision failure.
        """
        return (
            "❌ **চার্ট বিশ্লেষণ ব্যর্থ হয়েছে!**\n\n"
            f"**কারণ:** {error_message}\n\n"
            "অনুগ্রহ করে একটি পরিষ্কার ১-ঘণ্টা টাইমফ্রেমের চার্ট স্ক্রিনশট আপলোড করুন।"
        )

