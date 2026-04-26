"""
MongoDB client — single shared MongoClient, lazy-initialised.
Collections: users, book_history, book_cache, image_pool
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

_client: MongoClient = None


def _get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI", "")
        if not uri:
            try:
                import streamlit as st
                uri = st.secrets.get("MONGODB_URI", "")
            except Exception:
                pass
        if not uri:
            raise Exception(
                "MONGODB_URI not configured. Add it to .env or Streamlit secrets."
            )
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    db_name = os.getenv("MONGODB_DB", "children_book_generator")
    return _get_client()[db_name]


def users_col() -> Collection:
    return get_db()["users"]


def book_history_col() -> Collection:
    return get_db()["book_history"]


def book_cache_col() -> Collection:
    return get_db()["book_cache"]


def image_pool_col() -> Collection:
    return get_db()["image_pool"]


def sessions_col() -> Collection:
    return get_db()["sessions"]


def ensure_indexes() -> None:
    """Create indexes on first startup (idempotent)."""
    try:
        users_col().create_index("email", unique=True)
        book_history_col().create_index([("user_id", 1), ("created_at", DESCENDING)])
        book_cache_col().create_index(
            [("user_id", 1), ("template_id", 1), ("child_name", 1), ("gender", 1), ("age", 1)],
            unique=True,
        )
        image_pool_col().create_index("prompt_hash", unique=True)
        sessions_col().create_index("expires_at", expireAfterSeconds=0)
    except Exception:
        pass
