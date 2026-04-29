"""
Unified Gemini client: Vertex AI (primary) → Google AI API (fallback).

Configure Vertex AI by adding to Streamlit secrets or .env:
  VERTEX_PROJECT_ID   = "your-gcp-project-id"
  VERTEX_LOCATION     = "us-central1"           # optional, default us-central1
  GOOGLE_SERVICE_ACCOUNT_JSON = '{"type":"service_account",...}'  # full SA JSON

Vertex AI model names differ from Google AI Studio names.
If you get 404s, go to GCP Console → Vertex AI → Model Garden and enable
the Gemini models for your project.
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

# Vertex AI model names (without publishers/google/ prefix).
# Vertex uses different IDs than Google AI Studio.
# Models are tried in order; first success wins.
_TEXT_MODELS = [
    "gemini-2.5-pro-preview-05-06",   # Gemini 2.5 Pro (latest preview)
    "gemini-2.5-flash-preview-05-20", # Gemini 2.5 Flash
    "gemini-2.5-flash-preview-04-17", # Gemini 2.5 Flash (older preview)
    "gemini-2.0-flash",               # Gemini 2.0 Flash GA
    "gemini-2.0-flash-001",           # Gemini 2.0 Flash (versioned)
    "gemini-1.5-pro",                 # Gemini 1.5 Pro (stable)
    "gemini-1.5-flash",               # Gemini 1.5 Flash (stable)
]
_GEMINI_IMAGE_MODELS = [
    "gemini-2.5-flash-preview-image-generation",  # Gemini 2.5 Flash image (generateContent API)
    "gemini-2.5-flash-image",
    "gemini-2.0-flash-preview-image-generation",
    "gemini-2.0-flash-exp",
]
_IMAGEN_MODELS = [
    "imagen-4.0-generate-001",   # Imagen 4 (predict API, different payload format)
    "imagen-3.0-generate-001",
]


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _cfg() -> dict:
    # Session state (sidebar UI) takes highest priority, then env vars, then st.secrets
    project = ""
    location = ""
    sa_json = ""

    try:
        import streamlit as st
        project = st.session_state.get("vertex_project_id", "") or ""
        location = st.session_state.get("vertex_location", "") or ""
        sa_json = st.session_state.get("vertex_sa_json", "") or ""
    except Exception:
        pass

    # Fill gaps from env vars
    project = project or os.getenv("VERTEX_PROJECT_ID", "")
    location = location or os.getenv("VERTEX_LOCATION", "")
    sa_json = sa_json or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    # Fill remaining gaps from st.secrets (wrapped separately so secrets errors don't wipe session state)
    if not project or not sa_json:
        try:
            import streamlit as st
            project = project or str(st.secrets.get("VERTEX_PROJECT_ID", "") or "")
            location = location or str(st.secrets.get("VERTEX_LOCATION", "") or "")
            sa_json = sa_json or str(st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", "") or "")
        except Exception:
            pass

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


def _vertex_predict_url(model: str) -> str:
    """Endpoint for Imagen models which use :predict instead of :generateContent."""
    c = _cfg()
    p, l = c["project"], c["location"]
    return (
        f"https://{l}-aiplatform.googleapis.com/v1/projects/{p}"
        f"/locations/{l}/publishers/google/models/{model}:predict"
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
    vertex_errors = []
    if is_vertex_configured():
        try:
            tok = _token(raise_on_error=True)
        except Exception as e:
            tok = None
            vertex_errors.append(f"Auth failed: {e}")
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
                        vertex_errors.append(f"{model}: 200 but no text in response")
                    else:
                        vertex_errors.append(f"{model}: HTTP {r.status_code} — {r.text[:200]}")
                    logger.warning(f"Vertex text {model} → {r.status_code}: {r.text[:150]}")
                except Exception as e:
                    vertex_errors.append(f"{model}: {e}")
                    logger.warning(f"Vertex text {model} error: {e}")
        if vertex_errors:
            all_404 = all("404" in e for e in vertex_errors)
            try:
                import streamlit as st
                if all_404:
                    st.error(
                        "**Vertex AI: all models returned 404.** Your project may not have access. "
                        "Go to **GCP Console → Vertex AI → Model Garden**, find Gemini 2.5 Pro, "
                        "and click **Enable** to grant your project access. Then try again."
                    )
                else:
                    st.warning(f"Vertex AI errors: {'; '.join(vertex_errors[:2])}")
            except Exception:
                pass

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
    vertex_img_errors = []
    if is_vertex_configured():
        try:
            tok = _token(raise_on_error=True)
        except Exception as e:
            tok = None
            vertex_img_errors.append(f"Auth failed: {e}")
        if tok:
            headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

            # Try Gemini image models (generateContent API with responseModalities)
            for model in _GEMINI_IMAGE_MODELS:
                try:
                    r = requests.post(
                        _vertex_url(model),
                        headers=headers,
                        json={
                            "contents": [{"parts": _build_parts(True)}],
                            "generationConfig": {
                                "responseModalities": ["TEXT", "IMAGE"],
                                "temperature": 0.4,
                            },
                        },
                        timeout=180,
                    )
                    if r.status_code == 200:
                        for p in r.json().get("candidates", [{}])[0].get("content", {}).get("parts", []):
                            if "inlineData" in p:
                                logger.info(f"Vertex Gemini image OK: {model}")
                                return f"data:image/png;base64,{p['inlineData']['data']}"
                        vertex_img_errors.append(f"{model}: 200 but no image in response")
                    else:
                        vertex_img_errors.append(f"{model}: HTTP {r.status_code} — {r.text[:200]}")
                    logger.warning(f"Vertex Gemini image {model} → {r.status_code}: {r.text[:150]}")
                except Exception as e:
                    vertex_img_errors.append(f"{model}: {e}")
                    logger.warning(f"Vertex Gemini image {model} error: {e}")

            # Try Imagen models (predict API — different payload and response format)
            for model in _IMAGEN_MODELS:
                try:
                    imagen_prompt = prompt
                    if reference_image_b64:
                        imagen_prompt = f"{prompt}. Make the child look like the person in the reference photo."
                    r = requests.post(
                        _vertex_predict_url(model),
                        headers=headers,
                        json={
                            "instances": [{"prompt": imagen_prompt}],
                            "parameters": {
                                "sampleCount": 1,
                                "aspectRatio": "1:1",
                            },
                        },
                        timeout=180,
                    )
                    if r.status_code == 200:
                        predictions = r.json().get("predictions", [])
                        if predictions and predictions[0].get("bytesBase64Encoded"):
                            logger.info(f"Vertex Imagen OK: {model}")
                            return f"data:image/png;base64,{predictions[0]['bytesBase64Encoded']}"
                        vertex_img_errors.append(f"{model}: 200 but no image in response")
                    else:
                        vertex_img_errors.append(f"{model}: HTTP {r.status_code} — {r.text[:200]}")
                    logger.warning(f"Vertex Imagen {model} → {r.status_code}: {r.text[:150]}")
                except Exception as e:
                    vertex_img_errors.append(f"{model}: {e}")
                    logger.warning(f"Vertex Imagen {model} error: {e}")

        if vertex_img_errors:
            try:
                import streamlit as st
                all_404 = all("404" in e for e in vertex_img_errors)
                if all_404:
                    st.error(
                        "**Vertex AI image: all models returned 404.** Go to "
                        "**GCP Console → Vertex AI → Model Garden**, find "
                        "Gemini 2.5 Flash Image Generation or Imagen 4 and click **Enable**."
                    )
                else:
                    st.warning(f"Vertex AI image errors: {'; '.join(vertex_img_errors[:2])}")
            except Exception:
                pass

    # --- Google AI fallback ---
    if not api_key:
        return None
    try:
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent",
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
