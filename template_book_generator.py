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

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def init_supabase() -> Client:
    """Initialize Supabase client."""
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    # Try both possible env var names for anon key
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


def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def describe_photo_for_ai(image_bytes: bytes) -> str:
    """
    Create a simple description of the uploaded photo for AI context.
    For now, returns a placeholder. In production, could use vision AI to analyze.
    """
    return "Based on the uploaded photo"


def render_template_book_form():
    """Render the form for creating a template-based book."""

    st.title("Create Your Personalized Book")
    st.write("Choose a template and personalize it with your child's information!")

    # Fetch available templates
    templates = get_available_templates()

    if not templates:
        st.warning("No templates available yet. Please check back later.")
        return

    # Template selection
    st.subheader("1. Select a Book Template")

    template_options = {t["name"]: t for t in templates}
    selected_template_name = st.selectbox(
        "Choose a book template:",
        options=list(template_options.keys()),
        help="Select the type of personalized book you want to create"
    )

    selected_template = template_options[selected_template_name]

    # Show template info
    with st.expander("About this template", expanded=True):
        st.write(selected_template["description"])
        st.info(f"This book has **{selected_template['total_pages']} pages**")

    # Child information form
    st.subheader("2. Enter Child's Information")

    col1, col2 = st.columns(2)

    with col1:
        child_name = st.text_input(
            "Child's Name *",
            placeholder="e.g., Emma",
            help="The child's name will appear throughout the book"
        )

        child_age = st.number_input(
            "Child's Age *",
            min_value=2,
            max_value=16,
            value=5,
            help="Age of the child"
        )

    with col2:
        child_gender = st.selectbox(
            "Gender *",
            options=["Boy", "Girl", "Non-binary"],
            help="Used for pronouns in the story"
        )

    # Photo upload section
    st.subheader("3. Upload 3 Photos of the Child")
    st.write("These photos will be used to create personalized illustrations showing the child in different professions.")

    photo_cols = st.columns(3)

    uploaded_photos = []

    with photo_cols[0]:
        st.write("**Photo 1**")
        photo1 = st.file_uploader(
            "Upload first photo",
            type=["png", "jpg", "jpeg"],
            key="photo1",
            help="Clear photo of the child's face"
        )
        if photo1:
            st.image(photo1, caption="Photo 1", use_container_width=True)
            uploaded_photos.append(photo1)

    with photo_cols[1]:
        st.write("**Photo 2**")
        photo2 = st.file_uploader(
            "Upload second photo",
            type=["png", "jpg", "jpeg"],
            key="photo2",
            help="Another clear photo from different angle"
        )
        if photo2:
            st.image(photo2, caption="Photo 2", use_container_width=True)
            uploaded_photos.append(photo2)

    with photo_cols[2]:
        st.write("**Photo 3**")
        photo3 = st.file_uploader(
            "Upload third photo",
            type=["png", "jpg", "jpeg"],
            key="photo3",
            help="Third photo for variety"
        )
        if photo3:
            st.image(photo3, caption="Photo 3", use_container_width=True)
            uploaded_photos.append(photo3)

    # Validation and generation button
    st.divider()

    can_generate = (
        child_name and
        child_age and
        child_gender and
        len(uploaded_photos) == 3
    )

    if not can_generate:
        missing = []
        if not child_name:
            missing.append("Child's name")
        if not child_age:
            missing.append("Child's age")
        if not child_gender:
            missing.append("Gender")
        if len(uploaded_photos) < 3:
            missing.append(f"{3 - len(uploaded_photos)} more photo(s)")

        st.warning(f"Please provide: {', '.join(missing)}")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        generate_button = st.button(
            "Generate My Personalized Book",
            type="primary",
            disabled=not can_generate,
            use_container_width=True
        )

    if generate_button and can_generate:
        # Store form data in session state
        st.session_state.template_book_data = {
            "template_id": selected_template["id"],
            "template_name": selected_template["name"],
            "child_name": child_name,
            "child_age": child_age,
            "child_gender": child_gender,
            "photos": [photo1, photo2, photo3]
        }

        # Trigger book generation
        st.session_state.generate_template_book = True
        st.rerun()


def generate_template_book(api_key: str, template_data: Dict):
    """Generate the personalized book from template."""

    st.title(f"Generating: {template_data['template_name']}")

    # Fetch template pages
    template_pages = get_template_pages(template_data["template_id"])

    if not template_pages:
        st.error("Failed to load template pages. Please try again.")
        return

    st.info(f"Creating a {len(template_pages)}-page personalized book for {template_data['child_name']}...")

    # Create progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    generated_pages = []

    # Process each page
    for idx, page in enumerate(template_pages):
        progress = (idx + 1) / len(template_pages)
        progress_bar.progress(progress)
        status_text.text(f"Processing page {idx + 1} of {len(template_pages)}: {page['profession_title']}")

        # Personalize text
        personalized_text = personalize_template_text(
            page["text_template"],
            template_data["child_name"],
            template_data["child_gender"],
            template_data["child_age"]
        )

        # Personalize image prompt
        personalized_image_prompt = personalize_template_image_prompt(
            page["image_prompt_template"],
            template_data["child_name"],
            template_data["child_gender"],
            template_data["child_age"],
            photo_description="matching the uploaded photos"
        )

        # For now, we'll store the prompts but won't generate images immediately
        # User can preview and then generate images
        generated_pages.append({
            "page_number": page["page_number"],
            "profession_title": page["profession_title"],
            "text": personalized_text,
            "image_prompt": personalized_image_prompt,
            "image_url": None  # Will be generated later
        })

    status_text.text("Book structure generated successfully!")
    progress_bar.progress(1.0)

    st.success(f"Your personalized book '{template_data['template_name'].replace('{name}', template_data['child_name'])}' has been created!")

    # Store in session state
    st.session_state.template_generated_book = {
        "template_id": template_data["template_id"],
        "child_name": template_data["child_name"],
        "child_gender": template_data["child_gender"],
        "child_age": template_data["child_age"],
        "pages": generated_pages,
        "total_pages": len(generated_pages)
    }

    # Show preview
    st.divider()
    display_template_book_preview(st.session_state.template_generated_book)


def display_template_book_preview(book_data: Dict):
    """Display preview of the generated template book."""

    st.subheader(f"Preview: When {book_data['child_name']} Grows Up")

    st.write(f"Total Pages: {book_data['total_pages']}")

    # Show page selector
    page_numbers = [p["page_number"] for p in book_data["pages"]]
    selected_page_num = st.select_slider(
        "Select page to preview:",
        options=page_numbers,
        value=1
    )

    # Find selected page
    selected_page = next(p for p in book_data["pages"] if p["page_number"] == selected_page_num)

    # Display page
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(f"### {selected_page['profession_title']}")
        st.markdown(f"**Page {selected_page['page_number']} of {book_data['total_pages']}**")

        # Show text with nice formatting
        st.markdown("---")
        st.markdown(selected_page['text'])
        st.markdown("---")

    with col2:
        st.write("**Image Preview**")
        if selected_page['image_url']:
            st.image(selected_page['image_url'], use_container_width=True)
        else:
            from PIL import Image, ImageDraw, ImageFont
            import io

            # Create a placeholder image
            img = Image.new('RGB', (800, 800), color=(240, 240, 250))
            draw = ImageDraw.Draw(img)

            # Draw profession title
            title_text = selected_page['profession_title']
            bbox = draw.textbbox((0, 0), title_text)
            text_width = bbox[2] - bbox[0]
            text_x = (800 - text_width) // 2
            draw.text((text_x, 300), title_text, fill=(100, 100, 200))

            # Draw placeholder text
            placeholder_text = f"{book_data['child_name']} as a {selected_page['profession_title'].title()}"
            bbox2 = draw.textbbox((0, 0), placeholder_text)
            text_width2 = bbox2[2] - bbox2[0]
            text_x2 = (800 - text_width2) // 2
            draw.text((text_x2, 400), placeholder_text, fill=(150, 150, 150))

            # Draw info text
            info_text = "AI Image will be generated"
            bbox3 = draw.textbbox((0, 0), info_text)
            text_width3 = bbox3[2] - bbox3[0]
            text_x3 = (800 - text_width3) // 2
            draw.text((text_x3, 500), info_text, fill=(180, 180, 180))

            st.image(img, use_container_width=True)

            with st.expander("View AI Image Prompt"):
                st.code(selected_page['image_prompt'], language="text")

    # Actions
    st.divider()

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("Start Over", use_container_width=True):
            st.session_state.generate_template_book = False
            st.session_state.template_book_data = None
            st.session_state.template_generated_book = None
            st.rerun()

    with col2:
        st.button("Edit Pages", use_container_width=True, disabled=True, help="Coming soon")

    with col3:
        if st.button("Generate Images & PDF", type="primary", use_container_width=True):
            st.session_state.template_generate_images = True
            st.rerun()
