import os
import sys
import time
import logging
import threading
import requests
from datetime import datetime, timezone
from flask import Flask, jsonify, request

# Ensure dynamic module path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from config import PORT, LOG_LEVEL, logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("OTC_Enterprise_Quant.Server")
    PORT = int(os.getenv("PORT", "10000"))

# ------------------------------------------------------------------
# Flask Web Application Initialization
# ------------------------------------------------------------------
app = Flask(__name__)

# System Startup Timestamp for Uptime Monitoring
START_TIME = datetime.now(timezone.utc)


def get_system_uptime() -> str:
    """Calculates formatted server uptime."""
    delta = datetime.now(timezone.utc) - START_TIME
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


# ------------------------------------------------------------------
# HTTP REST Endpoints for Cloud Diagnostics & Keep-Alive
# ------------------------------------------------------------------
@app.route('/', methods=['GET'])
def root():
    """Main Landing & Overview Endpoint."""
    return jsonify({
        "status": "ONLINE",
        "service": "Quotex OTC Institutional Trading Core",
        "timeframe_policy": "1-HOUR ONLY",
        "uptime": get_system_uptime(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint used by Render / Cloud Load Balancers for Health Diagnostics."""
    return jsonify({
        "status": "HEALTHY",
        "http_code": 200,
        "uptime": get_system_uptime()
    }), 200


@app.route('/status', methods=['GET'])
def system_status():
    """In-depth System Analytics and Environment Diagnostics."""
    telegram_token_set = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    gemini_key_set = bool(os.getenv("GEMINI_API_KEY"))
    turso_url_set = bool(os.getenv("TURSO_DATABASE_URL"))

    return jsonify({
        "system_core": "Active",
        "uptime": get_system_uptime(),
        "integrations": {
            "telegram_bot_api": "CONNECTED" if telegram_token_set else "MISSING_TOKEN",
            "gemini_vision_ai": "ONLINE" if gemini_key_set else "MISSING_KEY",
            "turso_cloud_db": "ACTIVE" if turso_url_set else "LOCAL_SQLITE_MODE"
        },
        "execution_rules": {
            "timeframe": "1-Hour (Strict)",
            "risk_engine": "Fractional Kelly Criterion",
            "vision_model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        }
    }), 200


# ------------------------------------------------------------------
# Background Self-Keep-Alive Worker (Prevents Cloud Server Inactivity Spin-Down)
# ------------------------------------------------------------------
def background_self_ping():
    """
    Periodically sends HTTP GET requests to the server's own health endpoint
    to prevent free hosting services (like Render) from going into sleep mode.
    """
    time.sleep(10)  # Wait for Flask startup
    server_url = f"http://127.0.0.1:{PORT}/health"
    
    logger.info("Keep-Alive Self-Ping Worker initiated.")
    
    while True:
        try:
            response = requests.get(server_url, timeout=5)
            if response.status_code == 200:
                logger.debug("Self-ping successful: Keep-Alive pulse active.")
            else:
                logger.warning(f"Self-ping returned non-200 code: {response.status_code}")
        except Exception as e:
            logger.debug(f"Self-ping heartbeat check (normal during initial boot): {str(e)}")
        
        # Ping every 10 minutes (600 seconds)
        time.sleep(600)


# ------------------------------------------------------------------
# Web Server Control Functions
# ------------------------------------------------------------------
def run_flask_app():
    """Runs Flask application in a thread-safe environment."""
    # Suppress default noisy Flask logging in production
    cli = sys.modules.get('flask.cli')
    if cli:
        cli.show_server_banner = lambda *x: None
    
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting Web Keep-Alive Engine on {host}:{PORT}...")
    
    try:
        app.run(host=host, port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask Web Server encountered an execution error: {str(e)}")


def start_web_server():
    """
    Spawns the Flask web server and self-ping worker inside detached background daemon threads.
    Maintains 100% compatibility with `main.py`.
    """
    # 1. Start Web Server Thread
    server_thread = threading.Thread(target=run_flask_app, name="FlaskWebServerThread")
    server_thread.daemon = True
    server_thread.start()

    # 2. Start Self-Ping Heartbeat Worker
    ping_thread = threading.Thread(target=background_self_ping, name="KeepAlivePingThread")
    ping_thread.daemon = True
    ping_thread.start()

    logger.info("Web Diagnostics & Keep-Alive Daemon Threads Started Successfully!")


if __name__ == "__main__":
    # Standalone Execution Support
    start_web_server()
    while True:
        time.sleep(1)

