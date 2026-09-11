import html
import logging
from typing import Dict, Any, Optional

# Fallback Configuration Logging Setup
try:
    from config import logger
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("OTC_Enterprise_Quant.ReportEngine")


class ReportEngine:
    """
    Enterprise Telegram Signal Dashboard & High-Frequency Quant Report Generator.
    Specially engineered for Quotex OTC Binary Options focusing on strict 1-Hour Chart Analysis.
    Formats Multi-Engine SMC Confluences, Bayesian Probabilities, and Risk Management Guidance into Telegram HTML.
    """

    def __init__(self):
        pass

    def _generate_progress_bar(self, score: float, max_score: float = 100.0) -> str:
        """Generates a visual ASCII progress bar for Telegram UI."""
        total_blocks = 10
        filled_blocks = int(round((score / max_score) * total_blocks))
        filled_blocks = max(0, min(total_blocks, filled_blocks))
        return "█" * filled_blocks + "░" * (total_blocks - filled_blocks)

    def _clean_text(self, text: Any) -> str:
        """Safely escapes HTML tags to avoid Telegram parsing errors."""
        return html.escape(str(text)) if text is not None else "N/A"

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
        Generates an institutional-grade visual signal report for Telegram.
        """
        final_decision = str(validation_result.get("final_decision", "HOLD")).upper()
        confidence = float(validation_result.get("combined_confidence", 0.0))
        pattern_score = float(pattern_result.get("confidence_score", 0.0))
        liquidity_score = float(liquidity_result.get("liquidity_score", 0.0))

        bayesian_prob = float(quant_metrics.get("bayesian_win_probability", confidence))
        ev_dollar = float(quant_metrics.get("expected_value_per_dollar", 0.0))
        kelly_stake = float(pattern_result.get("kelly_risk_stake_pct", 0.0))
        samples = int(quant_metrics.get("sample_count", pattern_result.get("historical_matches_found", 0)))

        # Signal Header & Badge Logic
        if final_decision == "UP":
            direction_header = "🟢 <b>BUY / CALL (⬆️ UP)</b>"
            direction_badge = "🚀 INSTITUTIONAL BULLISH BIAS"
        elif final_decision == "DOWN":
            direction_header = "🔴 <b>SELL / PUT (⬇️ DOWN)</b>"
            direction_badge = "📉 INSTITUTIONAL BEARISH BIAS"
        else:
            direction_header = "⚠️ <b>HOLD / NO TRADE</b>"
            direction_badge = "🛑 HIGH-RISK RETAIL TRAP"

        # Timeframe Verification Safeguard
        tf_display = str(timeframe).upper()
        tf_warning = ""
        if "1" not in tf_display and "H" not in tf_display and "HOUR" not in tf_display:
            tf_warning = "\n⚠️ <i>সতর্কতা: শুধুমাত্র ১-ঘণ্টার (1-Hour) চার্ট এনালাইসিসের জন্য ফিল্টার করা হয়েছে।</i>"

        confidence_bar = self._generate_progress_bar(confidence)
        smc_bar = self._generate_progress_bar(liquidity_score)

        report = [
            "🦅 <b>QUOTEX OTC QUANT ENTERPRISE SIGNAL</b> 🦅",
            "═══════════════════════════════════",
            f"<b>🪙 এসেট পেয়ার:</b> <code>{self._clean_text(asset_pair)}</code>",
            f"<b>⏱️ এক্সিকিউশন টাইমফ্রেম:</b> <code>{self._clean_text(tf_display)}</code>{tf_warning}",
            f"<b>🎯 ট্রেড সিদ্ধান্ত:</b> {direction_header}",
            f"<b>🏷️ মার্কেট স্টেট:</b> <code>{direction_badge}</code>",
            f"<b>⚡ সাইনাল পাওয়ার:</b> <code>[{confidence_bar}] {confidence:.1f}%</code>",
            "═══════════════════════════════════",
            "",
            "🧠 <b>ইনস্টিটিউশনাল SMC ও প্রাইস অ্যাকশন বিশ্লেষণ:</b>",
            f"• <b>SMC Liquidity Score:</b> <code>[{smc_bar}] {liquidity_score:.1f}/100</code>",
            f"• <b>Pattern Score:</b> <code>{pattern_score:.1f} / 100</code>",
            f"• <b>Trend Alignment:</b> <code>{self._clean_text(pattern_result.get('trend_alignment_status'))}</code>",
            f"• <b>Order Flow Bias:</b> <code>{self._clean_text(liquidity_result.get('institutional_bias'))}</code>",
            f"• <b>FVG Status:</b> <code>{self._clean_text(liquidity_result.get('fvg_status'))}</code>",
            f"• <b>Sweep Status:</b> <code>{self._clean_text(liquidity_result.get('sweep_status'))}</code>",
            f"• <b>Order Block Status:</b> <code>{self._clean_text(liquidity_result.get('order_block_status'))}</code>",
            "",
            "📐 <b>কোয়ান্ট ও স্ট্যাটিস্টিক্যাল রিস্ক মেট্রিক্স:</b>",
            f"• <b>Bayesian Win Prob:</b> <code>{bayesian_prob:.1f}%</code>",
            f"• <b>Expected Value (EV):</b> <code>${ev_dollar:.2f} / $1.00</code>",
            f"• <b>Half-Kelly Risk Stake:</b> <code>{kelly_stake:.2f}% of Balance</code>",
            f"• <b>DB Memory Samples:</b> <code>{samples} টি মিলযুক্ত ট্রেড</code>",
            "═══════════════════════════════════"
        ]

        if final_decision != "HOLD":
            report.append("📌 <b>ট্রেড এক্সিকিউশন নির্দেশিকা:</b>")
            report.append("1. পরবর্তী <b>1-Hour Candle</b> খোলার সাথে সাথে এন্ট্রি নিন।")
            report.append("2. প্রসেস ফিল্টার অনুযায়ী মানি ম্যানেজমেন্ট (Half-Kelly) বজায় রাখুন।")
        else:
            reason = self._clean_text(validation_result.get("reason", "মডেল কনফ্লুয়েন্স থ্রেশহোল্ড (75%) পূর্ণ হয়নি।"))
            report.append(f"❌ <b>ট্রেড না নেওয়ার কারণ:</b> <i>{reason}</i>")

        report.append("\n⚠️ <i>রিস্ক ডিসক্লেইমার: OTC মার্কেট অ্যালগরিদম নির্ভর। কোনো মার্কেটেই ১০০% গ্যারান্টি নেই। কঠোরভাবে রিস্ক ম্যানেজমেন্ট অনুসরণ করুন।</i>")

        return "\n".join(report)

    def generate_error_report(self, error_message: str) -> str:
        """
        Generates user-friendly formatted error response.
        """
        clean_err = self._clean_text(error_message)
        return (
            "🚨 <b>কোয়ান্ট চার্ট এনালাইসিস ব্যর্থ হয়েছে!</b>\n\n"
            f"<b>কারণ:</b> <code>{clean_err}</code>\n\n"
            "📌 <b>সঠিক নিয়ম:</b>\n"
            "• Quotex OTC মার্কেটের একটি পরিষ্কার <b>1-Hour Timeframe</b> চার্টের স্ক্রিনশট দিন।\n"
            "• ক্যান্ডেলস্টিক, সাপোর্ট/রেজিস্ট্যান্স ও ট্রেন্ড যেন স্পষ্ট থাকে।"
        )


# Global Engine Instance Export
report_engine = ReportEngine()
# Class Alias for Flexible Import
EnterpriseReportEngine = ReportEngine

if __name__ == "__main__":
    print("Master Report Engine Module Ready.")
