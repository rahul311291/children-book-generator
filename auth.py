import streamlit as st
import os
import logging
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


def _get_supabase() -> Client:
    url = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = (os.getenv("VITE_SUPABASE_ANON_KEY")
           or os.getenv("VITE_SUPABASE_SUPABASE_ANON_KEY")
           or os.getenv("SUPABASE_ANON_KEY"))
    if not url or not key:
        raise Exception("Supabase credentials not configured")
    return create_client(url, key)


def init_auth_state():
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
    if "auth_session" not in st.session_state:
        st.session_state.auth_session = None
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
    if user:
        return user.get("id", "")
    return ""


def sign_up(email: str, password: str) -> bool:
    try:
        supabase = _get_supabase()
        result = supabase.auth.sign_up({"email": email, "password": password})
        if result.user:
            st.session_state.auth_user = {
                "id": result.user.id,
                "email": result.user.email,
            }
            st.session_state.auth_session = {
                "access_token": result.session.access_token if result.session else None,
            }
            _ensure_user_profile(result.user.id, email)
            st.session_state.auth_error = None
            st.session_state.auth_success = "Account created successfully!"
            return True
        st.session_state.auth_error = "Sign up failed. Please try again."
        return False
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "already been registered" in error_msg.lower():
            st.session_state.auth_error = "This email is already registered. Please log in instead."
        else:
            st.session_state.auth_error = f"Sign up failed: {error_msg}"
        logger.error(f"Sign up error: {e}")
        return False


def sign_in(email: str, password: str) -> bool:
    try:
        supabase = _get_supabase()
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if result.user:
            st.session_state.auth_user = {
                "id": result.user.id,
                "email": result.user.email,
            }
            st.session_state.auth_session = {
                "access_token": result.session.access_token if result.session else None,
            }
            _ensure_user_profile(result.user.id, result.user.email)
            api_key = load_user_api_key(result.user.id)
            if api_key:
                st.session_state.api_key = api_key
            openrouter_key = load_user_openrouter_key(result.user.id)
            if openrouter_key:
                st.session_state.openrouter_api_key = openrouter_key
            st.session_state.auth_error = None
            st.session_state.auth_success = None
            return True
        st.session_state.auth_error = "Login failed. Please check your credentials."
        return False
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            st.session_state.auth_error = "Invalid email or password."
        else:
            st.session_state.auth_error = f"Login failed: {error_msg}"
        logger.error(f"Sign in error: {e}")
        return False


def sign_out():
    try:
        supabase = _get_supabase()
        supabase.auth.sign_out()
    except Exception as e:
        logger.error(f"Sign out error: {e}")
    st.session_state.auth_user = None
    st.session_state.auth_session = None
    st.session_state.auth_error = None
    st.session_state.auth_success = None
    st.session_state.api_key = ""
    st.session_state.openrouter_api_key = ""


def _ensure_user_profile(user_id: str, email: str):
    try:
        supabase = _get_supabase()
        access_token = st.session_state.get("auth_session", {}).get("access_token")
        if access_token:
            supabase.postgrest.auth(access_token)
        existing = supabase.table("user_profiles").select("id").eq("id", user_id).maybe_single().execute()
        if not existing.data:
            supabase.table("user_profiles").insert({
                "id": user_id,
                "email": email,
            }).execute()
    except Exception as e:
        logger.error(f"Error ensuring user profile: {e}")


def save_user_api_key(user_id: str, api_key: str) -> bool:
    try:
        supabase = _get_supabase()
        access_token = st.session_state.get("auth_session", {}).get("access_token")
        if access_token:
            supabase.postgrest.auth(access_token)
        supabase.table("user_profiles").update({
            "gemini_api_key": api_key,
        }).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error saving API key: {e}")
        return False


def load_user_api_key(user_id: str) -> str:
    try:
        supabase = _get_supabase()
        access_token = st.session_state.get("auth_session", {}).get("access_token")
        if access_token:
            supabase.postgrest.auth(access_token)
        result = supabase.table("user_profiles").select("gemini_api_key").eq("id", user_id).maybe_single().execute()
        if result.data and result.data.get("gemini_api_key"):
            return result.data["gemini_api_key"]
    except Exception as e:
        logger.error(f"Error loading API key: {e}")
    return ""


def save_user_openrouter_key(user_id: str, api_key: str) -> bool:
    try:
        supabase = _get_supabase()
        access_token = st.session_state.get("auth_session", {}).get("access_token")
        if access_token:
            supabase.postgrest.auth(access_token)
        supabase.table("user_profiles").update({
            "openrouter_api_key": api_key,
        }).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error saving OpenRouter API key: {e}")
        return False


def load_user_openrouter_key(user_id: str) -> str:
    try:
        supabase = _get_supabase()
        access_token = st.session_state.get("auth_session", {}).get("access_token")
        if access_token:
            supabase.postgrest.auth(access_token)
        result = supabase.table("user_profiles").select("openrouter_api_key").eq("id", user_id).maybe_single().execute()
        if result.data and result.data.get("openrouter_api_key"):
            return result.data["openrouter_api_key"]
    except Exception as e:
        logger.error(f"Error loading OpenRouter API key: {e}")
    return ""


def get_authed_supabase() -> Client:
    """Return a Supabase client authenticated with the current user's access token."""
    supabase = _get_supabase()
    access_token = st.session_state.get("auth_session", {}).get("access_token")
    if access_token:
        supabase.postgrest.auth(access_token)
    return supabase


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
