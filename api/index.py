import sys
import os

# Add backend to path so app imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app

# Vercel requires a handler named "app" or "handler"
# FastAPI app is already ASGI-compatible - Vercel picks it up automatically
