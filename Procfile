# ==============================================================================
# QUOTEX OTC QUANTITATIVE ENTERPRISE SYSTEM - PRODUCTION DEPLOYMENT CONFIG
# Architecture: Gunicorn WSGI + Async Event-Driven Multi-Thread Engine
# Target Platform: Render Cloud / Heroku / Linux Container Infrastructure
# Execution Timeframe Focus: Strict 1-Hour OTC Candlestick Pipeline
# ==============================================================================

# 1. Primary Production Web Engine
# Maintains HTTP health checks, dynamic keep-alive daemons, and prevents Render idle sleep
web: gunicorn server:app --workers 2 --threads 4 --worker-class gthread --bind 0.0.0.0:$PORT --timeout 120 --keep-alive 5 --log-level info --max-requests 1000 --max-requests-jitter 50

# 2. Standalone Background Worker Engine
# Executes the main Telegram Bot polling process continuously in background RAM
worker: python main.py


