import streamlit as st
import os
import hashlib
import secrets
import uuid
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _users():
    from mongo_client import users_col
    return users_col()


def _hash_password(password: str) -> tuple:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return dk.hex(), salt


def _verify_password(password: str, stored_hash: str, salt: str) -> bool:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return dk.hex() == stored_hash


# ---------------------------------------------------------------------------
# Persistent session tokens (7-day login)
# ---------------------------------------------------------------------------

def _sessions():
    from mongo_client import sessions_col
    return sessions_col()


def _create_session_token(user_id: str) -> str:
    """Generate a 64-char hex token, store it in MongoDB, return it."""
    token = secrets.token_hex(32)
    expires = datetime.utcnow() + timedelta(days=7)
    try:
        _sessions().insert_one({
            "_id": token,
            "user_id": user_id,
            "expires_at": expires,
            "created_at": datetime.utcnow(),
        })
    except Exception as e:
        logger.error(f"Could not create session token: {e}")
    return token


def _delete_session_token(token: str) -> None:
    if not token:
        return
    try:
        _sessions().delete_one({"_id": token})
    except Exception as e:
        logger.error(f"Could not delete session token: {e}")


def restore_session_from_token(token: str) -> bool:
    """Validate a cookie token and restore auth_user if valid. Returns True on success."""
    if not token:
        return False
    try:
        session = _sessions().find_one(
            {"_id": token, "expires_at": {"$gt": datetime.utcnow()}}
        )
        if not session:
            return False
        user = _users().find_one({"_id": session["user_id"]}, {"email": 1})
        if not user:
            return False
        st.session_state.auth_user = {"id": session["user_id"], "email": user["email"]}
        if user.get("gemini_api_key"):
            st.session_state.api_key = user["gemini_api_key"]
        if user.get("openrouter_api_key"):
            st.session_state.openrouter_api_key = user["openrouter_api_key"]
        return True
    except Exception as e:
        logger.error(f"Session restore failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_auth_state():
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
    if "auth_error" not in st.session_state:
        st.session_state.auth_error = None
    if "auth_success" not in st.session_state:
        st.session_state.auth_success = None
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"


def is_authenticated() -> bool:
    return st.session_state.get("auth_user") is not None


def get_current_user_id() -> str:
    user = st.session_state.get("auth_user")
    return user.get("id", "") if user else ""


# ---------------------------------------------------------------------------
# Auth operations
# ---------------------------------------------------------------------------

def sign_up(email: str, password: str) -> bool:
    try:
        email = email.strip().lower()
        if _users().find_one({"email": email}):
            st.session_state.auth_error = "This email is already registered. Please log in instead."
            return False
        pw_hash, salt = _hash_password(password)
        user_id = str(uuid.uuid4())
        _users().insert_one({
            "_id": user_id,
            "email": email,
            "password_hash": pw_hash,
            "salt": salt,
            "gemini_api_key": "",
            "openrouter_api_key": "",
            "created_at": datetime.utcnow(),
        })
        st.session_state.auth_user = {"id": user_id, "email": email}
        st.session_state.auth_error = None
        st.session_state.auth_success = "Account created successfully!"
        st.session_state._pending_session_token = _create_session_token(user_id)
        return True
    except Exception as e:
        st.session_state.auth_error = f"Sign up failed: {e}"
        logger.error(f"Sign up error: {e}")
        return False


def sign_in(email: str, password: str) -> bool:
    try:
        email = email.strip().lower()
        user = _users().find_one({"email": email})
        if not user or not _verify_password(password, user["password_hash"], user["salt"]):
            st.session_state.auth_error = "Invalid email or password."
            return False
        user_id = str(user["_id"])
        st.session_state.auth_user = {"id": user_id, "email": email}
        st.session_state.auth_error = None
        st.session_state.auth_success = None
        if user.get("gemini_api_key"):
            st.session_state.api_key = user["gemini_api_key"]
        if user.get("openrouter_api_key"):
            st.session_state.openrouter_api_key = user["openrouter_api_key"]
        # Create persistent session token (cookie will be set by main.py)
        st.session_state._pending_session_token = _create_session_token(user_id)
        return True
    except Exception as e:
        st.session_state.auth_error = f"Login failed: {e}"
        logger.error(f"Sign in error: {e}")
        return False


def sign_out():
    # Mark current session token for deletion (main.py will clear the cookie)
    current_token = st.session_state.get("_session_token", "")
    if current_token:
        st.session_state._token_to_delete = current_token
    st.session_state.auth_user = None
    st.session_state.auth_error = None
    st.session_state.auth_success = None
    st.session_state.api_key = ""
    st.session_state.openrouter_api_key = ""
    st.session_state._session_token = ""


# ---------------------------------------------------------------------------
# API key persistence
# ---------------------------------------------------------------------------

def save_user_api_key(user_id: str, api_key: str) -> bool:
    try:
        _users().update_one({"_id": user_id}, {"$set": {"gemini_api_key": api_key}})
        return True
    except Exception as e:
        logger.error(f"Error saving API key: {e}")
        return False


def load_user_api_key(user_id: str) -> str:
    try:
        user = _users().find_one({"_id": user_id}, {"gemini_api_key": 1})
        return (user or {}).get("gemini_api_key", "")
    except Exception as e:
        logger.error(f"Error loading API key: {e}")
        return ""


def save_user_openrouter_key(user_id: str, api_key: str) -> bool:
    try:
        _users().update_one({"_id": user_id}, {"$set": {"openrouter_api_key": api_key}})
        return True
    except Exception as e:
        logger.error(f"Error saving OpenRouter API key: {e}")
        return False


def load_user_openrouter_key(user_id: str) -> str:
    try:
        user = _users().find_one({"_id": user_id}, {"openrouter_api_key": 1})
        return (user or {}).get("openrouter_api_key", "")
    except Exception as e:
        logger.error(f"Error loading OpenRouter API key: {e}")
        return ""


# ---------------------------------------------------------------------------
# Auth page UI
# ---------------------------------------------------------------------------

def render_auth_page():
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown(
            "<h1 style='text-align: center; margin-bottom: 0.2rem;'>Children's Book Generator</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: #666; margin-bottom: 2rem;'>Create personalized storybooks for children</p>",
            unsafe_allow_html=True,
        )

        # Show which backend and the exact error for debugging
        import os
        uri = os.getenv("MONGODB_URI", "")
        if not uri:
            try:
                uri = st.secrets.get("MONGODB_URI", "")
            except Exception:
                pass
        if uri:
            host = uri.split("@")[-1].split("/")[0] if "@" in uri else "unknown"
            st.caption(f"v2.0-mongodb · connected to: {host}")
        else:
            st.caption("v2.0-mongodb · MONGODB_URI not set")

        if st.session_state.auth_error:
            st.error(st.session_state.auth_error)
            st.session_state.auth_error = None

        if st.session_state.auth_success:
            st.success(st.session_state.auth_success)
            st.session_state.auth_success = None

        mode = st.radio(
            "Choose an option",
            ["Log In", "Sign Up"],
            horizontal=True,
            key="auth_mode_radio",
        )

        if mode == "Log In":
            with st.form("login_form", clear_on_submit=False):
                st.markdown("#### Welcome back")
                login_email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                    key="login_email",
                )
                login_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    key="login_password",
                )
                login_submitted = st.form_submit_button(
                    "Log In",
                    type="primary",
                    use_container_width=True,
                )
                if login_submitted:
                    if not login_email or not login_password:
                        st.session_state.auth_error = "Please enter both email and password."
                        st.rerun()
                    else:
                        if sign_in(login_email, login_password):
                            st.rerun()
                        else:
                            st.rerun()
        else:
            with st.form("signup_form", clear_on_submit=False):
                st.markdown("#### Create your account")
                signup_email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                    key="signup_email",
                )
                signup_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Choose a password (min 6 characters)",
                    key="signup_password",
                )
                signup_confirm = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Confirm your password",
                    key="signup_confirm",
                )
                signup_submitted = st.form_submit_button(
                    "Create Account",
                    type="primary",
                    use_container_width=True,
                )
                if signup_submitted:
                    if not signup_email or not signup_password:
                        st.session_state.auth_error = "Please fill in all fields."
                        st.rerun()
                    elif len(signup_password) < 6:
                        st.session_state.auth_error = "Password must be at least 6 characters."
                        st.rerun()
                    elif signup_password != signup_confirm:
                        st.session_state.auth_error = "Passwords do not match."
                        st.rerun()
                    else:
                        if sign_up(signup_email, signup_password):
                            st.rerun()
                        else:
                            st.rerun()
