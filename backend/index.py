"""Entrada de FastAPI detectable cuando backend/ es la raíz del proyecto Vercel."""

from app.main import app

__all__ = ["app"]
