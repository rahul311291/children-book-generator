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
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

ADMIN_EMAILS = {"rahul.31.shah@gmail.com"}

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
# OTP generation and email delivery
# ---------------------------------------------------------------------------

def _otps():
    from mongo_client import otps_col
    return otps_col()


def _generate_and_store_otp(email: str) -> str:
    """Create a 6-digit OTP, store its hash in MongoDB (TTL 10 min), return the plain OTP."""
    otp = str(random.randint(100000, 999999))
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    expires = datetime.utcnow() + timedelta(minutes=10)
    _otps().delete_many({"email": email})
    _otps().insert_one({"email": email, "otp_hash": otp_hash, "expires_at": expires,
                        "created_at": datetime.utcnow()})
    return otp


def _send_otp_email(to_email: str, otp: str, child_name: str = "") -> bool:
    """Send OTP via Gmail SMTP. Requires GMAIL_USER + GMAIL_APP_PASSWORD env vars."""
    gmail_user = os.getenv("GMAIL_USER", "")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD", "")
    if not gmail_user or not gmail_password:
        try:
            import streamlit as st
            gmail_user = gmail_user or str(st.secrets.get("GMAIL_USER", "") or "")
            gmail_password = gmail_password or str(st.secrets.get("GMAIL_APP_PASSWORD", "") or "")
        except Exception:
            pass
    if not gmail_user or not gmail_password:
        logger.error("Gmail credentials not set (GMAIL_USER / GMAIL_APP_PASSWORD)")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your Children's Book Generator verification code"
        msg["From"] = f"Children's Book Generator <{gmail_user}>"
        msg["To"] = to_email
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px;
                    border:1px solid #e0e0e0;border-radius:8px;">
          <h2 style="color:#1a73e8;margin-top:0;">Verify your email</h2>
          <p style="color:#444;">Use this code to verify your account:</p>
          <div style="background:#f5f5f5;border-radius:8px;padding:24px;text-align:center;
                      letter-spacing:12px;font-size:36px;font-weight:bold;color:#1a73e8;">
            {otp}
          </div>
          <p style="color:#888;font-size:13px;margin-top:20px;">
            This code expires in <strong>10 minutes</strong>.
            If you didn't request this, you can ignore this email.
          </p>
        </div>"""
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())
        logger.info(f"OTP email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {to_email}: {e}")
        return False


def send_otp(email: str) -> bool:
    """Generate OTP, store it, and email it. Returns True on success."""
    try:
        otp = _generate_and_store_otp(email)
        return _send_otp_email(email, otp)
    except Exception as e:
        logger.error(f"send_otp error: {e}")
        return False


def verify_otp(email: str, otp: str) -> bool:
    """Check OTP against stored hash. On success, marks user as email_verified."""
    try:
        email = email.strip().lower()
        record = _otps().find_one({"email": email, "expires_at": {"$gt": datetime.utcnow()}})
        if not record:
            return False
        if hashlib.sha256(otp.strip().encode()).hexdigest() != record["otp_hash"]:
            return False
        _users().update_one({"email": email}, {"$set": {"email_verified": True}})
        _otps().delete_many({"email": email})
        return True
    except Exception as e:
        logger.error(f"verify_otp error: {e}")
        return False


def is_email_verified(email: str) -> bool:
    try:
        user = _users().find_one({"email": email}, {"email_verified": 1})
        return bool((user or {}).get("email_verified", False))
    except Exception:
        return False


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
        user = _users().find_one(
            {"_id": session["user_id"]},
            {"email": 1, "gemini_api_key": 1, "openrouter_api_key": 1,
             "vertex_project_id": 1, "vertex_location": 1, "vertex_sa_json": 1},
        )
        if not user:
            return False
        st.session_state.auth_user = {"id": session["user_id"], "email": user["email"]}
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
    if "otp_pending_email" not in st.session_state:
        st.session_state.otp_pending_email = None
    if "otp_last_sent_at" not in st.session_state:
        st.session_state.otp_last_sent_at = None


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
        is_admin = email in ADMIN_EMAILS
        _users().insert_one({
            "_id": user_id,
            "email": email,
            "password_hash": pw_hash,
            "salt": salt,
            "gemini_api_key": "",
            "openrouter_api_key": "",
            "email_verified": is_admin,
            "credits": 0,
            "created_at": datetime.utcnow(),
        })
        st.session_state.auth_error = None
        if is_admin:
            user = _users().find_one({"_id": user_id})
            _load_user_into_session(user_id, email, user)
            st.session_state.auth_success = "Admin account created and logged in."
            return True
        # Non-admin: require OTP verification
        st.session_state.otp_pending_email = email
        st.session_state.otp_last_sent_at = datetime.utcnow()
        sent = send_otp(email)
        if sent:
            st.session_state.auth_success = f"Account created! A 6-digit code was sent to {email}."
        else:
            st.session_state.auth_success = (
                "Account created! Email delivery failed — check GMAIL_USER/GMAIL_APP_PASSWORD config."
            )
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
        # Admin bypasses OTP entirely
        if email in ADMIN_EMAILS:
            if not user.get("email_verified", False):
                _users().update_one({"_id": user["_id"]}, {"$set": {"email_verified": True}})
                user["email_verified"] = True
            user_id = str(user["_id"])
            _load_user_into_session(user_id, email, user)
            return True
        # Block unverified non-admin accounts
        if not user.get("email_verified", False):
            st.session_state.otp_pending_email = email
            st.session_state.otp_last_sent_at = datetime.utcnow()
            send_otp(email)
            st.session_state.auth_error = None
            st.session_state.auth_success = f"Please verify your email — a code was sent to {email}."
            return False  # Not yet authenticated; OTP screen will handle next step
        user_id = str(user["_id"])
        _load_user_into_session(user_id, email, user)
        return True
    except Exception as e:
        st.session_state.auth_error = f"Login failed: {e}"
        logger.error(f"Sign in error: {e}")
        return False


def _load_user_into_session(user_id: str, email: str, user: dict):
    """Set all session state fields after successful auth."""
    st.session_state.auth_user = {"id": user_id, "email": email}
    st.session_state.auth_error = None
    st.session_state.auth_success = None
    st.session_state.otp_pending_email = None
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
    st.session_state._pending_session_token = _create_session_token(user_id)


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
    st.session_state.otp_pending_email = None


def complete_otp_verification(email: str, otp_code: str) -> bool:
    """Verify OTP entered by user and log them in on success."""
    if not verify_otp(email, otp_code):
        st.session_state.auth_error = "Incorrect or expired code. Please try again."
        return False
    user = _users().find_one({"email": email})
    if not user:
        st.session_state.auth_error = "Account not found."
        return False
    _load_user_into_session(str(user["_id"]), email, user)
    return True


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


def save_user_vertex_config(user_id: str, project_id: str, location: str, sa_json: str) -> bool:
    try:
        _users().update_one({"_id": user_id}, {"$set": {
            "vertex_project_id": project_id,
            "vertex_location": location or "us-central1",
            "vertex_sa_json": sa_json,
        }})
        return True
    except Exception as e:
        logger.error(f"Error saving Vertex config: {e}")
        return False


def load_user_vertex_config(user_id: str) -> dict:
    try:
        user = _users().find_one({"_id": user_id}, {"vertex_project_id": 1, "vertex_location": 1, "vertex_sa_json": 1})
        if user:
            return {
                "project_id": user.get("vertex_project_id", ""),
                "location": user.get("vertex_location", "us-central1"),
                "sa_json": user.get("vertex_sa_json", ""),
            }
    except Exception as e:
        logger.error(f"Error loading Vertex config: {e}")
    return {"project_id": "", "location": "us-central1", "sa_json": ""}


# ---------------------------------------------------------------------------
# Auth page UI
# ---------------------------------------------------------------------------

def render_otp_page():
    """Show the OTP verification form. Returns True once verified and logged in."""
    email = st.session_state.get("otp_pending_email", "")
    # Admin never needs OTP — auto-complete verification
    if email in ADMIN_EMAILS:
        user = _users().find_one({"email": email})
        if user:
            _users().update_one({"_id": user["_id"]}, {"$set": {"email_verified": True}})
            _load_user_into_session(str(user["_id"]), email, user)
            st.rerun()
        return
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.markdown(
            "<h1 style='text-align:center;margin-bottom:0.2rem;'>Verify your email</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align:center;color:#666;'>We sent a 6-digit code to <strong>{email}</strong></p>",
            unsafe_allow_html=True,
        )

        if st.session_state.get("auth_error"):
            st.error(st.session_state.auth_error)
            st.session_state.auth_error = None
        if st.session_state.get("auth_success"):
            st.success(st.session_state.auth_success)
            st.session_state.auth_success = None

        with st.form("otp_form", clear_on_submit=True):
            otp_input = st.text_input(
                "Enter 6-digit code",
                placeholder="123456",
                max_chars=6,
                key="otp_input_field",
            )
            submitted = st.form_submit_button("Verify", type="primary", use_container_width=True)
            if submitted:
                if not otp_input or len(otp_input.strip()) != 6:
                    st.session_state.auth_error = "Please enter the full 6-digit code."
                    st.rerun()
                else:
                    if complete_otp_verification(email, otp_input.strip()):
                        st.rerun()
                    else:
                        st.rerun()

        st.write("")
        # Resend — rate-limited to once per 60 seconds
        last_sent = st.session_state.get("otp_last_sent_at")
        can_resend = (
            last_sent is None
            or (datetime.utcnow() - last_sent).total_seconds() >= 60
        )
        if can_resend:
            if st.button("Resend code", use_container_width=True):
                sent = send_otp(email)
                st.session_state.otp_last_sent_at = datetime.utcnow()
                st.session_state.auth_success = "A new code was sent." if sent else "Failed to send email — check server config."
                st.rerun()
        else:
            remaining = 60 - int((datetime.utcnow() - last_sent).total_seconds())
            st.caption(f"Resend available in {remaining}s")

        if st.button("← Back to login", use_container_width=True):
            st.session_state.otp_pending_email = None
            st.rerun()


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
