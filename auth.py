"""
Authentication for Storytime Studio.

Sign-in options (all shown on one screen):
  1. Google OIDC          — when [auth] secrets are configured
  2. Email + password     — primary path, works without SMTP
  3. Email OTP code       — fallback; shows code on-screen if SMTP not configured

Backward-compatible with the original MongoDB user schema:
  - _id = user UUID (primary key)
  - password_hash + salt  (PBKDF2, salt encoded as UTF-8 string, 200k iters)
  - email_verified, credits, gemini_api_key, openrouter_api_key,
    vertex_project_id, vertex_location, vertex_sa_json

New users created after this update also get a `user_id` field for
forward compatibility with new modules (template_flow etc.).

Session tokens: supports BOTH the old format (stored as _id) and the new
format (stored as token_hash) so existing sessions keep working.
"""

import streamlit as st
import os
import hashlib
import secrets
import uuid
import random
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

ADMIN_EMAILS = {"rahul.31.shah@gmail.com"}
APP_NAME = "Storytime Studio"

OTP_TTL_MINUTES = 10
OTP_RESEND_SECONDS = 60
MAX_OTP_ATTEMPTS = 5
SESSION_DAYS = 7

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _conf(key: str, default: str = "") -> str:
    """Read from env first, then Streamlit secrets."""
    val = os.getenv(key, "")
    if val:
        return val
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _users():
    from mongo_client import users_col
    return users_col()


def _sessions():
    from mongo_client import sessions_col
    return sessions_col()


def _otps():
    from mongo_client import otps_col
    return otps_col()


# ---------------------------------------------------------------------------
# Password (original schema: PBKDF2 with salt as UTF-8 string, 200k iters)
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> Tuple[str, str]:
    """Returns (pw_hash_hex, salt_hex). Salt stored/used as a UTF-8 string."""
    salt = secrets.token_hex(16)   # 32-char hex string
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return dk.hex(), salt


def _verify_password_original(password: str, stored_hash: str, salt: str) -> bool:
    """Verify against the original schema (salt.encode())."""
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return secrets.compare_digest(dk.hex(), stored_hash)


def _get_user_id(user: dict) -> str:
    """Return the user's UUID, handling both old (_id) and new (user_id) docs."""
    return user.get("user_id") or str(user["_id"])


# ---------------------------------------------------------------------------
# Session tokens (supports old _id format + new token_hash format)
# ---------------------------------------------------------------------------

def _create_session_token(user_id: str) -> str:
    token = secrets.token_hex(32)
    expires = _now_utc() + timedelta(days=SESSION_DAYS)
    try:
        _sessions().insert_one({
            "_id": token,                          # old format — keeps old sessions working
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),  # new format index
            "user_id": user_id,
            "expires_at": expires,
            "created_at": _now_utc(),
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
    """Validate a cookie token and restore auth session. Supports both schemas."""
    if not token:
        return False
    try:
        now = _now_utc()
        # Try token as _id (old format), or token_hash (new format)
        session = _sessions().find_one({"_id": token}) or _sessions().find_one(
            {"token_hash": hashlib.sha256(token.encode()).hexdigest()}
        )
        if not session:
            return False
        expires = session.get("expires_at")
        if expires:
            # Handle both naive and aware datetimes
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < now:
                _sessions().delete_one({"_id": session["_id"]})
                return False
        user_id = session.get("user_id")
        user = _users().find_one({"$or": [{"_id": user_id}, {"user_id": user_id}]})
        if not user:
            return False
        _load_user_into_session(_get_user_id(user), user["email"], user,
                                new_token=False)
        # CRITICAL: store the active token so sign_out() can delete it and clear
        # the cookie. Without this, clicking "Log Out" has no token to delete and
        # the cookie just restores the session on the next rerun.
        st.session_state._session_token = token
        return True
    except Exception as e:
        logger.error(f"Session restore failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_auth_state():
    defaults = {
        "auth_user": None,
        "auth_error": None,
        "auth_success": None,
        "auth_mode": "login",
        "auth_stage": "login",      # new style: login | otp | set_password
        "otp_pending_email": None,  # old style (kept for compat)
        "otp_last_sent_at": None,
        # new-style fields (used by template_flow etc.)
        "authenticated": False,
        "user_id": None,
        "user_email": None,
        "is_admin": False,
        "_pending_session_token": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def is_authenticated() -> bool:
    return (
        st.session_state.get("auth_user") is not None
        or bool(st.session_state.get("authenticated"))
    )


def get_current_user_id() -> str:
    # Support both old dict style and new field style
    user = st.session_state.get("auth_user")
    if user:
        return user.get("id", "")
    return st.session_state.get("user_id", "") or ""


def _load_user_into_session(user_id: str, email: str, user: dict,
                             new_token: bool = True):
    """Set all session state fields after successful auth — both old and new style."""
    # Old style (main.py uses auth_user["email"] / auth_user["id"])
    st.session_state.auth_user = {"id": user_id, "email": email}
    st.session_state.auth_error = None
    st.session_state.auth_success = None
    st.session_state.otp_pending_email = None

    # New style (template_flow / payments use these)
    st.session_state.authenticated = True
    st.session_state.user_id = user_id
    st.session_state.user_email = email
    st.session_state.is_admin = email in ADMIN_EMAILS
    st.session_state.auth_stage = "login"

    # API keys / Vertex
    if user.get("gemini_api_key"):
        st.session_state.api_key = user["gemini_api_key"]
    if user.get("openrouter_api_key"):
        st.session_state.openrouter_api_key = user["openrouter_api_key"]
    if user.get("vertex_project_id"):
        st.session_state.vertex_project_id = user["vertex_project_id"]
    if user.get("vertex_location"):
        st.session_state.vertex_location = user["vertex_location"]
    if user.get("vertex_sa_json"):
        st.session_state.vertex_sa_json = user["vertex_sa_json"]

    # Non-admin fallback to admin's shared credentials
    if email not in ADMIN_EMAILS and not user.get("vertex_sa_json"):
        admin_cfg = get_admin_vertex_config()
        if admin_cfg:
            if not st.session_state.get("vertex_project_id") and admin_cfg.get("project_id"):
                st.session_state.vertex_project_id = admin_cfg["project_id"]
            if not st.session_state.get("vertex_location"):
                st.session_state.vertex_location = admin_cfg.get("location", "us-central1")
            if not st.session_state.get("vertex_sa_json") and admin_cfg.get("sa_json"):
                st.session_state.vertex_sa_json = admin_cfg["sa_json"]
            if not st.session_state.get("api_key") and admin_cfg.get("gemini_api_key"):
                st.session_state.api_key = admin_cfg["gemini_api_key"]
            if not st.session_state.get("openrouter_api_key") and admin_cfg.get("openrouter_api_key"):
                st.session_state.openrouter_api_key = admin_cfg["openrouter_api_key"]

    if new_token:
        st.session_state._pending_session_token = _create_session_token(user_id)


def sign_out():
    current_token = st.session_state.get("_session_token", "")
    if current_token:
        st.session_state._token_to_delete = current_token
        _delete_session_token(current_token)
    # Clear old-style
    st.session_state.auth_user = None
    st.session_state.auth_error = None
    st.session_state.auth_success = None
    st.session_state.otp_pending_email = None
    # Clear new-style
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_email = None
    st.session_state.is_admin = False
    st.session_state.auth_stage = "login"
    # Clear keys
    for k in ("api_key", "openrouter_api_key", "_session_token", "_pending_session_token"):
        st.session_state[k] = ""
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
    if not hasattr(st, "login"):
        return False
    try:
        return bool(st.secrets.get("auth", {}).get("client_id"))
    except Exception:
        return False


def sync_google_session() -> bool:
    """Mirror st.user into our session after st.login(). Returns True if synced."""
    try:
        if not hasattr(st, "user") or not getattr(st.user, "is_logged_in", False):
            return False
        if is_authenticated():
            return True
        email = getattr(st.user, "email", None)
        if not email:
            return False
        email = email.strip().lower()
        user = _users().find_one({"email": email})
        if not user:
            uid = str(uuid.uuid4())
            user = {
                "_id": uid, "user_id": uid, "email": email,
                "email_verified": True, "auth_provider": "google",
                "credits": 0, "created_at": _now_utc(),
            }
            _users().insert_one(user)
        else:
            _users().update_one({"email": email},
                                {"$set": {"email_verified": True, "last_login_at": _now_utc()}})
        _load_user_into_session(_get_user_id(user), email, user)
        return True
    except Exception as e:
        logger.warning(f"Google session sync failed: {e}")
        return False


# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------

def _send_otp_email(to_email: str, otp: str) -> bool:
    # Support original GMAIL_* vars and generic SMTP_* vars
    smtp_user = _conf("GMAIL_USER") or _conf("SMTP_USER")
    smtp_password = _conf("GMAIL_APP_PASSWORD") or _conf("SMTP_PASSWORD")
    smtp_host = _conf("SMTP_HOST", "smtp.gmail.com")
    smtp_port_str = _conf("SMTP_PORT", "465")
    from_email = _conf("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_password:
        logger.warning("Email credentials not configured (GMAIL_USER/GMAIL_APP_PASSWORD or SMTP_*)")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your {APP_NAME} sign-in code: {otp}"
        msg["From"] = from_email
        msg["To"] = to_email
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px;
                    border:1px solid #e0e0e0;border-radius:8px;">
          <h2 style="color:#FF6B6B;margin-top:0;">{APP_NAME}</h2>
          <p style="color:#444;">Use this code to sign in:</p>
          <div style="background:#FFF4F4;border-radius:8px;padding:24px;text-align:center;
                      letter-spacing:12px;font-size:36px;font-weight:bold;color:#FF6B6B;">
            {otp}
          </div>
          <p style="color:#888;font-size:13px;margin-top:20px;">
            Expires in <strong>{OTP_TTL_MINUTES} minutes</strong>.
            If you didn't request this, ignore this email.
          </p>
        </div>"""
        msg.attach(MIMEText(html, "html"))
        port = int(smtp_port_str)
        if port == 465:
            with smtplib.SMTP_SSL(smtp_host, 465) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, to_email, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, port, timeout=15) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"OTP email failed: {e}")
        return False


def _generate_and_store_otp(email: str) -> str:
    otp = str(random.SystemRandom().randint(100000, 999999))
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    expires = _now_utc() + timedelta(minutes=OTP_TTL_MINUTES)
    _otps().delete_many({"email": email})
    _otps().insert_one({
        "email": email, "otp_hash": otp_hash, "attempts": 0,
        "expires_at": expires, "created_at": _now_utc(),
    })
    return otp


def send_otp(email: str) -> Tuple[bool, str]:
    """Generate, store and email OTP. Returns (email_sent, otp_code)."""
    otp = _generate_and_store_otp(email)
    sent = _send_otp_email(email, otp)
    return sent, otp


def verify_otp(email: str, otp: str) -> bool:
    """Check OTP. On success marks user email_verified and deletes the record."""
    try:
        email = email.strip().lower()
        now = _now_utc()
        doc = _otps().find_one({"email": email})
        if not doc:
            return False
        expires = doc.get("expires_at", _now_utc())
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            _otps().delete_many({"email": email})
            return False
        if doc.get("attempts", 0) >= MAX_OTP_ATTEMPTS:
            _otps().delete_many({"email": email})
            return False
        if hashlib.sha256(otp.strip().encode()).hexdigest() != doc["otp_hash"]:
            _otps().update_one({"email": email}, {"$inc": {"attempts": 1}})
            return False
        _users().update_one(
            {"$or": [{"email": email}]},
            {"$set": {"email_verified": True}}
        )
        _otps().delete_many({"email": email})
        return True
    except Exception as e:
        logger.error(f"verify_otp error: {e}")
        return False


def complete_otp_verification(email: str, otp_code: str) -> bool:
    if not verify_otp(email, otp_code):
        st.session_state.auth_error = "Incorrect or expired code. Please try again."
        return False
    user = _users().find_one({"email": email.strip().lower()})
    if not user:
        st.session_state.auth_error = "Account not found."
        return False
    _load_user_into_session(_get_user_id(user), email, user)
    return True


# ---------------------------------------------------------------------------
# Email + password auth (backward-compatible with original schema)
# ---------------------------------------------------------------------------

def sign_in(email: str, password: str) -> bool:
    """Sign in with email + password. Populates auth_error on failure."""
    try:
        email = email.strip().lower()
        user = _users().find_one({"email": email})
        if not user:
            st.session_state.auth_error = "No account found for this email. Please sign up."
            return False

        pw_hash = user.get("password_hash")
        salt = user.get("salt")
        if not pw_hash or not salt:
            st.session_state.auth_error = (
                "This account has no password set. "
                "Use 'Get a sign-in code' below."
            )
            return False

        if not _verify_password_original(password, pw_hash, salt):
            st.session_state.auth_error = "Incorrect password."
            return False

        # Admin bypasses OTP entirely
        if email in ADMIN_EMAILS:
            if not user.get("email_verified"):
                _users().update_one({"email": email}, {"$set": {"email_verified": True}})
            _load_user_into_session(_get_user_id(user), email, user)
            return True

        # Non-admin: require email verification via OTP
        if not user.get("email_verified", False):
            st.session_state.otp_pending_email = email
            st.session_state.otp_last_sent_at = _now_utc()
            sent, otp_code = send_otp(email)
            if sent:
                st.session_state.auth_success = f"Please verify your email — code sent to {email}."
            else:
                st.session_state.auth_success = (
                    f"Email delivery not configured. Your code is: **{otp_code}**"
                )
            st.session_state.auth_error = None
            return False  # wait for OTP screen

        _load_user_into_session(_get_user_id(user), email, user)
        return True
    except Exception as e:
        st.session_state.auth_error = f"Login failed: {e}"
        logger.error(f"sign_in error: {e}")
        return False


def check_password_login(email: str, password: str) -> Tuple[bool, str]:
    """Thin wrapper used by new-style callers. Returns (ok, error_msg)."""
    ok = sign_in(email, password)
    err = st.session_state.get("auth_error") or ""
    return ok, err


def sign_up(email: str, password: str) -> bool:
    """Create a new account. Admin accounts are auto-verified."""
    try:
        email = email.strip().lower()
        if len(password) < 6:
            st.session_state.auth_error = "Password must be at least 6 characters."
            return False
        if _users().find_one({"email": email}):
            st.session_state.auth_error = "This email is already registered. Please log in."
            return False
        pw_hash, salt = _hash_password(password)
        uid = str(uuid.uuid4())
        is_admin = email in ADMIN_EMAILS
        _users().insert_one({
            "_id": uid,
            "user_id": uid,   # forward-compat field
            "email": email,
            "password_hash": pw_hash,
            "salt": salt,
            "gemini_api_key": "",
            "openrouter_api_key": "",
            "email_verified": is_admin,
            "credits": 0,
            "created_at": _now_utc(),
        })
        st.session_state.auth_error = None
        if is_admin:
            user = _users().find_one({"_id": uid})
            _load_user_into_session(uid, email, user)
            st.session_state.auth_success = "Admin account created and logged in."
            return True
        # Send OTP for non-admin
        st.session_state.otp_pending_email = email
        st.session_state.otp_last_sent_at = _now_utc()
        sent, otp_code = send_otp(email)
        if sent:
            st.session_state.auth_success = f"Account created! Code sent to {email}."
        else:
            st.session_state.auth_success = (
                f"Account created! Email not configured. Your code: **{otp_code}**"
            )
        return True
    except Exception as e:
        st.session_state.auth_error = f"Sign up failed: {e}"
        logger.error(f"sign_up error: {e}")
        return False


def set_password(user_id: str, password: str) -> None:
    """Set (or reset) password for a user."""
    pw_hash, salt = _hash_password(password)
    _users().update_one(
        {"$or": [{"_id": user_id}, {"user_id": user_id}]},
        {"$set": {"password_hash": pw_hash, "salt": salt}},
    )


# ---------------------------------------------------------------------------
# Vertex / API key persistence  (original 4-arg signature kept)
# ---------------------------------------------------------------------------

def save_user_api_key(user_id: str, api_key: str) -> bool:
    try:
        _users().update_one(
            {"$or": [{"_id": user_id}, {"user_id": user_id}]},
            {"$set": {"gemini_api_key": api_key}}
        )
        return True
    except Exception as e:
        logger.error(f"save_user_api_key: {e}")
        return False


def load_user_api_key(user_id: str) -> str:
    user = _users().find_one({"$or": [{"_id": user_id}, {"user_id": user_id}]})
    return (user or {}).get("gemini_api_key", "")


def save_user_openrouter_key(user_id: str, api_key: str) -> bool:
    try:
        _users().update_one(
            {"$or": [{"_id": user_id}, {"user_id": user_id}]},
            {"$set": {"openrouter_api_key": api_key}}
        )
        return True
    except Exception as e:
        logger.error(f"save_user_openrouter_key: {e}")
        return False


def load_user_openrouter_key(user_id: str) -> str:
    user = _users().find_one({"$or": [{"_id": user_id}, {"user_id": user_id}]})
    return (user or {}).get("openrouter_api_key", "")


def save_user_vertex_config(user_id: str, project_id: str, location: str, sa_json: str) -> bool:
    """Original 4-argument signature — keeps main.py call sites working."""
    try:
        _users().update_one(
            {"$or": [{"_id": user_id}, {"user_id": user_id}]},
            {"$set": {
                "vertex_project_id": project_id,
                "vertex_location": location or "us-central1",
                "vertex_sa_json": sa_json,
            }}
        )
        return True
    except Exception as e:
        logger.error(f"save_user_vertex_config: {e}")
        return False


def load_user_vertex_config(user_id: str) -> dict:
    user = _users().find_one({"$or": [{"_id": user_id}, {"user_id": user_id}]})
    if user:
        return {
            "project_id": user.get("vertex_project_id", ""),
            "location": user.get("vertex_location", "us-central1"),
            "sa_json": user.get("vertex_sa_json", ""),
        }
    return {"project_id": "", "location": "us-central1", "sa_json": ""}


def get_admin_vertex_config() -> dict:
    try:
        for admin_email in ADMIN_EMAILS:
            admin = _users().find_one({"email": admin_email})
            if admin and admin.get("vertex_sa_json"):
                return {
                    "project_id": admin.get("vertex_project_id", ""),
                    "location": admin.get("vertex_location", "us-central1"),
                    "sa_json": admin.get("vertex_sa_json", ""),
                    "gemini_api_key": admin.get("gemini_api_key", ""),
                    "openrouter_api_key": admin.get("openrouter_api_key", ""),
                }
    except Exception as e:
        logger.warning(f"get_admin_vertex_config: {e}")
    return {}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

_CSS = """
<style>
.auth-hero{text-align:center;padding:8px 0 12px;}
.auth-hero h1{font-size:2rem;margin-bottom:0.2rem;}
.auth-hero p{color:#777;margin-top:0;}
</style>
"""


def render_auth_page():
    """Primary sign-in screen."""
    st.markdown(_CSS, unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1.5, 1])
    with center:
        st.markdown(
            f'<div class="auth-hero">'
            f'<div style="font-size:3rem;">📚</div>'
            f'<h1>{APP_NAME}</h1>'
            f'<p>Personalized storybooks your child will treasure.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.session_state.get("auth_error"):
            st.error(st.session_state.auth_error)
            st.session_state.auth_error = None
        if st.session_state.get("auth_success"):
            st.success(st.session_state.auth_success)
            st.session_state.auth_success = None

        # Google
        if google_auth_available():
            if st.button("Continue with Google", type="primary",
                         use_container_width=True, key="google_btn"):
                st.login()
            st.markdown(
                '<div style="display:flex;align-items:center;color:#aaa;margin:10px 0;">'
                '<div style="flex:1;height:1px;background:#e3e3e3;"></div>'
                '<span style="padding:0 12px;font-size:.85rem;">or</span>'
                '<div style="flex:1;height:1px;background:#e3e3e3;"></div></div>',
                unsafe_allow_html=True,
            )

        tab_login, tab_signup = st.tabs(["Sign in", "Create account"])

        with tab_login:
            with st.form("login_form"):
                login_email = st.text_input("Email", placeholder="you@example.com",
                                            label_visibility="collapsed", key="li_email")
                login_pw = st.text_input("Password", type="password",
                                         placeholder="Password",
                                         label_visibility="collapsed", key="li_pw")
                login_ok = st.form_submit_button("Sign in", type="primary",
                                                 use_container_width=True)
            if login_ok:
                if not login_email or not login_pw:
                    st.session_state.auth_error = "Please enter your email and password."
                    st.rerun()
                elif sign_in(login_email, login_pw):
                    st.rerun()
                elif st.session_state.get("otp_pending_email"):
                    st.rerun()   # go to OTP screen
                else:
                    st.rerun()   # show error

            st.divider()
            st.caption("No password? Get a one-time code instead:")
            with st.form("otp_req_form"):
                otp_email = st.text_input("Email for sign-in code",
                                          placeholder="you@example.com",
                                          label_visibility="collapsed",
                                          key="otp_req_email")
                otp_ok = st.form_submit_button("Get a sign-in code",
                                               use_container_width=True)
            if otp_ok:
                otp_email = (otp_email or "").strip().lower()
                if not otp_email:
                    st.error("Please enter your email.")
                else:
                    st.session_state.otp_pending_email = otp_email
                    st.session_state.otp_last_sent_at = _now_utc()
                    sent, otp_code = send_otp(otp_email)
                    if sent:
                        st.session_state.auth_success = f"Code sent to {otp_email}."
                    else:
                        st.session_state.auth_success = (
                            f"Email not configured. Your code: **{otp_code}**"
                        )
                    st.rerun()

        with tab_signup:
            with st.form("signup_form"):
                su_email = st.text_input("Email", placeholder="you@example.com",
                                         label_visibility="collapsed", key="su_email")
                su_pw = st.text_input("Password", type="password",
                                      placeholder="At least 6 characters",
                                      label_visibility="collapsed", key="su_pw")
                su_pw2 = st.text_input("Confirm password", type="password",
                                       placeholder="Repeat password",
                                       label_visibility="collapsed", key="su_pw2")
                su_ok = st.form_submit_button("Create account", type="primary",
                                              use_container_width=True)
            if su_ok:
                if su_pw != su_pw2:
                    st.error("Passwords don't match.")
                elif sign_up(su_email, su_pw):
                    st.rerun()
                elif st.session_state.get("otp_pending_email"):
                    st.rerun()
                else:
                    st.rerun()

        st.caption("By continuing you agree to our terms of use.")


def render_otp_page():
    """OTP verification screen."""
    email = st.session_state.get("otp_pending_email", "")

    # Admin never needs OTP — auto-verify and log in
    if email in ADMIN_EMAILS:
        user = _users().find_one({"email": email})
        if user:
            _users().update_one({"email": email}, {"$set": {"email_verified": True}})
            _load_user_into_session(_get_user_id(user), email, user)
            st.rerun()
        return

    _, center, _ = st.columns([1, 1.5, 1])
    with center:
        st.markdown(
            f'<div class="auth-hero">'
            f'<div style="font-size:3rem;">📨</div>'
            f'<h1>Check your email</h1>'
            f'<p>We sent a 6-digit code to <b>{email}</b></p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.session_state.get("auth_error"):
            st.error(st.session_state.auth_error)
            st.session_state.auth_error = None
        if st.session_state.get("auth_success"):
            st.success(st.session_state.auth_success)
            st.session_state.auth_success = None

        with st.form("otp_form", clear_on_submit=True):
            otp_input = st.text_input("Enter 6-digit code", placeholder="123456",
                                      max_chars=6, label_visibility="collapsed")
            otp_submitted = st.form_submit_button("Verify", type="primary",
                                                  use_container_width=True)
        if otp_submitted:
            if not otp_input or len(otp_input.strip()) != 6:
                st.session_state.auth_error = "Please enter the full 6-digit code."
            elif complete_otp_verification(email, otp_input.strip()):
                pass
            st.rerun()

        last_sent = st.session_state.get("otp_last_sent_at")
        can_resend = not last_sent or (_now_utc() - last_sent.replace(tzinfo=timezone.utc)
                                       if last_sent.tzinfo is None
                                       else _now_utc() - last_sent
                                       ).total_seconds() >= OTP_RESEND_SECONDS
        c1, c2 = st.columns(2)
        with c1:
            if can_resend:
                if st.button("Resend code", use_container_width=True):
                    sent, otp_code = send_otp(email)
                    st.session_state.otp_last_sent_at = _now_utc()
                    st.session_state.auth_success = (
                        "New code sent." if sent
                        else f"Email not configured. Code: **{otp_code}**"
                    )
                    st.rerun()
            else:
                remaining = OTP_RESEND_SECONDS - int(
                    (_now_utc() - (last_sent.replace(tzinfo=timezone.utc)
                                   if last_sent.tzinfo is None else last_sent)).total_seconds()
                )
                st.caption(f"Resend in {remaining}s")
        with c2:
            if st.button("← Back to login", use_container_width=True):
                st.session_state.otp_pending_email = None
                st.rerun()


def render_set_password_page():
    """Prompt a user to set/change their password (optional step after OTP)."""
    _, center, _ = st.columns([1, 1.5, 1])
    with center:
        st.markdown(
            '<div class="auth-hero">'
            '<div style="font-size:3rem;">🔑</div>'
            '<h1>Set a password</h1>'
            '<p>Sign in faster next time — set a password for your account.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        with st.form("set_pw_form"):
            pw = st.text_input("Password", type="password",
                               placeholder="At least 6 characters",
                               label_visibility="collapsed")
            pw2 = st.text_input("Confirm", type="password",
                                placeholder="Repeat password",
                                label_visibility="collapsed")
            c1, c2 = st.columns(2)
            with c1:
                save = st.form_submit_button("Save password", type="primary",
                                             use_container_width=True)
            with c2:
                skip = st.form_submit_button("Skip for now", use_container_width=True)
        if save:
            if len(pw) < 6:
                st.error("Password must be at least 6 characters.")
            elif pw != pw2:
                st.error("Passwords don't match.")
            else:
                uid = st.session_state.get("user_id") or (
                    st.session_state.get("auth_user") or {}
                ).get("id", "")
                if uid:
                    set_password(uid, pw)
                st.session_state.auth_stage = "login"
                st.success("Password saved!")
                st.rerun()
        if skip:
            st.session_state.auth_stage = "login"
            st.rerun()
