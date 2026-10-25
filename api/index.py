"""
api/index.py
============
Vercel serverless entry point.
Vercel runs this file and exposes the FastAPI `app` object via ASGI.

All backend source lives in backend/app/. We add it to sys.path so
imports work without restructuring the existing code.
"""
import sys
import os

# Make the backend package importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: F401  – Vercel picks up `app` automatically