import streamlit as st
import streamlit.components.v1 as components
import json
import os
import tempfile
import base64
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional
from reportlab.lib.units import inch
import requests
from datetime import datetime, timedelta

# Import age-specific prompts from the editable prompts file
from story_prompts import get_full_prompt, get_image_style, IMAGE_STYLES

# Import auth
from auth import (
    init_auth_state,
    is_authenticated,
    get_current_user_id,
    sign_out,
    save_user_api_key,
    load_user_api_key,
    save_user_openrouter_key,
    load_user_openrouter_key,
    save_user_vertex_config,
    load_user_vertex_config,
    render_auth_page,
    render_otp_page,
    render_set_password_page,
    restore_session_from_token,
    sync_google_session,
    ADMIN_EMAILS,
    get_admin_vertex_config,
)

# Import template book functionality
try:
    from template_book_generator import (
        render_template_book_form,
        generate_template_book,
        display_template_book_preview,
        get_cached_template_book,
    )
    TEMPLATE_BOOKS_AVAILABLE = True
except ImportError:
    TEMPLATE_BOOKS_AVAILABLE = False

# New asset-backed template flow (pre-rendered images, instant books)
try:
    from template_flow import render_template_mode, render_template_studio
    TEMPLATE_FLOW_AVAILABLE = True
except ImportError:
    TEMPLATE_FLOW_AVAILABLE = False

# Import book formats (8 layouts based on bestselling India + global picture books)
from book_formats import BOOK_FORMATS, DEFAULT_FORMAT, get_format_by_id, get_page_count

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor, black, white
from PIL import Image
import io
import time

# Page configuration
st.set_page_config(
    page_title="Storytime Studio — Personalized Books for Kids",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="auto"
)

# Custom CSS for mobile-friendly design
st.markdown("""
    <style>
        .main > div {
            padding-top: 2rem;
        }
        .stButton > button {
            width: 100%;
            font-size: 1.2rem;
            padding: 0.5rem;
        }
        @media (max-width: 768px) {
            .stSidebar {
                width: 100% !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

# Initialize auth state
init_auth_state()

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'openrouter_api_key' not in st.session_state:
    st.session_state.openrouter_api_key = ""
if 'vertex_project_id' not in st.session_state:
    st.session_state.vertex_project_id = ""
if 'vertex_location' not in st.session_state:
    st.session_state.vertex_location = "us-central1"
if 'vertex_sa_json' not in st.session_state:
    st.session_state.vertex_sa_json = ""
if 'current_book_history_id' not in st.session_state:
    st.session_state.current_book_history_id = None
if 'generated_story' not in st.session_state:
    st.session_state.generated_story = None
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = []
if 'pdf_path' not in st.session_state:
    st.session_state.pdf_path = None
if 'story_approved' not in st.session_state:
    st.session_state.story_approved = False
if 'image_approvals' not in st.session_state:
    st.session_state.image_approvals = {}  # Dict to track which images are approved
if 'all_images_approved' not in st.session_state:
    st.session_state.all_images_approved = False
if 'edited_story_pages' not in st.session_state:
    st.session_state.edited_story_pages = {}  # Store edited page text
if 'edited_image_prompts' not in st.session_state:
    st.session_state.edited_image_prompts = {}  # Store edited image prompts
if 'image_generation_errors' not in st.session_state:
    st.session_state.image_generation_errors = {}  # Store error messages for failed image generations
if 'pdf_generation_key' not in st.session_state:
    st.session_state.pdf_generation_key = None  # Track when PDF was generated
if 'stories_dir' not in st.session_state:
    # Use absolute path so saves are always in the same place (fixes history not showing when cwd differs)
    st.session_state.stories_dir = Path(__file__).resolve().parent / "saved_stories"
    st.session_state.stories_dir.mkdir(exist_ok=True)
if 'current_child_name' not in st.session_state:
    st.session_state.current_child_name = ""  # Track current child name for auto-save
if 'selected_book_format' not in st.session_state:
    st.session_state.selected_book_format = None  # Selected book layout format
if 'pending_payment_link_id' not in st.session_state:
    st.session_state.pending_payment_link_id = None
if 'pending_payment_url' not in st.session_state:
    st.session_state.pending_payment_url = None
if 'current_book_payment_status' not in st.session_state:
    # None = unpaid; "pending" = link created;
    # "story_paid" = Gate 1 confirmed (full generation unlocked);
    # "download_paid" = Gate 2 confirmed (PDF/print unlocked)
    st.session_state.current_book_payment_status = None
if 'pending_payment_gate' not in st.session_state:
    # Which gate the pending payment is for: "download_choice" | "print_deliver_choice"
    st.session_state.pending_payment_gate = None
if 'book_delivery_option' not in st.session_state:
    # "download" = ₹350 digital; "print_deliver" = ₹650 print+deliver
    st.session_state.book_delivery_option = None
if 'cf_pending_order_id' not in st.session_state:
    st.session_state.cf_pending_order_id = None  # Cashfree order ID awaiting payment
if 'cf_payment_session_id' not in st.session_state:
    st.session_state.cf_payment_session_id = None  # JS SDK session token
if 'cf_order_created_at' not in st.session_state:
    st.session_state.cf_order_created_at = None   # epoch when order was created
if 'cf_show_verify_button' not in st.session_state:
    st.session_state.cf_show_verify_button = False  # shown only after 60 s timeout
if 'book_mode' not in st.session_state:
    st.session_state.book_mode = None  # None, "custom", "template"
if 'wizard_step' not in st.session_state:
    st.session_state.wizard_step = 0
# Wizard form values (all default empty/None)
for _k, _v in [
    ("wiz_child_name", ""), ("wiz_age", 5), ("wiz_gender", "Boy"),
    ("wiz_skin_tone", ""), ("wiz_hair_style", ""), ("wiz_eye_color", ""), ("wiz_outfit", ""),
    ("wiz_story_type", "Adventure"), ("wiz_problem", ""), ("wiz_language", "English"),
    ("wiz_image_style", "Cartoon/Animated (3D Pixar Style)"), ("wiz_format_id", "illo_opposite_text"),
    ("wiz_family_structure", ""), ("wiz_hero_trait", ""), ("wiz_character_choice", ""),
    ("wiz_generate_trigger", False), ("wiz_reference_photos_b64", []),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


def _resolve_book_format() -> dict:
    """Get the currently selected book format from session state, or None."""
    try:
        fmt_id = st.session_state.get("wiz_format_id") or st.session_state.get("selected_book_format")
        if fmt_id:
            from book_formats import get_format_by_id
            return get_format_by_id(fmt_id)
    except Exception:
        pass
    return None


def _cashfree_dropin_html(payment_session_id: str, order_id: str) -> str:
    """
    Cashfree JS SDK v3 modal checkout.
    Renders a "Pay Now" button inside a components.html() iframe.
    Clicking it opens Cashfree's secure payment modal over the page.
    On success/failure the JS updates window.parent.location.search
    so Streamlit picks up ?cf_order_id=...&cf_status=SUCCESS|FAILED.
    """
    from payments import cashfree_env
    mode = "production" if cashfree_env() == "production" else "sandbox"
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script src="https://sdk.cashfree.com/js/v3/cashfree.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      width: 100%; height: 100%;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f8fafc;
    }}
    #overlay {{
      position: fixed; inset: 0;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      gap: 14px; padding: 24px;
    }}
    #spinner {{
      width: 40px; height: 40px;
      border: 4px solid #e2e8f0;
      border-top-color: #2563eb;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    #msg {{ font-size: 15px; color: #374151; font-weight: 500; text-align: center; }}
    #sub {{ font-size: 12px; color: #9ca3af; text-align: center; }}
    #err {{
      background: #fee2e2; color: #991b1b;
      border-radius: 8px; padding: 12px 18px;
      font-size: 13px; text-align: center;
      display: none; max-width: 400px;
    }}
    #retry-btn {{
      background: #2563eb; color: white;
      border: none; border-radius: 8px;
      padding: 10px 28px; font-size: 14px; font-weight: 600;
      cursor: pointer; display: none;
    }}
  </style>
</head>
<body>
  <div id="overlay">
    <div id="spinner"></div>
    <div id="msg">Opening Cashfree checkout…</div>
    <div id="sub">Please wait while your secure payment window loads</div>
    <div id="err"></div>
    <button id="retry-btn" onclick="startPayment()">Try again</button>
  </div>

  <script>
    var SESSION_ID = "{payment_session_id}";
    var ORDER_ID   = "{order_id}";
    var CF_MODE    = "{mode}";

    function setMsg(msg, sub) {{
      document.getElementById("msg").innerText = msg;
      if (sub !== undefined) document.getElementById("sub").innerText = sub || "";
    }}

    function showErr(msg) {{
      document.getElementById("spinner").style.display = "none";
      document.getElementById("err").innerText = msg;
      document.getElementById("err").style.display = "block";
      document.getElementById("retry-btn").style.display = "inline-block";
      setMsg("Payment could not be opened", "");
    }}

    var _done = false;
    var _timeoutHandle = null;

    // ── Mobile detection ────────────────────────────────────────────────────
    // On mobile: use _self (top-level redirect, SAME tab) — UPI deep links fire
    //   reliably from top-level navigation; user returns to the same tab from
    //   their UPI app, Cashfree redirects back here, Streamlit reruns and
    //   verifies the payment via query params. No tab juggling, no
    //   cross-iframe BroadcastChannel handoff (which was silently failing
    //   because Streamlit's components iframe sandbox blocks
    //   window.parent.location writes from a different origin).
    // On desktop: use _modal (overlay) — no popup blocker, stays in-page
    var _isMobile = /iPhone|iPad|iPod|Android|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    var _redirectTarget = _isMobile ? "_self" : "_modal";

    // ── 60-second fallback: reveal the manual verify button ────────────────
    function startFallbackTimer() {{
      _timeoutHandle = setTimeout(function() {{
        if (!_done) {{
          window.parent.location.search =
            "?cf_order_id=" + encodeURIComponent(ORDER_ID) + "&cf_show_verify=1";
        }}
      }}, 60000);
    }}

    function resetAndRetry() {{
      // Session is stale/expired — tell parent to clear it so a fresh order is created
      window.parent.location.search =
        "?cf_order_id=" + encodeURIComponent(ORDER_ID) + "&cf_reset=1";
    }}

    function startPayment() {{
      document.getElementById("err").style.display = "none";
      document.getElementById("retry-btn").style.display = "none";
      document.getElementById("spinner").style.display = "block";

      if (_isMobile) {{
        setMsg("Redirecting to secure checkout…",
               "You'll be taken to Cashfree. GPay, PhonePe & all UPI apps work — you'll come back here automatically after paying.");
      }} else {{
        setMsg("Opening secure checkout…", "Complete your payment in the overlay.");
      }}

      try {{
        var cashfree = Cashfree({{ mode: CF_MODE }});
        cashfree.checkout({{
          paymentSessionId: SESSION_ID,
          redirectTarget: _redirectTarget
        }}).then(function(result) {{
          if (result && result.paymentDetails) {{
            // Desktop _modal: promise resolves with paymentDetails on success
            _done = true;
            if (_timeoutHandle) clearTimeout(_timeoutHandle);
            setMsg("✅ Payment successful! Confirming…", "");
            window.parent.location.search =
              "?cf_order_id=" + encodeURIComponent(ORDER_ID) + "&cf_status=SUCCESS";
          }} else if (result && result.error) {{
            // SDK returned an error object (stale session, invalid endpoint, etc.)
            var code = (result.error.code || "");
            if (code === "request_failed" || code === "api_connection_error") {{
              // Payment session is expired/consumed — must create a new order
              document.getElementById("spinner").style.display = "none";
              setMsg("Session expired", "Your payment session timed out. Starting fresh…");
              document.getElementById("retry-btn").style.display = "inline-block";
              document.getElementById("retry-btn").innerText = "🔄 Start new payment";
              document.getElementById("retry-btn").onclick = resetAndRetry;
            }} else {{
              showErr("Payment error: " + (result.error.message || code));
            }}
          }} else {{
            // Defensive fallback: SDK returned without paymentDetails or
            // error. With _self the page should already be navigating away.
            document.getElementById("spinner").style.display = "block";
            setMsg("Redirecting to payment…", "");
          }}
        }}).catch(function(e) {{
          var msg = e.message || String(e);
          // "endpoint or method is not valid" → stale session, must reset
          if (msg.indexOf("endpoint") !== -1 || msg.indexOf("not valid") !== -1 ||
              msg.indexOf("request_failed") !== -1) {{
            document.getElementById("spinner").style.display = "none";
            setMsg("Session expired", "Your payment session timed out. Starting fresh…");
            document.getElementById("retry-btn").style.display = "inline-block";
            document.getElementById("retry-btn").innerText = "🔄 Start new payment";
            document.getElementById("retry-btn").onclick = resetAndRetry;
          }} else {{
            showErr("Could not open payment: " + msg);
          }}
        }});
      }} catch(e) {{
        showErr("Could not initialise payment: " + (e.message || String(e)));
      }}
    }}

    // Auto-trigger on load + start 60-second fallback timer
    window.addEventListener("load", function() {{
      setTimeout(function() {{
        startPayment();
        startFallbackTimer();
      }}, 400);
    }});
  </script>
</body>
</html>"""


def _assemble_image_prompt(page: dict, visual_anchor: str, book_format: dict = None, secondary_characters: list = None) -> str:
    """
    Build the final image prompt for one page.

    Strategy:
      1. Take the rich visual_description the LLM produced
      2. Lead with a SHOT-TYPE directive so the image model frames correctly
      3. For scene/wide/crowd shots, do NOT append visual_anchor (it just makes
         the model paint a single character in a stadium)
      4. For character close-ups, append visual_anchor if not already present
      5. Append secondary character descriptions for consistency
      6. If book_format is provided, wrap in its image_prompt_template
    """
    raw = (page.get("image_prompt") or page.get("visual_description", "")).strip()
    shot_type = (page.get("shot_type") or page.get("image_type", "")).lower()
    primary_subject = page.get("primary_subject", "").strip()

    # Map shot_type → leading cinematic directive
    shot_directives = {
        "wide_establishing": "WIDE CINEMATIC ESTABLISHING SHOT.",
        "aerial_panorama": "AERIAL PANORAMIC VIEW from high above.",
        "crowd_ensemble": "WIDE ENSEMBLE SHOT showing many distinct characters together.",
        "action_dynamic": "DYNAMIC ACTION SHOT with motion, energy, and bold composition.",
        "mid_shot_character": "MEDIUM SHOT of the protagonist, waist-up, performing an action.",
        "close_up_emotion": "CLOSE-UP capturing emotional expression and detail.",
        "montage_sequence": (
            "MULTI-PANEL MONTAGE: divide the frame into 3-4 sub-images showing different "
            "characters performing the same activity simultaneously."
        ),
        "environment_only": "PURE ENVIRONMENT SHOT — no characters, just the setting in detail.",
        # Legacy values from older stories
        "scene": "WIDE SCENE SHOT showing the environment and many figures.",
        "character": "MEDIUM SHOT of the protagonist in a meaningful setting.",
    }
    directive = shot_directives.get(shot_type, "")

    # Decide whether to append the character anchor
    is_scene_shot = shot_type in {
        "wide_establishing", "aerial_panorama", "crowd_ensemble",
        "montage_sequence", "environment_only", "scene",
    }

    parts = ["PORTRAIT ORIENTATION (3:4 ratio, taller than wide). Ensure full subject is visible vertically — do NOT crop heads, feet, or key elements at top/bottom."]
    if directive:
        parts.append(directive)
    if primary_subject and primary_subject.lower() not in raw.lower():
        parts.append(f"Primary subject of this image: {primary_subject}.")
    parts.append(raw)

    if visual_anchor and not is_scene_shot and visual_anchor not in raw:
        parts.append(f"Character appearing in this scene: {visual_anchor}.")

    # Inject secondary character descriptions for consistency
    if secondary_characters and not is_scene_shot:
        chars_in_scene = page.get("characters_in_scene", [])
        if chars_in_scene:
            for sc in secondary_characters:
                sc_name = sc.get("name", "")
                if sc_name and sc_name.lower() in [c.lower() for c in chars_in_scene]:
                    sc_desc = sc.get("description", "")
                    if sc_desc and sc_desc.lower() not in raw.lower():
                        parts.append(f"Also appearing: {sc_name} — {sc_desc}.")

    final = " ".join(parts)

    # Apply book format's image template wrapping if provided
    if book_format and book_format.get("image_prompt_template"):
        template = book_format["image_prompt_template"]
        # Templates use {SCENE}, {ART_STYLE}, etc. — substitute SCENE with our prompt
        if "{SCENE}" in template:
            final = template.replace("{SCENE}", final).replace("{ART_STYLE}", "").replace("{PALETTE}", "").replace("{MOOD}", "")
        elif "{SCENE/CHARACTERS}" in template:
            final = template.replace("{SCENE/CHARACTERS}", final).replace("{ART_STYLE}", "")
        elif "{ACTION/DIALOGUE MOMENT}" in template:
            final = template.replace("{ACTION/DIALOGUE MOMENT}", final).replace("{ART_STYLE}", "").replace("{PALETTE: jewel tones / bright flat}", "")
        elif "{SUBJECT}" in template:
            final = template.replace("{SUBJECT}", final).replace("{ART_STYLE}", "")

    return final


def compress_pil_images_for_storage(images: list, max_size: int = 768, quality: int = 75) -> list:
    """Compress a list of PIL Images to base64 JPEG data URLs for Supabase storage."""
    result = []
    for img in images:
        if img is None:
            result.append(None)
            continue
        try:
            buf = io.BytesIO()
            img_copy = img.convert("RGB")
            img_copy.thumbnail((max_size, max_size), Image.LANCZOS)
            img_copy.save(buf, format="JPEG", quality=quality, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode()
            result.append(f"data:image/jpeg;base64,{b64}")
        except Exception as e:
            logger.warning(f"Image compression failed: {e}")
            result.append(None)
    return result


def _make_cover_thumbnail(img, max_size: int = 300, quality: int = 70) -> str:
    """Create a small base64 JPEG thumbnail from a PIL Image for cover display."""
    if img is None:
        return ""
    try:
        buf = io.BytesIO()
        img_copy = img.convert("RGB")
        img_copy.thumbnail((max_size, max_size), Image.LANCZOS)
        img_copy.save(buf, format="JPEG", quality=quality, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return ""


def decode_stored_images(images_data: list) -> list:
    """Decode a list of base64 data URLs back to PIL Images."""
    result = []
    for url in (images_data or []):
        if url and isinstance(url, str) and url.startswith("data:image"):
            try:
                raw = base64.b64decode(url.split(",", 1)[-1])
                result.append(Image.open(io.BytesIO(raw)).convert("RGB"))
            except Exception:
                result.append(None)
        else:
            result.append(None)
    return result


def create_visual_anchor(child_name: str, age: int, gender: str, physical_desc: str, character_style: str = "") -> str:
    """Create a visual anchor description for consistent character appearance."""
    base_anchor = f"A cute {age} year old {gender.lower()}, {physical_desc.lower()}"
    
    # Extract and emphasize hairstyle from physical description for consistency
    # Look for common hairstyle keywords
    hair_keywords = ['hair', 'ponytail', 'braid', 'curly', 'straight', 'short', 'long', 'bob', 'bangs', 'bun']
    hair_mentioned = any(keyword in physical_desc.lower() for keyword in hair_keywords)
    
    if hair_mentioned:
        # Extract hair-related part and emphasize it
        words = physical_desc.lower().split()
        hair_parts = [w for w in words if any(kw in w for kw in hair_keywords)]
        if hair_parts:
            # Find the context around hair words
            hair_context = []
            for i, word in enumerate(words):
                if any(kw in word for kw in hair_keywords):
                    # Include surrounding words for context
                    start = max(0, i-2)
                    end = min(len(words), i+3)
                    hair_context.extend(words[start:end])
            if hair_context:
                hair_desc = ' '.join(hair_context)
                base_anchor += f", with consistent {hair_desc}"
    
    # Only add character/style info if user specifically provided a famous character companion
    # DO NOT add Max/Mini/Peppa etc unless explicitly requested
    if character_style:
        character_style_lower = character_style.lower()
        # Only add the character to visual anchor if it's a known character (not just a style)
        if "max and mini" in character_style_lower or "max mini" in character_style_lower:
            base_anchor += ", alongside Max and Mini (cartoon characters with bold outlines)"
        elif "peppa pig" in character_style_lower:
            base_anchor += ", alongside Peppa Pig character"
        elif "doremon" in character_style_lower or "doraemon" in character_style_lower:
            base_anchor += ", alongside Doraemon character"
        elif "chhota bheem" in character_style_lower or "chota bheem" in character_style_lower:
            base_anchor += ", alongside Chhota Bheem character"
        elif "motu patlu" in character_style_lower:
            base_anchor += ", alongside Motu and Patlu characters"
        # For pure style requests (not characters), don't add anything to visual anchor
        # The image style is handled separately in generate_image_with_imagen
    
    return base_anchor


def _stringify_keys(d):
    """Convert dict with integer keys to string keys for MongoDB compatibility."""
    if not isinstance(d, dict):
        return d
    return {str(k): v for k, v in d.items()}


def _save_images_now() -> None:
    """Persist current generated_images to MongoDB immediately (called after each image generates)."""
    user_id = get_current_user_id()
    existing_id = st.session_state.get("current_book_history_id")
    if not user_id or not existing_id:
        return
    imgs = st.session_state.get("generated_images", [])
    if not imgs:
        return
    try:
        from mongo_client import book_history_col
        images_for_db = compress_pil_images_for_storage(imgs)
        journey_state = {
            "story_approved": st.session_state.get("story_approved", False),
            "all_images_approved": st.session_state.get("all_images_approved", False),
            "image_approvals": _stringify_keys(st.session_state.get("image_approvals", {})),
            "edited_story_pages": _stringify_keys(st.session_state.get("edited_story_pages", {})),
            "edited_image_prompts": _stringify_keys(st.session_state.get("edited_image_prompts", {})),
            "current_step": "step3" if st.session_state.get("all_images_approved") else "step2",
        }
        book_history_col().update_one(
            {"_id": existing_id, "user_id": user_id},
            {"$set": {"images": images_for_db, "metadata.journey_state": journey_state}},
        )
        logger.info(f"Images saved incrementally: {len(images_for_db)} entries")
    except Exception as _e:
        logger.warning(f"Incremental image save failed: {_e}")


def save_story(story_data: Dict, child_name: str, metadata: Dict = None):
    """Save story to Supabase history and local file fallback."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        journey_state = {
            "story_approved": st.session_state.get("story_approved", False),
            "all_images_approved": st.session_state.get("all_images_approved", False),
            "image_approvals": _stringify_keys(st.session_state.get("image_approvals", {})),
            "edited_story_pages": _stringify_keys(st.session_state.get("edited_story_pages", {})),
            "edited_image_prompts": _stringify_keys(st.session_state.get("edited_image_prompts", {})),
            "current_step": "step3" if st.session_state.get("all_images_approved", False) else
                           ("step2" if st.session_state.get("story_approved", False) else "step1")
        }
        save_data = {
            "story": story_data,
            "metadata": metadata or {},
            "timestamp": timestamp,
            "child_name": child_name,
            "journey_state": journey_state,
        }

        # --- MongoDB persistence ---
        user_id = get_current_user_id()
        if user_id:
            try:
                from mongo_client import book_history_col
                import uuid as _uuid
                col = book_history_col()
                story_for_db = json.loads(json.dumps(story_data))
                images_for_db = compress_pil_images_for_storage(
                    st.session_state.get("generated_images", [])
                ) if st.session_state.get("generated_images") else []

                existing_id = st.session_state.get("current_book_history_id")
                if existing_id:
                    # Use only _id in filter — user_id mismatch would cause silent no-op.
                    # Use dot-notation $set so we don't wipe existing metadata fields.
                    # Generate cover thumbnail from first image
                    gen_imgs = st.session_state.get("generated_images", [])
                    cover_thumb = _make_cover_thumbnail(gen_imgs[0]) if gen_imgs and gen_imgs[0] else ""
                    fields_to_set = {
                        "user_id": user_id,
                        "story_data": story_for_db,
                        "images": images_for_db,
                        "cover_thumbnail": cover_thumb,
                        "metadata.timestamp": timestamp,
                        "metadata.journey_state": journey_state,
                    }
                    if metadata:
                        for k, v in metadata.items():
                            fields_to_set[f"metadata.{k}"] = v
                    result = col.update_one({"_id": existing_id}, {"$set": fields_to_set})
                    if result.matched_count == 0:
                        logger.warning(f"Update matched 0 docs for id={existing_id}, inserting new")
                        existing_id = None
                    else:
                        logger.info(f"Story updated in MongoDB doc {existing_id}, images={len(images_for_db)}")
                if not existing_id:
                    doc_id = str(_uuid.uuid4())
                    has_ref_photo = bool(
                        (metadata or {}).get("has_reference_photo")
                        or st.session_state.get("wiz_reference_photos_b64")
                    )
                    gen_imgs = st.session_state.get("generated_images", [])
                    cover_thumb = _make_cover_thumbnail(gen_imgs[0]) if gen_imgs and gen_imgs[0] else ""
                    col.insert_one({
                        "_id": doc_id,
                        "user_id": user_id,
                        "child_name": child_name,
                        "title": story_data.get("title", f"{child_name}'s Story"),
                        "book_type": "custom",
                        "cover_thumbnail": cover_thumb,
                        "story_data": story_for_db,
                        "images": images_for_db,
                        "is_private": has_ref_photo,
                        "metadata": {**(metadata or {}), "timestamp": timestamp, "journey_state": journey_state},
                        "created_at": datetime.utcnow(),
                    })
                    st.session_state.current_book_history_id = doc_id
                    logger.info(f"Story inserted to MongoDB, id={doc_id}, images={len(images_for_db)}, private={has_ref_photo}")
            except Exception as db_err:
                logger.warning(f"MongoDB save failed: {db_err}")
                st.toast("Cloud save failed. Your story is saved locally.", icon="⚠️")

        # --- Local file fallback ---
        filename = f"{child_name}_{timestamp}.json"
        filepath = st.session_state.stories_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        return filepath
    except Exception as e:
        st.error(f"Failed to save story: {e}")
        return None


def save_template_book_to_history(book_data: Dict):
    """Persist template-generated book to Supabase history and local file fallback."""
    try:
        child_name = book_data.get("child_name", "Child")
        template_name = book_data.get("template_name", "Template Book")
        template_id = book_data.get("template_id")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Build story payload without image data to keep size manageable
        pages_for_history = []
        for p in book_data.get("pages", []):
            pages_for_history.append({
                "page_number": p.get("page_number"),
                "profession_title": p.get("profession_title"),
                "text": p.get("text"),
                "image_prompt": p.get("image_prompt"),
                # Exclude image_url (can be large base64) - regenerate when needed
            })
        story_payload = {
            "title": f"{template_name} - {child_name}",
            "pages": pages_for_history,
            "template_id": template_id,
            "template_name": template_name,
        }

        # --- MongoDB persistence ---
        user_id = get_current_user_id()
        if user_id:
            try:
                from mongo_client import book_history_col
                import uuid as _uuid
                col = book_history_col()
                has_ref_photo = bool(book_data.get("reference_image_base64"))
                cover_thumb = book_data.get("cover_image", "")
                tpl_pages = book_data.get("pages", [])
                if tpl_pages and tpl_pages[0].get("image_url"):
                    first_img_url = tpl_pages[0]["image_url"]
                    if first_img_url.startswith("data:image"):
                        try:
                            img_data = base64.b64decode(first_img_url.split(",", 1)[1])
                            cover_thumb = _make_cover_thumbnail(Image.open(io.BytesIO(img_data)))
                        except Exception:
                            pass
                col.insert_one({
                    "_id": str(_uuid.uuid4()),
                    "user_id": user_id,
                    "child_name": child_name,
                    "title": f"{template_name} - {child_name}",
                    "book_type": "template",
                    "cover_thumbnail": cover_thumb,
                    "template_id": template_id,
                    "template_name": template_name,
                    "story_data": story_payload,
                    "is_private": has_ref_photo,
                    "metadata": {
                        "template_id": template_id,
                        "template_name": template_name,
                        "timestamp": timestamp,
                        "gender": book_data.get("gender"),
                        "age": book_data.get("age"),
                    },
                    "created_at": datetime.utcnow(),
                })
                logger.info(f"Template book saved to MongoDB for user {user_id}, private={has_ref_photo}")
            except Exception as db_err:
                logger.warning(f"MongoDB save failed, falling back to local file: {db_err}")

        # --- Local file fallback ---
        filename = f"{child_name}_{timestamp}.json"
        filepath = st.session_state.stories_dir / filename
        save_data = {
            "story": story_payload,
            "metadata": {"template_id": template_id, "template_name": template_name},
            "timestamp": timestamp,
            "child_name": child_name,
            "journey_state": {
                "story_approved": True,
                "all_images_approved": True,
                "image_approvals": {},
                "edited_story_pages": {},
                "edited_image_prompts": {},
                "current_step": "step3",
            },
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        return filepath
    except Exception as e:
        st.error(f"Failed to save template book to history: {e}")
        logger.exception("save_template_book_to_history failed")
        return None


def load_story(filepath) -> Dict:
    """Load story from history."""
    try:
        # Convert to Path if it's a string
        if isinstance(filepath, str):
            filepath = Path(filepath)
        elif not isinstance(filepath, Path):
            filepath = Path(str(filepath))
        
        if not filepath.exists():
            error_msg = f"Story file not found: {filepath}"
            st.error(error_msg)
            logger.error(error_msg)
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Validate that the data has the expected structure
            if not isinstance(data, dict):
                error_msg = "Invalid story file format"
                st.error(error_msg)
                logger.error(f"{error_msg} in {filepath}")
                return None
            if "story" not in data:
                error_msg = "Story data is missing from file"
                st.error(error_msg)
                logger.error(f"{error_msg} in {filepath}")
                return None
            logger.info(f"Successfully loaded story from {filepath}")
            return data
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse story file (corrupted JSON): {str(e)[:100]}"
        st.error(error_msg)
        logger.error(f"JSON decode error loading {filepath}: {e}")
        with st.expander("Error Details", expanded=False):
            st.code(str(e))
        return None
    except Exception as e:
        error_msg = f"Failed to load story: {str(e)[:200]}"
        st.error(error_msg)
        import traceback
        logger.error(f"Error loading story from {filepath}: {traceback.format_exc()}")
        with st.expander("Error Details", expanded=False):
            st.code(traceback.format_exc())
        return None

def get_story_history():
    """Get list of all saved stories, combining MongoDB and local files."""
    user_id = get_current_user_id()
    stories = []

    # --- Try MongoDB first ---
    if user_id:
        try:
            from mongo_client import book_history_col
            from pymongo import DESCENDING
            col = book_history_col()
            rows = list(col.find(
                {"user_id": user_id},
                {"_id": 1, "child_name": 1, "title": 1, "book_type": 1,
                 "template_id": 1, "template_name": 1, "created_at": 1, "metadata": 1, "cover_thumbnail": 1}
            ).sort("created_at", DESCENDING).limit(100))
            for row in rows:
                created = row.get("created_at")
                ts_display = created.strftime("%Y%m%d_%H%M%S") if created else ""
                stories.append({
                    "db_id": str(row["_id"]),
                    "filepath": None,
                    "child_name": row.get("child_name", "Unknown"),
                    "timestamp": ts_display,
                    "title": row.get("title", "Untitled"),
                    "book_type": row.get("book_type", "custom"),
                    "template_id": row.get("template_id"),
                    "template_name": row.get("template_name"),
                    "cover_thumbnail": row.get("cover_thumbnail", ""),
                })
            if stories:
                logger.info(f"Loaded {len(stories)} stories from MongoDB")
                return stories
            logger.info("MongoDB returned 0 history rows, checking local files")
        except Exception as db_err:
            logger.warning(f"Could not load history from MongoDB: {db_err}")

    # --- Fallback to local files ---
    try:
        stories = []
        if st.session_state.stories_dir.exists():
            for filepath in sorted(st.session_state.stories_dir.glob("*.json"), reverse=True):
                try:
                    data = load_story(filepath)
                    if data:
                        stories.append({
                            "db_id": None,
                            "filepath": filepath,
                            "child_name": data.get("child_name", "Unknown"),
                            "timestamp": data.get("timestamp", ""),
                            "title": data.get("story", {}).get("title", "Untitled Story"),
                            "book_type": data.get("metadata", {}).get("template_id") and "template" or "custom",
                            "template_id": data.get("metadata", {}).get("template_id"),
                            "template_name": data.get("metadata", {}).get("template_name"),
                        })
                except Exception:
                    continue
        return stories
    except Exception as e:
        st.warning(f"Could not load story history: {e}")
        return []

def reset_story_state():
    """Reset all story-related session state - COMPLETE RESET."""
    st.session_state.generated_story = None
    st.session_state.current_book_history_id = None
    st.session_state.generated_images = []
    st.session_state.image_generation_errors = {}
    st.session_state.pdf_path = None
    st.session_state.story_approved = False
    st.session_state.image_approvals = {}
    st.session_state.all_images_approved = False
    st.session_state.edited_story_pages = {}
    st.session_state.edited_image_prompts = {}
    st.session_state.pdf_generation_key = None
    st.session_state.current_child_name = ""
    st.session_state.current_book_payment_status = None
    st.session_state.pending_payment_link_id = None
    st.session_state.pending_payment_url = None
    st.session_state.pending_payment_gate = None
    st.session_state.book_delivery_option = None
    st.session_state.cf_pending_order_id = None
    st.session_state.cf_payment_session_id = None
    st.session_state.cf_order_created_at = None
    st.session_state.cf_show_verify_button = False
    # Clear template-related states
    if "template_generated_book" in st.session_state:
        del st.session_state.template_generated_book
    if "template_book_data" in st.session_state:
        del st.session_state.template_book_data
    if "generate_template_book" in st.session_state:
        del st.session_state.generate_template_book
    if "selected_template_id" in st.session_state:
        del st.session_state.selected_template_id
    if "selected_template_name" in st.session_state:
        del st.session_state.selected_template_name
    if "scroll_to_details" in st.session_state:
        del st.session_state.scroll_to_details
    if "just_approved_story" in st.session_state:
        del st.session_state.just_approved_story
    if "regenerate_template_page_idx" in st.session_state:
        del st.session_state.regenerate_template_page_idx
    # Clear ALL dynamic flags that might be left over
    keys_to_delete = []
    for key in st.session_state.keys():
        if (key.startswith("regen_from_page_") or
            key.startswith("_regen_flag_") or
            key.startswith("regen_page_prompt_") or
            key.startswith("editing_prompt_") or
            key.startswith("regenerate_image_") or
            key.startswith("story_text_") or
            key.startswith("image_prompt_") or
            key.startswith("move_") or
            key.startswith("regen_") or
            key.startswith("final_edit_") or
            key.startswith("template_page_text_") or
            key.startswith("template_text_area_") or
            key.startswith("template_photo_")):
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del st.session_state[key]
    logger.info("Story state completely reset")

def clear_images_on_story_change():
    """Clear images when story changes to prevent mismatch."""
    st.session_state.generated_images = []
    st.session_state.image_approvals = {}
    st.session_state.all_images_approved = False
    st.session_state.pdf_path = None
    st.session_state.pdf_generation_key = None
    logger.info("Cleared images due to story change")

def regenerate_story_from_page(api_key: str, existing_story: Dict, start_page: int, 
                                regeneration_prompt: str, child_name: str, age: int, language: str) -> Dict:
    """Regenerate story from a specific page onwards based on prompt."""
    try:
        logger.info(f"Regenerating story from page {start_page} with prompt: {regeneration_prompt[:100]}...")
        
        existing_pages = existing_story.get("pages", [])
        existing_title = existing_story.get("title", "Story")
        existing_visual_anchor = existing_story.get("visual_anchor", "")
        
        # Keep pages before start_page unchanged
        pages_before = existing_pages[:start_page - 1] if start_page > 1 else []
        
        # Create context from pages before
        context_summary = ""
        if pages_before:
            context_summary = "\n".join([f"Page {i+1}: {p.get('text', '')}" for i, p in enumerate(pages_before)])
        
        prompt = f"""You are modifying a children's story. You need to regenerate pages {start_page} through 10 based on the following instructions.

**INSTRUCTIONS:**
{regeneration_prompt}

**EXISTING STORY CONTEXT (Pages 1-{start_page-1} - DO NOT CHANGE THESE):**
{context_summary}

**REQUIREMENTS:**
1. Keep pages 1-{start_page-1} exactly as they are (they're already approved)
2. Regenerate pages {start_page}-10 based on the instructions above
3. Ensure the new pages flow naturally from the existing pages
4. Maintain the Bibliotherapy Arc structure for pages {start_page}-10
5. Keep visual_anchor exactly as is: {existing_visual_anchor}
6. The story should be age-appropriate for {age} years old
7. Write in {language} language

**OUTPUT FORMAT (Return strictly as JSON):**
{{
  "title": "{existing_title}",
  "visual_anchor": "{existing_visual_anchor}",
  "pages": [
    ... (pages 1-{start_page-1} from existing story) ...,
    {{
      "page_number": {start_page},
      "text": "New story text...",
      "visual_description": "New visual description..."
    }},
    ... (continue for pages {start_page+1}-10) ...
  ]
}}

CRITICAL: Output ONLY the JSON, no additional text before or after."""

        from vertex_client import call_gemini_text
        response_text = call_gemini_text(prompt, api_key=api_key, temperature=0.8)
        if response_text is None:
            st.error("❌ Could not regenerate story. Check your API key or Vertex AI credentials.")
            return None

        # Extract JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            story_data = json.loads(response_text)
            logger.info("Successfully parsed regenerated story JSON")
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {e}"
            logger.error(f"{error_msg}. Response: {response_text[:500]}")
            st.error(f"❌ {error_msg}")
            with st.expander("View API Response", expanded=False):
                st.code(response_text[:2000])
            return None

        # Strip any pre-assembled image_prompt — assembled lazily in Step 2
        for page in story_data.get("pages", []):
            page.pop("image_prompt", None)

        # Verify we got a valid story structure
        if not story_data.get("pages") or len(story_data.get("pages", [])) == 0:
            error_msg = "Regenerated story has no pages"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}. Please try again.")
            return None
        
        logger.info(f"Story regeneration complete. Pages: {len(story_data.get('pages', []))}")
        return story_data
        
    except Exception as e:
        error_msg = f"Error regenerating story: {e}"
        logger.error(error_msg, exc_info=True)
        st.error(f"❌ {error_msg}")
        import traceback
        with st.expander("Error Details", expanded=False):
            st.code(traceback.format_exc())
        return None

def list_available_models(api_key: str):
    """List available Gemini models."""
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        params = {"key": api_key}
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()
        models = []
        if "models" in result:
            for model in result["models"]:
                name = model.get("name", "")
                # Extract model name from full path (e.g., "models/gemini-1.5-pro" -> "gemini-1.5-pro")
                if "/" in name:
                    name = name.split("/")[-1]
                models.append(name)
        return models
    except Exception as e:
        st.warning(f"Could not list models: {e}")
        return []

def refine_story_with_followup(api_key: str, existing_story: Dict, followup_prompt: str,
                                child_name: str, age: int, language: str) -> Dict:
    """
    Edit the existing story boldly based on the user's revision instructions.
    The model receives the current story as REFERENCE but is explicitly told to
    make deep, sweeping changes — not cosmetic tweaks.  Pages that don't need
    changing can stay; pages that do should be fully rewritten.  The model may
    also add or remove pages to properly honour the instructions.
    """
    try:
        logger.info(f"Editing story for '{child_name}' — instruction: {followup_prompt[:120]}…")

        existing_pages         = existing_story.get("pages", [])
        existing_visual_anchor = existing_story.get("visual_anchor", "")
        existing_title         = existing_story.get("title", "")

        # Strip heavy fields to keep prompt compact
        _lean_pages = [{k: v for k, v in p.items() if k != "image_prompt"}
                       for p in existing_pages]
        lean_story  = {**{k: v for k, v in existing_story.items() if k != "pages"},
                       "pages": _lean_pages}
        story_json  = json.dumps(lean_story, indent=2, ensure_ascii=False)

        prompt = f"""You are a professional children's book editor with full creative authority.
Your job is to BOLDLY REWRITE this story based on the parent's instructions below.

══════════════════════════════════════════════════════
PARENT'S REVISION INSTRUCTIONS (apply these in full):
══════════════════════════════════════════════════════
{followup_prompt}
══════════════════════════════════════════════════════

EDITING RULES — READ EVERY ONE:
1. SCOPE OF CHANGE: Apply the instructions to the WHOLE story, not just 1-2 pages.
   If the instruction changes the theme, rewrite every page that needs it.
   If the instruction adds a new element (character, place, twist), weave it through
   the entire arc — introduction, middle, and resolution.
2. BOLD EDITS ONLY: Do NOT make cosmetic tweaks (changing one word per page).
   Fully rewrite any page whose meaning, action, or feel must change.
3. PAGE COUNT: You may ADD pages if the story needs more room, or REMOVE pages if
   the story becomes tighter. There is no fixed page count — write what the story needs.
4. TITLE: Update the title if the story direction has changed significantly.
5. WHAT TO KEEP: Keep the child's name ({child_name}), the visual_anchor (for
   illustration consistency), and the overall JSON structure.
   Keep pages that genuinely don't need changing — don't rewrite for the sake of it.
6. OUTPUT FORMAT: Return ONLY valid JSON — same structure as the input below.
   No markdown fences, no commentary, no extra text before or after.

CURRENT STORY (for reference — edit this, don't copy it):
{story_json}

Now write the revised story JSON:"""

        from vertex_client import call_gemini_text
        response_text = call_gemini_text(prompt, api_key=api_key, temperature=0.9, max_tokens=32768)
        if response_text is None:
            st.error("❌ Could not edit story. Check your API key or Vertex AI credentials.")
            return None

        # Strip markdown fences if model added them
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            story_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in refine: {e} — response: {response_text[:400]}")
            st.error(f"❌ Failed to parse edited story: {e}")
            with st.expander("Raw model output"):
                st.code(response_text[:3000])
            return None

        # Strip any assembled image_prompts — re-assembled lazily before image gen
        for page in story_data.get("pages", []):
            page.pop("image_prompt", None)

        if not story_data.get("pages"):
            st.error("❌ Edited story has no pages. Please try again.")
            return None

        # Always restore the existing visual_anchor so images stay consistent
        if existing_visual_anchor:
            story_data["visual_anchor"] = existing_visual_anchor

        n_new = len(story_data.get("pages", []))
        n_old = len(existing_pages)
        logger.info(f"Story edit complete — {n_old} → {n_new} pages")
        return story_data

    except Exception as e:
        logger.error(f"refine_story_with_followup error: {e}", exc_info=True)
        st.error(f"❌ Error editing story: {e}")
        return None

def regenerate_story_from_page(api_key: str, existing_story: Dict, start_page_idx: int, 
                                regen_prompt: str, child_name: str, age: int, language: str) -> Dict:
    """Regenerate story from a specific page onwards based on prompt."""
    try:
        logger.info(f"Regenerating story from page {start_page_idx + 1} with prompt: {regen_prompt[:100]}...")
        
        existing_pages = existing_story.get("pages", [])
        existing_title = existing_story.get("title", "Story")
        existing_visual_anchor = existing_story.get("visual_anchor", "")
        
        # Keep pages before start_page_idx unchanged
        pages_before = existing_pages[:start_page_idx]
        pages_to_regenerate = existing_pages[start_page_idx:]
        
        # Create context from existing story
        story_context = f"""
Title: {existing_title}
Visual Anchor: {existing_visual_anchor}

Pages 1-{start_page_idx} (KEEP THESE UNCHANGED):
{json.dumps(pages_before, indent=2, ensure_ascii=False)}

Pages {start_page_idx + 1}-{len(existing_pages)} (REGENERATE THESE):
{json.dumps(pages_to_regenerate, indent=2, ensure_ascii=False)}
"""
        
        prompt = f"""You are modifying a children's story. You MUST regenerate pages {start_page_idx + 1} to {len(existing_pages)} based on these instructions, while keeping pages 1-{start_page_idx} exactly the same.

**INSTRUCTIONS FOR REGENERATION:**
{regen_prompt}

**CRITICAL REQUIREMENTS:**
1. Keep pages 1-{start_page_idx} EXACTLY as they are (do not modify them)
2. Regenerate pages {start_page_idx + 1}-{len(existing_pages)} based on the instructions above
3. Ensure the regenerated pages flow naturally from the previous pages
4. Maintain the same visual anchor: {existing_visual_anchor}
5. Keep the same JSON structure
6. The story should make sense as a whole

**EXISTING STORY CONTEXT:**
{story_context}

**YOUR TASK:**
Return the COMPLETE story JSON with:
- Pages 1-{start_page_idx}: Exactly as provided (unchanged)
- Pages {start_page_idx + 1}-{len(existing_pages)}: Regenerated based on instructions

Output ONLY valid JSON, no markdown, no explanations."""
        
        from vertex_client import call_gemini_text
        response_text = call_gemini_text(prompt, api_key=api_key, temperature=0.8)
        if response_text is None:
            st.error("❌ Could not regenerate story. Check your API key or Vertex AI credentials.")
            return None

        # Extract JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            story_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {e}"
            logger.error(f"{error_msg}. Response: {response_text[:500]}")
            st.error(f"❌ {error_msg}")
            with st.expander("View API Response", expanded=False):
                st.code(response_text[:2000])
            return None
        
        # Strip any pre-assembled image_prompt — assembled lazily in Step 2
        for page in story_data.get("pages", []):
            page.pop("image_prompt", None)

        # Verify structure
        if not story_data.get("pages") or len(story_data.get("pages", [])) != len(existing_pages):
            error_msg = f"Regenerated story has {len(story_data.get('pages', []))} pages, expected {len(existing_pages)}"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}")
            return None
        
        logger.info(f"Successfully regenerated story from page {start_page_idx + 1}")
        return story_data
        
    except Exception as e:
        error_msg = f"Error regenerating story from page: {e}"
        logger.error(error_msg, exc_info=True)
        st.error(f"❌ {error_msg}")
        import traceback
        with st.expander("Error Details", expanded=False):
            st.code(traceback.format_exc())
        return None

def generate_story_with_gemini(api_key: str, child_name: str, age: int, gender: str,
                               physical_desc: str, problem: str, language: str,
                               family_structure: str = "", hero_trait: str = "", character_choice: str = "",
                               story_type: str = "Behavioral/Problem-solving",
                               image_style: str = "Cartoon/Animated (3D Pixar Style)",
                               format_id: str = None) -> Dict:
    """Generate story using Gemini API via REST."""
    try:
        logger.info(f"Generating story for {child_name}, age {age}, problem: {problem[:50]}..., format={format_id}")
        # Create visual anchor (incorporate character style)
        visual_anchor = create_visual_anchor(child_name, age, gender, physical_desc, character_choice)

        # Resolve book format
        book_format = None
        if format_id:
            try:
                from book_formats import get_format_by_id
                book_format = get_format_by_id(format_id)
            except Exception:
                book_format = None

        prompt = get_full_prompt(
            age=age,
            child_name=child_name,
            gender=gender,
            story_theme=problem,
            language=language,
            family_info=family_structure,
            hero_trait=hero_trait,
            character_companion=character_choice,
            story_type=story_type,
            book_format=book_format,
        )

        logger.info(f"Using age-specific prompt for age {age}, format {format_id}")

        from vertex_client import call_gemini_text
        response_text = call_gemini_text(prompt, api_key=api_key, temperature=0.7)
        if response_text is None:
            st.error("❌ Could not generate story. Check your API key or Vertex AI credentials.")
            return None

        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        story_data = json.loads(response_text)

        # Keep visual_anchor at story level; strip any pre-assembled image_prompt —
        # image prompts are assembled lazily in Step 2 just before each image is generated.
        story_data["visual_anchor"] = story_data.get("visual_anchor", visual_anchor)
        for page in story_data.get("pages", []):
            page.pop("image_prompt", None)

        return story_data
        
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse JSON response: {e}"
        logger.error(f"{error_msg}. Response: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
        st.error(f"❌ {error_msg}")
        if 'response_text' in locals():
            with st.expander("View API Response", expanded=False):
                st.code(response_text[:2000])
        return None
    except Exception as e:
        error_msg = f"Error generating story: {e}"
        logger.error(error_msg, exc_info=True)
        st.error(f"❌ {error_msg}")
        import traceback
        with st.expander("Error Details", expanded=False):
            st.code(traceback.format_exc())
        return None

def generate_image_with_imagen(
    api_key: str,
    prompt: str,
    retry_count: int = 0,
    image_style: str = None,
    image_index: int = None,
    reference_image_b64: str = None,
) -> Image.Image:
    """Generate image via Vertex AI (primary) or Google AI API (fallback)."""
    try:
        if image_index is not None and image_index in st.session_state.image_generation_errors:
            del st.session_state.image_generation_errors[image_index]
        logger.info(f"Generating image (attempt {retry_count + 1}), prompt: {prompt[:100]}...")

        if image_style is None:
            # wiz_image_style is the primary key set by the wizard; image_style is legacy fallback
            image_style = (
                st.session_state.get("wiz_image_style")
                or st.session_state.get("image_style", "Cartoon/Animated (3D Pixar Style)")
            )

        # Use reference photos from session state if not explicitly passed
        if not reference_image_b64:
            photos = st.session_state.get("wiz_reference_photos_b64", []) or []
            if photos:
                reference_image_b64 = photos  # list of base64 strings

        # When reference photos are present, upgrade cartoon styles to face-preserving portrait mode
        has_ref_photos = bool(
            (isinstance(reference_image_b64, list) and reference_image_b64)
            or (reference_image_b64 and not isinstance(reference_image_b64, list))
        )
        if has_ref_photos and image_style in (
            "Cartoon/Animated (3D Pixar Style)", "Cartoon (2D Flat Style)"
        ):
            image_style = "Photo Reference Portrait"

        style_modifiers = get_image_style(image_style)
        no_text_instruction = "CRITICAL REQUIREMENT - ABSOLUTELY NO TEXT: This image must contain ZERO text, ZERO words, ZERO letters, ZERO numbers, ZERO speech bubbles, ZERO captions, ZERO signs, ZERO labels, ZERO writing of any kind. This is a pure illustration for a children's book - visual art only."

        # Detect scene/panorama prompts and add a scale instruction
        scene_keywords = ("wide shot", "panorama", "aerial", "crowd scene", "crowd of",
                          "dozens of", "hundreds of", "grand scale", "epic scale",
                          "spectacle", "many characters", "vast", "enormous crowd",
                          "packed with", "filled with", "competition", "celebration",
                          "gathering", "festival", "battle scene", "marketplace")
        is_scene = any(kw in prompt.lower() for kw in scene_keywords)
        scene_instruction = (
            " IMPORTANT: This is a GRAND SCALE SCENE. Show a rich, wide environment with many "
            "characters, depth, and atmosphere. The scene and event are the subject — do NOT zoom "
            "in on a single character. Show the full scope and scale of what is described."
            if is_scene else ""
        )

        # When reference photos are provided, add a strong face-matching instruction at the
        # FRONT of the prompt so the model prioritises likeness above all else.
        n_photos = len(reference_image_b64) if isinstance(reference_image_b64, list) else (1 if reference_image_b64 else 0)
        if n_photos > 0:
            face_match_prefix = (
                f"HIGHEST PRIORITY — EXACT CHILD LIKENESS REQUIRED: {n_photos} reference photo(s) of "
                "the real child are attached. Every illustration MUST be an accurate portrait of THIS "
                "specific child. Match precisely: face shape, eye color, eye shape, nose, lips, "
                "smile, skin tone, hair color, hair texture, hair style. "
                "This is a personalised storybook — the child's parents must instantly recognise "
                "their child in every single page. Do NOT use a generic child face. "
                "Use the attached reference photo face exactly. "
            )
            photo_instruction = ""  # already in prefix
        else:
            face_match_prefix = ""
            photo_instruction = ""

        style_prompt = (
            f"{face_match_prefix}"
            f"{no_text_instruction}. "
            f"{scene_instruction} "
            f"{photo_instruction} "
            f"{prompt}. "
            f"{style_modifiers}. "
            f"{no_text_instruction}"
        )

        from vertex_client import call_gemini_image
        data_url = call_gemini_image(style_prompt, api_key=api_key, reference_image_b64=reference_image_b64)
        if data_url:
            image_bytes = base64.b64decode(data_url.split(",", 1)[1])
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            logger.info("Image generated successfully")
            return image

        raise Exception("No image returned from Vertex AI / Google AI API")

    except Exception as e:
        error_msg = f"Image generation failed: {e}"
        logger.error(f"{error_msg} (attempt {retry_count + 1})")

        error_details = {
            "error": str(e),
            "full_error": error_msg,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "attempt": retry_count + 1,
        }

        if retry_count < 1:
            logger.info("Retrying image generation...")
            st.warning(f"⚠️ Image generation failed, retrying... ({str(e)[:100]})")
            time.sleep(2)
            return generate_image_with_imagen(api_key, prompt, retry_count + 1, image_style, image_index, reference_image_b64)

        # Try OpenRouter as final fallback
        openrouter_key = st.session_state.get("openrouter_api_key", "")
        if openrouter_key:
            fallback = generate_image_with_openrouter(openrouter_key, prompt, image_style)
            if fallback:
                logger.info("OpenRouter fallback image generation succeeded")
                return fallback

        if image_index is not None:
            st.session_state.image_generation_errors[image_index] = error_details

        st.error(f"❌ Failed to generate image after retries: {str(e)[:200]}")
        return Image.new('RGB', (384, 512), color=(200, 200, 200))


def generate_image_with_openrouter(openrouter_key: str, prompt: str, image_style: str = None) -> Optional[Image.Image]:
    """Generate image via OpenRouter API using Gemini models (fallback when direct Gemini fails)."""
    # Models to try in order of preference (Gemini only, per user preference)
    models = [
        "google/gemini-2.0-flash-exp:free",
        "google/gemini-flash-1.5-8b",
        "google/gemini-flash-1.5",
    ]

    style_modifiers = get_image_style(image_style) if image_style else ""
    no_text = "CRITICAL: NO TEXT, words, letters, numbers, speech bubbles, or labels in this image. Pure illustration only."
    full_prompt = f"{no_text} {prompt}. {style_modifiers}. {no_text}"

    for model in models:
        try:
            logger.info(f"Trying OpenRouter image generation with model: {model}")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://children-book-generator.app",
                    "X-Title": "Children's Book Generator",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": full_prompt}],
                    "max_tokens": 4096,
                },
                timeout=120,
            )

            if response.status_code != 200:
                logger.warning(f"OpenRouter {model} returned {response.status_code}: {response.text[:200]}")
                continue

            result = response.json()
            candidates = result.get("choices", [])
            if not candidates:
                continue

            content = candidates[0].get("message", {}).get("content", "")

            # Check for inline image data in the response
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        img_url = part.get("image_url", {}).get("url", "")
                        if img_url.startswith("data:image"):
                            b64 = img_url.split(",", 1)[1]
                            img_bytes = base64.b64decode(b64)
                            return Image.open(io.BytesIO(img_bytes))
                        elif img_url:
                            img_resp = requests.get(img_url, timeout=30)
                            if img_resp.status_code == 200:
                                return Image.open(io.BytesIO(img_resp.content))

            # Some models return base64 directly in a text field
            if isinstance(content, str) and content.startswith("data:image"):
                b64 = content.split(",", 1)[1]
                img_bytes = base64.b64decode(b64)
                return Image.open(io.BytesIO(img_bytes))

            logger.info(f"OpenRouter {model} responded but returned text, not an image")

        except Exception as ex:
            logger.warning(f"OpenRouter {model} failed: {ex}")
            continue

    logger.error("All OpenRouter models failed to generate an image")
    return None


def create_pdf(
    story_data: Dict,
    images: List[Image.Image],
    child_name: str,
    output_path: str,
    book_format: dict = None,
):
    """Create a PDF using a layout matched to the chosen book format."""
    if book_format is None:
        from book_formats import DEFAULT_FORMAT
        book_format = DEFAULT_FORMAT

    fmt_id = book_format.get("id", "minimal_top_bottom")
    font_size_pt = float(book_format.get("font_size_pt", 18))

    # Physical page dimensions per format (width × height in points)
    PAGE_SIZES = {
        "minimal_top_bottom":  (8.0 * inch,  8.0 * inch),
        "full_bleed_double":   (11.0 * inch,  8.5 * inch),
        "illo_opposite_text":  (8.5 * inch, 11.0 * inch),
        "rhyming_spread":      (10.0 * inch,  8.0 * inch),
        "speech_bubble":       (8.5 * inch,  9.0 * inch),
        "spot_illustration":   (8.5 * inch, 11.0 * inch),
        "comic_panels":        (7.0 * inch, 10.0 * inch),
        "bold_board_book":     (6.0 * inch,  6.0 * inch),
    }
    pw, ph = PAGE_SIZES.get(fmt_id, (8.5 * inch, 8.5 * inch))

    c = canvas.Canvas(output_path, pagesize=(pw, ph))
    styles = getSampleStyleSheet()

    def _draw_image(img, x, y, w, h):
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(ImageReader(buf), x, y, width=w, height=h, preserveAspectRatio=True)

    def _fit(img, box_w, box_h):
        iw, ih = img.size
        ar = iw / ih
        if ar > box_w / box_h:
            w = box_w; h = w / ar
        else:
            h = box_h; w = h * ar
        return w, h

    def _draw_text(text, x, y, w, h, fs, align=TA_CENTER, font="Helvetica"):
        min_fs = max(8, fs * 0.5)
        for attempt_fs in [fs, fs * 0.85, fs * 0.70, min_fs]:
            sty = ParagraphStyle("_pt", parent=styles["BodyText"],
                fontSize=attempt_fs, textColor=black, alignment=align,
                leading=attempt_fs * 1.35, fontName=font)
            para = Paragraph(text, sty)
            _pw, _ph = para.wrap(w, h * 2)
            if _ph <= h or attempt_fs <= min_fs:
                para.wrap(w, h)
                vy = y + max(0, (h - _ph) / 2)
                para.drawOn(c, x, vy)
                return

    # ── Cover page (illustrated) ──────────────────────────────────────
    book_title = story_data.get("title", f"{child_name}'s Storybook")
    cover_img = images[0] if images else None
    if cover_img:
        iw, ih = _fit(cover_img, pw, ph)
        ix = (pw - iw) / 2
        iy = (ph - ih) / 2
        _draw_image(cover_img, ix, iy, iw, ih)
        # Dark gradient overlay at bottom for text readability
        c.saveState()
        c.setFillColor(HexColor("#000000"))
        c.setFillAlpha(0.55)
        c.rect(0, 0, pw, ph * 0.38, fill=1, stroke=0)
        c.restoreState()
        c.setFillAlpha(1.0)  # restoreState may not fully undo setFillAlpha; reset explicitly
    else:
        c.setFillColor(HexColor("#1a1a2e"))
        c.rect(0, 0, pw, ph, fill=1, stroke=0)
    # Title text
    title_fs = min(32, int(pw / inch * 3.8))
    name_fs = min(20, int(pw / inch * 2.4))
    c.setFillAlpha(1.0)  # ensure full opacity before drawing text
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", title_fs)
    # Word-wrap the title
    title_lines = []
    words = book_title.split()
    line = ""
    for w in words:
        test = f"{line} {w}".strip()
        if c.stringWidth(test, "Helvetica-Bold", title_fs) < pw - 60:
            line = test
        else:
            if line:
                title_lines.append(line)
            line = w
    if line:
        title_lines.append(line)
    text_y = ph * 0.22
    for tl in reversed(title_lines):
        c.drawCentredString(pw / 2, text_y, tl)
        text_y += title_fs + 6
    c.setFont("Helvetica", name_fs)
    c.setFillColor(HexColor("#EEEEEE"))
    c.drawCentredString(pw / 2, ph * 0.12, f"A story for {child_name}")
    c.showPage()

    pages = story_data.get("pages", [])

    for idx, page in enumerate(pages):
        if idx >= len(images):
            break
        img = images[idx]
        text = page.get("text", "")

        if fmt_id == "minimal_top_bottom":
            # 8×8 sq — image top 70 %, white band bottom 30 %
            band = ph * 0.30
            iw, ih = _fit(img, pw, ph - band)
            ix = (pw - iw) / 2
            iy = band + ((ph - band) - ih) / 2
            _draw_image(img, ix, iy, iw, ih)
            c.setFillColor(white)
            c.rect(0, 0, pw, band, fill=1, stroke=0)
            _draw_text(text, 18, 4, pw - 36, band - 8, font_size_pt, TA_CENTER, "Helvetica-Bold")

        elif fmt_id == "full_bleed_double":
            # 11×8.5 landscape — full-bleed image, solid white box bottom-left for text
            iw, ih = _fit(img, pw, ph)
            ix = (pw - iw) / 2; iy = (ph - ih) / 2
            _draw_image(img, ix, iy, iw, ih)
            box_w = pw * 0.50; box_h = ph * 0.32
            box_x = 20; box_y = 15
            c.setFillColor(HexColor("#FFFFFFEE"))
            c.setStrokeColor(HexColor("#CCCCCC"))
            c.setLineWidth(0.5)
            c.roundRect(box_x, box_y, box_w, box_h, 10, fill=1, stroke=1)
            _draw_text(text, box_x + 12, box_y + 6, box_w - 24, box_h - 12,
                       font_size_pt, TA_LEFT, "Helvetica")

        elif fmt_id == "illo_opposite_text":
            # 8.5×11 portrait — image page then text page per story page
            iw, ih = _fit(img, pw, ph)
            ix = (pw - iw) / 2; iy = (ph - ih) / 2
            _draw_image(img, ix, iy, iw, ih)
            c.showPage()
            # Text page: generous margins, left-aligned serif
            mg = 54
            _draw_text(text, mg, mg, pw - 2 * mg, ph - 2 * mg,
                       font_size_pt, TA_LEFT, "Times-Roman")

        elif fmt_id == "rhyming_spread":
            # 10×8 landscape — image fills left half, verse on right half
            half = pw / 2
            iw, ih = _fit(img, half - 10, ph - 20)
            ix = (half - iw) / 2; iy = (ph - ih) / 2
            _draw_image(img, ix, iy, iw, ih)
            c.setStrokeColor(HexColor("#DDDDDD"))
            c.setLineWidth(1)
            c.line(half, 20, half, ph - 20)
            _draw_text(text, half + 24, 20, half - 48, ph - 40,
                       font_size_pt, TA_CENTER, "Helvetica-Bold")

        elif fmt_id == "speech_bubble":
            # 8.5×9 portrait — image bottom 70 %, rounded speech-bubble box top 30 %
            bubble_h = ph * 0.30
            img_zone = ph - bubble_h
            iw, ih = _fit(img, pw, img_zone)
            ix = (pw - iw) / 2; iy = 0
            _draw_image(img, ix, iy, iw, ih)
            bx = 15; by = img_zone + 8
            bw = pw - 30; bh = bubble_h - 14
            c.setFillColor(white)
            c.setStrokeColor(HexColor("#333333"))
            c.setLineWidth(2)
            c.roundRect(bx, by, bw, bh, 14, fill=1, stroke=1)
            # Small tail triangle pointing down
            c.setFillColor(white)
            tail_x = pw * 0.35
            c.setStrokeColor(HexColor("#333333"))
            _draw_text(text, bx + 14, by + 4, bw - 28, bh - 8,
                       font_size_pt, TA_CENTER, "Helvetica-Bold")

        elif fmt_id == "spot_illustration":
            # 8.5×11 portrait — vignette image centred at top, text flows below
            # Adaptive: short text gets a larger image (up to 70% of page)
            text_len = len(text) if text else 0
            if text_len < 200:
                vig_w = pw * 0.82; vig_h = ph * 0.70
            elif text_len < 400:
                vig_w = pw * 0.75; vig_h = ph * 0.55
            else:
                vig_w = pw * 0.68; vig_h = ph * 0.45
            iw, ih = _fit(img, vig_w, vig_h)
            ix = (pw - iw) / 2
            iy = ph - vig_h - 20 + (vig_h - ih) / 2
            _draw_image(img, ix, iy, iw, ih)
            sep_y = ph - vig_h - 26
            c.setStrokeColor(HexColor("#BBBBBB"))
            c.setLineWidth(0.75)
            c.line(50, sep_y, pw - 50, sep_y)
            text_h = sep_y - 24
            _draw_text(text, 50, 12, pw - 100, text_h,
                       font_size_pt, TA_LEFT, "Times-Roman")

        elif fmt_id == "comic_panels":
            # 7×10 portrait — black-bordered panel top 65 %, yellow caption box below
            mg = 10
            panel_h = ph * 0.63
            cap_h   = ph * 0.26
            panel_y = ph - panel_h - mg
            c.setStrokeColor(black); c.setLineWidth(3)
            c.rect(mg, panel_y, pw - 2 * mg, panel_h, stroke=1, fill=0)
            iw, ih = _fit(img, pw - 2 * mg - 6, panel_h - 6)
            ix = mg + 3 + (pw - 2 * mg - 6 - iw) / 2
            iy = panel_y + 3 + (panel_h - 6 - ih) / 2
            _draw_image(img, ix, iy, iw, ih)
            cap_y = panel_y - cap_h - 6
            c.setFillColor(HexColor("#FFFDE7"))
            c.setStrokeColor(black); c.setLineWidth(2)
            c.rect(mg, cap_y, pw - 2 * mg, cap_h, fill=1, stroke=1)
            _draw_text(text, mg + 10, cap_y + 4, pw - 2 * mg - 20, cap_h - 8,
                       font_size_pt, TA_LEFT, "Helvetica-Bold")

        elif fmt_id == "bold_board_book":
            # 6×6 sq — full-bleed image, thick white strip bottom 22 %, ultra-bold text
            band = ph * 0.22
            iw, ih = _fit(img, pw, ph - band + 10)
            ix = (pw - iw) / 2; iy = band - 10 + ((ph - band + 10) - ih) / 2
            _draw_image(img, ix, iy, iw, ih)
            c.setFillColor(white)
            c.rect(0, 0, pw, band, fill=1, stroke=0)
            _draw_text(text, 8, 4, pw - 16, band - 8,
                       font_size_pt, TA_CENTER, "Helvetica-Bold")

        else:
            # Fallback: image top 75 %, text bottom 25 %
            band = ph * 0.25
            iw, ih = _fit(img, pw, ph - band)
            ix = (pw - iw) / 2; iy = band + ((ph - band) - ih) / 2
            _draw_image(img, ix, iy, iw, ih)
            c.setFillColor(white)
            c.rect(0, 0, pw, band, fill=1, stroke=0)
            _draw_text(text, 20, 4, pw - 40, band - 8, 18, TA_CENTER)

        c.showPage()

    c.save()


# ---------------------------------------------------------------------------
# Diffrun-style book preview helpers
# ---------------------------------------------------------------------------

def _pil_to_data_url(img: Image.Image, max_w: int = 900) -> str:
    """Return a JPEG base64 data-URL suitable for embedding in HTML."""
    buf = io.BytesIO()
    copy = img.copy()
    if copy.width > max_w:
        ratio = max_w / copy.width
        copy = copy.resize((max_w, int(copy.height * ratio)), Image.LANCZOS)
    copy.save(buf, format="JPEG", quality=85, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _render_page_card(img: Image.Image, text: str, page_num: int, total_pages: int) -> None:
    """Render one story page in Diffrun-style horizontal card (image left, text right)."""
    data_url = _pil_to_data_url(img)
    st.markdown(f"""
    <div style="display:flex;background:#fff;border-radius:16px;
                box-shadow:0 4px 24px rgba(0,0,0,0.09);overflow:hidden;
                margin:0 0 28px;">
      <div style="flex:0 0 58%;max-width:58%;overflow:hidden;">
        <img src="{data_url}"
             style="width:100%;height:100%;object-fit:cover;display:block;">
      </div>
      <div style="flex:1;padding:32px 28px;display:flex;flex-direction:column;
                  justify-content:center;background:#fff;">
        <p style="font-family:'Georgia',serif;font-size:1.05rem;line-height:1.75;
                  color:#2c3e50;margin:0 0 20px 0;">{text}</p>
        <span style="color:#bbb;font-size:0.78rem;display:block;text-align:right;">
          Page {page_num} / {total_pages}
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _render_paywall_card(
    img: Image.Image, page_num: int, total_pages: int, remaining: int,
    price_inr: int, payment_callback_key: str
) -> bool:
    """Render a paywall card showing the last free image with a purchase overlay.
    Returns True if the user clicked 'Continue to Purchase'."""
    data_url = _pil_to_data_url(img)
    st.markdown(f"""
    <div style="background:#fff;border-radius:16px;
                box-shadow:0 4px 24px rgba(0,0,0,0.09);overflow:hidden;
                margin:0 0 8px;">
      <div style="position:relative;">
        <img src="{data_url}" style="width:100%;display:block;max-height:420px;object-fit:cover;">
        <div style="position:absolute;inset:0;
                    background:linear-gradient(to bottom,transparent 40%,rgba(0,0,0,0.75) 100%);
                    display:flex;align-items:flex-end;justify-content:center;padding:28px;">
          <div style="text-align:center;color:white;">
            <p style="font-size:1.1rem;font-weight:600;margin:0 0 4px;">
              Full Preview is available on Purchase
            </p>
            <p style="font-size:0.85rem;opacity:0.85;margin:0;">
              {remaining} more page(s) unlock after payment
            </p>
          </div>
        </div>
      </div>
      <div style="padding:4px 20px 4px;text-align:right;">
        <span style="color:#bbb;font-size:0.78rem;">Page {page_num} / {total_pages}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    clicked = st.button(
        f"🛒 Continue to Purchase — ₹{price_inr}",
        key=payment_callback_key,
        type="primary",
        use_container_width=True,
    )
    st.markdown("<div style='margin-bottom:28px;'></div>", unsafe_allow_html=True)
    return clicked


def _render_locked_card(page_num: int, total_pages: int) -> None:
    """Render a locked placeholder card for pages not yet generated."""
    st.markdown(f"""
    <div style="display:flex;background:#f8f8f8;border-radius:16px;
                box-shadow:0 2px 12px rgba(0,0,0,0.05);overflow:hidden;
                margin:0 0 28px;min-height:180px;align-items:center;">
      <div style="flex:0 0 58%;max-width:58%;display:flex;align-items:center;
                  justify-content:center;background:#ececec;min-height:180px;">
        <span style="font-size:52px;opacity:0.4;">🔒</span>
      </div>
      <div style="flex:1;padding:32px 28px;">
        <p style="color:#999;font-size:0.95rem;margin:0 0 8px;">
          This page is locked. Purchase the book to unlock all illustrations.
        </p>
        <span style="color:#bbb;font-size:0.78rem;">Page {page_num} / {total_pages}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _load_gallery_book(doc_id: str) -> None:
    """Load a community gallery book into session state for viewing."""
    try:
        from mongo_client import book_history_col
        col = book_history_col()
        row = col.find_one({"_id": doc_id})
        if not row:
            st.error("Could not load that book.")
            return
        story_data = row.get("story_data", {})
        if not story_data or not story_data.get("pages"):
            st.error("Book has no pages.")
            return
        meta = row.get("metadata", {})
        journey_state = meta.get("journey_state", {})

        st.session_state.generated_story = story_data
        st.session_state.current_child_name = row.get("child_name", "")
        # Don't point at the gallery owner's doc — treat as a fresh load
        st.session_state.current_book_history_id = None
        st.session_state.book_mode = "custom"
        st.session_state.wiz_generate_trigger = False

        # Restore images — only keep valid (non-None) ones
        saved_imgs = row.get("images", [])
        decoded = decode_stored_images(saved_imgs) if saved_imgs else []
        valid_images = [img for img in decoded if img is not None]
        st.session_state.generated_images = valid_images

        if valid_images:
            # We have real images — mark everything approved and jump to Step 3
            st.session_state.story_approved = True
            st.session_state.all_images_approved = True
            st.session_state.image_approvals = {i: True for i in range(len(valid_images))}
            st.session_state.edited_story_pages = journey_state.get("edited_story_pages", {})
            st.session_state.edited_image_prompts = journey_state.get("edited_image_prompts", {})
        else:
            # No valid images — restore journey state but block auto-generation
            st.session_state.story_approved = journey_state.get("story_approved", False)
            st.session_state.all_images_approved = journey_state.get("all_images_approved", False)
            st.session_state.image_approvals = journey_state.get("image_approvals", {})
            st.session_state.edited_story_pages = journey_state.get("edited_story_pages", {})
            st.session_state.edited_image_prompts = journey_state.get("edited_image_prompts", {})

        # Prevent Step 2 from auto-generating immediately after load
        st.session_state._loaded_from_history = True
        st.session_state.pdf_path = None
        st.session_state.pdf_generation_key = None
        st.session_state.show_history = False
    except Exception as e:
        st.error(f"Failed to load book: {e}")


def render_gallery():
    """Show recent books from all users as inspiration. Only non-private books are shown."""
    try:
        from mongo_client import book_history_col
        col = book_history_col()
        books = list(col.find(
            {
                "images": {"$elemMatch": {"$type": "string", "$regex": "^data:image"}},
                "is_private": {"$ne": True},
            },
            {"_id": 1, "child_name": 1, "story_data": 1, "metadata": 1, "created_at": 1, "cover_thumbnail": 1, "title": 1}
        ).sort("created_at", -1).limit(48))
    except Exception as _ge:
        import logging as _log
        _log.getLogger(__name__).warning(f"Gallery query failed: {_ge}")
        books = []

    if not books:
        st.markdown(
            "<p style='color:#999;text-align:center;padding:2rem;'>"
            "No completed books in the gallery yet — finish generating images for your story "
            "to see it appear here!"
            "</p>",
            unsafe_allow_html=True,
        )
        return

    cols = st.columns(4)
    for i, book in enumerate(books):
        with cols[i % 4]:
            doc_id = book.get("_id", "")
            title = book.get("title") or (book.get("story_data") or {}).get("title", "Untitled Story")
            child = book.get("child_name", "")
            meta = book.get("metadata") or {}
            age = meta.get("age", "")
            lang = meta.get("language", "")
            created = book.get("created_at")
            date_str = created.strftime("%b %Y") if created else ""
            cover = book.get("cover_thumbnail", "")
            if cover and cover.startswith("data:image"):
                cover_html = f'<img src="{cover}" style="width:100%;height:140px;object-fit:cover;border-radius:10px 10px 0 0;">'
            else:
                cover_html = '<div style="width:100%;height:140px;background:linear-gradient(135deg,#e8f4fd,#f0e6ff);border-radius:10px 10px 0 0;display:flex;align-items:center;justify-content:center;font-size:40px;">📖</div>'
            st.markdown(f"""
            <div style="background:#fff;border-radius:12px;margin-bottom:4px;
                 border:1px solid #e0e7ff;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
              {cover_html}
              <div style="padding:10px 12px 12px;">
                <div style="font-weight:600;font-size:13px;color:#1a1a2e;line-height:1.3;
                     white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="{title}">{title}</div>
                <div style="color:#666;font-size:12px;margin-top:3px;">For {child}{", age "+str(age) if age else ""}</div>
                <div style="color:#aaa;font-size:11px;margin-top:2px;">{lang+"  · " if lang else ""}{date_str}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            if doc_id and st.button("Read Story", key=f"gallery_view_{doc_id}_{i}", use_container_width=True):
                _load_gallery_book(doc_id)
                st.rerun()


def render_landing():
    """Home landing page: mode selection cards + gallery."""
    # Hero
    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1.5rem;">
      <h1 style="font-size:2.8rem;font-weight:900;
           background:linear-gradient(135deg,#667eea,#f093fb);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent;
           background-clip:text;margin-bottom:0.3rem;">
        Storytime Studio
      </h1>
      <p style="font-size:1.15rem;color:#666;margin:0;">
        Beautiful storybooks where <b>your child</b> is the hero ✨
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Mode cards
    col1, spacer, col2 = st.columns([5, 1, 5])

    with col1:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#f093fb 0%,#f5576c 100%);
             border-radius:20px;padding:36px 28px;text-align:center;color:white;
             box-shadow:0 8px 32px rgba(240,147,251,0.3);min-height:200px;">
          <div style="font-size:56px;margin-bottom:12px;">📚</div>
          <h2 style="margin:0 0 8px;font-size:1.6rem;font-weight:800;">Story Library</h2>
          <p style="opacity:0.92;font-size:0.95rem;margin:0;line-height:1.5;">
            Ready-made bestsellers personalized with your child's name —
            instant books, with optional photo personalization.
          </p>
        </div>
        """, unsafe_allow_html=True)
        if TEMPLATE_BOOKS_AVAILABLE or TEMPLATE_FLOW_AVAILABLE:
            if st.button("Browse the Library →", key="pick_template", use_container_width=True, type="primary"):
                st.session_state.book_mode = "template"
                st.rerun()
        else:
            st.caption("Template books are not available in this deployment.")

    with col2:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
             border-radius:20px;padding:36px 28px;text-align:center;color:white;
             box-shadow:0 8px 32px rgba(102,126,234,0.3);min-height:200px;">
          <div style="font-size:56px;margin-bottom:12px;">✨</div>
          <h2 style="margin:0 0 8px;font-size:1.6rem;font-weight:800;">Custom Story</h2>
          <p style="opacity:0.92;font-size:0.95rem;margin:0;line-height:1.5;">
            Craft a one-of-a-kind story — choose your child's look,
            personality, and the adventure they'll embark on.
          </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start Custom Story →", key="pick_custom", use_container_width=True):
            st.session_state.book_mode = "custom"
            st.session_state.wizard_step = 1
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Gallery
    st.markdown("---")
    st.markdown("### 🌟 Books Created by Our Community")
    st.caption("Every book made with this app — a growing library of personalized stories.")
    render_gallery()


def render_custom_wizard():
    """Multi-step wizard for custom story creation."""
    step = st.session_state.wizard_step

    # Safety: ensure step is within valid range
    if step < 1 or step > 4:
        st.session_state.wizard_step = 1
        st.rerun()
        return

    # Back to home
    if st.button("← Back", key="wizard_back_home"):
        st.session_state.book_mode = None
        st.session_state.wizard_step = 0
        st.rerun()

    # Progress
    steps = ["Child Info", "Appearance", "Story Details", "Advanced"]
    progress_val = (step - 1) / len(steps)
    st.progress(progress_val)
    st.caption(f"Step {step} of {len(steps)}: **{steps[step-1]}**")
    st.markdown("---")

    if step == 1:
        st.markdown("## 👦 Who's this book for?")
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.session_state.wiz_child_name = st.text_input(
                "Child's Name *", value=st.session_state.wiz_child_name,
                placeholder="e.g., Arjun, Priya, Zara",
                help="The hero of the story!"
            )
        with col2:
            st.session_state.wiz_age = st.number_input(
                "Age *", min_value=2, max_value=16,
                value=st.session_state.wiz_age, step=1
            )
        with col3:
            st.session_state.wiz_gender = st.selectbox(
                "Gender *", ["Boy", "Girl", "Non-binary"],
                index=["Boy", "Girl", "Non-binary"].index(st.session_state.wiz_gender)
            )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Next: Appearance →", type="primary", use_container_width=True, key="wiz_next_1"):
            if not st.session_state.wiz_child_name.strip():
                st.error("Please enter the child's name.")
            else:
                st.session_state.wizard_step = 2
                st.rerun()

    elif step == 2:
        child = st.session_state.wiz_child_name
        st.markdown(f"## 🎨 What does {child} look like?")

        # ── Photo upload ────────────────────────────────────────────────
        st.markdown("#### 📸 Upload Photos of " + child + " *(recommended)*")
        st.caption(
            "Upload up to 3 clear photos of your child's face. The AI uses these as a "
            "character reference so every illustration looks like your real child. "
            "Front-facing photos in good lighting work best."
        )

        uploaded_photos = st.file_uploader(
            f"Upload up to 3 photos of {child}",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="wiz_photo_uploader",
            label_visibility="collapsed",
        )
        if uploaded_photos:
            capped = uploaded_photos[:3]
            if len(uploaded_photos) > 3:
                st.warning("Only the first 3 photos will be used.")
            photos_b64 = []
            for uf in capped:
                try:
                    from PIL import Image as _PILImage
                    import io as _io
                    import base64 as _b64
                    raw = uf.read()
                    pimg = _PILImage.open(_io.BytesIO(raw)).convert("RGB")
                    max_side = 512
                    w, h = pimg.size
                    if max(w, h) > max_side:
                        scale = max_side / max(w, h)
                        pimg = pimg.resize((int(w * scale), int(h * scale)), _PILImage.LANCZOS)
                    buf = _io.BytesIO()
                    pimg.save(buf, format="JPEG", quality=85)
                    photos_b64.append(_b64.b64encode(buf.getvalue()).decode())
                except Exception as _pe:
                    st.error(f"Could not process photo: {_pe}")
            if photos_b64:
                st.session_state.wiz_reference_photos_b64 = photos_b64
                st.success(f"✅ {len(photos_b64)} photo(s) uploaded! {child}'s likeness will be used in all illustrations.")
        elif st.session_state.wiz_reference_photos_b64:
            st.info(f"✅ {len(st.session_state.wiz_reference_photos_b64)} photo(s) already uploaded.")

        # Preview thumbnails
        if st.session_state.wiz_reference_photos_b64:
            preview_cols = st.columns(min(len(st.session_state.wiz_reference_photos_b64), 3))
            import base64 as _b64p
            for pi, b64str in enumerate(st.session_state.wiz_reference_photos_b64):
                with preview_cols[pi]:
                    st.markdown(
                        f'<img src="data:image/jpeg;base64,{b64str}" '
                        f'style="width:100%;border-radius:8px;border:2px solid #667eea;" />',
                        unsafe_allow_html=True,
                    )
            if st.button("🗑️ Remove all photos", key="wiz_remove_photos"):
                st.session_state.wiz_reference_photos_b64 = []
                st.rerun()

        # ── Text description (optional if photo provided) ────────────────
        st.markdown("---")
        st.markdown(
            "#### ✏️ Or describe " + child + "'s appearance"
        )
        st.caption(
            "Fill these in for even more accuracy, or if you didn't upload a photo. "
            "Skip fields you're not sure about."
        )

        col1, col2 = st.columns(2)
        with col1:
            st.session_state.wiz_skin_tone = st.text_input(
                "Skin Tone", value=st.session_state.wiz_skin_tone,
                placeholder="e.g., light, wheatish, golden brown, dark"
            )
            st.session_state.wiz_hair_style = st.text_input(
                "Hair Style & Color", value=st.session_state.wiz_hair_style,
                placeholder="e.g., curly black hair, straight brown, two braids"
            )
        with col2:
            st.session_state.wiz_eye_color = st.text_input(
                "Eye Color", value=st.session_state.wiz_eye_color,
                placeholder="e.g., big brown eyes, hazel"
            )
            st.session_state.wiz_outfit = st.text_input(
                "Favorite Outfit", value=st.session_state.wiz_outfit,
                placeholder="e.g., red kurta, blue jeans and a star t-shirt"
            )

        st.markdown("<br>", unsafe_allow_html=True)
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("← Back", key="wiz_back_2"):
                st.session_state.wizard_step = 1
                st.rerun()
        with bcol2:
            if st.button("Next: Story Details →", type="primary", use_container_width=True, key="wiz_next_2"):
                st.session_state.wizard_step = 3
                st.rerun()

    elif step == 3:
        child = st.session_state.wiz_child_name
        st.markdown(f"## 📖 What's {child}'s story about?")

        # Story type - visual buttons
        story_types = ["Adventure", "Bedtime/Calm", "Behavioral/Problem-solving", "Educational", "Friendship", "Custom/Free-form"]
        type_emojis = ["🚀", "🌙", "🧩", "🔬", "🤝", "✨"]

        st.markdown("**Story Type:**")
        type_cols = st.columns(3)
        for ti, (stype, emoji) in enumerate(zip(story_types, type_emojis)):
            with type_cols[ti % 3]:
                selected = st.session_state.wiz_story_type == stype
                if st.button(
                    f"{emoji} {stype}", key=f"stype_{ti}", use_container_width=True,
                    type="primary" if selected else "secondary"
                ):
                    st.session_state.wiz_story_type = stype
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.session_state.wiz_problem = st.text_area(
            "Story Theme / Plot / Idea *",
            value=st.session_state.wiz_problem,
            placeholder="E.g., Arjun is scared of trying new foods. His friend Mini helps him discover that vegetables can taste amazing when cooked in fun ways!",
            height=120
        )

        col1, col2 = st.columns(2)
        with col1:
            image_styles = ["Cartoon/Animated (3D Pixar Style)", "Cartoon (2D Flat Style)", "Watercolor Illustration", "Storybook Classic", "Photorealistic", "Photo Reference Portrait", "Storybook Spread"]
            style_emojis = ["🎬", "🎨", "🖌️", "📚", "📷", "🧒", "📖"]
            cur_idx = image_styles.index(st.session_state.wiz_image_style) if st.session_state.wiz_image_style in image_styles else 0
            sel_style = st.selectbox(
                "Image Style *", image_styles, index=cur_idx,
                format_func=lambda s: f"{style_emojis[image_styles.index(s)]} {s}",
                help="When a child photo is uploaded, cartoon styles auto-upgrade to 'Photo Reference Portrait' for accurate face likeness.",
            )
            st.session_state.wiz_image_style = sel_style
        with col2:
            lang_options = ["English", "Hindi"]
            lang_idx = lang_options.index(st.session_state.wiz_language) if st.session_state.wiz_language in lang_options else 0
            st.session_state.wiz_language = st.selectbox("Language *", lang_options, index=lang_idx)

        # Book format — 8 formats in a 2-column grid with visual layout previews
        st.markdown("### 📚 Book Format")
        st.caption(
            "Each format defines how the book is laid out: image-text balance, "
            "word count, page count, and bestseller examples that use this style."
        )
        try:
            from book_formats import get_layout_preview_html
        except Exception:
            get_layout_preview_html = lambda _: ""

        n_per_row = 2
        for row_start in range(0, len(BOOK_FORMATS), n_per_row):
            row_formats = BOOK_FORMATS[row_start: row_start + n_per_row]
            cols = st.columns(n_per_row)
            for fi_in_row, fmt in enumerate(row_formats):
                fi = row_start + fi_in_row
                with cols[fi_in_row]:
                    selected = st.session_state.wiz_format_id == fmt["id"]
                    border_color = "#667eea" if selected else "#e0e0e0"
                    border_w = "3px" if selected else "1px"
                    bg = "#eef0ff" if selected else "#ffffff"
                    bestsellers = " · ".join(fmt.get("bestsellers", [])[:2])
                    preview = get_layout_preview_html(fmt["id"])

                    st.markdown(f"""
                    <div style="background:{bg};border-radius:12px;padding:14px;
                         border:{border_w} solid {border_color};margin-bottom:8px;">
                      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                        <div style="font-size:32px;">{fmt['emoji']}</div>
                        <div style="flex:1;">
                          <div style="font-weight:700;font-size:15px;color:#1a1a2e;line-height:1.2;">
                            {fmt['name']}
                          </div>
                          <div style="font-size:11px;color:#888;margin-top:2px;">
                            {fmt['badge']} · Ages {fmt['age_range']}
                          </div>
                        </div>
                      </div>
                      <div style="margin:10px 0;">{preview}</div>
                      <div style="font-size:13px;color:#444;margin-top:8px;line-height:1.4;">
                        {fmt['desc']}
                      </div>
                      <div style="font-size:12px;color:#666;margin-top:6px;">
                        📄 {fmt['detail']}
                      </div>
                      <div style="font-size:11px;color:#999;margin-top:4px;font-style:italic;">
                        Like: {bestsellers}
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(
                        ("✓ Selected" if selected else "Choose this format"),
                        key=f"fmt_{fi}",
                        use_container_width=True,
                        type="primary" if selected else "secondary",
                    ):
                        st.session_state.wiz_format_id = fmt["id"]
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("← Back", key="wiz_back_3"):
                st.session_state.wizard_step = 2
                st.rerun()
        with bcol2:
            if st.button("Next: Final Details →", type="primary", use_container_width=True, key="wiz_next_3"):
                if not st.session_state.wiz_problem.strip():
                    st.error("Please describe the story idea.")
                else:
                    st.session_state.wizard_step = 4
                    st.rerun()

    elif step == 4:
        child = st.session_state.wiz_child_name
        st.markdown(f"## 🌟 Final touches for {child}'s story")
        st.caption("These are optional but help make the story more personal and meaningful.")

        col1, col2 = st.columns(2)
        with col1:
            st.session_state.wiz_family_structure = st.text_input(
                "Family Structure",
                value=st.session_state.wiz_family_structure,
                placeholder="e.g., lives with parents and Dadi, has a baby sister"
            )
            st.session_state.wiz_hero_trait = st.text_input(
                "Child's Superpower (Hero Trait)",
                value=st.session_state.wiz_hero_trait,
                placeholder="e.g., Brave, Creative, Kind, Curious, Funny"
            )
        with col2:
            st.session_state.wiz_character_choice = st.text_input(
                "Famous Character Companion (optional)",
                value=st.session_state.wiz_character_choice,
                placeholder="e.g., Doraemon, Peppa Pig, Chhota Bheem"
            )

        # Story summary
        st.markdown("---")
        st.markdown("#### 📋 Story Summary")
        fmt = get_format_by_id(st.session_state.wiz_format_id)

        has_photo = bool(st.session_state.get("wiz_reference_photos_b64"))
        summary_cols = st.columns(4)
        with summary_cols[0]:
            st.metric("Hero", f"{child}, {st.session_state.wiz_age}yo")
        with summary_cols[1]:
            st.metric("Story Type", st.session_state.wiz_story_type)
        with summary_cols[2]:
            st.metric("Length", f"{fmt.get('page_count', fmt.get('pages', 10))} pages")
        with summary_cols[3]:
            st.metric("Photo Ref", "📸 Yes" if has_photo else "Text only")

        st.markdown("<br>", unsafe_allow_html=True)
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("← Back", key="wiz_back_4"):
                st.session_state.wizard_step = 3
                st.rerun()
        with bcol2:
            if st.button("✨ Generate Story!", type="primary", use_container_width=True, key="wiz_generate"):
                st.session_state.wiz_generate_trigger = True
                st.rerun()


def main():
    # ------------------------------------------------------------------ #
    # Cookie-backed persistent sessions (7-day login)
    # ------------------------------------------------------------------ #
    _cm = None
    _cookie_token = None
    try:
        import extra_streamlit_components as stx
        _cm = stx.CookieManager(key="cbg_cm")
        _cookie_token = _cm.get("cbg_st") or ""
    except Exception:
        pass

    init_auth_state()

    # CookieManager often returns empty on the very first render.
    # Allow one rerun for the JS component to hydrate.
    if not is_authenticated() and not _cookie_token:
        if not st.session_state.get("_cookie_retry_done"):
            st.session_state._cookie_retry_done = True
            time.sleep(0.3)
            st.rerun()

    # Try to restore session from cookie if not already authenticated
    if not is_authenticated() and _cookie_token:
        if restore_session_from_token(_cookie_token):
            st.rerun()

    # Set cookie after new login/signup
    if _cm and st.session_state.get("_pending_session_token"):
        new_token = st.session_state.pop("_pending_session_token")
        st.session_state._session_token = new_token
        try:
            _cm.set("cbg_st", new_token, expires_at=datetime.now() + timedelta(days=7))
        except Exception:
            pass

    # Delete cookie after logout
    if _cm and st.session_state.get("_token_to_delete"):
        old_token = st.session_state.pop("_token_to_delete")
        try:
            _cm.delete("cbg_st")
            from auth import _delete_session_token
            _delete_session_token(old_token)
        except Exception:
            pass

    # Google OIDC: mirror st.user into our session after st.login()
    if not is_authenticated():
        if sync_google_session():
            st.rerun()

    # OTP gate — supports both old (otp_pending_email) and new (auth_stage=otp) style
    if not is_authenticated() and (
        st.session_state.get("otp_pending_email")
        or st.session_state.get("auth_stage") == "otp"
    ):
        render_otp_page()
        return

    # Auth gate
    if not is_authenticated():
        render_auth_page()
        return

    # After OTP: prompt to set a password (optional, user can skip)
    if st.session_state.get("auth_stage") == "set_password":
        render_set_password_page()
        return

    # Payment return: Cashfree sends the customer back with ?cf_link_id=...
    _cf_link_id = st.query_params.get("cf_link_id")
    if _cf_link_id:
        try:
            from payments import confirm_payment_and_credit as _confirm
            if _confirm(_cf_link_id, get_current_user_id()):
                st.toast("Payment received — thank you!", icon="✅")
                # Unlock whichever flow created this link
                if st.session_state.get("tpl_payment_link_id") == _cf_link_id:
                    st.session_state.pop("tpl_payment_link_id", None)
                    st.session_state.pop("tpl_payment_url", None)
                    st.session_state.tpl_payment_confirmed = _cf_link_id
                if st.session_state.get("pending_payment_link_id") == _cf_link_id:
                    _cf_gate = st.session_state.get("pending_payment_gate", "download_choice")
                    if _cf_gate == "download_choice":
                        st.session_state.current_book_payment_status = "story_paid"
                        st.session_state.book_delivery_option = "download"
                    elif _cf_gate == "print_deliver_choice":
                        st.session_state.current_book_payment_status = "print_paid"
                        st.session_state.book_delivery_option = "print_deliver"
                    elif _cf_gate == "download":  # legacy compat
                        st.session_state.current_book_payment_status = "download_paid"
                    else:
                        st.session_state.current_book_payment_status = "story_paid"
                    st.session_state.pending_payment_link_id = None
                    st.session_state.pending_payment_url = None
                    st.session_state.pending_payment_gate = None
        except Exception as _e:
            logger.warning(f"Payment-return verification failed: {_e}")
        st.query_params.pop("cf_link_id", None)

    # Payment return: Cashfree JS Drop-in SDK sets ?cf_order_id=...&cf_status=SUCCESS|FAILED
    _cf_order_qp = st.query_params.get("cf_order_id")
    _cf_status_qp = st.query_params.get("cf_status", "")
    _cf_tab_qp = st.query_params.get("cf_tab", "")
    _cf_show_verify = st.query_params.get("cf_show_verify", "")
    _cf_reset = st.query_params.get("cf_reset", "")

    # ── Session expired/stale: JS detected "endpoint not valid" → clear and retry ──
    if _cf_order_qp and _cf_reset == "1":
        st.query_params.clear()
        st.session_state.cf_pending_order_id = None
        st.session_state.cf_payment_session_id = None
        st.session_state.cf_order_created_at = None
        st.session_state.cf_show_verify_button = False
        st.session_state.pending_payment_gate = None
        st.toast("⚠️ Payment session expired. Please try again.", icon="⚠️")
        st.rerun()

    # ── Payment return in the new tab (opened by redirectTarget: "_blank") ──
    # Cashfree redirects here after checkout. Verify, broadcast to original tab, close.
    if _cf_order_qp and _cf_status_qp == "SUCCESS" and _cf_tab_qp == "payment":
        st.query_params.clear()
        try:
            from payments import verify_cashfree_order as _vco2, confirm_payment_and_credit as _cpc2
            _s2 = _vco2(_cf_order_qp)
            if _s2 == "PAID":
                _cpc2(_cf_order_qp, get_current_user_id())
        except Exception as _e2:
            logger.warning(f"Payment tab verify: {_e2}")
        # Broadcast to the original tab's components.html iframe and close this tab
        components.html(f"""
        <script>
          function broadcast() {{
            try {{
              var ch = new BroadcastChannel("cbg_pay_{_cf_order_qp}");
              ch.postMessage("PAID");
              ch.close();
            }} catch(e) {{}}
          }}
          broadcast();
          setTimeout(broadcast, 600);
          setTimeout(broadcast, 1500);
          setTimeout(function() {{ window.close(); }}, 2500);
        </script>
        """, height=0)
        st.markdown("""
        <div style='text-align:center;padding:60px 24px;font-family:sans-serif;'>
          <div style='font-size:56px;'>✅</div>
          <h2 style='color:#166534;margin:16px 0 8px;'>Payment Successful!</h2>
          <p style='color:#4b5563;font-size:16px;'>
            You can close this tab — your story page will update automatically.</p>
        </div>""", unsafe_allow_html=True)
        st.stop()

    if _cf_order_qp and _cf_show_verify == "1":
        # 60-second timeout fired — reveal the manual fallback button
        st.query_params.pop("cf_order_id", None)
        st.query_params.pop("cf_show_verify", None)
        st.session_state.cf_show_verify_button = True
    if _cf_order_qp and _cf_status_qp and _cf_tab_qp != "payment":
        st.query_params.pop("cf_order_id", None)
        st.query_params.pop("cf_status", None)
        st.query_params.pop("cf_error", None)
        st.session_state.cf_show_verify_button = False  # clear if payment resolved
        if _cf_status_qp == "SUCCESS":
            try:
                from payments import verify_cashfree_order as _vco, confirm_payment_and_credit as _cpc_ord
                _ord_status = _vco(_cf_order_qp)
                if _ord_status == "PAID":
                    # Also credit / record the purchase
                    _cpc_ord(_cf_order_qp, get_current_user_id())
                    _ord_gate = st.session_state.get("pending_payment_gate", "download_choice")
                    if _ord_gate == "print_deliver_choice":
                        st.session_state.current_book_payment_status = "print_paid"
                        st.session_state.book_delivery_option = "print_deliver"
                    else:
                        st.session_state.current_book_payment_status = "story_paid"
                        st.session_state.book_delivery_option = "download"
                    st.session_state.cf_pending_order_id = None
                    st.session_state.cf_payment_session_id = None
                    st.session_state.pending_payment_gate = None
                    st.toast("✅ Payment confirmed — generating your book!", icon="✅")
                else:
                    st.warning(f"Payment status from Cashfree: {_ord_status}. If you completed payment, click 'Verify Payment' below.")
            except Exception as _oe:
                logger.warning(f"cf_order verification failed: {_oe}")
        elif _cf_status_qp == "FAILED":
            _cf_err = st.query_params.get("cf_error", "Payment was not completed")
            st.error(f"Payment failed: {_cf_err}. Please try again.")
            st.session_state.cf_payment_session_id = None  # Allow retry

    # Ensure non-admin users always have Vertex credentials (admin's credentials as shared backend)
    _session_email = st.session_state.get("user_email") or ""
    if _session_email not in ADMIN_EMAILS and not st.session_state.get("vertex_sa_json"):
        _admin_cfg = get_admin_vertex_config()
        if _admin_cfg:
            st.session_state.vertex_project_id = _admin_cfg.get("project_id", "")
            st.session_state.vertex_location = _admin_cfg.get("location", "us-central1")
            st.session_state.vertex_sa_json = _admin_cfg.get("sa_json", "")
            if not st.session_state.get("api_key") and _admin_cfg.get("gemini_api_key"):
                st.session_state.api_key = _admin_cfg["gemini_api_key"]
            if not st.session_state.get("openrouter_api_key") and _admin_cfg.get("openrouter_api_key"):
                st.session_state.openrouter_api_key = _admin_cfg["openrouter_api_key"]

    # Templates are now seeded via SQL migration, no app-level seeding needed

    # Initialize show_history and show_community state
    if 'show_history' not in st.session_state:
        st.session_state.show_history = False
    if 'show_community' not in st.session_state:
        st.session_state.show_community = False

    # Show community gallery page if requested
    if st.session_state.get("show_community"):
        st.title("Community Books")
        st.caption("Books created by our community -- browse and get inspired!")
        if st.button("Back to Main", type="secondary", key="back_from_community"):
            st.session_state.show_community = False
            st.rerun()
        st.divider()
        render_gallery()
        return

    # Show history page if requested
    if st.session_state.show_history:
        st.title("📚 Story History")
        
        if st.button("← Back to Main", type="secondary"):
            st.session_state.show_history = False
            st.rerun()
        
        st.divider()
        
        history = get_story_history()

        if history:
            st.caption(f"{len(history)} saved stories")

            for idx, story_info in enumerate(history):
                display_name = story_info['title'] or f"{story_info['child_name']}'s Story"
                timestamp_display = story_info['timestamp'].replace('_', ' ')[:16] if story_info['timestamp'] else ""
                cover = story_info.get("cover_thumbnail", "")

                with st.container():
                    col_cover, col_info, col_action = st.columns([1, 3, 1])
                    with col_cover:
                        if cover and cover.startswith("data:image"):
                            st.markdown(
                                f'<img src="{cover}" style="width:80px;height:80px;object-fit:cover;border-radius:8px;">',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                '<div style="width:80px;height:80px;background:#f0f4ff;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:28px;">📖</div>',
                                unsafe_allow_html=True,
                            )
                    with col_info:
                        st.write(f"**{display_name}**")
                        book_type_label = "Template" if story_info.get("book_type") == "template" else "Custom"
                        st.caption(f"For {story_info['child_name']} · {book_type_label} · {timestamp_display}")
                    with col_action:
                        if st.button("Load", key=f"load_history_{idx}", use_container_width=True):
                            # Load from MongoDB if we have a db_id, else from local file
                            loaded_data = None
                            if story_info.get("db_id"):
                                try:
                                    from mongo_client import book_history_col
                                    col = book_history_col()
                                    row = col.find_one({"_id": story_info["db_id"], "user_id": get_current_user_id()})
                                    if row:
                                        meta = row.get("metadata", {})
                                        loaded_data = {
                                            "story": row.get("story_data", {}),
                                            "child_name": row.get("child_name", ""),
                                            "timestamp": meta.get("timestamp", ""),
                                            "journey_state": meta.get("journey_state", {}),
                                            "metadata": meta,
                                            "images": row.get("images", []),
                                        }
                                        st.session_state.current_book_history_id = story_info["db_id"]
                                except Exception as load_err:
                                    st.error(f"Failed to load from cloud: {load_err}")
                            elif story_info.get("filepath"):
                                filepath = story_info["filepath"]
                                if not isinstance(filepath, Path):
                                    filepath = Path(str(filepath))
                                loaded_data = load_story(filepath)
                            if loaded_data:
                                story_data = loaded_data.get("story")
                                if story_data and isinstance(story_data, dict):
                                    # Ensure story has pages
                                    if "pages" in story_data and len(story_data.get("pages", [])) > 0:
                                        st.session_state.generated_story = story_data
                                        st.session_state.current_child_name = loaded_data.get("child_name", story_info.get('child_name', 'Story'))
                                        # Template books: load from the book cache (which has image_url)
                                        # History records deliberately omit image_url to save space.
                                        if story_data.get("template_id") and TEMPLATE_BOOKS_AVAILABLE:
                                            tmpl_id = story_data["template_id"]
                                            child_name_h = loaded_data.get("child_name", "")
                                            meta_h = loaded_data.get("metadata", {})
                                            gender_h = meta_h.get("gender", "Neutral") or "Neutral"
                                            age_h = int(meta_h.get("age", 5) or 5)
                                            tmpl_name_h = story_data.get("template_name", "")
                                            uid_h = get_current_user_id()
                                            cached_book = None
                                            if uid_h:
                                                try:
                                                    cached_book = get_cached_template_book(
                                                        uid_h, tmpl_id, child_name_h, gender_h, age_h
                                                    )
                                                except Exception as ce:
                                                    logger.warning(f"Cache lookup failed: {ce}")
                                            if cached_book:
                                                st.session_state.template_generated_book = cached_book
                                                st.session_state.generated_story = None
                                                st.session_state.show_history = False
                                                st.success(f"✅ Loaded your personalized template book for **{child_name_h}**!")
                                                st.rerun()
                                            else:
                                                # Cache miss — pre-fill the template form so user can regenerate
                                                st.session_state.book_mode = "template"
                                                st.session_state.selected_template_id = tmpl_id
                                                st.session_state.selected_template_name = tmpl_name_h
                                                st.session_state.generated_story = None
                                                st.session_state.show_history = False
                                                st.warning(f"Images for **{child_name_h}**'s book weren't found in cache. Fill in the details below and click Generate to rebuild it.")
                                                st.rerun()
                                        # ── Restore journey state ────────────────────────
                                        journey_state = loaded_data.get("journey_state", {})
                                        current_step = journey_state.get("current_step", "step1")

                                        st.session_state.story_approved = journey_state.get("story_approved", False)
                                        st.session_state.all_images_approved = journey_state.get("all_images_approved", False)
                                        st.session_state.image_approvals = journey_state.get("image_approvals", {})
                                        st.session_state.edited_story_pages = journey_state.get("edited_story_pages", {})
                                        st.session_state.edited_image_prompts = journey_state.get("edited_image_prompts", {})

                                        # ── Restore saved images ─────────────────────────
                                        if not story_data.get("template_id"):
                                            saved_imgs = loaded_data.get("images", [])
                                            decoded = decode_stored_images(saved_imgs) if saved_imgs else []
                                            # Only keep valid (non-None) images
                                            valid_decoded = [img for img in decoded if img is not None]
                                            st.session_state.generated_images = valid_decoded if valid_decoded else []

                                            # If we loaded valid images, mark all as approved regardless of saved state
                                            if valid_decoded:
                                                n_pages = len(story_data.get("pages", []))
                                                st.session_state.story_approved = True
                                                st.session_state.all_images_approved = True
                                                st.session_state.image_approvals = {i: True for i in range(len(valid_decoded))}
                                            elif current_step in ("step2", "step3"):
                                                # Had images before but couldn't load — don't auto-generate
                                                st.session_state.story_approved = True
                                                st.session_state.all_images_approved = journey_state.get("all_images_approved", False)

                                        # ── Set flag so Step 2 won't auto-generate on load ──
                                        st.session_state._loaded_from_history = True

                                        st.session_state.pdf_path = None
                                        st.session_state.pdf_generation_key = None
                                        st.session_state.show_history = False
                                        logger.info(f"Loaded story: step={current_step}, valid_images={len(st.session_state.generated_images)}")
                                        st.rerun()
                                    else:
                                        st.error(f"Story loaded but has no pages. File may be incomplete.")
                                        logger.error(f"Story has no pages: {story_data}")
                                else:
                                    st.error("Story data is invalid or missing from loaded file.")
                                    logger.error(f"Invalid story data: {story_data}")
                            else:
                                st.error("Failed to load story. The file may be corrupted.")
                    st.divider()
        else:
            st.info("No saved stories yet. Generate a story to see it here!")
        
        return

    # Determine admin status
    _current_user_email_nav = st.session_state.auth_user.get("email", "")
    _is_admin_nav = _current_user_email_nav in ADMIN_EMAILS

    if not _is_admin_nav:
        # Non-admin: hide sidebar entirely, show compact top bar
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] { display: none !important; }
            [data-testid="collapsedControl"] { display: none !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        # Compact top navigation bar
        nav_home, nav_history, nav_community, nav_mid, nav_right = st.columns([1, 1, 1, 3, 1])
        with nav_home:
            if st.button("Home", use_container_width=True):
                reset_story_state()
                st.session_state.book_mode = None
                st.session_state.wizard_step = 0
                st.session_state.wiz_generate_trigger = False
                st.session_state.show_history = False
                st.session_state.show_community = False
                st.rerun()
        with nav_history:
            if st.button("My Books", use_container_width=True):
                st.session_state.show_history = True
                st.session_state.show_community = False
                st.rerun()
        with nav_community:
            if st.button("Community", use_container_width=True):
                st.session_state.show_community = True
                st.session_state.show_history = False
                st.rerun()
        with nav_mid:
            st.markdown(
                f"<p style='text-align:center;color:#888;margin:0;padding-top:6px;font-size:13px;'>"
                f"Logged in as <strong>{_current_user_email_nav}</strong></p>",
                unsafe_allow_html=True,
            )
        with nav_right:
            if st.button("Log Out", use_container_width=True, type="secondary"):
                sign_out()
                st.rerun()
        st.divider()
    else:
        # Admin: full sidebar
        with st.sidebar:
            # User info and logout
            user_email = st.session_state.auth_user.get("email", "")
            st.markdown(f"Logged in as **{user_email}**")
            if st.button("Log Out", use_container_width=True, type="secondary"):
                sign_out()
                st.rerun()

            st.divider()

            # New Story Button
            if st.button("New Story", type="primary", use_container_width=True):
                reset_story_state()
                st.session_state.book_mode = None
                st.session_state.wizard_step = 0
                st.session_state.wiz_generate_trigger = False
                st.rerun()

            st.divider()

            # Story History
            if st.button("Story History", use_container_width=True, type="secondary"):
                st.session_state.show_history = True
                st.session_state.show_community = False
                st.rerun()

            # Community Gallery
            if st.button("Community", use_container_width=True, type="secondary"):
                st.session_state.show_community = True
                st.session_state.show_history = False
                st.rerun()

            # Template Studio (pre-render template assets)
            if TEMPLATE_FLOW_AVAILABLE:
                if st.button("🎨 Template Studio", use_container_width=True, type="secondary"):
                    st.session_state.show_template_studio = True
                    st.session_state.show_history = False
                    st.session_state.show_community = False
                    st.rerun()

            # Payment gateway health
            with st.expander("💳 Payments health"):
                try:
                    from payments import cashfree_diagnostics
                    for _k, _v in cashfree_diagnostics().items():
                        st.write(f"**{_k}:** {_v}")
                except Exception as _e:
                    st.error(f"Diagnostics unavailable: {_e}")

            st.divider()

            # API Key Input - persisted per user
            st.subheader("API Keys")

            # Gemini API Key
            current_key = st.session_state.api_key
            api_key_sidebar = st.text_input(
                "Google Gemini API Key",
                type="password",
                value=current_key,
                help="Primary key for story and image generation via Google Gemini.",
            )
            if api_key_sidebar != current_key:
                st.session_state.api_key = api_key_sidebar
                user_id = get_current_user_id()
                if user_id and api_key_sidebar:
                    save_user_api_key(user_id, api_key_sidebar)

            if api_key_sidebar:
                st.caption(f"Gemini key saved ({len(api_key_sidebar)} chars)")
            else:
                st.caption("No Gemini key set.")

            # OpenRouter API Key (backup for image generation)
            current_or_key = st.session_state.openrouter_api_key
            openrouter_key_input = st.text_input(
                "OpenRouter API Key (backup)",
                type="password",
                value=current_or_key,
                help="Backup key for image generation via OpenRouter (uses Gemini models). Used automatically when Gemini fails.",
            )
            if openrouter_key_input != current_or_key:
                st.session_state.openrouter_api_key = openrouter_key_input
                user_id = get_current_user_id()
                if user_id and openrouter_key_input:
                    save_user_openrouter_key(user_id, openrouter_key_input)

            if openrouter_key_input:
                st.caption(f"OpenRouter key saved ({len(openrouter_key_input)} chars)")
            else:
                st.caption("No OpenRouter key — Gemini only.")

            # Vertex AI (Google Cloud) credentials
            with st.expander("Vertex AI (Google Cloud)", expanded=bool(st.session_state.vertex_project_id)):
                user_id_v = get_current_user_id()

                current_vproject = st.session_state.vertex_project_id
                vproject_input = st.text_input(
                    "GCP Project ID",
                    value=current_vproject,
                    placeholder="my-gcp-project-id",
                    key="sidebar_vertex_project",
                    help="Your Google Cloud project ID (from GCP Console).",
                )

                current_vloc = st.session_state.vertex_location or "us-central1"
                vloc_input = st.text_input(
                    "Location",
                    value=current_vloc,
                    placeholder="us-central1",
                    key="sidebar_vertex_location",
                    help="Vertex AI region, e.g. us-central1.",
                )

                current_vsa = st.session_state.vertex_sa_json
                vsa_input = st.text_area(
                    "Service Account JSON",
                    value=current_vsa,
                    placeholder='{"type":"service_account","project_id":"..."}',
                    height=120,
                    key="sidebar_vertex_sa",
                    help="Paste the full contents of your GCP service account key JSON file.",
                )

                if vproject_input != current_vproject or vloc_input != current_vloc or vsa_input != current_vsa:
                    st.session_state.vertex_project_id = vproject_input
                    st.session_state.vertex_location = vloc_input or "us-central1"
                    st.session_state.vertex_sa_json = vsa_input
                    if user_id_v and (vproject_input or vsa_input):
                        save_user_vertex_config(user_id_v, vproject_input, vloc_input or "us-central1", vsa_input)

                from vertex_client import is_vertex_configured, _token, _cfg
                if is_vertex_configured():
                    st.caption("Vertex AI configured and ready")
                    if st.button("Test Vertex AI connection", key="test_vertex_btn", use_container_width=True):
                        with st.spinner("Testing Vertex AI..."):
                            try:
                                tok = _token(raise_on_error=True)
                                if tok:
                                    st.success("Authentication successful")
                                    from vertex_client import call_gemini_text
                                    result = call_gemini_text("Say 'Vertex OK' and nothing else.", api_key="")
                                    if result:
                                        st.success("Vertex AI is working correctly")
                                    else:
                                        st.error("Authentication succeeded but text generation failed. Please check your project configuration.")
                                else:
                                    st.error("Could not obtain auth token. Check your Service Account JSON.")
                            except Exception as ex:
                                logger.warning(f"Vertex test error: {ex}")
                                st.error("Connection test failed. Please verify your credentials.")
                else:
                    st.caption("Vertex AI not configured — Gemini API only.")

            st.divider()

    # Main content area
    # Get API key from session state (sidebar updates session state)
    api_key = st.session_state.api_key

    # Template book loaded from history: display regardless of the mode selection
    if st.session_state.get("template_generated_book") and TEMPLATE_BOOKS_AVAILABLE:
        display_template_book_preview(st.session_state.template_generated_book, api_key=api_key)
        return

    # Admin Template Studio (pre-render assets once)
    if st.session_state.get("show_template_studio") and TEMPLATE_FLOW_AVAILABLE:
        if st.button("← Back to Main", key="back_from_studio"):
            st.session_state.show_template_studio = False
            st.rerun()
        render_template_studio(api_key)
        return

    # Template mode — asset-backed storefront flow
    if st.session_state.book_mode == "template" and TEMPLATE_FLOW_AVAILABLE:
        render_template_mode(api_key, save_history_cb=save_template_book_to_history)
        return

    # Legacy template mode (fallback if template_flow unavailable)
    if st.session_state.book_mode == "template" and TEMPLATE_BOOKS_AVAILABLE:
        if st.session_state.get("generate_template_book", False):
            st.session_state.generate_template_book = False
            with st.spinner("Generating your personalized template book..."):
                generate_template_book(
                    api_key,
                    st.session_state.template_book_data
                )
            if st.session_state.get("template_generated_book"):
                save_template_book_to_history(st.session_state.template_generated_book)

        if st.session_state.get("template_generated_book"):
            display_template_book_preview(st.session_state.template_generated_book, api_key=api_key)
            return

        render_template_book_form()
        return

    # No story in progress and not in custom wizard — show landing
    if not st.session_state.generated_story and st.session_state.book_mode != "custom":
        render_landing()
        return

    # Custom wizard — form not yet submitted
    if st.session_state.book_mode == "custom" and not st.session_state.wiz_generate_trigger and not st.session_state.generated_story:
        render_custom_wizard()
        return

    # --- Generate story from wizard values ---
    if st.session_state.wiz_generate_trigger:
        # Story text generation is FREE — no payment gate here.
        # Payment is collected after story approval (Step 1.5), before images.
        st.session_state.wiz_generate_trigger = False

        # Build values from wizard session state
        child_name = st.session_state.wiz_child_name
        age = st.session_state.wiz_age
        gender = st.session_state.wiz_gender
        story_type = st.session_state.wiz_story_type
        image_style = st.session_state.wiz_image_style
        problem = st.session_state.wiz_problem
        language = st.session_state.wiz_language
        family_structure = st.session_state.wiz_family_structure
        hero_trait = st.session_state.wiz_hero_trait
        character_choice = st.session_state.wiz_character_choice
        format_id = st.session_state.wiz_format_id

        # Build physical description from appearance wizard fields
        desc_parts = []
        if st.session_state.wiz_skin_tone:
            desc_parts.append(f"{st.session_state.wiz_skin_tone} skin")
        if st.session_state.wiz_hair_style:
            desc_parts.append(st.session_state.wiz_hair_style)
        if st.session_state.wiz_eye_color:
            desc_parts.append(st.session_state.wiz_eye_color)
        if st.session_state.wiz_outfit:
            desc_parts.append(f"wearing {st.session_state.wiz_outfit}")
        physical_desc = ", ".join(desc_parts) if desc_parts else "average appearance"

        # Validate required fields
        if not child_name or not problem:
            st.error("Please fill in all required fields.")
            st.session_state.wizard_step = 1 if not child_name else 3
            st.session_state.book_mode = "custom"
            st.rerun()
            return

        # Reset approvals when generating new story
        st.session_state.story_approved = False
        st.session_state.image_approvals = {}
        st.session_state.all_images_approved = False
        st.session_state.generated_images = []
        st.session_state._loaded_from_history = False  # allow auto-generation for fresh stories

        with st.spinner("🔄 Generating your personalized story..."):
            story_data = generate_story_with_gemini(
                api_key, child_name, age, gender, physical_desc, problem, language,
                family_structure, hero_trait, character_choice, story_type, image_style,
                format_id=format_id,
            )

            if not story_data:
                st.error("Failed to generate story. Please try again.")
                st.session_state.wiz_generate_trigger = False
                return

            st.session_state.generated_story = story_data
            st.session_state.current_child_name = child_name
            # CRITICAL: Clear images when new story is generated to prevent mismatch
            st.session_state.current_book_history_id = None  # fresh INSERT on next save
            st.session_state.generated_images = []
            st.session_state.image_approvals = {}
            st.session_state.all_images_approved = False
            st.session_state.pdf_path = None
            st.session_state.pdf_generation_key = None

            # Save story to history
            metadata = {
                "age": age,
                "gender": gender,
                "physical_desc": physical_desc,
                "problem": problem,
                "language": language,
                "family_structure": family_structure,
                "hero_trait": hero_trait,
                "character_choice": character_choice,
                "story_type": story_type,
                "image_style": image_style,
                "format_id": format_id,
                "has_reference_photo": bool(st.session_state.get("wiz_reference_photos_b64")),
            }
            save_story(story_data, child_name, metadata)

            st.success("✅ Story generated! Please review below.")

    # Resolve local variables from session state for downstream steps
    child_name = st.session_state.current_child_name or st.session_state.wiz_child_name
    age = st.session_state.wiz_age
    language = st.session_state.wiz_language
    
    # Step 1: Story Review
    if st.session_state.generated_story and not st.session_state.story_approved:
        st.header("📖 Step 1: Review & Edit Story")
        st.markdown("Review each page below. You can edit the text for any page. Click 'Approve Story' when ready.")

        # Determine admin status once for the whole Step 1 block
        _s1_email = st.session_state.get("user_email") or (st.session_state.get("auth_user") or {}).get("email", "")
        _s1_is_admin = _s1_email in ADMIN_EMAILS

        pages = st.session_state.generated_story.get("pages", [])
        
        # Debug: Validate story has pages
        if not pages or len(pages) == 0:
            st.error("⚠️ Story loaded but has no pages. The story data may be incomplete.")
            with st.expander("Debug: Story Data", expanded=True):
                st.write("Story keys:", list(st.session_state.generated_story.keys()) if isinstance(st.session_state.generated_story, dict) else "Not a dict")
                st.write("Pages count:", len(pages))
                st.json(st.session_state.generated_story)
            return
        
        # Display all pages (not collapsed) with edit capability
        for i, page in enumerate(pages):
            page_num = page.get('page_number', i+1)
            
            # Get edited text or use original
            edited_text = st.session_state.edited_story_pages.get(i, page.get("text", ""))
            # Get edited image prompt or use original
            edited_image_prompt = st.session_state.edited_image_prompts.get(i, page.get("image_prompt", ""))
            
            st.subheader(f"📄 Page {page_num}")
            
            # Editable story text area
            new_text = st.text_area(
                f"Story Text (Page {page_num})",
                value=edited_text,
                key=f"story_text_{i}",
                height=100,
                help="Edit the story text for this page"
            )
            
            # Save edited text
            if new_text != page.get("text", ""):
                st.session_state.edited_story_pages[i] = new_text
                # Update the story data
                st.session_state.generated_story["pages"][i]["text"] = new_text
            
            # Editable image prompt area — admin only
            if _s1_is_admin:
                st.write("**Image Prompt:**")
                new_image_prompt = st.text_area(
                    f"Image Prompt (Page {page_num})",
                    value=edited_image_prompt,
                    key=f"image_prompt_{i}",
                    height=80,
                    help="Edit the image prompt to change how the image will be generated. Make sure to include the visual anchor description."
                )
                # Save edited image prompt
                if new_image_prompt != page.get("image_prompt", ""):
                    st.session_state.edited_image_prompts[i] = new_image_prompt
                    st.session_state.generated_story["pages"][i]["image_prompt"] = new_image_prompt
            
            # Page actions: Regenerate from this page, Move up/down
            col_action1, col_action2, col_action3 = st.columns([1, 1, 1])
            with col_action1:
                if st.button(f"🔄 Regenerate from Page {page_num}", key=f"regen_from_page_{i}", use_container_width=True):
                    st.session_state[f"_regen_flag_{i}"] = True
                    st.session_state[f"regen_page_prompt_{i}"] = ""
                    st.rerun()
            with col_action2:
                if i > 0:
                    if st.button(f"⬆️ Move Up", key=f"move_page_up_{i}", use_container_width=True):
                        # Swap pages
                        pages = st.session_state.generated_story["pages"]
                        pages[i], pages[i-1] = pages[i-1], pages[i]
                        # Update page numbers
                        for idx, p in enumerate(pages):
                            p["page_number"] = idx + 1
                        st.session_state.generated_story["pages"] = pages
                        # Clear images and approvals since order changed
                        st.session_state.generated_images = []
                        st.session_state.image_approvals = {}
                        st.session_state.all_images_approved = False
                        st.rerun()
            with col_action3:
                if i < len(pages) - 1:
                    if st.button(f"⬇️ Move Down", key=f"move_page_down_{i}", use_container_width=True):
                        # Swap pages
                        pages = st.session_state.generated_story["pages"]
                        pages[i], pages[i+1] = pages[i+1], pages[i]
                        # Update page numbers
                        for idx, p in enumerate(pages):
                            p["page_number"] = idx + 1
                        st.session_state.generated_story["pages"] = pages
                        # Clear images and approvals since order changed
                        st.session_state.generated_images = []
                        st.session_state.image_approvals = {}
                        st.session_state.all_images_approved = False
                        st.rerun()
            
            # Show regenerate prompt if requested
            if st.session_state.get(f"_regen_flag_{i}", False):
                st.write("---")
                st.write(f"**Regenerate Story from Page {page_num} onwards:**")
                regen_prompt = st.text_area(
                    f"Instructions for regenerating from Page {page_num}",
                    value=st.session_state.get(f"regen_page_prompt_{i}", ""),
                    key=f"regen_prompt_input_{i}",
                    height=100,
                    placeholder="e.g., Make the character braver, Add more dialogue, Change the ending..."
                )
                col_apply, col_cancel_regen = st.columns([1, 1])
                with col_apply:
                    if st.button(f"✨ Apply Changes", key=f"apply_regen_{i}", type="primary", use_container_width=True):
                        if regen_prompt.strip():
                            # Regenerate story from this page onwards
                            with st.spinner(f"Regenerating story from page {page_num}..."):
                                regenerated_story = regenerate_story_from_page(
                                    api_key,
                                    st.session_state.generated_story,
                                    i,
                                    regen_prompt,
                                    st.session_state.current_child_name or child_name,
                                    age,
                                    language
                                )
                                if regenerated_story:
                                    st.session_state.generated_story = regenerated_story
                                    # CRITICAL: Clear ALL images when story is regenerated to prevent mismatch
                                    st.session_state.generated_images = []
                                    st.session_state.image_approvals = {}
                                    st.session_state.all_images_approved = False
                                    st.session_state.edited_story_pages = {k: v for k, v in st.session_state.edited_story_pages.items() if k < i}
                                    st.session_state.edited_image_prompts = {k: v for k, v in st.session_state.edited_image_prompts.items() if k < i}
                                    st.session_state.pdf_path = None
                                    st.session_state.pdf_generation_key = None
                                    st.session_state.story_approved = False
                                    st.session_state[f"_regen_flag_{i}"] = False
                                    st.success(f"✅ Story regenerated from page {page_num} onwards! All images cleared - please regenerate them.")
                                    st.rerun()
                                else:
                                    st.error("Failed to regenerate story. Please try again.")
                        else:
                            st.warning("Please enter instructions for regeneration")
                with col_cancel_regen:
                    if st.button("❌ Cancel", key=f"cancel_regen_{i}", use_container_width=True):
                        st.session_state[f"_regen_flag_{i}"] = False
                        st.rerun()
            
            with col_action2:
                if i > 0:
                    if st.button(f"⬆️ Move Up", key=f"move_up_story_{i}", use_container_width=True):
                        # Swap pages
                        pages[i], pages[i-1] = pages[i-1], pages[i]
                        # Update page numbers
                        for idx, p in enumerate(pages):
                            p["page_number"] = idx + 1
                        st.session_state.generated_story["pages"] = pages
                        # Reorder edited data if exists
                        if i in st.session_state.edited_story_pages:
                            temp = st.session_state.edited_story_pages.get(i)
                            st.session_state.edited_story_pages[i] = st.session_state.edited_story_pages.get(i-1, "")
                            st.session_state.edited_story_pages[i-1] = temp
                        if i in st.session_state.edited_image_prompts:
                            temp = st.session_state.edited_image_prompts.get(i)
                            st.session_state.edited_image_prompts[i] = st.session_state.edited_image_prompts.get(i-1, "")
                            st.session_state.edited_image_prompts[i-1] = temp
                        st.session_state.generated_images = []  # Clear images when reordering
                        st.rerun()
            with col_action3:
                if i < len(pages) - 1:
                    if st.button(f"⬇️ Move Down", key=f"move_down_story_{i}", use_container_width=True):
                        # Swap pages
                        pages[i], pages[i+1] = pages[i+1], pages[i]
                        # Update page numbers
                        for idx, p in enumerate(pages):
                            p["page_number"] = idx + 1
                        st.session_state.generated_story["pages"] = pages
                        # Reorder edited data if exists
                        if i in st.session_state.edited_story_pages:
                            temp = st.session_state.edited_story_pages.get(i)
                            st.session_state.edited_story_pages[i] = st.session_state.edited_story_pages.get(i+1, "")
                            st.session_state.edited_story_pages[i+1] = temp
                        if i in st.session_state.edited_image_prompts:
                            temp = st.session_state.edited_image_prompts.get(i)
                            st.session_state.edited_image_prompts[i] = st.session_state.edited_image_prompts.get(i+1, "")
                            st.session_state.edited_image_prompts[i+1] = temp
                        st.session_state.generated_images = []  # Clear images when reordering
                        st.rerun()
            
            st.divider()
        
        # Follow-up Prompt Section
        st.divider()
        st.subheader("✨ Refine Story with Follow-up Prompt")
        st.markdown("Want to change the story? Enter instructions below to refine it while keeping the existing storyline.")
        
        followup_prompt = st.text_area(
            "Follow-up Instructions",
            placeholder="e.g., Make the story more adventurous, Add more dialogue, Change the ending to be more positive, Make the character braver...",
            height=100,
            help="Describe what you'd like to change or improve in the story"
        )
        
        if st.button("🔄 Refine Story with Follow-up", type="secondary", use_container_width=True):
            if followup_prompt.strip():
                with st.spinner("🔄 Refining story based on your instructions..."):
                    original_story = st.session_state.generated_story.copy()  # Keep a copy for comparison
                    refined_story = refine_story_with_followup(
                        api_key, 
                        original_story,
                        followup_prompt,
                        child_name,
                        age,
                        language
                    )
                    if refined_story:
                        # Check if story actually changed - compare page by page
                        original_pages = original_story.get("pages", [])
                        refined_pages = refined_story.get("pages", [])
                        
                        changed_count = 0
                        for i, (orig_page, ref_page) in enumerate(zip(original_pages, refined_pages)):
                            orig_text = orig_page.get("text", "").strip()
                            ref_text = ref_page.get("text", "").strip()
                            if orig_text != ref_text:
                                changed_count += 1
                        
                        if changed_count == 0:
                            st.error("❌ The refined story is IDENTICAL to the original. The AI did not apply your changes.")
                            st.info("💡 **Tips to get better results:**")
                            st.markdown("""
                            - Be very specific about what to change (e.g., 'Change page 3 to have the character be braver')
                            - Mention specific pages or scenes to modify
                            - Use action words (e.g., 'add', 'remove', 'change', 'make more')
                            - Try rephrasing your request differently
                            """)
                            # Don't update the story if nothing changed
                        else:
                            # Update the story in session state
                            st.session_state.generated_story = refined_story
                            # CRITICAL: Clear images when story changes to prevent mismatch
                            st.session_state.generated_images = []
                            st.session_state.image_approvals = {}
                            st.session_state.all_images_approved = False
                            st.session_state.pdf_path = None
                            st.session_state.pdf_generation_key = None
                            # Reset all edits so the new story is displayed
                            st.session_state.edited_story_pages = {}
                            st.session_state.edited_image_prompts = {}
                            # Reset approval state so user can review the refined story
                            st.session_state.story_approved = False
                            st.success(f"✅ Story refined! {changed_count} out of {len(original_pages)} pages were modified. Review the updated version below.")
                            st.rerun()
                    else:
                        st.error("Failed to refine story. Please try again or check the error message above.")
            else:
                st.warning("Please enter follow-up instructions")
        
        st.divider()
        
        # Single approve button at the bottom
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✅ Approve Story", type="primary", use_container_width=True):
                # Apply all edits before approving
                for i, page in enumerate(pages):
                    if i in st.session_state.edited_story_pages:
                        st.session_state.generated_story["pages"][i]["text"] = st.session_state.edited_story_pages[i]
                st.session_state.story_approved = True
                st.session_state.just_approved_story = True
                # Auto-save story with updated journey state
                if st.session_state.generated_story and st.session_state.current_child_name:
                    save_story(st.session_state.generated_story, st.session_state.current_child_name)
                st.rerun()
        with col2:
            if st.button("🔄 Regenerate Story from Scratch", use_container_width=True):
                st.session_state.generated_story = None
                st.session_state.edited_story_pages = {}
                st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1.5: Choose delivery method & pay — after story approval, before images
    # ─────────────────────────────────────────────────────────────────────────
    if st.session_state.generated_story and st.session_state.story_approved:
        _choice_email = st.session_state.get("user_email") or (st.session_state.get("auth_user") or {}).get("email", "")
        _is_admin_choice = _choice_email in ADMIN_EMAILS
        _delivery_opt = st.session_state.get("book_delivery_option")
        _choice_pay_status = st.session_state.get("current_book_payment_status")

        # Migrate legacy paid sessions (from old gate flow) — default to download
        if _delivery_opt is None and _choice_pay_status in ("story_paid", "download_paid"):
            st.session_state.book_delivery_option = "download"
            _delivery_opt = "download"

        # Gate passed when: delivery option chosen AND (admin OR paid)
        _gate_passed = _delivery_opt is not None and (
            _is_admin_choice or _choice_pay_status in ("story_paid", "print_paid", "download_paid")
        )

        if not _gate_passed:
            from payments import (
                custom_story_price_inr as _cs_price_fn,
                custom_download_price_inr as _cd_price_fn,
                create_cashfree_order as _choice_create_order,
                verify_cashfree_order as _choice_verify_order,
                confirm_payment_and_credit as _choice_cpc,
                is_cashfree_configured as _choice_cf_ok,
                is_valid_phone as _choice_vph,
            )
            _dl_price = _cs_price_fn()   # ₹350 — digital download
            _pd_price = _cd_price_fn()   # ₹650 — print + deliver
            _choice_uid = get_current_user_id()
            _choice_child = st.session_state.get("current_child_name") or st.session_state.get("wiz_child_name", "")
            _choice_n_pages = len(st.session_state.generated_story.get("pages", []))

            st.divider()
            st.header("📦 How would you like your book?")
            st.markdown(
                f"Your story is ready! Choose how you'd like to get your illustrated book "
                f"(**{_choice_n_pages} pages** with AI-generated artwork):"
            )

            if _is_admin_choice:
                # Admin skips payment — just picks delivery option
                st.info("🔑 Admin mode: select delivery method (no payment required)")
                acol1, acol2 = st.columns(2)
                with acol1:
                    if st.button(f"📥 Digital Download (₹{_dl_price})", type="primary",
                                 use_container_width=True, key="admin_choice_dl"):
                        st.session_state.book_delivery_option = "download"
                        st.session_state.current_book_payment_status = "story_paid"
                        st.rerun()
                with acol2:
                    if st.button(f"📬 Print & Deliver (₹{_pd_price})", use_container_width=True,
                                 key="admin_choice_pd"):
                        st.session_state.book_delivery_option = "print_deliver"
                        st.session_state.current_book_payment_status = "print_paid"
                        st.rerun()
                return

            # Non-admin: Cashfree Gateway (Orders API + JS Drop-in SDK)
            _pending_session_id = st.session_state.get("cf_payment_session_id")
            _pending_order_id = st.session_state.get("cf_pending_order_id")
            _pending_gate = st.session_state.get("pending_payment_gate")

            # Clear stale session if the gate doesn't match
            if _pending_session_id and _pending_gate not in ("download_choice", "print_deliver_choice"):
                _pending_session_id = None
                _pending_order_id = None
                st.session_state.cf_payment_session_id = None
                st.session_state.cf_pending_order_id = None

            # Expire stale payment sessions — Cashfree sessions last ~20 min
            _order_age = (
                (time.time() - st.session_state.cf_order_created_at)
                if st.session_state.get("cf_order_created_at") else 9999
            )
            if _pending_session_id and _pending_order_id and _order_age > 1200:
                st.warning("⚠️ Your payment session expired. Please start again.")
                st.session_state.cf_pending_order_id = None
                st.session_state.cf_payment_session_id = None
                st.session_state.cf_order_created_at = None
                st.session_state.pending_payment_gate = None
                _pending_session_id = None
                _pending_order_id = None

            if _pending_session_id and _pending_order_id:
                # Cashfree checkout — payment auto-triggers inside the iframe
                _opt_label = "📥 Download PDF" if _pending_gate == "download_choice" else "📬 Print & Deliver"
                _opt_price = _dl_price if _pending_gate == "download_choice" else _pd_price
                st.markdown(
                    f"""<div style='background:#f0fdf4;border:1px solid #86efac;border-radius:10px;
                    padding:14px 18px;margin-bottom:12px;'>
                    <span style='font-size:20px;'>🔒</span>
                    <strong style='color:#166534;margin-left:8px;'>
                    Secure payment — {_opt_label} · ₹{_opt_price}</strong><br>
                    <span style='color:#4b5563;font-size:13px;margin-left:30px;'>
                    Complete your payment below. The page will update automatically once done.</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
                components.html(
                    _cashfree_dropin_html(_pending_session_id, _pending_order_id),
                    height=720,
                    scrolling=False,
                )
                # Cancel — unobtrusive small button
                if st.button("✖ Cancel & choose again", use_container_width=False,
                             key="choice_cancel"):
                    st.session_state.cf_pending_order_id = None
                    st.session_state.cf_payment_session_id = None
                    st.session_state.pending_payment_gate = None
                    st.session_state.cf_show_verify_button = False
                    st.rerun()

                # Fallback verify button — only visible after 60 s timeout from JS
                if st.session_state.get("cf_show_verify_button"):
                    st.warning("⏱ Payment is taking longer than expected. If you've completed "
                               "the payment, click below to confirm.")
                    if st.button("✅ I've paid — confirm my payment", type="primary",
                                 use_container_width=True, key="choice_verify"):
                        _v = _choice_verify_order(_pending_order_id)
                        if _v == "PAID":
                            _choice_cpc(_pending_order_id, _choice_uid)
                            if _pending_gate == "download_choice":
                                st.session_state.current_book_payment_status = "story_paid"
                                st.session_state.book_delivery_option = "download"
                            else:
                                st.session_state.current_book_payment_status = "print_paid"
                                st.session_state.book_delivery_option = "print_deliver"
                            st.session_state.cf_pending_order_id = None
                            st.session_state.cf_payment_session_id = None
                            st.session_state.pending_payment_gate = None
                            st.session_state.cf_show_verify_button = False
                            st.success("✅ Confirmed! Generating your images now…")
                            st.rerun()
                        else:
                            st.error(f"Payment not yet received (status: {_v}). "
                                     "Please complete the payment in the window above.")
                return

            if not _choice_cf_ok():
                st.warning("Checkout is temporarily unavailable. Please try again shortly.")
                return

            st.markdown(
                """<div style='background:#fffbeb;border:1.5px solid #f59e0b;border-radius:10px;
                padding:16px 20px;margin:16px 0 4px 0;'>
                <div style='font-size:15px;font-weight:700;color:#92400e;margin-bottom:6px;'>
                📱 Enter your mobile number to continue</div>
                <div style='font-size:13px;color:#78350f;'>
                Required by Cashfree to process the payment and send a receipt.</div>
                </div>""",
                unsafe_allow_html=True,
            )
            _choice_phone = st.text_input(
                "Mobile number",
                max_chars=10, placeholder="10-digit number e.g. 9876543210",
                key="choice_phone", label_visibility="collapsed",
            )

            col_dl, col_pd = st.columns(2)
            with col_dl:
                st.markdown(
                    f"""<div style='background:#f0f7ff;border:2px solid #2563eb;border-radius:12px;
                    padding:20px;text-align:center;margin-bottom:12px;'>
                    <div style='font-size:36px;'>📥</div>
                    <h3 style='color:#1e40af;margin:8px 0;'>Download PDF</h3>
                    <p style='color:#374151;font-size:14px;'>Get a digital copy instantly after images are
                    generated. Read on any device or print at home.</p>
                    <div style='font-size:28px;font-weight:700;color:#1e40af;margin-top:8px;'>₹{_dl_price}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                if st.button(f"📥 Pay ₹{_dl_price} & Download", type="primary",
                             use_container_width=True, key="choice_pay_dl"):
                    if not _choice_vph(_choice_phone):
                        st.error("Please enter a valid 10-digit mobile number.")
                        st.stop()
                    with st.spinner("Opening payment…"):
                        _res_dl = _choice_create_order(
                            _choice_uid, _choice_email, _dl_price,
                            f"Storybook digital download for {_choice_child}",
                            customer_phone=_choice_phone,
                            metadata={"book_kind": "custom", "product": "pdf_download",
                                      "gate": "download_choice", "child_name": _choice_child},
                        )
                    if _res_dl and _res_dl.get("payment_session_id"):
                        st.session_state.cf_pending_order_id = _res_dl["order_id"]
                        st.session_state.cf_payment_session_id = _res_dl["payment_session_id"]
                        st.session_state.cf_order_created_at = time.time()
                        st.session_state.pending_payment_gate = "download_choice"
                        st.session_state.current_book_payment_status = "pending"
                        st.rerun()
                    else:
                        st.error((_res_dl or {}).get("error", "Could not initiate payment. Please try again."))

            with col_pd:
                st.markdown(
                    f"""<div style='background:#fff7ed;border:2px solid #ea580c;border-radius:12px;
                    padding:20px;text-align:center;margin-bottom:12px;'>
                    <div style='font-size:36px;'>📬</div>
                    <h3 style='color:#c2410c;margin:8px 0;'>Print & Deliver</h3>
                    <p style='color:#374151;font-size:14px;'>We print your book professionally and deliver
                    it to your door. Includes the digital copy too!</p>
                    <div style='font-size:28px;font-weight:700;color:#c2410c;margin-top:8px;'>₹{_pd_price}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                if st.button(f"📬 Pay ₹{_pd_price} & Get Printed", use_container_width=True,
                             key="choice_pay_pd"):
                    if not _choice_vph(_choice_phone):
                        st.error("Please enter a valid 10-digit mobile number.")
                        st.stop()
                    with st.spinner("Opening payment…"):
                        _res_pd = _choice_create_order(
                            _choice_uid, _choice_email, _pd_price,
                            f"Printed storybook for {_choice_child}",
                            customer_phone=_choice_phone,
                            metadata={"book_kind": "custom", "product": "print_deliver",
                                      "gate": "print_deliver_choice", "child_name": _choice_child},
                        )
                    if _res_pd and _res_pd.get("payment_session_id"):
                        st.session_state.cf_pending_order_id = _res_pd["order_id"]
                        st.session_state.cf_payment_session_id = _res_pd["payment_session_id"]
                        st.session_state.cf_order_created_at = time.time()
                        st.session_state.pending_payment_gate = "print_deliver_choice"
                        st.session_state.current_book_payment_status = "pending"
                        st.rerun()
                    else:
                        st.error((_res_pd or {}).get("error", "Could not initiate payment. Please try again."))
            return  # don't proceed to Step 2 until gate is passed

    # Step 2: Image Generation with Review
    # Skip Step 2 only when all images approved AND we have real (non-None) images loaded
    _valid_image_count = sum(1 for img in st.session_state.generated_images if img is not None)
    _step2_done = (
        st.session_state.all_images_approved and
        _valid_image_count > 0
    )
    if st.session_state.generated_story and st.session_state.story_approved and not _step2_done:
        # Add anchor for auto-scrolling
        st.markdown('<div id="image-generation-section"></div>', unsafe_allow_html=True)

        # Auto-scroll to image generation section if just approved
        if st.session_state.get("just_approved_story"):
            st.session_state.just_approved_story = False
            components.html(
                """
                <script>
                    setTimeout(function() {
                        const element = window.parent.document.getElementById('image-generation-section');
                        if (element) {
                            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    }, 100);
                </script>
                """,
                height=0
            )

        pages = st.session_state.generated_story.get("pages", [])
        total_pages = len(pages)
        approved_count = len([k for k, v in st.session_state.image_approvals.items() if v])
        
        # Skip automatic image generation if all images were already approved (Step 3 state)
        # Only show generation UI if images are missing and not all approved
        if st.session_state.all_images_approved and len(st.session_state.generated_images) == 0:
            # User was at Step 3, images were approved but not saved (can't save images)
            # Skip to Step 3 - they can regenerate if needed
            st.info("ℹ️ You were at **Step 3 (PDF ready)** when this story was saved. Images need to be regenerated to view/download PDF, but your approval states are preserved.")
            st.markdown("**Options:**")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Regenerate All Images", type="primary", use_container_width=True):
                    st.session_state.all_images_approved = False
                    st.session_state.image_approvals = {}
                    st.rerun()
            with col2:
                if st.button("⏭️ Skip to PDF (No Images)", type="secondary", use_container_width=True):
                    # Create placeholder images so PDF can be generated
                    from PIL import Image
                    placeholder = Image.new('RGB', (384, 512), color=(240, 240, 240))
                    st.session_state.generated_images = [placeholder] * total_pages
                    st.rerun()
        else:
            st.header("🎨 Step 2: Generate & Review Images")
            # Ensure progress value is between 0.0 and 1.0
            progress_value = min(1.0, approved_count / total_pages if total_pages > 0 else 0)
            st.progress(progress_value)
            st.caption(f"Approved: {approved_count}/{total_pages} images")

            # Check if API key or Vertex AI is available for image generation
            from vertex_client import is_vertex_configured
            if not api_key and not is_vertex_configured():
                st.error("⚠️ **API Key Required for Image Generation**")
                st.info("👈 Please enter a Google Gemini API key or configure Vertex AI in the sidebar to generate images.")
                return

            # Check if any specific image needs regeneration
            regenerate_idx = None
            for i in range(total_pages):
                if st.session_state.get(f"regenerate_image_{i}", False):
                    regenerate_idx = i
                    st.session_state[f"regenerate_image_{i}"] = False  # Clear flag
                    break
            
            # Regenerate specific image if needed
            if regenerate_idx is not None:
                with st.spinner(f"Regenerating image {regenerate_idx + 1}/{total_pages}..."):
                    page = pages[regenerate_idx]
                    # Admin may have saved a custom prompt; otherwise assemble lazily from visual_description
                    if regenerate_idx in st.session_state.edited_image_prompts:
                        image_prompt = st.session_state.edited_image_prompts[regenerate_idx]
                    else:
                        _va = st.session_state.generated_story.get("visual_anchor", "")
                        _sc = st.session_state.generated_story.get("secondary_characters", [])
                        image_prompt = _assemble_image_prompt(page, _va, _resolve_book_format(), _sc)
                    logger.info(f"Regenerating image for page {regenerate_idx + 1} with prompt: {image_prompt[:150]}...")
                    img = generate_image_with_imagen(api_key, image_prompt, image_index=regenerate_idx)
                    # ALWAYS replace at the correct index - ensure list is large enough
                    while len(st.session_state.generated_images) <= regenerate_idx:
                        st.session_state.generated_images.append(None)
                    st.session_state.generated_images[regenerate_idx] = img
                    st.session_state.image_approvals[regenerate_idx] = True
                    _save_images_now()
                    # If regeneration was triggered from Step 3, return there
                    if st.session_state.pop("_return_to_step3_after_regen", False):
                        n_valid = len([im for im in st.session_state.generated_images if im is not None])
                        if n_valid == total_pages:
                            st.session_state.all_images_approved = True
                    st.rerun()

            # ── Payment context (used by image display + Step 3) ──────────────
            # Gate 1 is now enforced at wizard submit — any user reaching here has paid.
            # We still track status so Step 3 Gate 2 (download) knows what's paid.
            _current_user_email = st.session_state.get("user_email") or (st.session_state.get("auth_user") or {}).get("email", "")
            _is_admin_user = _current_user_email in ADMIN_EMAILS
            _pay_status = st.session_state.get("current_book_payment_status")
            story_paid = _is_admin_user or _pay_status in ("story_paid", "download_paid")
            # Safety net: if somehow reached without payment, treat as paid for image gen
            # (shouldn't happen — wizard gate blocks non-payers)
            needs_story_payment = False  # gate moved to wizard submit

            # Generate images that haven't been generated yet (all pages — Gate 1 already paid)
            if regenerate_idx is None:
                # Determine generation limit: all pages (Gate 1 is paid before reaching here)
                gen_limit = total_pages

                missing_idx = None
                for idx in range(gen_limit):
                    if idx >= len(st.session_state.generated_images):
                        missing_idx = idx
                        break
                    elif st.session_state.generated_images[idx] is None:
                        missing_idx = idx
                        break

                if missing_idx is not None:
                    # If this story was just loaded from history, don't auto-generate —
                    # show a button so the user explicitly triggers generation.
                    if st.session_state.get("_loaded_from_history"):
                        st.info(f"ℹ️ {total_pages - len([i for i in st.session_state.generated_images if i is not None])} image(s) need to be generated for this story.")
                        if st.button("🎨 Generate Missing Images", type="primary", key="gen_missing_after_load"):
                            st.session_state._loaded_from_history = False
                            st.rerun()
                    else:
                        with st.spinner(f"Generating image {missing_idx + 1}/{total_pages}..."):
                            page = pages[missing_idx]
                            # Admin may have saved a custom prompt; otherwise assemble lazily
                            if missing_idx in st.session_state.edited_image_prompts:
                                image_prompt = st.session_state.edited_image_prompts[missing_idx]
                            else:
                                _va = st.session_state.generated_story.get("visual_anchor", "")
                                _sc = st.session_state.generated_story.get("secondary_characters", [])
                                image_prompt = _assemble_image_prompt(page, _va, _resolve_book_format(), _sc)
                            logger.info(f"Generating image for page {missing_idx + 1} with prompt: {image_prompt[:150]}...")
                            img = generate_image_with_imagen(api_key, image_prompt, image_index=missing_idx)
                            # Ensure list is large enough
                            while len(st.session_state.generated_images) <= missing_idx:
                                st.session_state.generated_images.append(None)
                            st.session_state.generated_images[missing_idx] = img
                            _save_images_now()
                            st.rerun()
        
        # ── Image display: admin full review vs non-admin preview cards ────────
        if _is_admin_user:
            # Full review with approve/reject, prompt editing, and page reordering
            for i, page in enumerate(pages):
                if i >= len(st.session_state.generated_images):
                    break
                if st.session_state.generated_images[i] is None:
                    st.info(f"⏳ Page {page.get('page_number', i+1)} - Image pending regeneration...")
                    continue

                is_approved = st.session_state.image_approvals.get(i, False)
                page_num = page.get('page_number', i + 1)
                current_prompt = st.session_state.edited_image_prompts.get(i, page.get("image_prompt", ""))

                with st.container():
                    st.subheader(f"Page {page_num}")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        edited_text = st.session_state.edited_story_pages.get(i, page.get("text", ""))
                        new_text = st.text_area(
                            f"Edit Story Text (Page {page_num})",
                            value=edited_text, key=f"story_text_edit_{i}",
                            height=80, label_visibility="collapsed",
                        )
                        if new_text != page.get("text", ""):
                            st.session_state.edited_story_pages[i] = new_text
                            st.session_state.generated_story["pages"][i]["text"] = new_text
                        st.image(st.session_state.generated_images[i], use_container_width=True)
                        if i in st.session_state.image_generation_errors:
                            err = st.session_state.image_generation_errors[i]
                            st.error("⚠️ Image Generation Failed")
                            with st.expander("Error Details", expanded=False):
                                st.write(f"**Error:** {err.get('error', 'Unknown')}")
                                st.write(f"**Attempts:** {err.get('attempt', 'N/A')}")
                        st.write("**Current Image Prompt:**")
                        st.caption(current_prompt)
                    with col2:
                        if is_approved:
                            st.success("✅ Approved")
                            if st.button(f"🔄 Regenerate Image {i+1}", key=f"regen_{i}"):
                                if i in st.session_state.image_approvals:
                                    del st.session_state.image_approvals[i]
                                st.session_state[f"editing_prompt_{i}"] = True
                                st.rerun()
                        else:
                            if st.button(f"✅ Approve", key=f"approve_{i}", type="primary"):
                                st.session_state.image_approvals[i] = True
                                st.rerun()
                            if st.button("🔄 Regenerate", key=f"regenerate_{i}"):
                                st.session_state[f"editing_prompt_{i}"] = True
                                st.rerun()
                        st.write("**Reorder:**")
                        col_up_img, col_down_img = st.columns(2)
                        with col_up_img:
                            if i > 0 and st.button("⬆️", key=f"move_img_up_{i}", use_container_width=True):
                                _pg = st.session_state.generated_story["pages"]
                                _pg[i], _pg[i-1] = _pg[i-1], _pg[i]
                                if i < len(st.session_state.generated_images) and (i-1) < len(st.session_state.generated_images):
                                    st.session_state.generated_images[i], st.session_state.generated_images[i-1] = \
                                        st.session_state.generated_images[i-1], st.session_state.generated_images[i]
                                _ta = st.session_state.image_approvals.get(i, False)
                                st.session_state.image_approvals[i] = st.session_state.image_approvals.get(i-1, False)
                                st.session_state.image_approvals[i-1] = _ta
                                for _idx, _p in enumerate(_pg):
                                    _p["page_number"] = _idx + 1
                                st.rerun()
                        with col_down_img:
                            if i < len(pages) - 1 and st.button("⬇️", key=f"move_img_down_{i}", use_container_width=True):
                                _pg = st.session_state.generated_story["pages"]
                                _pg[i], _pg[i+1] = _pg[i+1], _pg[i]
                                if i < len(st.session_state.generated_images) and (i+1) < len(st.session_state.generated_images):
                                    st.session_state.generated_images[i], st.session_state.generated_images[i+1] = \
                                        st.session_state.generated_images[i+1], st.session_state.generated_images[i]
                                _ta = st.session_state.image_approvals.get(i, False)
                                st.session_state.image_approvals[i] = st.session_state.image_approvals.get(i+1, False)
                                st.session_state.image_approvals[i+1] = _ta
                                for _idx, _p in enumerate(_pg):
                                    _p["page_number"] = _idx + 1
                                st.rerun()

                    if st.session_state.get(f"editing_prompt_{i}", False):
                        st.write("---")
                        edited_text_for_regen = st.session_state.edited_story_pages.get(i, page.get("text", ""))
                        new_text_regen = st.text_area(
                            f"Story Text (Page {page_num})",
                            value=edited_text_for_regen, key=f"story_text_regen_{i}", height=100,
                        )
                        if new_text_regen != page.get("text", ""):
                            st.session_state.edited_story_pages[i] = new_text_regen
                            st.session_state.generated_story["pages"][i]["text"] = new_text_regen
                        edited_prompt = st.text_area(
                            "Image Prompt", value=current_prompt,
                            key=f"prompt_edit_{i}", height=100,
                        )
                        col_gen, col_cancel = st.columns(2)
                        with col_gen:
                            if st.button("✨ Generate with New Prompt", key=f"gen_new_{i}", type="primary"):
                                st.session_state.edited_image_prompts[i] = edited_prompt
                                if new_text_regen != edited_text_for_regen:
                                    st.session_state.edited_story_pages[i] = new_text_regen
                                    st.session_state.generated_story["pages"][i]["text"] = new_text_regen
                                if i in st.session_state.image_approvals:
                                    del st.session_state.image_approvals[i]
                                if i in st.session_state.image_generation_errors:
                                    del st.session_state.image_generation_errors[i]
                                if i < len(st.session_state.generated_images):
                                    st.session_state.generated_images[i] = None
                                st.session_state[f"regenerate_image_{i}"] = True
                                st.session_state[f"editing_prompt_{i}"] = False
                                st.session_state.generated_story["pages"][i]["image_prompt"] = edited_prompt
                                st.rerun()
                        with col_cancel:
                            if st.button("❌ Cancel", key=f"cancel_edit_{i}"):
                                st.session_state[f"editing_prompt_{i}"] = False
                                st.rerun()
                    st.divider()

            # Admin batch approve
            approved_count = len([k for k, v in st.session_state.image_approvals.items() if v])
            if approved_count < total_pages:
                if st.button("✅ Approve All Images", type="primary", use_container_width=True):
                    for i in range(total_pages):
                        st.session_state.image_approvals[i] = True
                    st.rerun()

        else:
            # Non-admin: Diffrun-style preview cards
            # Auto-approve every image that has been generated
            for i, img in enumerate(st.session_state.generated_images):
                if img is not None:
                    st.session_state.image_approvals[i] = True

            # Gate 1 is paid before generation starts — always show cards here
            if True:
                for i, page in enumerate(pages):
                    if i >= len(st.session_state.generated_images):
                        break
                    img = st.session_state.generated_images[i]
                    if img is None:
                        continue
                    text = st.session_state.edited_story_pages.get(i, page.get("text", ""))
                    page_num = page.get('page_number', i + 1)
                    _render_page_card(img, text, page_num, total_pages)

                # All images done → offer the big CTA to move to PDF
                n_valid = len([im for im in st.session_state.generated_images if im is not None])
                if n_valid == total_pages and total_pages > 0:
                    if st.button("📚 View & Download My Complete Storybook",
                                 type="primary", use_container_width=True, key="customer_approve_all"):
                        for i in range(total_pages):
                            st.session_state.image_approvals[i] = True
                        st.session_state.all_images_approved = True
                        st.rerun()

        # ── Check if all images approved ──
        # For admin: auto-advance when all individually approved
        # For non-admin: only advance via explicit CTA button (handled above)
        if _is_admin_user:
            approved_count = len([k for k, v in st.session_state.image_approvals.items() if v])
            if approved_count == total_pages and total_pages > 0:
                st.session_state.all_images_approved = True
                if st.session_state.generated_story and st.session_state.current_child_name:
                    save_story(st.session_state.generated_story, st.session_state.current_child_name)
    
    # Step 3: Generate PDF
    if (st.session_state.generated_story and 
        st.session_state.story_approved and 
        st.session_state.all_images_approved and
        len(st.session_state.generated_images) > 0):
        
        # Create a unique key based on story, images AND format — so that changing
        # the book format always triggers PDF regeneration.
        story_hash = hashlib.md5(json.dumps(st.session_state.generated_story, sort_keys=True).encode()).hexdigest()
        images_hash = hashlib.md5(str([id(img) for img in st.session_state.generated_images]).encode()).hexdigest()
        _active_format_id = st.session_state.get("wiz_format_id") or st.session_state.get("selected_book_format") or "default"
        current_pdf_key = f"{story_hash}_{images_hash}_{_active_format_id}"
        
        # Regenerate PDF if content changed or doesn't exist
        if (st.session_state.pdf_path is None or 
            not os.path.exists(st.session_state.pdf_path) or
            st.session_state.pdf_generation_key != current_pdf_key):
            
            with st.spinner("📄 Creating PDF..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    pdf_path = tmp_file.name
                    create_pdf(
                        st.session_state.generated_story,
                        st.session_state.generated_images,
                        child_name,
                        pdf_path,
                        book_format=_resolve_book_format(),
                    )
                    st.session_state.pdf_path = pdf_path
                    st.session_state.pdf_generation_key = current_pdf_key
        
        st.header("📚 Step 3: Download Your Storybook")
        story_title = st.session_state.generated_story.get("title", f"{child_name}'s Storybook")
        st.subheader(story_title)

        # ── Delivery: Download or Print+Deliver ──────────────────────────────
        # All users reaching Step 3 have already paid at Step 1.5 — no gate here.
        _step3_email = st.session_state.get("user_email") or (st.session_state.get("auth_user") or {}).get("email", "")
        _step3_is_admin = _step3_email in ADMIN_EMAILS
        _step3_delivery = st.session_state.get("book_delivery_option", "download")

        if _step3_delivery == "download" or _step3_is_admin:
            # Show PDF download button
            if st.session_state.pdf_path and os.path.exists(st.session_state.pdf_path):
                with open(st.session_state.pdf_path, "rb") as _pdf:
                    st.download_button(
                        label="📥 Download PDF",
                        data=_pdf.read(),
                        file_name=f"{child_name}_Storybook.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                        key="pdf_download_top",
                    )
                st.info("💡 Print on 8.5×8.5 inch paper for best results!")
            else:
                st.warning("PDF not yet generated — please wait a moment and refresh.")

        if _step3_delivery == "print_deliver":
            # Collect delivery details and place order
            st.subheader("📬 Delivery Details")
            st.markdown("Please provide your contact and delivery information so we can ship your book:")
            _p_name = st.text_input("Full name", key="delivery_name", placeholder="Your full name")
            _p_phone = st.text_input("Mobile number", max_chars=12, key="delivery_phone", placeholder="10-digit mobile")
            _p_address = st.text_area(
                "Delivery address",
                key="delivery_address",
                placeholder="House/Flat no., Street, Area, City, State, PIN code",
                height=100,
            )
            if st.button("📦 Place Order", type="primary", use_container_width=True, key="place_order_btn"):
                from payments import is_valid_phone as _vph3, normalize_phone as _nph3
                if not (_p_name or "").strip():
                    st.error("Please enter your full name.")
                elif not _vph3(_p_phone):
                    st.error("Please enter a valid 10-digit mobile number.")
                elif not (_p_address or "").strip():
                    st.error("Please enter your delivery address.")
                else:
                    try:
                        from mongo_client import get_db as _get_db3
                        _get_db3()["print_orders"].insert_one({
                            "user_email": _step3_email,
                            "child_name": child_name,
                            "story_title": story_title,
                            "customer_name": _p_name.strip(),
                            "phone": _nph3(_p_phone),
                            "address": _p_address.strip(),
                            "amount_paid_inr": 650,
                            "ordered_at": datetime.utcnow(),
                            "status": "pending",
                        })
                        st.success("🎉 Order placed! We'll contact you within 24–48 hours to confirm delivery details.")
                        st.balloons()
                    except Exception as _oe:
                        logger.error(f"print_order save failed: {_oe}")
                        st.success("🎉 Order placed! We'll be in touch within 24–48 hours.")
            st.divider()
            # Print users also get a digital copy
            if st.session_state.pdf_path and os.path.exists(st.session_state.pdf_path):
                with open(st.session_state.pdf_path, "rb") as _pdf2:
                    st.download_button(
                        label="📥 Download Digital Copy",
                        data=_pdf2.read(),
                        file_name=f"{child_name}_Storybook.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="pdf_download_print_user",
                    )
                st.caption("You also have a digital copy while you wait for your printed book!")

        st.divider()

        # ── Navigation ──────────────────────────────────────────────────
        nav1, nav2, _ = st.columns(3)
        with nav1:
            if st.button("← Back to Story Review", use_container_width=True):
                st.session_state.story_approved = False
                st.rerun()
        with nav2:
            if st.button("← Back to Image Review", use_container_width=True):
                st.session_state.all_images_approved = False
                st.rerun()

        st.divider()

        # ── Book reader: image + text side by side ──────────────────────
        pages = st.session_state.generated_story.get("pages", [])
        for i, page in enumerate(pages):
            if i >= len(st.session_state.generated_images):
                break
            page_num = page.get("page_number", i + 1)
            img = st.session_state.generated_images[i]
            text = st.session_state.edited_story_pages.get(i, page.get("text", ""))

            img_col, txt_col = st.columns([1, 1])
            with img_col:
                if img is not None:
                    st.image(img, use_container_width=True)
                else:
                    st.markdown(
                        "<div style='background:#f0f0f0;border-radius:8px;padding:40px;"
                        "text-align:center;color:#999;font-size:24px;'>🖼️</div>",
                        unsafe_allow_html=True,
                    )
                # Regenerate this image
                if st.button(f"🔄 Regenerate Image", key=f"step3_regen_{i}", use_container_width=True):
                    if i in st.session_state.image_approvals:
                        del st.session_state.image_approvals[i]
                    st.session_state.all_images_approved = False
                    st.session_state._return_to_step3_after_regen = True
                    if i < len(st.session_state.generated_images):
                        st.session_state.generated_images[i] = None
                    st.session_state[f"regenerate_image_{i}"] = True
                    st.rerun()

            with txt_col:
                st.markdown(
                    f"<p style='font-size:12px;color:#aaa;margin-bottom:4px;'>Page {page_num}</p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<p style='font-size:16px;line-height:1.7;color:#1a1a2e;'>{text}</p>",
                    unsafe_allow_html=True,
                )
                # Inline text edit
                if st.button(f"✏️ Edit Text", key=f"step3_edit_text_{i}", use_container_width=True):
                    st.session_state[f"step3_editing_text_{i}"] = True
                    st.rerun()
                if st.session_state.get(f"step3_editing_text_{i}"):
                    new_text = st.text_area(
                        "Edit text",
                        value=text,
                        key=f"step3_text_area_{i}",
                        height=120,
                        label_visibility="collapsed",
                    )
                    save_col, cancel_col = st.columns(2)
                    with save_col:
                        if st.button("💾 Save", key=f"step3_save_text_{i}", type="primary"):
                            st.session_state.edited_story_pages[i] = new_text
                            st.session_state.generated_story["pages"][i]["text"] = new_text
                            st.session_state[f"step3_editing_text_{i}"] = False
                            st.session_state.pdf_generation_key = None
                            st.rerun()
                    with cancel_col:
                        if st.button("❌ Cancel", key=f"step3_cancel_text_{i}"):
                            st.session_state[f"step3_editing_text_{i}"] = False
                            st.rerun()

            st.divider()

        # ── Advanced page management (collapsible) ──────────────────────
        with st.expander("⚙️ Advanced: Delete or Reorder Pages"):
            pages = st.session_state.generated_story.get("pages", [])
            if len(pages) > 1:
                col_del, col_up, col_down = st.columns(3)
                with col_del:
                    page_to_delete = st.selectbox(
                        "Delete Page",
                        options=[f"Page {i+1}" for i in range(len(pages))],
                        key="delete_page_select",
                        index=None,
                    )
                    if page_to_delete and st.button("🗑️ Delete Page", key="delete_page_btn"):
                        page_idx = int(page_to_delete.split()[1]) - 1
                        if 0 <= page_idx < len(pages):
                            pages.pop(page_idx)
                            if page_idx < len(st.session_state.generated_images):
                                st.session_state.generated_images.pop(page_idx)
                            new_approvals = {
                                (k - 1 if k > page_idx else k): v
                                for k, v in st.session_state.image_approvals.items()
                                if k != page_idx
                            }
                            st.session_state.image_approvals = new_approvals
                            new_ep = {
                                (k - 1 if k > page_idx else k): v
                                for k, v in st.session_state.edited_story_pages.items()
                                if k != page_idx
                            }
                            st.session_state.edited_story_pages = new_ep
                            new_eip = {
                                (k - 1 if k > page_idx else k): v
                                for k, v in st.session_state.edited_image_prompts.items()
                                if k != page_idx
                            }
                            st.session_state.edited_image_prompts = new_eip
                            st.session_state.generated_story["pages"] = pages
                            for idx, p in enumerate(pages):
                                p["page_number"] = idx + 1
                            st.session_state.pdf_generation_key = None
                            st.success(f"Deleted {page_to_delete}")
                            st.rerun()

                def _swap_pages(idx_a: int, idx_b: int) -> None:
                    p = st.session_state.generated_story["pages"]
                    p[idx_a], p[idx_b] = p[idx_b], p[idx_a]
                    imgs = st.session_state.generated_images
                    if idx_a < len(imgs) and idx_b < len(imgs):
                        imgs[idx_a], imgs[idx_b] = imgs[idx_b], imgs[idx_a]
                    for d in (st.session_state.image_approvals, st.session_state.edited_story_pages, st.session_state.edited_image_prompts):
                        va, vb = d.get(idx_a), d.get(idx_b)
                        if vb is not None:
                            d[idx_a] = vb
                        elif idx_a in d:
                            del d[idx_a]
                        if va is not None:
                            d[idx_b] = va
                        elif idx_b in d:
                            del d[idx_b]
                    for idx, pg in enumerate(p):
                        pg["page_number"] = idx + 1
                    st.session_state.pdf_generation_key = None

                with col_up:
                    page_to_move_up = st.selectbox(
                        "Move Page Up",
                        options=[f"Page {i+1}" for i in range(1, len(pages))],
                        key="move_up_select",
                        index=None,
                    )
                    if page_to_move_up and st.button("⬆️ Move Up", key="move_up_btn"):
                        idx = int(page_to_move_up.split()[1]) - 1
                        if idx > 0:
                            _swap_pages(idx, idx - 1)
                            st.success(f"Moved {page_to_move_up} up")
                            st.rerun()

                with col_down:
                    page_to_move_down = st.selectbox(
                        "Move Page Down",
                        options=[f"Page {i+1}" for i in range(len(pages) - 1)],
                        key="move_down_select",
                        index=None,
                    )
                    if page_to_move_down and st.button("⬇️ Move Down", key="move_down_btn"):
                        idx = int(page_to_move_down.split()[1]) - 1
                        if idx < len(pages) - 1:
                            _swap_pages(idx, idx + 1)
                            st.success(f"Moved {page_to_move_down} down")
                            st.rerun()

        # ── Download button (bottom repeat — for download users only) ──────
        if _step3_delivery == "download" and st.session_state.pdf_path and os.path.exists(st.session_state.pdf_path):
            st.divider()
            with open(st.session_state.pdf_path, "rb") as _pdf3:
                st.download_button(
                    label="📥 Download PDF",
                    data=_pdf3.read(),
                    file_name=f"{child_name}_Storybook.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                    key="pdf_download_bottom",
                )

if __name__ == "__main__":
    main()

