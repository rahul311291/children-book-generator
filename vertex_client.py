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
import time
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
    "gemini-2.5-pro",    # Gemini 2.5 Pro GA (stable)
    "gemini-2.5-flash",  # Gemini 2.5 Flash GA (stable)
    "gemini-2.0-flash",  # Gemini 2.0 Flash GA
    "gemini-1.5-pro",    # Gemini 1.5 Pro (stable)
    "gemini-1.5-flash",  # Gemini 1.5 Flash (stable)
]
# Order matters: tried top-to-bottom, first 200-with-image wins.
# Per Google migration notice (email 2026), Imagen 4 endpoints will be
# discontinued on 2026-08-17; recommended migration target is
# gemini-3.1-flash-image (same cost, better performance). We put it on
# top so all new gens flow through the new model immediately; older
# Gemini-image and Imagen models stay below as fallbacks until they're
# actually shut off.
_GEMINI_IMAGE_MODELS = [
    "gemini-3.1-flash-image",                       # Primary (migration target)
    "gemini-2.5-flash-image",                       # GA fallback
    "gemini-2.0-flash-preview-image-generation",    # Preview fallback
    "gemini-2.0-flash-exp",                         # Older preview fallback
]
# These will return 404 after 2026-08-17. Kept ONLY because they may be
# the only thing enabled in some projects today; safe to delete once
# gemini-3.1-flash-image is verified working in production.
_IMAGEN_MODELS = [
    "imagen-4.0-generate-001",       # discontinues 2026-08-17 → use gemini-3.1-flash-image
    "imagen-3.0-generate-001",
]

import threading as _threading
_last_image_errors = _threading.local()


def get_last_image_errors() -> list:
    """Return the per-backend error messages from the most recent
    call_gemini_image invocation on THIS thread. Used by main.py's
    threadsafe worker to surface real failure details to the user."""
    return list(getattr(_last_image_errors, "errors", []) or [])




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


def _vertex_global_url(model: str) -> str:
    """Global endpoint (required for gemini-2.5-flash-image and other global-only models)."""
    c = _cfg()
    p = c["project"]
    return (
        f"https://aiplatform.googleapis.com/v1/projects/{p}"
        f"/locations/global/publishers/google/models/{model}:generateContent"
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
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
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
            refs = reference_image_b64 if isinstance(reference_image_b64, list) else [reference_image_b64]
            n = len(refs)
            parts = [{"inlineData": {"mimeType": "image/jpeg", "data": r}} for r in refs]
            likeness_instruction = (
                "CRITICAL LIKENESS REQUIREMENT: The child in this illustration MUST closely match the reference photo(s). "
                "Preserve the EXACT same face shape, skin tone, hair color, hair texture, hair length, eye shape, "
                "eye color, nose shape, and facial proportions. The child should be immediately recognizable as "
                "the same person in the reference photo. Do NOT change any facial features."
            )
            note = (
                f"Use all {n} reference photos together to build a complete picture of the child's appearance. {likeness_instruction}"
                if n > 1
                else f"Make the child look EXACTLY like the person in the reference photo. {likeness_instruction}"
            )
            parts.append({"text": f"{prompt}. {note}"})
            return parts
        return [{"text": prompt}]

    # --- Vertex AI ---
    vertex_img_errors = []
    # Reset thread-local error list so callers can read it after this
    # invocation returns None / falls through.
    _last_image_errors.errors = vertex_img_errors
    if is_vertex_configured():
        try:
            tok = _token(raise_on_error=True)
        except Exception as e:
            tok = None
            vertex_img_errors.append(f"Auth failed: {e}")
        if tok:
            headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

            # Try Gemini image models (generateContent API with responseModalities)
            # Global endpoint is tried first as gemini-2.5-flash-image requires it;
            # regional endpoint is the fallback for older models.
            payload = {
                "contents": [{"role": "user", "parts": _build_parts(True)}],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"],
                    "temperature": 0.4,
                },
            }
            for model in _GEMINI_IMAGE_MODELS:
                urls_to_try = [_vertex_global_url(model), _vertex_url(model)]
                model_success = False
                for url in urls_to_try:
                    for _attempt in range(3):
                        try:
                            r = requests.post(url, headers=headers, json=payload, timeout=180)
                            if r.status_code == 200:
                                for part in r.json().get("candidates", [{}])[0].get("content", {}).get("parts", []):
                                    if "inlineData" in part:
                                        logger.info(f"Vertex Gemini image OK: {model} ({url})")
                                        return f"data:image/png;base64,{part['inlineData']['data']}"
                                vertex_img_errors.append(f"{model}: 200 but no image in response")
                                model_success = True
                                break
                            elif r.status_code == 429:
                                # Honour Retry-After if Cashfree sends it,
                                # else exponential backoff (8s, 20s, 45s).
                                _ra = r.headers.get("Retry-After", "")
                                try:
                                    wait = int(_ra) if _ra else [8, 20, 45][_attempt]
                                except ValueError:
                                    wait = [8, 20, 45][_attempt]
                                logger.warning(f"Vertex Gemini image {model} rate limited (429), waiting {wait}s (attempt {_attempt+1}/3)")
                                time.sleep(wait)
                                continue
                            elif r.status_code == 404:
                                logger.warning(f"Vertex Gemini image {model} 404 at {url}, trying next")
                                break
                            elif r.status_code in (500, 502, 503, 504):
                                # Transient server error — retry with backoff.
                                # These are common during Vertex hot-pathing.
                                wait = [5, 15, 40][_attempt]
                                logger.warning(f"Vertex Gemini image {model} server error ({r.status_code}), waiting {wait}s (attempt {_attempt+1}/3)")
                                time.sleep(wait)
                                continue
                            else:
                                # Real 4xx (400 bad request, 401 auth, 403 perm) — not retryable
                                vertex_img_errors.append(f"{model}: HTTP {r.status_code} — {r.text[:200]}")
                                logger.warning(f"Vertex Gemini image {model} → {r.status_code}: {r.text[:150]}")
                                model_success = True
                                break
                        except (requests.Timeout, requests.ConnectionError) as e:
                            # Network glitch — retry. Last attempt falls through to next model.
                            if _attempt < 2:
                                wait = [2, 5, 10][_attempt]
                                logger.warning(f"Vertex Gemini image {model} network error, waiting {wait}s (attempt {_attempt+1}/3): {e}")
                                time.sleep(wait)
                                continue
                            vertex_img_errors.append(f"{model}: {e}")
                            model_success = True
                            break
                        except Exception as e:
                            vertex_img_errors.append(f"{model}: {e}")
                            logger.warning(f"Vertex Gemini image {model} error: {e}")
                            model_success = True
                            break
                    if model_success:
                        break
                if not model_success:
                    vertex_img_errors.append(f"{model}: 404 on all endpoints")

            # Try Imagen models (predict API — different payload and response format)
            for model in _IMAGEN_MODELS:
                imagen_prompt = prompt
                if reference_image_b64:
                    imagen_prompt = f"{prompt}. Make the child look like the person in the reference photo."
                for _attempt in range(3):
                    try:
                        r = requests.post(
                            _vertex_predict_url(model),
                            headers=headers,
                            json={
                                "instances": [{"prompt": imagen_prompt}],
                                "parameters": {
                                    "sampleCount": 1,
                                    "aspectRatio": "3:4",
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
                            break
                        elif r.status_code == 429:
                            _ra = r.headers.get("Retry-After", "")
                            try:
                                wait = int(_ra) if _ra else [8, 20, 45][_attempt]
                            except ValueError:
                                wait = [8, 20, 45][_attempt]
                            logger.warning(f"Vertex Imagen {model} rate limited (429), waiting {wait}s (attempt {_attempt+1}/3)")
                            time.sleep(wait)
                            continue
                        elif r.status_code in (500, 502, 503, 504):
                            wait = [5, 15, 40][_attempt]
                            logger.warning(f"Vertex Imagen {model} server error ({r.status_code}), waiting {wait}s (attempt {_attempt+1}/3)")
                            time.sleep(wait)
                            continue
                        else:
                            vertex_img_errors.append(f"{model}: HTTP {r.status_code} — {r.text[:200]}")
                            logger.warning(f"Vertex Imagen {model} → {r.status_code}: {r.text[:150]}")
                            break
                    except (requests.Timeout, requests.ConnectionError) as e:
                        if _attempt < 2:
                            wait = [2, 5, 10][_attempt]
                            logger.warning(f"Vertex Imagen {model} network error, waiting {wait}s (attempt {_attempt+1}/3): {e}")
                            time.sleep(wait)
                            continue
                        vertex_img_errors.append(f"{model}: {e}")
                        break
                    except Exception as e:
                        vertex_img_errors.append(f"{model}: {e}")
                        logger.warning(f"Vertex Imagen {model} error: {e}")
                        break

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
                    "imageConfig": {"aspectRatio": "3:4", "imageSize": "2K"},
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
        msg = f"Google AI direct: HTTP {r.status_code} — {r.text[:200]}"
        logger.warning(msg)
        vertex_img_errors.append(msg)
    except Exception as e:
        msg = f"Google AI direct: {e}"
        logger.warning(msg)
        vertex_img_errors.append(msg)
    # Vertex AI not configured at all: tell the user clearly.
    if not vertex_img_errors:
        vertex_img_errors.append(
            "No image backend is configured. Set GEMINI_API_KEY or configure "
            "Vertex AI (Project + Service Account JSON) in the admin sidebar."
        )
    _last_image_errors.errors = vertex_img_errors
    return None
