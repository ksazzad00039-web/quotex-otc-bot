import json
import base64
import time
import requests
from config import GEMINI_API_KEY, GEMINI_MODEL, VISION_TIMEOUT_SECONDS, VISION_MAX_RETRIES, logger

class GeminiVisionEngine:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL

    def analyze_chart_screenshot(self, image_bytes, timeframe="1H"):
        if not self.api_key:
            logger.error("Gemini API Key missing.")
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        prompt = (
            f"You are an expert technical chart analyst for Quotex OTC markets ({timeframe} Timeframe).\n"
            "Analyze this candlestick chart screenshot and output ONLY valid JSON without markdown fences:\n"
            "{\n"
            '  "primary_trend": "STRONG_BULLISH" | "WEAK_BULLISH" | "STRONG_BEARISH" | "WEAK_BEARISH" | "CONSOLIDATION",\n'
            '  "support_resistance_count": <integer>,\n'
            '  "volatility_score": <float 0.0 to 100.0>,\n'
            '  "rejection_zone": "UPPER_REJECTION" | "LOWER_REJECTION" | "NEUTRAL",\n'
            '  "recommended_direction": "UP" | "DOWN" | "NO_TRADE"\n'
            "}"
        )

        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": base64_image}}
                ]
            }]
        }
        headers = {"Content-Type": "application/json"}

        for attempt in range(VISION_MAX_RETRIES):
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=VISION_TIMEOUT_SECONDS)
                if res.status_code == 200:
                    data = res.json()
                    text_response = data['candidates'][0]['content']['parts'][0]['text'].strip()
                    if text_response.startswith("```json"):
                        text_response = text_response.replace("```json", "").replace("```", "").strip()
                    return json.loads(text_response)
            except Exception as e:
                logger.error(f"Gemini API Error (Attempt {attempt+1}): {str(e)}")
                time.sleep(1.5)
        
        return None

