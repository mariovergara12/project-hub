"""ASGI entrypoint for Vercel's FastAPI runtime."""

from app.main import create_app

app = create_app()
