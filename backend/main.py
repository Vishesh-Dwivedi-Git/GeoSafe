"""
Compatibility launcher so the backend can be started with:
    uvicorn main:app --reload
"""

from app.main import app

__all__ = ["app"]
