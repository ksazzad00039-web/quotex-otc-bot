# ==============================================================================
# QUOTEX OTC QUANTITATIVE ENTERPRISE SYSTEM - DEPLOYMENT PROCESS CONFIGURATION
# Framework: Gunicorn WSGI + Asynchronous Event-Driven Architecture
# Target Platform: Render Cloud / Linux Container Infrastructure
# Multi-Thread Engine: Gunicorn Eventlet / Gevent Socket Engine Integration
# ==============================================================================

# Primary Production Web Process Engine
# Handles dynamic background keep-alive daemons, HTTP health checks, and Telegram webhook APIs safely.
web: gunicorn server:app --workers 2 --threads 4 --worker-class gthread --bind 0.0.0.0:$PORT --timeout 120 --keep-alive 5 --log-level info

# Secondary Standalone Daemon Process Engine (Alternative Execution Mode)
# Useful for polling bot deployment without exposing WSGI server interface.
# worker: python main.py


