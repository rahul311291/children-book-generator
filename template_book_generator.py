"""
Template-based book generator for predefined book templates
Handles "When I Grow Up" and other template-based personalized books
"""

import streamlit as st
import os
import base64
from pathlib import Path
from typing import List, Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from template_data import personalize_template_text, personalize_template_image_prompt
from PIL import Image
import io
import logging
import requests
import json
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER
from datetime import datetime

logger = logging.getLogger(__name__)

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


def init_supabase() -> Client:
    """Initialize Supabase client."""
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_SUPABASE_ANON_KEY")

    if not supabase_url:
        supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_key:
        supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        try:
            supabase_url = st.secrets.get("VITE_SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
            supabase_key = st.secrets.get("VITE_SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY")
        except Exception:
            pass

    if not supabase_url or not supabase_key:
        error_msg = f"Supabase credentials not found. URL: {'found' if supabase_url else 'missing'}, Key: {'found' if supabase_key else 'missing'}"
        logger.error(error_msg)
        raise Exception(error_msg)

    return create_client(supabase_url, supabase_key)


def get_available_templates() -> List[Dict]:
    """Fetch all available templates from database, with hardcoded fallback."""
    # First try to fetch from database
    try:
        supabase = init_supabase()
        response = supabase.table("templates").select("*").execute()
        if response.data:
            return response.data
    except Exception as e:
        logger.warning(f"Database templates not available: {e}, using hardcoded template")

    # Fallback to hardcoded template
    from template_data import WHEN_I_GROW_UP_TEMPLATE
    return [{
        "id": "when_i_grow_up",
        "name": WHEN_I_GROW_UP_TEMPLATE["name"],
        "description": WHEN_I_GROW_UP_TEMPLATE["description"],
        "total_pages": WHEN_I_GROW_UP_TEMPLATE["total_pages"]
    }]


def get_template_pages(template_id: str) -> List[Dict]:
    """Fetch all pages for a specific template, with hardcoded fallback."""
    # First try to fetch from database
    try:
        supabase = init_supabase()
        response = supabase.table("template_pages").select("*").eq("template_id", template_id).order("page_number").execute()
        if response.data:
            return response.data
    except Exception as e:
        logger.warning(f"Database template pages not available: {e}, using hardcoded template")

    # Fallback to hardcoded template
    if template_id == "when_i_grow_up":
        from template_data import WHEN_I_GROW_UP_TEMPLATE
        return WHEN_I_GROW_UP_TEMPLATE["pages"]

    return []


def render_template_book_form():
    """Render the form for template book creation."""
    st.header("📖 Create Your Personalized Template Book")

    templates = get_available_templates()

    if not templates:
        st.warning("No templates available. Please contact support.")
        return

    st.markdown("### Choose Your Template")
    template_options = {t['name']: t['id'] for t in templates}
    selected_template_name = st.selectbox(
        "Select a book template",
        options=list(template_options.keys()),
        help="Choose from our pre-designed book templates"
    )

    selected_template_id = template_options[selected_template_name]
    template_info = next(t for t in templates if t['id'] == selected_template_id)

    st.info(f"📚 **{template_info['description']}**")
    st.caption(f"This template includes {template_info['total_pages']} pages")

    st.markdown("---")
    st.markdown("### Personalize Your Book")

    col1, col2 = st.columns(2)

    with col1:
        child_name = st.text_input(
            "Child's Name *",
            placeholder="e.g., Emma, Jack, Alex",
            help="The child's name that will appear throughout the book"
        )

        gender = st.selectbox(
            "Gender *",
            options=["Boy", "Girl", "Neutral"],
            help="This affects pronouns used in the story (he/she/they)"
        )

    with col2:
        age = st.number_input(
            "Child's Age *",
            min_value=1,
            max_value=12,
            value=5,
            help="The child's age helps personalize the imagery"
        )

    st.markdown("### Upload Photos (Optional)")
    st.caption("Upload 1-3 photos of the child to personalize select pages")

    photo_cols = st.columns(3)

    photos = []
    for i, col in enumerate(photo_cols):
        with col:
            uploaded_file = st.file_uploader(
                f"Photo {i + 1}",
                type=['png', 'jpg', 'jpeg'],
                key=f"template_photo_{i}"
            )
            if uploaded_file:
                photos.append(uploaded_file)
                st.image(uploaded_file, caption=f"Photo {i + 1}", use_container_width=True)

    st.markdown("---")

    if st.button("✨ Generate Template Book", type="primary", use_container_width=True):
        if not child_name:
            st.error("⚠️ Please enter the child's name")
            return

        with st.spinner("Creating your personalized book..."):
            st.session_state.template_book_data = {
                'template_id': selected_template_id,
                'template_name': selected_template_name,
                'child_name': child_name,
                'gender': gender,
                'age': age,
                'photos': photos
            }
            st.session_state.generate_template_book = True
            st.rerun()


def generate_template_book(api_key: str, book_data: Dict):
    """Generate a complete template book with AI-generated images."""
    try:
        template_id = book_data['template_id']
        child_name = book_data['child_name']
        gender = book_data['gender']
        age = book_data['age']
        photos = book_data.get('photos', [])

        pages = get_template_pages(template_id)

        if not pages:
            st.error("No pages found for this template")
            return

        reference_image_base64 = None
        if photos:
            reference_image_base64 = convert_uploaded_file_to_base64(photos[0])

        generated_book = {
            'template_id': template_id,
            'template_name': book_data['template_name'],
            'child_name': child_name,
            'gender': gender,
            'age': age,
            'pages': []
        }

        progress_bar = st.progress(0)
        status_text = st.empty()
        error_display = st.empty()

        total_pages = len(pages)
        successful_pages = 0
        failed_pages = 0

        for idx, page in enumerate(pages):
            try:
                status_text.text(f"Generating page {idx + 1} of {total_pages}: {page['profession_title']}")

                personalized_text = personalize_template_text(
                    page['text_template'],
                    child_name,
                    gender
                )

                personalized_image_prompt = personalize_template_image_prompt(
                    page['image_prompt_template'],
                    child_name,
                    gender,
                    age
                )

                logger.info(f"Generating image for page {idx + 1}: {page['profession_title']}")

                image_url = generate_page_image(
                    api_key,
                    personalized_image_prompt,
                    reference_image_base64
                )

                if image_url:
                    successful_pages += 1
                    logger.info(f"Successfully generated image for page {idx + 1}")
                else:
                    failed_pages += 1
                    logger.warning(f"Failed to generate image for page {idx + 1}")

                generated_book['pages'].append({
                    'page_number': page['page_number'],
                    'profession_title': page['profession_title'],
                    'text': personalized_text,
                    'image_prompt': personalized_image_prompt,
                    'image_url': image_url,
                    'error': None if image_url else "Image generation failed"
                })

                progress_bar.progress((idx + 1) / total_pages)

            except Exception as page_error:
                logger.error(f"Error generating page {idx + 1}: {page_error}")
                failed_pages += 1

                generated_book['pages'].append({
                    'page_number': page.get('page_number', idx + 1),
                    'profession_title': page.get('profession_title', 'Unknown'),
                    'text': personalize_template_text(page.get('text_template', ''), child_name, gender),
                    'image_prompt': personalize_template_image_prompt(page.get('image_prompt_template', ''), child_name, gender, age),
                    'image_url': None,
                    'error': str(page_error)
                })

                progress_bar.progress((idx + 1) / total_pages)

        if failed_pages > 0:
            error_display.warning(f"⚠️ Book generated with {failed_pages} failed images out of {total_pages} pages. You can regenerate failed images on the preview screen.")
            status_text.text(f"✅ Book generation complete! ({successful_pages}/{total_pages} images generated)")
        else:
            status_text.text("✅ Book generation complete!")

        st.session_state.template_generated_book = generated_book

    except Exception as e:
        logger.error(f"Error generating template book: {e}", exc_info=True)
        st.error(f"Failed to generate book: {e}")


def convert_uploaded_file_to_base64(uploaded_file) -> str:
    """Convert Streamlit uploaded file to base64 string."""
    try:
        bytes_data = uploaded_file.getvalue()
        return base64.b64encode(bytes_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Error converting file to base64: {e}")
        return None


def generate_page_image(api_key: str, prompt: str, reference_image_base64: Optional[str] = None) -> Optional[str]:
    """Generate a single image using Gemini API with optional reference image."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:generate"

        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt,
            "number_of_images": 1,
            "aspect_ratio": "1:1",
            "safety_filter_level": "block_some",
            "person_generation": "allow_all"
        }

        if reference_image_base64:
            payload["referenceImages"] = [{
                "imageBytes": reference_image_base64,
                "referenceType": "STYLE"
            }]
            payload["prompt"] = f"{prompt}. Match the child's facial features and appearance from the reference image."

        response = requests.post(
            f"{url}?key={api_key}",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            if 'generatedImages' in result and len(result['generatedImages']) > 0:
                image_data = result['generatedImages'][0].get('imageBytes')
                if image_data:
                    return f"data:image/png;base64,{image_data}"

        logger.warning(f"Image generation failed with status {response.status_code}: {response.text if response.text else 'No error message'}")
        return None

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None


def display_template_book_preview(book_data: Dict):
    """Display the generated template book with comprehensive edit and download options."""
    if 'template_editing_mode' not in st.session_state:
        st.session_state.template_editing_mode = {}
    if 'template_edited_texts' not in st.session_state:
        st.session_state.template_edited_texts = {}
    if 'template_edited_prompts' not in st.session_state:
        st.session_state.template_edited_prompts = {}

    st.success(f"✨ Your personalized book for **{book_data['child_name']}** is ready!")

    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.markdown("### 📖 Book Preview & Editor")
    with col_header2:
        if st.button("📥 Download as PDF", type="primary", use_container_width=True):
            with st.spinner("Creating PDF..."):
                pdf_path = create_template_book_pdf(book_data)
                if pdf_path:
                    with open(pdf_path, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()
                    st.download_button(
                        label="💾 Save PDF",
                        data=pdf_bytes,
                        file_name=f"{book_data['child_name']}_book.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("PDF ready for download!")

    st.markdown("---")

    failed_images_count = sum(1 for page in book_data['pages'] if not page.get('image_url'))
    if failed_images_count > 0:
        col_warn, col_regen_all = st.columns([3, 1])
        with col_warn:
            st.warning(f"⚠️ {failed_images_count} images failed to generate. You can regenerate them individually below.")
        with col_regen_all:
            if st.button("🔄 Regenerate All Failed", type="secondary", use_container_width=True):
                api_key = st.session_state.get('api_key') or os.getenv("GEMINI_API_KEY", "")
                if not api_key:
                    st.error("API key not found. Please check your API key in the sidebar.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    failed_pages = [p for p in book_data['pages'] if not p.get('image_url')]
                    total_failed = len(failed_pages)
                    success_count = 0

                    for idx, page in enumerate(failed_pages):
                        page_key = f"{page['page_number']}"
                        status_text.text(f"Regenerating {idx + 1}/{total_failed}: {page['profession_title']}")

                        prompt = st.session_state.template_edited_prompts.get(page_key, page['image_prompt'])

                        reference_image_base64 = None
                        if book_data.get('photos'):
                            try:
                                reference_image_base64 = convert_uploaded_file_to_base64(book_data['photos'][0])
                            except Exception:
                                pass

                        new_image = generate_page_image(api_key, prompt, reference_image_base64)
                        if new_image:
                            page['image_url'] = new_image
                            page['error'] = None
                            success_count += 1

                        progress_bar.progress((idx + 1) / total_failed)

                    st.session_state.template_generated_book = book_data
                    status_text.text(f"✅ Regenerated {success_count}/{total_failed} images successfully!")
                    st.rerun()

    for idx, page in enumerate(book_data['pages']):
        page_key = f"{page['page_number']}"

        status_icon = "✅" if page.get('image_url') else "❌"
        expanded_by_default = not page.get('image_url')

        with st.expander(f"{status_icon} Page {page['page_number']}: {page['profession_title']}", expanded=expanded_by_default):
            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("#### 🖼️ Image")

                if page.get('image_url'):
                    try:
                        if page['image_url'].startswith('data:image'):
                            image_data = page['image_url'].split(',')[1]
                            image_bytes = base64.b64decode(image_data)
                            st.image(image_bytes, use_container_width=True)
                        else:
                            st.image(page['image_url'], use_container_width=True)
                    except Exception as e:
                        st.error(f"Failed to display image: {e}")
                else:
                    st.warning("❌ Image generation failed")
                    if page.get('error'):
                        st.caption(f"Error: {page['error']}")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"🔄 Regenerate Image", key=f"regen_img_{page_key}", use_container_width=True):
                        with st.spinner("Regenerating image..."):
                            api_key = st.session_state.get('api_key') or os.getenv("GEMINI_API_KEY", "")
                            if not api_key:
                                st.error("API key not found. Please check your API key in the sidebar.")
                            else:
                                prompt = st.session_state.template_edited_prompts.get(page_key, page['image_prompt'])

                                reference_image_base64 = None
                                if book_data.get('photos'):
                                    try:
                                        reference_image_base64 = convert_uploaded_file_to_base64(book_data['photos'][0])
                                    except Exception:
                                        pass

                                new_image = generate_page_image(api_key, prompt, reference_image_base64)
                                if new_image:
                                    page['image_url'] = new_image
                                    page['error'] = None
                                    st.session_state.template_generated_book = book_data
                                    st.success("Image regenerated successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to regenerate image. Please try again or edit the prompt.")

                with col_btn2:
                    if st.button(f"✏️ Edit Prompt", key=f"edit_prompt_{page_key}", use_container_width=True):
                        st.session_state.template_editing_mode[f"prompt_{page_key}"] = True
                        st.rerun()

                if st.session_state.template_editing_mode.get(f"prompt_{page_key}", False):
                    edited_prompt = st.text_area(
                        "Image Prompt",
                        value=st.session_state.template_edited_prompts.get(page_key, page['image_prompt']),
                        key=f"prompt_edit_{page_key}",
                        height=100
                    )
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("💾 Save", key=f"save_prompt_{page_key}", use_container_width=True):
                            st.session_state.template_edited_prompts[page_key] = edited_prompt
                            page['image_prompt'] = edited_prompt
                            st.session_state.template_editing_mode[f"prompt_{page_key}"] = False
                            st.success("Prompt updated!")
                            st.rerun()
                    with col_cancel:
                        if st.button("❌ Cancel", key=f"cancel_prompt_{page_key}", use_container_width=True):
                            st.session_state.template_editing_mode[f"prompt_{page_key}"] = False
                            st.rerun()

            with col2:
                st.markdown("#### 📝 Story Text")

                if st.session_state.template_editing_mode.get(f"text_{page_key}", False):
                    edited_text = st.text_area(
                        "Edit Story Text",
                        value=st.session_state.template_edited_texts.get(page_key, page['text']),
                        key=f"text_edit_{page_key}",
                        height=200
                    )
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("💾 Save", key=f"save_text_{page_key}", use_container_width=True):
                            st.session_state.template_edited_texts[page_key] = edited_text
                            page['text'] = edited_text
                            st.session_state.template_editing_mode[f"text_{page_key}"] = False
                            st.success("Text updated!")
                            st.rerun()
                    with col_cancel:
                        if st.button("❌ Cancel", key=f"cancel_text_{page_key}", use_container_width=True):
                            st.session_state.template_editing_mode[f"text_{page_key}"] = False
                            st.rerun()
                else:
                    st.markdown(f"*{st.session_state.template_edited_texts.get(page_key, page['text'])}*")
                    if st.button(f"✏️ Edit Text", key=f"edit_text_{page_key}", use_container_width=True):
                        st.session_state.template_editing_mode[f"text_{page_key}"] = True
                        st.rerun()

            st.markdown("---")

    st.markdown("### 🎯 Final Actions")

    col_action1, col_action2 = st.columns(2)
    with col_action1:
        if st.button("🔄 Create Another Book", use_container_width=True):
            for key in ['template_generated_book', 'template_book_data', 'generate_template_book',
                       'template_editing_mode', 'template_edited_texts', 'template_edited_prompts']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    with col_action2:
        if st.button("📥 Download Final PDF", type="primary", use_container_width=True):
            with st.spinner("Creating your final PDF..."):
                pdf_path = create_template_book_pdf(book_data)
                if pdf_path:
                    with open(pdf_path, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()
                    st.download_button(
                        label="💾 Download Now",
                        data=pdf_bytes,
                        file_name=f"{book_data['child_name']}_book_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("✅ PDF is ready!")


def create_template_book_pdf(book_data: Dict) -> Optional[str]:
    """Create a PDF from the template book data."""
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        pdf_path = temp_file.name
        temp_file.close()

        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#2E86AB',
            alignment=TA_CENTER,
            spaceAfter=30
        )
        text_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=14,
            leading=20,
            alignment=TA_CENTER
        )

        c.setTitle(f"{book_data['child_name']}'s Book")

        title_text = f"{book_data['template_name']}"
        subtitle_text = f"Personalized for {book_data['child_name']}"

        title_para = Paragraph(title_text, title_style)
        subtitle_para = Paragraph(subtitle_text, text_style)

        title_para.wrapOn(c, width - 100, height)
        title_para.drawOn(c, 50, height - 150)

        subtitle_para.wrapOn(c, width - 100, height)
        subtitle_para.drawOn(c, 50, height - 200)

        c.showPage()

        for page in book_data['pages']:
            page_number = page.get('page_number', 1)
            profession = page.get('profession_title', '')
            text = page.get('text', '')
            image_url = page.get('image_url')

            if image_url:
                try:
                    if image_url.startswith('data:image'):
                        image_data = image_url.split(',')[1]
                        image_bytes = base64.b64decode(image_data)
                        img = Image.open(io.BytesIO(image_bytes))

                        img_reader = ImageReader(io.BytesIO(image_bytes))

                        img_width = width - 100
                        img_height = img_width * (img.size[1] / img.size[0])

                        if img_height > height - 300:
                            img_height = height - 300
                            img_width = img_height * (img.size[0] / img.size[1])

                        x_position = (width - img_width) / 2
                        y_position = height - 150 - img_height

                        c.drawImage(img_reader, x_position, y_position, width=img_width, height=img_height)

                        text_y_position = y_position - 80

                except Exception as img_error:
                    logger.error(f"Error adding image to PDF: {img_error}")
                    text_y_position = height - 150
                else:
                    text_y_position = height - 150

                c.setFont("Helvetica-Bold", 16)
                c.setFillColorRGB(0.18, 0.52, 0.67)
                c.drawCentredString(width / 2, text_y_position, profession)

                text_para = Paragraph(text, text_style)
                text_para.wrapOn(c, width - 100, 100)
                text_para.drawOn(c, 50, text_y_position - 80)

                c.setFont("Helvetica", 10)
                c.setFillColorRGB(0.5, 0.5, 0.5)
                c.drawCentredString(width / 2, 30, f"Page {page_number}")

                c.showPage()

        c.save()
        logger.info(f"PDF created successfully: {pdf_path}")
        return pdf_path

    except Exception as e:
        logger.error(f"Error creating PDF: {e}", exc_info=True)
        st.error(f"Failed to create PDF: {e}")
        return None
