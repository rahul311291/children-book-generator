import streamlit as st
import json
import os
import tempfile
import base64
import hashlib
import logging
from pathlib import Path
from typing import List, Dict
from reportlab.lib.units import inch
import requests
from datetime import datetime

# Import age-specific prompts from the editable prompts file
from story_prompts import get_full_prompt, get_image_style, IMAGE_STYLES

# Import template book functionality
try:
    from template_book_generator import (
        render_template_book_form,
        generate_template_book,
        display_template_book_preview
    )
    from job_history_ui import render_job_history
    TEMPLATE_BOOKS_AVAILABLE = True
except ImportError:
    TEMPLATE_BOOKS_AVAILABLE = False

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
from reportlab.lib.enums import TA_CENTER
from PIL import Image
import io
import time

# Page configuration
st.set_page_config(
    page_title="Children's Book Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
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

# Initialize session state
# Try to load API key from environment variable first (for secure backend storage)
if 'api_key' not in st.session_state:
    # Check environment variable first, then use empty string
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")
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
    st.session_state.stories_dir = Path("saved_stories")
    st.session_state.stories_dir.mkdir(exist_ok=True)
if 'current_child_name' not in st.session_state:
    st.session_state.current_child_name = ""  # Track current child name for auto-save

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

def save_story(story_data: Dict, child_name: str, metadata: Dict = None):
    """Save story to history."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{child_name}_{timestamp}.json"
        filepath = st.session_state.stories_dir / filename
        
        # Save journey state to resume where user left off
        journey_state = {
            "story_approved": st.session_state.get("story_approved", False),
            "all_images_approved": st.session_state.get("all_images_approved", False),
            "image_approvals": st.session_state.get("image_approvals", {}),
            "edited_story_pages": st.session_state.get("edited_story_pages", {}),
            "edited_image_prompts": st.session_state.get("edited_image_prompts", {}),
            "current_step": "step3" if st.session_state.get("all_images_approved", False) else 
                           ("step2" if st.session_state.get("story_approved", False) else "step1")
        }
        
        save_data = {
            "story": story_data,
            "metadata": metadata or {},
            "timestamp": timestamp,
            "child_name": child_name,
            "journey_state": journey_state  # Save where user was in the journey
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    except Exception as e:
        st.error(f"Failed to save story: {e}")
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
    """Get list of all saved stories."""
    try:
        stories = []
        if st.session_state.stories_dir.exists():
            for filepath in sorted(st.session_state.stories_dir.glob("*.json"), reverse=True):
                try:
                    data = load_story(filepath)
                    if data:
                        stories.append({
                            "filepath": filepath,
                            "child_name": data.get("child_name", "Unknown"),
                            "timestamp": data.get("timestamp", ""),
                            "title": data.get("story", {}).get("title", "Untitled Story")
                        })
                except:
                    continue
        return stories
    except Exception as e:
        st.warning(f"Could not load story history: {e}")
        return []

def reset_story_state():
    """Reset all story-related session state - COMPLETE RESET."""
    st.session_state.generated_story = None
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
    # Clear ALL dynamic flags that might be left over
    keys_to_delete = []
    for key in st.session_state.keys():
        if (key.startswith("regen_from_page_") or 
            key.startswith("regen_page_prompt_") or 
            key.startswith("editing_prompt_") or
            key.startswith("regenerate_image_") or
            key.startswith("story_text_") or
            key.startswith("image_prompt_") or
            key.startswith("move_") or
            key.startswith("regen_") or
            key.startswith("final_edit_")):
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

        # Use same model selection logic
        available_models = list_available_models(api_key)
        preferred_models = ['gemini-3-pro', 'gemini-3.0-pro', 'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash-exp']
        model_names = [m for m in preferred_models if m in available_models] if available_models else preferred_models
        
        if not model_names and available_models:
            text_models = [m for m in available_models if 'image' not in m.lower() and 'vision' not in m.lower()]
            model_names = text_models[:3] if text_models else ['gemini-1.5-pro']
        
        response_text = None
        last_error = None
        
        for model_name in model_names:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.8, "topK": 40, "topP": 0.95}
                }
                params = {"key": api_key}
                
                response = requests.post(url, headers=headers, json=payload, params=params)
                response.raise_for_status()
                
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    parts = result["candidates"][0].get("content", {}).get("parts", [])
                    response_text = ""
                    for part in parts:
                        if "text" in part:
                            response_text += part["text"]
                    response_text = response_text.strip()
                    logger.info(f"Successfully got response from {model_name}, length: {len(response_text)}")
                    break
            except Exception as e:
                logger.error(f"Error with model {model_name}: {e}")
                last_error = e
                continue
        
        if response_text is None:
            error_msg = f"Could not regenerate story with any model. Last error: {last_error}"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}")
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
        
        # Handle format mapping and ensure visual anchor
        visual_anchor = story_data.get("visual_anchor", existing_visual_anchor)
        for page in story_data.get("pages", []):
            if "visual_description" in page and "image_prompt" not in page:
                page["image_prompt"] = page["visual_description"]
            image_prompt = page.get("image_prompt", "")
            if visual_anchor and visual_anchor not in image_prompt:
                page["image_prompt"] = f"{visual_anchor}, {image_prompt}"
        
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
    """Refine existing story based on follow-up prompt - simplified direct approach."""
    try:
        logger.info(f"Starting story refinement for {child_name} with prompt: {followup_prompt[:100]}...")
        
        # Get existing story structure
        existing_pages = existing_story.get("pages", [])
        existing_title = existing_story.get("title", "Story")
        existing_visual_anchor = existing_story.get("visual_anchor", "")
        
        # Create full story JSON for context
        existing_story_json = json.dumps(existing_story, indent=2, ensure_ascii=False)
        logger.info(f"Original story has {len(existing_pages)} pages")
        
        # Detect if this is about medical/health issues
        is_medical_issue = any(keyword in followup_prompt.lower() for keyword in [
            'doctor', 'medical', 'hospital', 'clinic', 'medicine', 'treatment', 
            'ginger', 'home remedy', 'home made', 'remedy', 'cure', 'sick', 'illness'
        ])
        
        medical_instruction = ""
        if is_medical_issue:
            medical_instruction = """
**CRITICAL MEDICAL CONTEXT:**
- If the instructions mention going to a doctor, hospital, or medical professional, you MUST replace any home remedies (like ginger, turmeric, home-made solutions) with proper medical care
- The story should show the character visiting a doctor or medical professional when health issues arise
- Do NOT use home remedies as the primary solution for medical problems
- Medical issues should be resolved through professional medical care, not home remedies
"""
        
        # Strong, explicit prompt that forces changes
        prompt = f"""You are a story editor. Your job is to MODIFY an existing children's story based on specific instructions. You MUST make changes - returning the same story is NOT acceptable.

**CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE EXACTLY:**
{followup_prompt}
{medical_instruction}

**ABSOLUTE REQUIREMENTS (DO NOT SKIP):**
1. You MUST change the story text in at least 5-7 pages (not just 1-2 pages)
2. DO NOT copy the original text - rewrite it with the requested changes
3. If instructions mention "doctor" or "medical", you MUST replace ALL mentions of home remedies (ginger, turmeric, etc.) with doctor visits
4. If the original has "ginger" anywhere, and instructions want "doctor", change EVERY instance
5. Keep the same JSON structure (10 pages, visual_anchor, etc.)
6. Keep visual_anchor exactly as is: {existing_visual_anchor}
7. The modified story MUST be clearly different - someone reading both should notice the changes immediately

**ORIGINAL STORY (DO NOT COPY THIS - MODIFY IT):**
{existing_story_json}

**YOUR TASK:**
1. Read the instructions carefully: {followup_prompt}
2. Go through EACH page of the original story
3. Modify the "text" field to incorporate the requested changes
4. Make sure at least 5-7 pages have visible changes
5. If instructions mention "doctor" and original has "ginger" or "home remedy", replace those completely

**SPECIFIC EXAMPLES OF REQUIRED CHANGES:**
- Original: "Mama gave ginger tea to help" → Modified: "Mama took [child] to the doctor for help"
- Original: "Grandma's home remedy worked" → Modified: "The doctor's treatment worked"
- Original: "They tried turmeric" → Modified: "They visited the clinic"

**OUTPUT:**
Return ONLY the modified JSON. Every page's "text" field should reflect the requested changes. Do NOT return the same JSON. Output ONLY valid JSON, no markdown, no explanations."""

        # Use same model selection logic as generate_story_with_gemini
        available_models = list_available_models(api_key)
        preferred_models = ['gemini-3-pro', 'gemini-3.0-pro', 'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash-exp']
        model_names = [m for m in preferred_models if m in available_models] if available_models else preferred_models
        
        if not model_names and available_models:
            text_models = [m for m in available_models if 'image' not in m.lower() and 'vision' not in m.lower()]
            model_names = text_models[:3]
        
        if not model_names:
            model_names = ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash-exp']
        
        logger.info(f"Trying models: {model_names}")
        response_text = None
        last_error = None
        
        for model_name in model_names:
            try:
                logger.info(f"Attempting refinement with model: {model_name}")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.8, "topK": 40, "topP": 0.95}  # Slightly higher temp for more variation
                }
                params = {"key": api_key}
                
                response = requests.post(url, headers=headers, json=payload, params=params)
                response.raise_for_status()
                
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    parts = result["candidates"][0].get("content", {}).get("parts", [])
                    response_text = ""
                    for part in parts:
                        if "text" in part:
                            response_text += part["text"]
                    response_text = response_text.strip()
                    logger.info(f"Successfully got response from {model_name}, length: {len(response_text)}")
                    break
            except Exception as e:
                logger.error(f"Error with model {model_name}: {e}")
                last_error = e
                continue
        
        if response_text is None:
            error_msg = f"Could not refine story with any model. Last error: {last_error}"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}")
            if last_error:
                st.error(f"Details: {str(last_error)}")
            return None
        
        # Extract JSON
        original_response = response_text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            story_data = json.loads(response_text)
            logger.info("Successfully parsed refined story JSON")
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {e}"
            logger.error(f"{error_msg}. Response: {original_response[:500]}")
            st.error(f"❌ {error_msg}")
            st.expander("View API Response", expanded=False).code(original_response[:2000])
            return None
        
        # Handle format mapping
        visual_anchor = story_data.get("visual_anchor", existing_visual_anchor)
        for page in story_data.get("pages", []):
            if "visual_description" in page and "image_prompt" not in page:
                page["image_prompt"] = page["visual_description"]
            image_prompt = page.get("image_prompt", "")
            if visual_anchor and visual_anchor not in image_prompt:
                page["image_prompt"] = f"{visual_anchor}, {image_prompt}"
        
        # Verify we got a valid story structure
        if not story_data.get("pages") or len(story_data.get("pages", [])) == 0:
            error_msg = "Refined story has no pages"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}. Please try again.")
            return None
        
        # Log comparison to detect if story actually changed
        original_texts = [p.get("text", "").strip() for p in existing_pages]
        refined_texts = [p.get("text", "").strip() for p in story_data.get("pages", [])]
        changes_detected = original_texts != refined_texts
        
        # Count how many pages actually changed
        changed_pages = sum(1 for i, (orig, ref) in enumerate(zip(original_texts, refined_texts)) if orig != ref)
        
        logger.info(f"Story refinement complete. Pages: {len(story_data.get('pages', []))}, Total pages changed: {changed_pages}/{len(original_texts)}")
        
        if not changes_detected:
            logger.warning("⚠️ Refined story appears identical to original - AI may not have applied changes")
            logger.warning(f"Original story preview: {original_texts[0][:100] if original_texts else 'N/A'}")
            logger.warning(f"Refined story preview: {refined_texts[0][:100] if refined_texts else 'N/A'}")
        else:
            logger.info(f"✅ Story successfully modified! {changed_pages} pages changed.")
            # Log a sample of changes
            for i, (orig, ref) in enumerate(zip(original_texts, refined_texts)):
                if orig != ref:
                    logger.info(f"Page {i+1} changed: '{orig[:50]}...' -> '{ref[:50]}...'")
                    break  # Just log first change
        
        return story_data
        
    except Exception as e:
        error_msg = f"Error refining story: {e}"
        logger.error(error_msg, exc_info=True)
        st.error(f"❌ {error_msg}")
        import traceback
        with st.expander("Error Details", expanded=False):
            st.code(traceback.format_exc())
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
        
        # Use same model selection logic
        available_models = list_available_models(api_key)
        preferred_models = ['gemini-3-pro', 'gemini-3.0-pro', 'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash-exp']
        model_names = [m for m in preferred_models if m in available_models] if available_models else preferred_models
        
        if not model_names and available_models:
            text_models = [m for m in available_models if 'image' not in m.lower() and 'vision' not in m.lower()]
            model_names = text_models[:3] if text_models else ['gemini-1.5-pro']
        
        response_text = None
        last_error = None
        
        for model_name in model_names:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.8, "topK": 40, "topP": 0.95}
                }
                params = {"key": api_key}
                
                response = requests.post(url, headers=headers, json=payload, params=params)
                response.raise_for_status()
                
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    parts = result["candidates"][0].get("content", {}).get("parts", [])
                    response_text = ""
                    for part in parts:
                        if "text" in part:
                            response_text += part["text"]
                    response_text = response_text.strip()
                    logger.info(f"Successfully got response from {model_name}")
                    break
            except Exception as e:
                logger.error(f"Error with model {model_name}: {e}")
                last_error = e
                continue
        
        if response_text is None:
            error_msg = f"Could not regenerate story. Last error: {last_error}"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}")
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
        
        # Handle format mapping and ensure visual anchor
        visual_anchor = story_data.get("visual_anchor", existing_visual_anchor)
        for page in story_data.get("pages", []):
            if "visual_description" in page and "image_prompt" not in page:
                page["image_prompt"] = page["visual_description"]
            image_prompt = page.get("image_prompt", "")
            if visual_anchor and visual_anchor not in image_prompt:
                page["image_prompt"] = f"{visual_anchor}, {image_prompt}"
        
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
                               story_type: str = "Behavioral/Problem-solving", image_style: str = "Cartoon/Animated (3D Pixar Style)") -> Dict:
    """Generate story using Gemini API via REST."""
    try:
        logger.info(f"Generating story for {child_name}, age {age}, problem: {problem[:50]}...")
        # Create visual anchor (incorporate character style)
        visual_anchor = create_visual_anchor(child_name, age, gender, physical_desc, character_choice)
        
        # ============================================================================
        # AGE-SPECIFIC PROMPTS - Edit story_prompts.py to customize prompts
        # ============================================================================
        # All prompts are now in story_prompts.py - edit that file to change prompts
        # Each age group (2-3, 3-4, 4-5, 5-6, 6-7, 7-8, 8-10) has its own section
        
        prompt = get_full_prompt(
            age=age,
            child_name=child_name,
            gender=gender,
            story_theme=problem,
            language=language,
            family_info=family_structure,
            hero_trait=hero_trait,
            character_companion=character_choice
        )
        
        logger.info(f"Using age-specific prompt for age {age}")
        
        # ============================================================================
        # END OF PROMPT SECTION
        # ============================================================================

        # Try to list available models first, then use appropriate ones
        available_models = list_available_models(api_key)
        
        # Priority order: try Gemini 3.x first, then 1.5 Pro, then Flash
        preferred_models = ['gemini-3-pro', 'gemini-3.0-pro', 'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash-exp']
        
        # Filter to only models that are actually available
        model_names = [m for m in preferred_models if m in available_models] if available_models else preferred_models
        
        # If no preferred models found, try all available models that support generateContent
        if not model_names and available_models:
            # Filter models that likely support text generation (exclude image-only models)
            text_models = [m for m in available_models if 'image' not in m.lower() and 'vision' not in m.lower()]
            model_names = text_models[:3]  # Try first 3 text models
        
        # Fallback to common models if listing failed
        if not model_names:
            model_names = ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash-exp']
        
        response_text = None
        last_error = None
        
        for model_name in model_names:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                }
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topK": 40,
                        "topP": 0.95
                    }
                }
                params = {"key": api_key}
                
                response = requests.post(url, headers=headers, json=payload, params=params)
                response.raise_for_status()
                
                result = response.json()
                
                # Extract text from response
                if "candidates" in result and len(result["candidates"]) > 0:
                    parts = result["candidates"][0].get("content", {}).get("parts", [])
                    response_text = ""
                    for part in parts:
                        if "text" in part:
                            response_text += part["text"]
                    response_text = response_text.strip()
                    break
            except Exception as e:
                last_error = e
                continue
        
        if response_text is None:
            error_msg = f"Could not generate story with any model. Tried: {model_names}."
            if available_models:
                error_msg += f" Available models: {', '.join(available_models[:10])}"
            if last_error:
                error_msg += f" Last error: {last_error}"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}")
            return None
        
        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        story_data = json.loads(response_text)
        
        # Handle new format: map "visual_description" to "image_prompt" for compatibility
        visual_anchor = story_data.get("visual_anchor", visual_anchor)
        for page in story_data.get("pages", []):
            # If using new format with "visual_description", map it to "image_prompt"
            if "visual_description" in page and "image_prompt" not in page:
                page["image_prompt"] = page["visual_description"]
            # Ensure visual anchor is in image prompt
            image_prompt = page.get("image_prompt", "")
            if visual_anchor and visual_anchor not in image_prompt:
                page["image_prompt"] = f"{visual_anchor}, {image_prompt}"
        
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

def generate_image_with_imagen(api_key: str, prompt: str, retry_count: int = 0, image_style: str = None, image_index: int = None) -> Image.Image:
    """Generate image using Gemini 3 Pro Image Preview (Nano Banana Pro) via REST API."""
    try:
        # Clear any previous error for this image
        if image_index is not None and image_index in st.session_state.image_generation_errors:
            del st.session_state.image_generation_errors[image_index]
        logger.info(f"Generating image (attempt {retry_count + 1}), prompt: {prompt[:100]}...")
        # ============================================================================
        # IMAGE STYLE PROMPT - Based on user selection
        # ============================================================================
        # Get image style from session state if not passed directly
        if image_style is None:
            image_style = st.session_state.get("image_style", "Cartoon/Animated (3D Pixar Style)")
        
        logger.info(f"Image style selected: {image_style}")
        
        # Get style modifiers from story_prompts.py (all styles defined in one place)
        style_modifiers = get_image_style(image_style)
        
        logger.info(f"Style modifiers applied: {style_modifiers[:50]}...")
        # ============================================================================
        
        # Enhanced prompt with style - STRONG guardrail to prevent text in images
        # Add this instruction at the BEGINNING and END of prompt for maximum emphasis
        no_text_instruction = "CRITICAL REQUIREMENT - ABSOLUTELY NO TEXT: This image must contain ZERO text, ZERO words, ZERO letters, ZERO numbers, ZERO speech bubbles, ZERO captions, ZERO signs, ZERO labels, ZERO writing of any kind. This is a pure illustration for a children's book - visual art only. Any visible text will make the image completely unusable. Generate ONLY visual elements - characters, objects, backgrounds - but NO text whatsoever."
        style_prompt = f"{no_text_instruction}. {prompt}. {style_modifiers}. {no_text_instruction}"
        
        # Use REST API matching the user's working example
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"
        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [{
                "parts": [{
                    "text": style_prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "topK": 32,
                "topP": 1,
                "imageConfig": {
                    "aspectRatio": "1:1",
                    "imageSize": "2K"
                }
            }
        }
        params = {"key": api_key}
        
        response = requests.post(url, headers=headers, json=payload, params=params)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract image from response
        if "candidates" in result and len(result["candidates"]) > 0:
            parts = result["candidates"][0].get("content", {}).get("parts", [])
            for part in parts:
                if "inlineData" in part:
                    image_data = part["inlineData"]["data"]
                    image_bytes = base64.b64decode(image_data)
                    image = Image.open(io.BytesIO(image_bytes))
                    logger.info("Image generated successfully")
                    return image
        
        error_msg = "No image generated in response"
        logger.error(error_msg)
        raise Exception(error_msg)
            
    except Exception as e:
        error_msg = f"Image generation failed: {e}"
        logger.error(f"{error_msg} (attempt {retry_count + 1})")

        # Store detailed error information
        error_details = {
            "error": str(e),
            "full_error": error_msg,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "attempt": retry_count + 1
        }

        if retry_count < 1:
            logger.info(f"Retrying image generation...")
            st.warning(f"⚠️ Image generation failed, retrying... ({str(e)[:100]})")
            time.sleep(2)
            return generate_image_with_imagen(api_key, prompt, retry_count + 1, image_style, image_index)
        else:
            logger.error(f"Image generation failed after all retries")

            # Store error in session state for this specific image
            if image_index is not None:
                st.session_state.image_generation_errors[image_index] = error_details

            st.error(f"❌ Failed to generate image after retries: {str(e)[:200]}")

            # Return placeholder image
            placeholder = Image.new('RGB', (512, 512), color=(200, 200, 200))
            return placeholder

def create_pdf(story_data: Dict, images: List[Image.Image], child_name: str, output_path: str):
    """Create PDF using reportlab."""
    # Page size: 8.5 x 8.5 inches
    page_width = 8.5 * inch
    page_height = 8.5 * inch
    
    c = canvas.Canvas(output_path, pagesize=(page_width, page_height))
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='black',
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    text_style = ParagraphStyle(
        'CustomText',
        parent=styles['BodyText'],
        fontSize=18,
        textColor='black',
        alignment=TA_CENTER,
        leading=24
    )
    
    # Dedication Page
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(page_width / 2, page_height / 2 + 50, "This book belongs to")
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(page_width / 2, page_height / 2 - 20, child_name)
    c.showPage()
    
    # Story Pages
    pages = story_data.get("pages", [])
    for idx, page in enumerate(pages):
        if idx >= len(images):
            break
        
        # Layout: 5% top margin, 85% image, 10% text at bottom
        top_margin = page_height * 0.05
        image_area_height = page_height * 0.85
        text_area_height = page_height * 0.10
        
        # Common width for both image and text (aligned)
        content_width = page_width - 40  # 20px margin on each side
        content_x_offset = 20  # Left margin
        
        # ===== IMAGE AREA (85% - after 5% top margin) =====
        image_y_start = page_height - top_margin - image_area_height  # Start after top margin
        image_available_height = image_area_height
        
        # Resize and place image
        img = images[idx]
        img_width, img_height = img.size
        aspect_ratio = img_width / img_height
        
        # Calculate image dimensions to fit in 85% area, using common width
        if aspect_ratio > 1:
            # Landscape image - use common width
            display_width = content_width
            display_height = display_width / aspect_ratio
            if display_height > image_available_height:
                display_height = image_available_height
                display_width = display_height * aspect_ratio
        else:
            # Portrait/square image - fit to height, but respect max width
            display_height = image_available_height
            display_width = display_height * aspect_ratio
            if display_width > content_width:
                display_width = content_width
                display_height = display_width / aspect_ratio
        
        # Center image horizontally
        image_x_offset = (page_width - display_width) / 2
        # Position image in the 85% area, centered vertically
        image_y_offset = image_y_start + (image_available_height - display_height) / 2
        
        img_resized = img.resize((int(display_width), int(display_height)), Image.Resampling.LANCZOS)
        img_io = io.BytesIO()
        img_resized.save(img_io, format='PNG')
        img_io.seek(0)
        
        c.drawImage(ImageReader(img_io), image_x_offset, image_y_offset, 
                   width=display_width, height=display_height, preserveAspectRatio=True)
        
        # ===== TEXT AREA (Bottom 10%) =====
        # Make text width match image width (or slightly less) and center-align with image
        text_width = display_width * 0.95  # Slightly less than image width (5% smaller)
        text_x_offset = image_x_offset + (display_width - text_width) / 2  # Center with image
        
        text = page.get("text", "")
        
        # Dynamic font size adjustment based on text length
        # Start with base font size
        base_font_size = 18
        min_font_size = 12
        max_font_size = 20
        
        # Estimate text length (rough calculation)
        text_length = len(text)
        char_per_line_estimate = int(text_width / (base_font_size * 0.6))  # Rough chars per line
        estimated_lines = max(1, text_length / char_per_line_estimate)
        
        # Adjust font size based on estimated lines needed
        if estimated_lines > 3:
            # Text is long, reduce font size
            font_size = max(min_font_size, base_font_size - (estimated_lines - 3) * 1.5)
        else:
            font_size = min(max_font_size, base_font_size + (3 - estimated_lines) * 0.5)
        
        # Create text style with dynamic font size
        dynamic_text_style = ParagraphStyle(
            'DynamicText',
            parent=text_style,
            fontSize=font_size,
            textColor='black',
            alignment=TA_CENTER,
            leading=font_size * 1.3  # Line spacing proportional to font size
        )
        
        para = Paragraph(text, dynamic_text_style)
        para_height = para.wrap(text_width, text_area_height)[1]
        
        # If text still doesn't fit, reduce font size further
        if para_height > text_area_height * 0.95:  # 95% of available space
            # Reduce font size more aggressively
            font_size = max(min_font_size, font_size * 0.85)
            dynamic_text_style = ParagraphStyle(
                'DynamicText',
                parent=text_style,
                fontSize=font_size,
                textColor='black',
                alignment=TA_CENTER,
                leading=font_size * 1.3
            )
            para = Paragraph(text, dynamic_text_style)
            para_height = para.wrap(text_width, text_area_height)[1]
        
        # Position text at bottom 10%, centered vertically in text area, aligned with image center
        text_y = (text_area_height - para_height) / 2
        para.drawOn(c, text_x_offset, text_y)
        
        c.showPage()
    
    c.save()

def main():
    # Initialize show_history state
    if 'show_history' not in st.session_state:
        st.session_state.show_history = False
    
    # Show history page if requested
    if st.session_state.show_history:
        st.title("📚 Story History")
        
        if st.button("← Back to Main", type="secondary"):
            st.session_state.show_history = False
            st.rerun()
        
        st.divider()
        
        history = get_story_history()
        
        if history:
            st.info(f"Found {len(history)} saved stories. These are your backups - you can load any story to view, edit, and regenerate images or PDF.")
            st.markdown("**Note:** When you load a story, you'll need to regenerate images since they're not saved. The story text and prompts are preserved.")
            
            for idx, story_info in enumerate(history):
                display_name = f"{story_info['child_name']} - {story_info['title']}"
                timestamp_display = story_info['timestamp'].replace('_', ' ')[:16] if story_info['timestamp'] else ""
                
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{display_name}**")
                        st.caption(f"Saved: {timestamp_display}")
                        # Show file path for reference
                        filepath_display = story_info['filepath']
                        if isinstance(filepath_display, Path):
                            st.caption(f"File: {filepath_display.name}")
                        else:
                            st.caption(f"File: {Path(str(filepath_display)).name}")
                    with col2:
                        if st.button("📖 Load Story", key=f"load_history_{idx}", use_container_width=True):
                            # Ensure filepath is a Path object
                            filepath = story_info['filepath']
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
                                        
                                        # Restore journey state if available
                                        journey_state = loaded_data.get("journey_state", {})
                                        child_name_from_file = loaded_data.get("child_name", story_info.get('child_name', 'Story'))
                                        
                                        if journey_state:
                                            # Restore where user was in the journey
                                            st.session_state.story_approved = journey_state.get("story_approved", False)
                                            st.session_state.all_images_approved = journey_state.get("all_images_approved", False)
                                            st.session_state.image_approvals = journey_state.get("image_approvals", {})
                                            st.session_state.edited_story_pages = journey_state.get("edited_story_pages", {})
                                            st.session_state.edited_image_prompts = journey_state.get("edited_image_prompts", {})
                                            current_step = journey_state.get("current_step", "step1")
                                            
                                            # Images aren't saved (too large), so clear them but preserve approval state
                                            st.session_state.generated_images = []
                                            st.session_state.pdf_path = None
                                            st.session_state.pdf_generation_key = None
                                            
                                            # Show message based on where they were
                                            if current_step == "step3":
                                                st.success(f"✅ Loaded story: {display_name}. You were at **Step 3 (PDF ready)**. Images need to be regenerated to view/download PDF, but your approval states are preserved.")
                                            elif current_step == "step2":
                                                st.success(f"✅ Loaded story: {display_name}. You were at **Step 2 (Image Review)**. Images need to be regenerated, but your approval states are preserved.")
                                            else:
                                                st.success(f"✅ Loaded story: {display_name}. You were at **Step 1 (Story Review)**.")
                                            
                                            logger.info(f"Restored journey state: {current_step}, story_approved={st.session_state.story_approved}, images_approved={st.session_state.all_images_approved}")
                                        else:
                                            # No journey state saved - start fresh
                                            st.session_state.story_approved = False
                                            st.session_state.all_images_approved = False
                                            st.session_state.edited_story_pages = {}
                                            st.session_state.edited_image_prompts = {}
                                            st.session_state.image_approvals = {}
                                            st.session_state.generated_images = []
                                            st.session_state.pdf_path = None
                                            st.session_state.pdf_generation_key = None
                                            st.success(f"✅ Loaded story: {display_name} ({len(story_data.get('pages', []))} pages). Please review the story below.")
                                        
                                        st.session_state.show_history = False
                                        logger.info(f"Successfully loaded story with {len(story_data.get('pages', []))} pages")
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
    
    st.title("📚 Print-on-Demand Children's Book Generator")
    st.markdown("Create personalized storybooks for children in real-time!")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # New Story Button
        if st.button("🆕 New Story", type="primary", use_container_width=True):
            reset_story_state()
            st.rerun()
        
        st.divider()
        
        # Story History - Button to open history page
        if st.button("📚 Story History", use_container_width=True, type="secondary"):
            st.session_state.show_history = True
            st.rerun()
        
        st.divider()
        
        # Log Viewer
        with st.expander("📋 View Logs", expanded=False):
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        log_lines = f.readlines()
                        # Show last 50 lines
                        recent_logs = log_lines[-50:] if len(log_lines) > 50 else log_lines
                        st.code(''.join(recent_logs))
                    if st.button("Clear Logs", key="clear_logs"):
                        with open(log_file, 'w') as f:
                            f.write("")
                        st.success("Logs cleared")
                        st.rerun()
                except Exception as e:
                    st.error(f"Could not read logs: {e}")
            else:
                st.info("No logs yet")
            st.caption(f"Log file: {log_file}")
        
        st.divider()
        
        # API Key Input
        # Show if API key is set from environment
        env_key_set = bool(os.getenv("GEMINI_API_KEY"))
        if env_key_set:
            env_key_value = os.getenv("GEMINI_API_KEY")
            st.success(f"🔐 API key loaded from environment (length: {len(env_key_value)} chars)")
            api_key = st.session_state.api_key
            if st.button("🔑 Override with Manual Entry", use_container_width=True):
                st.session_state.use_manual_key = True
                st.rerun()
        else:
            api_key = st.text_input(
                "Google Gemini API Key",
                type="password",
                value=st.session_state.api_key,
                help="Enter your Google Gemini API key. Get one from https://makersuite.google.com/app/apikey. Or set GEMINI_API_KEY environment variable for secure storage."
            )
            st.session_state.api_key = api_key
        
        # Allow manual override even if env var is set
        if env_key_set and st.session_state.get("use_manual_key", False):
            api_key = st.text_input(
                "Manual API Key (Override)",
                type="password",
                value=st.session_state.api_key,
                help="Override environment variable with manual entry"
            )
            st.session_state.api_key = api_key
            if st.button("✅ Use Manual Key", use_container_width=True):
                st.session_state.use_manual_key = False
                st.rerun()
        
        st.divider()

        # Book Mode Selection
        if 'book_mode' not in st.session_state:
            st.session_state.book_mode = "Custom Story"

        st.header("📚 Book Mode")
        book_mode_options = ["Custom Story", "Template Book", "Job History"] if TEMPLATE_BOOKS_AVAILABLE else ["Custom Story"]
        st.session_state.book_mode = st.radio(
            "Choose creation mode:",
            options=book_mode_options,
            help="Custom Story: Create a unique personalized story | Template Book: Use pre-designed profession templates | Job History: View and resume previous generations"
        )

        st.divider()

        # Only show custom story form if in Custom Story mode
        if st.session_state.book_mode == "Custom Story":
            st.header("📝 Child Details")

            child_name = st.text_input("Child's Name *", placeholder="Enter child's name")

            age = st.number_input("Age *", min_value=2, max_value=16, value=5, step=1)

            gender = st.selectbox("Gender *", ["Boy", "Girl", "Non-binary"])

            st.subheader("Physical Description")
            skin_tone = st.text_input("Skin Tone", placeholder="e.g., light, medium, dark")
            hair_style = st.text_input("Hair Style/Color", placeholder="e.g., curly black hair")
            eye_color = st.text_input("Eye Color", placeholder="e.g., brown eyes")
            favorite_outfit = st.text_input("Favorite Outfit", placeholder="e.g., blue t-shirt and jeans")

            # Build physical description from non-empty fields
            desc_parts = []
            if skin_tone:
                desc_parts.append(f"{skin_tone} skin")
            if hair_style:
                desc_parts.append(hair_style)
            if eye_color:
                desc_parts.append(eye_color)
            if favorite_outfit:
                desc_parts.append(f"wearing {favorite_outfit}")
            physical_desc = ", ".join(desc_parts) if desc_parts else "average appearance"

            st.divider()

            # Story Type Selection
            story_type = st.selectbox(
                "Story Type *",
                ["Behavioral/Problem-solving", "Adventure", "Bedtime/Calm", "Educational", "Friendship", "Custom/Free-form"],
                help="Choose the type of story you want to create"
            )

            # Image Style Selection
            image_style = st.selectbox(
                "Image Style *",
                ["Cartoon/Animated (3D Pixar Style)", "Cartoon (2D Flat Style)", "Photorealistic", "Watercolor Illustration", "Storybook Classic"],
                help="Choose the visual style for images"
            )
            st.session_state.image_style = image_style  # Save for image generation

            problem = st.text_area(
                "Story Theme / Plot / Idea *",
                placeholder="Examples:\n• Scared of the dark (behavioral)\n• A magical adventure to find a lost teddy bear\n• Learning about planets and space\n• Making a new friend at school\n• Any story idea you have!",
                height=120,
                help="Describe your story idea - can be a problem to solve, an adventure, an educational theme, or any creative plot"
            )

            language = st.selectbox("Language *", ["English", "Hindi"])

            st.divider()

            st.subheader("Advanced Story Options (Optional)")
            family_structure = st.text_input(
                "Family Structure",
                placeholder="e.g., Lives with parents and Nani, Has a big brother",
                help="Describe the child's family context"
            )
            hero_trait = st.text_input(
                "Hero Trait (Child's Strength)",
                placeholder="e.g., Brave, Creative, Helpful, Curious",
                help="The child's natural strength that helps solve the problem"
            )
            character_choice = st.text_input(
                "Famous Character Companion",
                placeholder="e.g., Max and Mini, Peppa Pig, Doraemon, Chhota Bheem",
                help="Famous character to include as a friend in the story. They will appear in the story and images! (optional)"
            )

            st.divider()

            generate_button = st.button("✨ Generate Story", type="primary", use_container_width=True)
        else:
            # Set default values for variables when in Template Book mode
            child_name = ""
            age = 5
            gender = "Boy"
            physical_desc = ""
            story_type = ""
            image_style = ""
            problem = ""
            language = "English"
            family_structure = ""
            hero_trait = ""
            character_choice = ""
            generate_button = False

    # Main content area
    # Get API key from session state (sidebar updates session state)
    api_key = st.session_state.api_key

    # Handle Job History Mode
    if st.session_state.book_mode == "Job History" and TEMPLATE_BOOKS_AVAILABLE:
        render_job_history()
        return

    # Handle Template Book Mode
    if st.session_state.book_mode == "Template Book" and TEMPLATE_BOOKS_AVAILABLE:
        if not api_key:
            st.info("👈 Please enter your Google Gemini API key in the sidebar to get started.")
            return

        if st.session_state.get("generate_template_book", False):
            st.session_state.generate_template_book = False

            job_id = st.session_state.get('resume_job_id')
            if 'resume_job_id' in st.session_state:
                del st.session_state.resume_job_id

            with st.spinner("Generating your personalized template book..."):
                generate_template_book(
                    api_key,
                    st.session_state.template_book_data,
                    job_id=job_id
                )

        if st.session_state.get("template_generated_book"):
            display_template_book_preview(st.session_state.template_generated_book)
            return

        render_template_book_form()
        return

    # Allow viewing loaded stories even without API key (needed for generating new images)
    if not api_key and not st.session_state.generated_story:
        st.info("👈 Please enter your Google Gemini API key in the sidebar to get started.")
        return
    
    if generate_button:
        if not child_name or not problem:
            st.error("Please fill in all required fields (marked with *)")
            return
        
        # Reset approvals when generating new story
        st.session_state.story_approved = False
        st.session_state.image_approvals = {}
        st.session_state.all_images_approved = False
        st.session_state.generated_images = []
        
        with st.spinner("🔄 Generating your personalized story..."):
            story_data = generate_story_with_gemini(
                api_key, child_name, age, gender, physical_desc, problem, language,
                family_structure, hero_trait, character_choice, story_type, image_style
            )
            
            if not story_data:
                st.error("Failed to generate story. Please try again.")
                return
            
            st.session_state.generated_story = story_data
            # CRITICAL: Clear images when new story is generated to prevent mismatch
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
                "image_style": image_style
            }
            save_story(story_data, child_name, metadata)
            
            st.success("✅ Story generated! Please review below.")
    
    # Step 1: Story Review
    if st.session_state.generated_story and not st.session_state.story_approved:
        st.header("📖 Step 1: Review & Edit Story")
        st.markdown("Review each page below. You can edit the text for any page. Click 'Approve Story' when ready.")
        
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
            
            # Editable image prompt area
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
                # Update the story data
                st.session_state.generated_story["pages"][i]["image_prompt"] = new_image_prompt
            
            # Page actions: Regenerate from this page, Move up/down
            col_action1, col_action2, col_action3 = st.columns([1, 1, 1])
            with col_action1:
                if st.button(f"🔄 Regenerate from Page {page_num}", key=f"regen_from_page_{i}", use_container_width=True):
                    st.session_state[f"regen_from_page_{i}"] = True
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
            if st.session_state.get(f"regen_from_page_{i}", False):
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
                                    st.session_state[f"regen_from_page_{i}"] = False
                                    st.success(f"✅ Story regenerated from page {page_num} onwards! All images cleared - please regenerate them.")
                                    st.rerun()
                                else:
                                    st.error("Failed to regenerate story. Please try again.")
                        else:
                            st.warning("Please enter instructions for regeneration")
                with col_cancel_regen:
                    if st.button("❌ Cancel", key=f"cancel_regen_{i}", use_container_width=True):
                        st.session_state[f"regen_from_page_{i}"] = False
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
                # Auto-save story with updated journey state
                if st.session_state.generated_story and st.session_state.current_child_name:
                    save_story(st.session_state.generated_story, st.session_state.current_child_name)
                st.rerun()
        with col2:
            if st.button("🔄 Regenerate Story from Scratch", use_container_width=True):
                st.session_state.generated_story = None
                st.session_state.edited_story_pages = {}
                st.rerun()
    
    # Step 2: Image Generation with Review
    if st.session_state.generated_story and st.session_state.story_approved:
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
                    placeholder = Image.new('RGB', (512, 512), color=(240, 240, 240))
                    st.session_state.generated_images = [placeholder] * total_pages
                    st.rerun()
        else:
            st.header("🎨 Step 2: Generate & Review Images")
            # Ensure progress value is between 0.0 and 1.0
            progress_value = min(1.0, approved_count / total_pages if total_pages > 0 else 0)
            st.progress(progress_value)
            st.caption(f"Approved: {approved_count}/{total_pages} images")

            # Check if API key is available for image generation
            if not api_key:
                st.error("⚠️ **API Key Required for Image Generation**")
                st.info("👈 Please enter your Google Gemini API key in the sidebar to generate images.")
                st.markdown("Get your free API key from: https://makersuite.google.com/app/apikey")

                # Debug information
                with st.expander("🔍 Debug Information"):
                    st.write(f"**API Key in session state:** {bool(st.session_state.api_key)}")
                    st.write(f"**API Key length:** {len(st.session_state.api_key) if st.session_state.api_key else 0}")
                    st.write(f"**Environment variable set:** {bool(os.getenv('GEMINI_API_KEY'))}")
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
                    # Use edited prompt if available, otherwise use original
                    # NOTE: Visual anchor is already included in the image_prompt during story generation
                    # DO NOT add it again to avoid duplicate character descriptions
                    image_prompt = st.session_state.edited_image_prompts.get(
                        regenerate_idx, 
                        page.get("image_prompt", "")
                    )
                    logger.info(f"Regenerating image for page {regenerate_idx + 1} with prompt: {image_prompt[:150]}...")
                    img = generate_image_with_imagen(api_key, image_prompt, image_index=regenerate_idx)
                    # ALWAYS replace at the correct index - ensure list is large enough
                    while len(st.session_state.generated_images) <= regenerate_idx:
                        st.session_state.generated_images.append(None)
                    st.session_state.generated_images[regenerate_idx] = img
                    st.rerun()
            
            # Generate images that haven't been generated yet (only if no regeneration is happening)
            # Also regenerate any None entries (images marked for regeneration)
            if regenerate_idx is None:
                # Find first missing or None image
                missing_idx = None
                for idx in range(total_pages):
                    if idx >= len(st.session_state.generated_images):
                        missing_idx = idx
                        break
                    elif st.session_state.generated_images[idx] is None:
                        missing_idx = idx
                        break
                
                if missing_idx is not None:
                    with st.spinner(f"Generating image {missing_idx + 1}/{total_pages}..."):
                        page = pages[missing_idx]
                        # Use edited prompt if available, otherwise use original
                        # NOTE: Visual anchor is already included in the image_prompt during story generation
                        # DO NOT add it again to avoid duplicate character descriptions
                        image_prompt = st.session_state.edited_image_prompts.get(
                            missing_idx, 
                            page.get("image_prompt", "")
                        )
                        logger.info(f"Generating image for page {missing_idx + 1} with prompt: {image_prompt[:150]}...")
                        img = generate_image_with_imagen(api_key, image_prompt, image_index=missing_idx)
                        # Ensure list is large enough
                        while len(st.session_state.generated_images) <= missing_idx:
                            st.session_state.generated_images.append(None)
                        st.session_state.generated_images[missing_idx] = img
                        st.rerun()
        
        # Show images for review
        for i, page in enumerate(pages):
            if i >= len(st.session_state.generated_images):
                break
            
            # Skip if image is None (pending regeneration)
            if st.session_state.generated_images[i] is None:
                st.info(f"⏳ Page {page.get('page_number', i+1)} - Image pending regeneration...")
                continue
                
            is_approved = st.session_state.image_approvals.get(i, False)
            page_num = page.get('page_number', i+1)
            
            with st.container():
                st.subheader(f"Page {page_num}")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Editable story text
                    st.write("**Story Text:**")
                    # Get edited text or use original
                    edited_text = st.session_state.edited_story_pages.get(i, page.get("text", ""))
                    new_text = st.text_area(
                        f"Edit Story Text (Page {page_num})",
                        value=edited_text,
                        key=f"story_text_edit_{i}",
                        height=80,
                        help="Edit the story text for this page",
                        label_visibility="collapsed"
                    )
                    
                    # Save edited text
                    if new_text != page.get("text", ""):
                        st.session_state.edited_story_pages[i] = new_text
                        # Update the story data
                        st.session_state.generated_story["pages"][i]["text"] = new_text
                    
                    st.image(st.session_state.generated_images[i], use_container_width=True)

                    # Display error message if image generation failed
                    if i in st.session_state.image_generation_errors:
                        error_info = st.session_state.image_generation_errors[i]
                        st.error(f"⚠️ **Image Generation Failed**")
                        with st.expander("Error Details", expanded=False):
                            st.write(f"**Error:** {error_info.get('error', 'Unknown error')}")
                            st.write(f"**Time:** {error_info.get('timestamp', 'N/A')}")
                            st.write(f"**Attempts:** {error_info.get('attempt', 'N/A')}")
                            st.info("💡 **Common Reasons:**\n"
                                   "- Invalid or expired API key\n"
                                   "- API quota exceeded\n"
                                   "- Network connection issues\n"
                                   "- API service temporarily unavailable\n\n"
                                   "Click '🔄 Regenerate' to try again")

                    # Show current prompt
                    current_prompt = st.session_state.edited_image_prompts.get(i, page.get("image_prompt", ""))
                    st.write("**Current Image Prompt:**")
                    st.caption(current_prompt)
                
                with col2:
                    st.write("")  # Spacing
                    if is_approved:
                        st.success("✅ Approved")
                        if st.button(f"🔄 Regenerate Image {i+1}", key=f"regen_{i}"):
                            # Remove approval and show prompt editor
                            if i in st.session_state.image_approvals:
                                del st.session_state.image_approvals[i]
                            st.session_state[f"editing_prompt_{i}"] = True
                            st.rerun()
                    else:
                        if st.button("🔄 Regenerate", key=f"regenerate_{i}"):
                            # Show prompt editor
                            st.session_state[f"editing_prompt_{i}"] = True
                            st.rerun()
                    
                    # Page reordering buttons
                    st.write("**Reorder:**")
                    col_up_img, col_down_img = st.columns(2)
                    with col_up_img:
                        if i > 0:
                            if st.button("⬆️", key=f"move_img_up_{i}", use_container_width=True):
                                # Swap pages in story
                                pages = st.session_state.generated_story["pages"]
                                pages[i], pages[i-1] = pages[i-1], pages[i]
                                # Swap images
                                if i < len(st.session_state.generated_images) and (i-1) < len(st.session_state.generated_images):
                                    st.session_state.generated_images[i], st.session_state.generated_images[i-1] = \
                                        st.session_state.generated_images[i-1], st.session_state.generated_images[i]
                                # Swap approvals
                                temp_approval = st.session_state.image_approvals.get(i, False)
                                st.session_state.image_approvals[i] = st.session_state.image_approvals.get(i-1, False)
                                st.session_state.image_approvals[i-1] = temp_approval
                                # Update page numbers
                                for idx, p in enumerate(pages):
                                    p["page_number"] = idx + 1
                                st.session_state.generated_story["pages"] = pages
                                st.rerun()
                    with col_down_img:
                        if i < len(pages) - 1:
                            if st.button("⬇️", key=f"move_img_down_{i}", use_container_width=True):
                                # Swap pages in story
                                pages = st.session_state.generated_story["pages"]
                                pages[i], pages[i+1] = pages[i+1], pages[i]
                                # Swap images
                                if i < len(st.session_state.generated_images) and (i+1) < len(st.session_state.generated_images):
                                    st.session_state.generated_images[i], st.session_state.generated_images[i+1] = \
                                        st.session_state.generated_images[i+1], st.session_state.generated_images[i]
                                # Swap approvals
                                temp_approval = st.session_state.image_approvals.get(i, False)
                                st.session_state.image_approvals[i] = st.session_state.image_approvals.get(i+1, False)
                                st.session_state.image_approvals[i+1] = temp_approval
                                # Update page numbers
                                for idx, p in enumerate(pages):
                                    p["page_number"] = idx + 1
                                st.session_state.generated_story["pages"] = pages
                                st.rerun()
                
                # Prompt and text editor (shown when regenerating)
                if st.session_state.get(f"editing_prompt_{i}", False):
                    st.write("---")
                    st.write(f"**Edit Content for Page {page_num}:**")
                    
                    # Editable story text in regeneration mode
                    edited_text_for_regen = st.session_state.edited_story_pages.get(i, page.get("text", ""))
                    new_text_regen = st.text_area(
                        f"Story Text (Page {page_num})",
                        value=edited_text_for_regen,
                        key=f"story_text_regen_{i}",
                        height=100,
                        help="Edit the story text for this page"
                    )
                    
                    # Save edited text immediately
                    if new_text_regen != page.get("text", ""):
                        st.session_state.edited_story_pages[i] = new_text_regen
                        st.session_state.generated_story["pages"][i]["text"] = new_text_regen
                    
                    # Editable image prompt
                    edited_prompt = st.text_area(
                        "Image Prompt",
                        value=current_prompt,
                        key=f"prompt_edit_{i}",
                        height=100,
                        help="Edit the prompt to change how the image is generated"
                    )
                    
                    col_gen, col_cancel = st.columns(2)
                    with col_gen:
                        if st.button(f"✨ Generate with New Prompt", key=f"gen_new_{i}", type="primary"):
                            # NOTE: Visual anchor is already included in the original prompt from story generation
                            # DO NOT add it again to avoid duplicate character descriptions
                            # The user can see and edit the full prompt including visual anchor
                            
                            # Save edited prompt (already has visual anchor from original)
                            st.session_state.edited_image_prompts[i] = edited_prompt
                            # Save edited text if changed
                            if new_text_regen != edited_text_for_regen:
                                st.session_state.edited_story_pages[i] = new_text_regen
                                st.session_state.generated_story["pages"][i]["text"] = new_text_regen
                            
                            # Remove approval for this specific image
                            if i in st.session_state.image_approvals:
                                del st.session_state.image_approvals[i]
                            # Clear any error for this image since we're regenerating
                            if i in st.session_state.image_generation_errors:
                                del st.session_state.image_generation_errors[i]
                            # Mark this slot for regeneration - don't pop, just set to None
                            # This prevents index shifting which causes text/image mismatch
                            if i < len(st.session_state.generated_images):
                                st.session_state.generated_images[i] = None
                            # Set flag to regenerate only this image
                            st.session_state[f"regenerate_image_{i}"] = True
                            st.session_state[f"editing_prompt_{i}"] = False
                            # Update page prompt
                            st.session_state.generated_story["pages"][i]["image_prompt"] = edited_prompt
                            st.rerun()
                    with col_cancel:
                        if st.button("❌ Cancel", key=f"cancel_edit_{i}"):
                            st.session_state[f"editing_prompt_{i}"] = False
                            st.rerun()
                
                st.divider()
        
        # Batch approve all images button
        if approved_count < total_pages:
            if st.button("✅ Approve All Images", type="primary", use_container_width=True):
                for i in range(total_pages):
                    st.session_state.image_approvals[i] = True
                st.rerun()
        
        # Check if all images are approved
        if approved_count == total_pages and total_pages > 0:
            st.session_state.all_images_approved = True
            # Auto-save story with updated journey state (all images approved)
            if st.session_state.generated_story and st.session_state.current_child_name:
                save_story(st.session_state.generated_story, st.session_state.current_child_name)
    
    # Step 3: Generate PDF
    if (st.session_state.generated_story and 
        st.session_state.story_approved and 
        st.session_state.all_images_approved and
        len(st.session_state.generated_images) > 0):
        
        # Create a unique key based on story and images to detect changes
        story_hash = hashlib.md5(json.dumps(st.session_state.generated_story, sort_keys=True).encode()).hexdigest()
        images_hash = hashlib.md5(str([id(img) for img in st.session_state.generated_images]).encode()).hexdigest()
        current_pdf_key = f"{story_hash}_{images_hash}"
        
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
                        pdf_path
                    )
                    st.session_state.pdf_path = pdf_path
                    st.session_state.pdf_generation_key = current_pdf_key
        
        st.header("📚 Step 3: Download Your Storybook")
        st.success("🎉 All content approved! Your storybook is ready to download.")
        
        # Navigation buttons to go back
        col_nav1, col_nav2, col_nav3 = st.columns(3)
        with col_nav1:
            if st.button("← Back to Story Review", use_container_width=True, type="secondary"):
                st.session_state.story_approved = False
                st.rerun()
        with col_nav2:
            if st.button("← Back to Image Review", use_container_width=True, type="secondary"):
                st.session_state.all_images_approved = False
                st.rerun()
        with col_nav3:
            st.write("")  # Spacing
        
        st.divider()
        
        if st.session_state.pdf_path and os.path.exists(st.session_state.pdf_path):
            with open(st.session_state.pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_bytes,
                    file_name=f"{child_name}_Storybook.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
            
            st.info("💡 Print this PDF on 8.5x8.5 inch paper for best results!")
            
            # Final Preview with editing capabilities
            st.subheader("Final Preview & Edit")
            st.markdown("You can edit text, delete pages, or rearrange pages here. Changes will require regenerating the PDF.")
            
            pages = st.session_state.generated_story.get("pages", [])
            
            # Page management controls
            if len(pages) > 1:
                st.markdown("**Page Management:**")
                col_del, col_up, col_down = st.columns([1, 1, 1])
                with col_del:
                    page_to_delete = st.selectbox(
                        "Delete Page",
                        options=[f"Page {i+1}" for i in range(len(pages))],
                        key="delete_page_select",
                        index=None
                    )
                    if page_to_delete and st.button("🗑️ Delete Page", key="delete_page_btn"):
                        page_idx = int(page_to_delete.split()[1]) - 1
                        if 0 <= page_idx < len(pages):
                            # Remove page and corresponding image
                            pages.pop(page_idx)
                            if page_idx < len(st.session_state.generated_images):
                                st.session_state.generated_images.pop(page_idx)
                            
                            # Clean up approvals - remove deleted page and reindex remaining approvals
                            new_approvals = {}
                            for old_idx, approved in st.session_state.image_approvals.items():
                                if old_idx < page_idx:
                                    # Keep approvals before deleted page
                                    new_approvals[old_idx] = approved
                                elif old_idx > page_idx:
                                    # Shift approvals after deleted page down by 1
                                    new_approvals[old_idx - 1] = approved
                            st.session_state.image_approvals = new_approvals
                            
                            # Clean up edited pages and prompts - reindex them
                            new_edited_pages = {}
                            for old_idx, text in st.session_state.edited_story_pages.items():
                                if old_idx < page_idx:
                                    new_edited_pages[old_idx] = text
                                elif old_idx > page_idx:
                                    new_edited_pages[old_idx - 1] = text
                            st.session_state.edited_story_pages = new_edited_pages
                            
                            new_edited_prompts = {}
                            for old_idx, prompt in st.session_state.edited_image_prompts.items():
                                if old_idx < page_idx:
                                    new_edited_prompts[old_idx] = prompt
                                elif old_idx > page_idx:
                                    new_edited_prompts[old_idx - 1] = prompt
                            st.session_state.edited_image_prompts = new_edited_prompts
                            
                            st.session_state.generated_story["pages"] = pages
                            # Update page numbers
                            for idx, p in enumerate(pages):
                                p["page_number"] = idx + 1
                            # Force PDF regeneration
                            st.session_state.pdf_generation_key = None
                            st.success(f"Deleted {page_to_delete}")
                            st.rerun()
                
                with col_up:
                    page_to_move_up = st.selectbox(
                        "Move Page Up",
                        options=[f"Page {i+1}" for i in range(1, len(pages))],
                        key="move_up_select",
                        index=None
                    )
                    if page_to_move_up and st.button("⬆️ Move Up", key="move_up_btn"):
                        page_idx = int(page_to_move_up.split()[1]) - 1
                        if page_idx > 0:
                            # Swap pages
                            pages[page_idx], pages[page_idx - 1] = pages[page_idx - 1], pages[page_idx]
                            # Swap images
                            if page_idx < len(st.session_state.generated_images) and (page_idx - 1) < len(st.session_state.generated_images):
                                st.session_state.generated_images[page_idx], st.session_state.generated_images[page_idx - 1] = \
                                    st.session_state.generated_images[page_idx - 1], st.session_state.generated_images[page_idx]
                            # Swap edited story pages
                            temp_text = st.session_state.edited_story_pages.get(page_idx)
                            st.session_state.edited_story_pages[page_idx] = st.session_state.edited_story_pages.get(page_idx - 1)
                            st.session_state.edited_story_pages[page_idx - 1] = temp_text
                            # Swap edited image prompts
                            temp_prompt = st.session_state.edited_image_prompts.get(page_idx)
                            st.session_state.edited_image_prompts[page_idx] = st.session_state.edited_image_prompts.get(page_idx - 1)
                            st.session_state.edited_image_prompts[page_idx - 1] = temp_prompt
                            # Swap approvals
                            temp_approval = st.session_state.image_approvals.get(page_idx, False)
                            st.session_state.image_approvals[page_idx] = st.session_state.image_approvals.get(page_idx - 1, False)
                            st.session_state.image_approvals[page_idx - 1] = temp_approval
                            st.session_state.generated_story["pages"] = pages
                            # Update page numbers
                            for idx, p in enumerate(pages):
                                p["page_number"] = idx + 1
                            st.session_state.pdf_generation_key = None
                            st.success(f"Moved {page_to_move_up} up")
                            st.rerun()
                
                with col_down:
                    page_to_move_down = st.selectbox(
                        "Move Page Down",
                        options=[f"Page {i+1}" for i in range(len(pages) - 1)],
                        key="move_down_select",
                        index=None
                    )
                    if page_to_move_down and st.button("⬇️ Move Down", key="move_down_btn"):
                        page_idx = int(page_to_move_down.split()[1]) - 1
                        if page_idx < len(pages) - 1:
                            # Swap pages
                            pages[page_idx], pages[page_idx + 1] = pages[page_idx + 1], pages[page_idx]
                            # Swap images
                            if page_idx < len(st.session_state.generated_images) and (page_idx + 1) < len(st.session_state.generated_images):
                                st.session_state.generated_images[page_idx], st.session_state.generated_images[page_idx + 1] = \
                                    st.session_state.generated_images[page_idx + 1], st.session_state.generated_images[page_idx]
                            # Swap edited story pages
                            temp_text = st.session_state.edited_story_pages.get(page_idx)
                            st.session_state.edited_story_pages[page_idx] = st.session_state.edited_story_pages.get(page_idx + 1)
                            st.session_state.edited_story_pages[page_idx + 1] = temp_text
                            # Swap edited image prompts
                            temp_prompt = st.session_state.edited_image_prompts.get(page_idx)
                            st.session_state.edited_image_prompts[page_idx] = st.session_state.edited_image_prompts.get(page_idx + 1)
                            st.session_state.edited_image_prompts[page_idx + 1] = temp_prompt
                            # Swap approvals
                            temp_approval = st.session_state.image_approvals.get(page_idx, False)
                            st.session_state.image_approvals[page_idx] = st.session_state.image_approvals.get(page_idx + 1, False)
                            st.session_state.image_approvals[page_idx + 1] = temp_approval
                            st.session_state.generated_story["pages"] = pages
                            # Update page numbers
                            for idx, p in enumerate(pages):
                                p["page_number"] = idx + 1
                            st.session_state.pdf_generation_key = None
                            st.success(f"Moved {page_to_move_down} down")
                            st.rerun()
                
                st.divider()
            
            # Editable preview of pages
            for i, page in enumerate(pages):
                if i < len(st.session_state.generated_images):
                    page_num = page.get('page_number', i+1)
                    with st.expander(f"📄 Page {page_num} - Click to Edit", expanded=False):
                        # Editable text
                        edited_text = st.session_state.edited_story_pages.get(i, page.get("text", ""))
                        new_text = st.text_area(
                            f"Story Text (Page {page_num})",
                            value=edited_text,
                            key=f"final_edit_text_{i}",
                            height=100,
                            help="Edit the story text for this page"
                        )
                        
                        # Save edited text
                        if new_text != page.get("text", ""):
                            st.session_state.edited_story_pages[i] = new_text
                            st.session_state.generated_story["pages"][i]["text"] = new_text
                            # Force PDF regeneration
                            st.session_state.pdf_generation_key = None
                        
                        # Show image
                        st.image(st.session_state.generated_images[i], use_container_width=True)

                        # Display error message if image generation failed
                        if i in st.session_state.image_generation_errors:
                            error_info = st.session_state.image_generation_errors[i]
                            st.error(f"⚠️ **Image Generation Failed**")
                            with st.expander("Error Details", expanded=False):
                                st.write(f"**Error:** {error_info.get('error', 'Unknown error')}")
                                st.write(f"**Time:** {error_info.get('timestamp', 'N/A')}")
                                st.write(f"**Attempts:** {error_info.get('attempt', 'N/A')}")
                                st.info("💡 Go back to Step 2 to regenerate this image")

                        # Regenerate PDF button if text was edited
                        if new_text != edited_text:
                            if st.button(f"🔄 Regenerate PDF with Changes", key=f"regen_pdf_{i}"):
                                st.rerun()
        else:
            st.warning("PDF not available")

if __name__ == "__main__":
    main()

