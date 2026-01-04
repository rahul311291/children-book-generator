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

logger = logging.getLogger(__name__)

load_dotenv()


def init_supabase() -> Client:
    """Initialize Supabase client."""
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        raise Exception("Supabase credentials not found in environment variables")

    return create_client(supabase_url, supabase_key)


def get_available_templates() -> List[Dict]:
    """Fetch all available templates from database."""
    try:
        supabase = init_supabase()
        response = supabase.table("templates").select("*").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching templates: {e}")
        st.error(f"Failed to load templates: {e}")
        return []


def get_template_pages(template_id: str) -> List[Dict]:
    """Fetch all pages for a specific template."""
    try:
        supabase = init_supabase()
        response = supabase.table("template_pages").select("*").eq("template_id", template_id).order("page_number").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching template pages: {e}")
        st.error(f"Failed to load template pages: {e}")
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

        pages = get_template_pages(template_id)

        if not pages:
            st.error("No pages found for this template")
            return

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

        total_pages = len(pages)

        for idx, page in enumerate(pages):
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

            image_url = generate_page_image(api_key, personalized_image_prompt)

            generated_book['pages'].append({
                'page_number': page['page_number'],
                'profession_title': page['profession_title'],
                'text': personalized_text,
                'image_prompt': personalized_image_prompt,
                'image_url': image_url
            })

            progress_bar.progress((idx + 1) / total_pages)

        status_text.text("✅ Book generation complete!")

        st.session_state.template_generated_book = generated_book

    except Exception as e:
        logger.error(f"Error generating template book: {e}")
        st.error(f"Failed to generate book: {e}")


def generate_page_image(api_key: str, prompt: str) -> Optional[str]:
    """Generate a single image using Gemini API."""
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

        logger.warning(f"Image generation failed with status {response.status_code}")
        return None

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None


def display_template_book_preview(book_data: Dict):
    """Display the generated template book for preview."""
    st.success(f"✨ Your personalized book for **{book_data['child_name']}** is ready!")

    st.markdown("---")
    st.markdown("### 📖 Book Preview")

    for page in book_data['pages']:
        with st.container():
            st.markdown(f"#### Page {page['page_number']}: {page['profession_title']}")

            col1, col2 = st.columns([1, 1])

            with col1:
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
                    st.info("Image generation in progress or failed")

            with col2:
                st.markdown("**Story Text:**")
                st.markdown(f"```\n{page['text']}\n```")

            st.markdown("---")

    if st.button("🔄 Create Another Book", use_container_width=True):
        for key in ['template_generated_book', 'template_book_data', 'generate_template_book']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
