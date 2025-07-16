# app/api/data/cache.py
from functools import lru_cache
from app.config import settings


"""Uses @lru_cache() to avoid reloading DB handler or settings repeatedly."""


@lru_cache()
def get_settings():
    """
    Cache the application settings to avoid reloading from environment repeatedly.
    """
    return settings


@lru_cache()
def get_cached_db_handler():
    """
    Cached instance of DBHandler. Useful if DBHandler is lightweight and reusable.
    If DBHandler holds connections, prefer managing with FastAPI's lifecycle events.
    """
    from app.data.db import DBHandler
    return DBHandler()
