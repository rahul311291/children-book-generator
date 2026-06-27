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


def otps_col() -> Collection:
    return get_db()["otps"]


def purchases_col() -> Collection:
    """Paid entitlements: one doc per confirmed purchase."""
    return get_db()["purchases"]


def template_assets_col() -> Collection:
    """Pre-rendered template page images: one doc per (template_id, page_number)."""
    return get_db()["template_assets"]


def events_col() -> Collection:
    """Funnel analytics events: story_started, payment_succeeded,
    book_generated, book_failed, download, print_requested."""
    return get_db()["events"]


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
        otps_col().create_index("expires_at", expireAfterSeconds=0)
        otps_col().create_index("email")
        purchases_col().create_index([("user_id", 1), ("template_id", 1)])
        purchases_col().create_index("link_id", unique=True)
        template_assets_col().create_index(
            [("template_id", 1), ("page_number", 1)], unique=True
        )
        events_col().create_index([("ts", DESCENDING)])
        events_col().create_index("type")
        events_col().create_index("email")
    except Exception:
        pass
