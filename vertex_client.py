"""
Unified Gemini client: Vertex AI (primary) → Google AI API (fallback).

Configure Vertex AI by adding to Streamlit secrets or .env:
  VERTEX_PROJECT_ID   = "your-gcp-project-id"
  VERTEX_LOCATION     = "us-central1"           # optional, default us-central1
  GOOGLE_SERVICE_ACCOUNT_JSON = '{"type":"service_account",...}'  # full SA JSON
"""

import os
import json
import logging
import requests
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

logger = logging.getLogger(__name__)

# Vertex AI model preference order
_TEXT_MODELS = [
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.0-flash-001",
    "gemini-1.5-pro-002",
    "gemini-1.5-flash-002",
]
_IMAGE_MODELS = [
    "gemini-2.0-flash-preview-image-generation",
    "gemini-2.0-flash-exp",
]


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _cfg() -> dict:
    # Session state (sidebar UI) takes highest priority
    try:
        import streamlit as st
        project = st.session_state.get("vertex_project_id", "") or os.getenv("VERTEX_PROJECT_ID", "")
        location = st.session_state.get("vertex_location", "") or os.getenv("VERTEX_LOCATION", "us-central1")
        sa_json = st.session_state.get("vertex_sa_json", "") or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        if not (project and sa_json):
            project = project or str(st.secrets.get("VERTEX_PROJECT_ID", "") or "")
            location = str(st.secrets.get("VERTEX_LOCATION", "") or location)
            sa_json = sa_json or str(st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", "") or "")
    except Exception:
        project = os.getenv("VERTEX_PROJECT_ID", "")
        location = os.getenv("VERTEX_LOCATION", "us-central1")
        sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    return {"project": project, "location": location or "us-central1", "sa_json": sa_json}


def is_vertex_configured() -> bool:
    c = _cfg()
    return bool(c["project"] and c["sa_json"])


def _token(raise_on_error: bool = False) -> Optional[str]:
    sa = _cfg()["sa_json"]
    if not sa:
        return None
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request as R
        creds = service_account.Credentials.from_service_account_info(
            json.loads(sa),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        creds.refresh(R())
        return creds.token
    except json.JSONDecodeError as e:
        msg = f"Service Account JSON is not valid JSON: {e}"
        logger.error(f"Vertex SA JSON parse error: {e}")
        if raise_on_error:
            raise ValueError(msg) from e
        return None
    except Exception as e:
        logger.warning(f"Vertex auth failed: {e}")
        if raise_on_error:
            raise
        return None


def _vertex_url(model: str) -> str:
    c = _cfg()
    p, l = c["project"], c["location"]
    return (
        f"https://{l}-aiplatform.googleapis.com/v1/projects/{p}"
        f"/locations/{l}/publishers/google/models/{model}:generateContent"
    )


# ---------------------------------------------------------------------------
# Text generation
# ---------------------------------------------------------------------------

def call_gemini_text(
    prompt: str,
    api_key: str = "",
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> Optional[str]:
    """Generate text. Vertex AI first, then Google AI API fallback."""

    def _extract(resp_json: dict) -> Optional[str]:
        parts = resp_json.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or None

    # --- Vertex AI ---
    if is_vertex_configured():
        tok = _token()
        if tok:
            headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": max_tokens,
                },
            }
            for model in _TEXT_MODELS:
                try:
                    r = requests.post(_vertex_url(model), headers=headers, json=payload, timeout=120)
                    if r.status_code == 200:
                        text = _extract(r.json())
                        if text:
                            logger.info(f"Vertex text OK: {model}")
                            return text
                    logger.warning(f"Vertex text {model} → {r.status_code}: {r.text[:150]}")
                except Exception as e:
                    logger.warning(f"Vertex text {model} error: {e}")

    # --- Google AI fallback ---
    if not api_key:
        return None
    for model in ["gemini-2.0-flash-001", "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"]:
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": max_tokens,
                    },
                },
                params={"key": api_key},
                timeout=120,
            )
            if r.status_code == 200:
                text = _extract(r.json())
                if text:
                    logger.info(f"Google AI text OK: {model}")
                    return text
        except Exception as e:
            logger.warning(f"Google AI text {model} error: {e}")
    return None


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------

def call_gemini_image(
    prompt: str,
    api_key: str = "",
    reference_image_b64: Optional[str] = None,
) -> Optional[str]:
    """Generate an image. Vertex AI first, then Google AI API fallback. Returns data URL or None."""

    def _build_parts(include_ref: bool) -> list:
        if include_ref and reference_image_b64:
            return [
                {"inlineData": {"mimeType": "image/jpeg", "data": reference_image_b64}},
                {"text": f"{prompt}. Make the child look like the person in the reference photo."},
            ]
        return [{"text": prompt}]

    # --- Vertex AI ---
    if is_vertex_configured():
        tok = _token()
        if tok:
            headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
            for model in _IMAGE_MODELS:
                try:
                    r = requests.post(
                        _vertex_url(model),
                        headers=headers,
                        json={
                            "contents": [{"parts": _build_parts(True)}],
                            "generationConfig": {
                                "responseModalities": ["IMAGE"],
                                "temperature": 0.4,
                            },
                        },
                        timeout=180,
                    )
                    if r.status_code == 200:
                        for p in r.json().get("candidates", [{}])[0].get("content", {}).get("parts", []):
                            if "inlineData" in p:
                                logger.info(f"Vertex image OK: {model}")
                                return f"data:image/png;base64,{p['inlineData']['data']}"
                    logger.warning(f"Vertex image {model} → {r.status_code}: {r.text[:150]}")
                except Exception as e:
                    logger.warning(f"Vertex image {model} error: {e}")

    # --- Google AI fallback ---
    if not api_key:
        return None
    try:
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": _build_parts(True)}],
                "generationConfig": {
                    "temperature": 0.4,
                    "topK": 32,
                    "topP": 1,
                    "imageConfig": {"aspectRatio": "1:1", "imageSize": "2K"},
                },
            },
            params={"key": api_key},
            timeout=180,
        )
        if r.status_code == 200:
            for p in r.json().get("candidates", [{}])[0].get("content", {}).get("parts", []):
                if "inlineData" in p:
                    logger.info("Google AI image OK")
                    return f"data:image/png;base64,{p['inlineData']['data']}"
        logger.warning(f"Google AI image → {r.status_code}: {r.text[:150]}")
    except Exception as e:
        logger.warning(f"Google AI image error: {e}")
    return None
