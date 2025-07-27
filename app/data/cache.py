# app/data/cache.py
from functools import lru_cache
from app.config import settings


@lru_cache()
def get_settings():
    """
    Cache the application settings to avoid reloading from environment repeatedly.
    """
    return settings

# OLD CODE (REMOVED): This was problematic because it shared a single database
# session across multiple requests, which is not thread-safe and causes blocking.
#
# @lru_cache()
# def get_cached_db_handler():
#     """
#     Cached instance of DBHandler. Useful if DBHandler is lightweight and reusable.
#     If DBHandler holds connections, prefer managing with FastAPIs lifecycle events.
#     """
#     from app.data.db import DBHandler
#     return DBHandler()
