"""
Authentication for Storytime Studio.

Passwordless auth with two paths:
  1. Google sign-in (Streamlit native OIDC via st.login / st.user)
  2. Email + one-time code (OTP) sent over SMTP

Sessions persist across reloads via a signed token stored in a browser
cookie (handled in main.py) and mirrored in the `sessions` collection.

No passwords are ever stored.
"""

import streamlit as st
import os
import hashlib
import secrets
import uuid
import random
import smtplib
import logging
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from dotenv import load_dotenv

from mongo_client import users_col, sessions_col, otps_col

logger = logging.getLogger(__name__)

APP_NAME = "Storytime Studio"
ADMIN_EMAILS = {"rahul.31.shah@gmail.com"}

OTP_TTL_MINUTES = 10
OTP_RESEND_SECONDS = 60
MAX_OTP_ATTEMPTS = 5
SESSION_DAYS = 7

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _conf(key: str, default: str = "") -> str:
    """Env var first, then Streamlit secrets."""
    val = os.getenv(key, "")
    if val:
        return val
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def _get_or_create_user(email: str, verified: bool = True, via: str = "email") -> dict:
    email = email.strip().lower()
    user = users_col().find_one({"email": email})
    if user is None:
        user = {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "email_verified": verified,
            "auth_provider": via,
            "created_at": _now(),
            "last_login_at": _now(),
        }
        users_col().insert_one(user)
    else:
        updates = {"last_login_at": _now()}
        if verified and not user.get("email_verified"):
            updates["email_verified"] = True
        users_col().update_one({"email": email}, {"$set": updates})
        user.update(updates)
    return user


# ---------------------------------------------------------------------------
# Session tokens (cookie-backed persistence)
# ---------------------------------------------------------------------------

def _create_session_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    sessions_col().insert_one(
        {
            "token_hash": _hash(token),
            "user_id": user_id,
            "created_at": _now(),
            "expires_at": _now() + timedelta(days=SESSION_DAYS),
        }
    )
    return token


def _delete_session_token(token: str) -> None:
    try:
        sessions_col().delete_one({"token_hash": _hash(token)})
    except Exception:
        pass


def restore_session_from_token(token: str) -> bool:
    """Restore a login from a cookie token. Returns True on success."""
    if not token:
        return False
    try:
        doc = sessions_col().find_one({"token_hash": _hash(token)})
        if not doc:
            return False
        expires = doc.get("expires_at")
        if expires is not None and expires.replace(tzinfo=timezone.utc) < _now():
            sessions_col().delete_one({"_id": doc["_id"]})
            return False
        user = users_col().find_one({"user_id": doc["user_id"]})
        if not user:
            return False
        _load_user_into_session(user, new_session_token=False)
        return True
    except Exception as e:
        logger.warning(f"Session restore failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_auth_state() -> None:
    defaults = {
        "authenticated": False,
        "user_id": None,
        "user_email": None,
        "is_admin": False,
        "auth_stage": "login",  # login | otp
        "otp_email": "",
        "otp_sent_at": None,
        "_pending_session_token": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


def get_current_user_id() -> Optional[str]:
    return st.session_state.get("user_id")


def _load_user_into_session(user: dict, new_session_token: bool = True) -> None:
    st.session_state.authenticated = True
    st.session_state.user_id = user["user_id"]
    st.session_state.user_email = user["email"]
    # Legacy shape used across main.py / template_book_generator.py
    st.session_state.auth_user = {"id": user["user_id"], "email": user["email"]}
    st.session_state.is_admin = user["email"] in ADMIN_EMAILS
    st.session_state.auth_stage = "login"
    if new_session_token:
        st.session_state._pending_session_token = _create_session_token(user["user_id"])
    _hydrate_keys_into_session(user)


def sign_out() -> None:
    token = st.session_state.get("_session_token") or st.session_state.get(
        "_pending_session_token"
    )
    if token:
        _delete_session_token(token)
        # main.py watches this key to clear the browser cookie
        st.session_state._token_to_delete = token
    for key in [
        "authenticated",
        "user_id",
        "user_email",
        "auth_user",
        "is_admin",
        "_session_token",
        "_pending_session_token",
        "otp_email",
        "otp_sent_at",
        "api_key",
        "openrouter_key",
        "openrouter_api_key",
        "vertex_config",
    ]:
        st.session_state.pop(key, None)
    st.session_state.auth_stage = "login"
    # Also end Google OIDC session if active
    try:
        if hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
            st.logout()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Google sign-in (Streamlit native OIDC)
# ---------------------------------------------------------------------------

def google_auth_available() -> bool:
    """True when [auth] is configured in Streamlit secrets."""
    if not hasattr(st, "login"):
        return False
    try:
        auth_cfg = st.secrets.get("auth", {})
        return bool(auth_cfg.get("client_id"))
    except Exception:
        return False


def sync_google_session() -> bool:
    """If the user just completed Google login, mirror it into our session."""
    try:
        if not hasattr(st, "user"):
            return False
        if not getattr(st.user, "is_logged_in", False):
            return False
        if is_authenticated():
            return True
        email = getattr(st.user, "email", None)
        if not email:
            return False
        user = _get_or_create_user(email, verified=True, via="google")
        _load_user_into_session(user)
        return True
    except Exception as e:
        logger.warning(f"Google session sync failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Email OTP
# ---------------------------------------------------------------------------

def _send_otp_email(to_email: str, otp_code: str) -> bool:
    smtp_host = _conf("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(_conf("SMTP_PORT", "587") or 587)
    smtp_user = _conf("SMTP_USER")
    smtp_password = _conf("SMTP_PASSWORD")
    from_email = _conf("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_password:
        logger.warning("SMTP not configured; OTP email not sent.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{otp_code} is your {APP_NAME} sign-in code"
    msg["From"] = from_email
    msg["To"] = to_email
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:440px;margin:0 auto;padding:24px;">
      <h2 style="color:#FF6B6B;margin-bottom:4px;">{APP_NAME}</h2>
      <p>Use this code to sign in. It expires in {OTP_TTL_MINUTES} minutes.</p>
      <div style="font-size:32px;font-weight:bold;letter-spacing:8px;
                  background:#FFF4F4;border-radius:12px;padding:16px;
                  text-align:center;margin:16px 0;">{otp_code}</div>
      <p style="color:#888;font-size:12px;">If you didn't request this, you can ignore this email.</p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception as e:
        logger.error(f"OTP email failed: {e}")
        return False


def _issue_otp(email: str) -> Tuple[bool, str]:
    """Create + email an OTP. Returns (ok, error_message)."""
    email = email.strip().lower()
    otp_code = f"{random.SystemRandom().randint(0, 999999):06d}"
    otps_col().delete_many({"email": email})
    otps_col().insert_one(
        {
            "email": email,
            "otp_hash": _hash(otp_code),
            "attempts": 0,
            "created_at": _now(),
            "expires_at": _now() + timedelta(minutes=OTP_TTL_MINUTES),
        }
    )
    sent = _send_otp_email(email, otp_code)
    allow_dev = _conf("ALLOW_DEV_OTP", "").lower() == "true"
    if not sent and allow_dev:
        st.session_state["_dev_otp"] = otp_code
        return True, ""
    if not sent:
        return False, "Could not send the sign-in code. Please try again in a minute."
    return True, ""


def start_email_login(email: str) -> Tuple[bool, str]:
    """Begin email OTP flow. Returns (ok, error_message)."""
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        return False, "Please enter a valid email address."
    last_sent = st.session_state.get("otp_sent_at")
    if last_sent and (_now() - last_sent).total_seconds() < OTP_RESEND_SECONDS:
        return False, f"Please wait a moment before requesting another code."
    ok, err = _issue_otp(email)
    if not ok:
        return False, err
    st.session_state.otp_email = email
    st.session_state.otp_sent_at = _now()
    st.session_state.auth_stage = "otp"
    return True, ""


def verify_otp(email: str, otp_code: str) -> Tuple[bool, str]:
    """Check an OTP. Returns (ok, error_message)."""
    email = (email or "").strip().lower()
    otp_code = (otp_code or "").strip()
    if not otp_code.isdigit() or len(otp_code) != 6:
        return False, "The code is 6 digits."
    doc = otps_col().find_one({"email": email})
    if not doc:
        return False, "Code expired or not found. Request a new one."
    if doc.get("expires_at") and doc["expires_at"].replace(
        tzinfo=timezone.utc
    ) < _now():
        otps_col().delete_one({"_id": doc["_id"]})
        return False, "That code has expired. Request a new one."
    if doc.get("attempts", 0) >= MAX_OTP_ATTEMPTS:
        otps_col().delete_one({"_id": doc["_id"]})
        return False, "Too many attempts. Request a new code."
    if _hash(otp_code) != doc["otp_hash"]:
        otps_col().update_one({"_id": doc["_id"]}, {"$inc": {"attempts": 1}})
        return False, "That code isn't right. Check and try again."
    otps_col().delete_one({"_id": doc["_id"]})
    return True, ""


def complete_otp_verification(email: str, otp_code: str) -> Tuple[bool, str]:
    ok, err = verify_otp(email, otp_code)
    if not ok:
        return False, err
    user = _get_or_create_user(email, verified=True, via="email")
    _load_user_into_session(user)
    st.session_state.pop("_dev_otp", None)
    return True, ""


# ---------------------------------------------------------------------------
# Per-user API keys (BYO keys for admins / power users)
# ---------------------------------------------------------------------------

def save_user_api_key(user_id: str, api_key: str) -> None:
    users_col().update_one({"user_id": user_id}, {"$set": {"gemini_api_key": api_key}})


def load_user_api_key(user_id: str) -> Optional[str]:
    user = users_col().find_one({"user_id": user_id})
    return user.get("gemini_api_key") if user else None


def save_user_openrouter_key(user_id: str, api_key: str) -> None:
    users_col().update_one(
        {"user_id": user_id}, {"$set": {"openrouter_api_key": api_key}}
    )


def load_user_openrouter_key(user_id: str) -> Optional[str]:
    user = users_col().find_one({"user_id": user_id})
    return user.get("openrouter_api_key") if user else None


def save_user_vertex_config(user_id: str, config: dict) -> None:
    users_col().update_one({"user_id": user_id}, {"$set": {"vertex_config": config}})


def load_user_vertex_config(user_id: str) -> Optional[dict]:
    user = users_col().find_one({"user_id": user_id})
    return user.get("vertex_config") if user else None


def get_admin_vertex_config() -> Optional[dict]:
    """Shared Vertex config from the admin account — customers fall back to this."""
    for admin_email in ADMIN_EMAILS:
        admin = users_col().find_one({"email": admin_email})
        if admin and admin.get("vertex_config"):
            return admin["vertex_config"]
    return None


def _hydrate_keys_into_session(user: dict) -> None:
    """Load API keys into session. Customers fall back to the admin's keys."""
    api_key = user.get("gemini_api_key")
    openrouter_key = user.get("openrouter_api_key")
    vertex_config = user.get("vertex_config")

    if user["email"] not in ADMIN_EMAILS:
        if not vertex_config:
            vertex_config = get_admin_vertex_config()
        if not api_key or not openrouter_key:
            for admin_email in ADMIN_EMAILS:
                admin = users_col().find_one({"email": admin_email})
                if admin:
                    api_key = api_key or admin.get("gemini_api_key")
                    openrouter_key = openrouter_key or admin.get("openrouter_api_key")
                    break

    if api_key:
        st.session_state.api_key = api_key
    if openrouter_key:
        st.session_state.openrouter_key = openrouter_key
        st.session_state.openrouter_api_key = openrouter_key
    if vertex_config:
        st.session_state.vertex_config = vertex_config
        st.session_state.vertex_project_id = vertex_config.get("project_id", "")
        st.session_state.vertex_location = vertex_config.get("location", "us-central1")
        st.session_state.vertex_sa_json = vertex_config.get("sa_json", "")


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

_AUTH_CSS = """
<style>
.auth-hero { text-align:center; padding: 8px 0 4px 0; }
.auth-hero h1 { font-size: 2.2rem; margin-bottom: 0.2rem; }
.auth-hero p { color: #777; font-size: 1.05rem; margin-top: 0; }
.auth-divider { display:flex; align-items:center; color:#aaa; margin: 12px 0; }
.auth-divider::before, .auth-divider::after {
  content:""; flex:1; height:1px; background:#e3e3e3;
}
.auth-divider span { padding: 0 12px; font-size: 0.85rem; }
</style>
"""


def render_auth_page() -> None:
    """Sign-in screen: Google button + email OTP."""
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1.4, 1])
    with center:
        st.markdown(
            f"""
            <div class="auth-hero">
              <div style="font-size:3rem;">&#128214;</div>
              <h1>{APP_NAME}</h1>
              <p>Personalized storybooks your child will treasure.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")

        if google_auth_available():
            if st.button(
                "Continue with Google",
                use_container_width=True,
                type="primary",
                key="google_login_btn",
            ):
                st.login()
            st.markdown(
                '<div class="auth-divider"><span>or</span></div>',
                unsafe_allow_html=True,
            )

        with st.form("email_login_form", border=False):
            email = st.text_input(
                "Email address",
                placeholder="you@example.com",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                "Continue with email", use_container_width=True
            )
        if submitted:
            ok, err = start_email_login(email)
            if ok:
                st.rerun()
            else:
                st.error(err)

        st.caption(
            "We'll email you a one-time code — no password needed. "
            "By continuing you agree to our terms of use."
        )


def render_otp_page() -> None:
    """Code-entry screen after an OTP has been emailed."""
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    email = st.session_state.get("otp_email", "")
    _, center, _ = st.columns([1, 1.4, 1])
    with center:
        st.markdown(
            f"""
            <div class="auth-hero">
              <div style="font-size:3rem;">&#128231;</div>
              <h1>Check your email</h1>
              <p>We sent a 6-digit code to <b>{email}</b></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        dev_otp = st.session_state.get("_dev_otp")
        if dev_otp:
            st.info(f"Dev mode — your code is **{dev_otp}**")

        with st.form("otp_form", border=False):
            otp_code = st.text_input(
                "6-digit code",
                max_chars=6,
                placeholder="123456",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            ok, err = complete_otp_verification(email, otp_code)
            if ok:
                st.rerun()
            else:
                st.error(err)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Resend code", use_container_width=True):
                ok, err = start_email_login(email)
                if ok:
                    st.success("New code sent.")
                else:
                    st.error(err)
        with col_b:
            if st.button("Use a different email", use_container_width=True):
                st.session_state.auth_stage = "login"
                st.session_state.otp_email = ""
                st.rerun()
