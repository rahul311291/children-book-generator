import streamlit as st
import json
import os
import tempfile
import base64
from pathlib import Path
from typing import List, Dict
from reportlab.lib.units import inch
import requests
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
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
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

def create_visual_anchor(child_name: str, age: int, gender: str, physical_desc: str) -> str:
    """Create a visual anchor description for consistent character appearance."""
    anchor = f"A cute {age} year old {gender.lower()}, {physical_desc.lower()}"
    return anchor

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

def generate_story_with_gemini(api_key: str, child_name: str, age: int, gender: str, 
                               physical_desc: str, problem: str, language: str) -> Dict:
    """Generate story using Gemini API via REST."""
    try:
        # Create visual anchor
        visual_anchor = create_visual_anchor(child_name, age, gender, physical_desc)
        
        # System instruction
        system_instruction = f"""You are an expert children's book author. Write a 10-page story for a {age} year old child named {child_name}. 
The story must follow a clear arc: Problem -> Struggle -> Solution. Use simple, rhythmic language appropriate for a {age} year old.
Write in {language} language.

CRITICAL: You must output ONLY a valid JSON object with this exact structure:
{{
    "visual_anchor": "{visual_anchor}",
    "pages": [
        {{
            "page_number": 1,
            "text": "Story text for page 1 (max 2 sentences)",
            "image_prompt": "[Visual Anchor] detailed scene description for page 1"
        }},
        ...
    ]
}}

IMPORTANT RULES:
1. Create exactly 10 pages
2. Each page text should be max 2 sentences, simple and age-appropriate
3. EVERY image_prompt MUST start with the visual_anchor string to ensure character consistency
4. The story should address the problem: {problem}
5. Make the story engaging, positive, and educational
6. Output ONLY the JSON, no additional text before or after"""

        prompt = f"""Write a personalized children's story for {child_name}, a {age} year old {gender}.
Problem/Theme: {problem}
Physical Description: {physical_desc}

{system_instruction}"""

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
            raise Exception(error_msg)
        
        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        story_data = json.loads(response_text)
        
        # Ensure visual anchor is prepended to all image prompts
        visual_anchor = story_data.get("visual_anchor", visual_anchor)
        for page in story_data.get("pages", []):
            if not page.get("image_prompt", "").startswith(visual_anchor):
                page["image_prompt"] = f"{visual_anchor}, {page.get('image_prompt', '')}"
        
        return story_data
        
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON response: {e}")
        st.code(response_text)
        return None
    except Exception as e:
        st.error(f"Error generating story: {e}")
        return None

def generate_image_with_imagen(api_key: str, prompt: str, retry_count: int = 0) -> Image.Image:
    """Generate image using Gemini 3 Pro Image Preview (Nano Banana Pro) via REST API."""
    try:
        # Enhanced prompt with style
        style_prompt = f"{prompt}. Storybook illustration, vibrant colors, soft lighting, 3D Pixar style, children's book art, high quality, detailed"
        
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
                    return image
        
        raise Exception("No image generated in response")
            
    except Exception as e:
        if retry_count < 1:
            st.warning(f"Image generation failed, retrying... ({e})")
            time.sleep(2)
            return generate_image_with_imagen(api_key, prompt, retry_count + 1)
        else:
            st.error(f"Failed to generate image after retries: {e}")
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
            
        # Image area (top 70%)
        image_height = page_height * 0.7
        image_y = page_height - image_height
        
        # Resize and place image
        img = images[idx]
        img_width, img_height = img.size
        aspect_ratio = img_width / img_height
        
        if aspect_ratio > 1:
            # Landscape image
            display_width = page_width
            display_height = page_width / aspect_ratio
            if display_height > image_height:
                display_height = image_height
                display_width = image_height * aspect_ratio
        else:
            # Portrait image
            display_height = image_height
            display_width = image_height * aspect_ratio
            if display_width > page_width:
                display_width = page_width
                display_height = page_width / aspect_ratio
        
        x_offset = (page_width - display_width) / 2
        y_offset = image_y + (image_height - display_height) / 2
        
        img_resized = img.resize((int(display_width), int(display_height)), Image.Resampling.LANCZOS)
        img_io = io.BytesIO()
        img_resized.save(img_io, format='PNG')
        img_io.seek(0)
        
        c.drawImage(ImageReader(img_io), x_offset, y_offset, 
                   width=display_width, height=display_height, preserveAspectRatio=True)
        
        # Text area (bottom 30%)
        text_area_height = page_height * 0.3
        text_area_y = 0  # Bottom of page
        
        # Draw text - position at bottom 30% of page, centered
        text = page.get("text", "")
        para = Paragraph(text, text_style)
        para_width = page_width - 60  # Leave margins on sides
        para_height = para.wrap(para_width, text_area_height)[1]
        
        # Center text vertically in the bottom 30% area
        text_y = text_area_y + (text_area_height - para_height) / 2
        
        # Draw text centered horizontally
        para.drawOn(c, 30, text_y)
        
        c.showPage()
    
    c.save()

def main():
    st.title("📚 Print-on-Demand Children's Book Generator")
    st.markdown("Create personalized storybooks for children in real-time!")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # API Key Input
        api_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            value=st.session_state.api_key,
            help="Enter your Google Gemini API key. Get one from https://makersuite.google.com/app/apikey"
        )
        st.session_state.api_key = api_key
        
        st.divider()
        
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
        
        problem = st.text_area(
            "Problem/Theme *",
            placeholder="e.g., Refuses to eat vegetables, Scared of the dark, Doesn't like to share",
            height=100
        )
        
        language = st.selectbox("Language *", ["English", "Hindi"])
        
        st.divider()
        
        generate_button = st.button("✨ Generate Story", type="primary", use_container_width=True)
    
    # Main content area
    if not api_key:
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
                api_key, child_name, age, gender, physical_desc, problem, language
            )
            
            if not story_data:
                st.error("Failed to generate story. Please try again.")
                return
            
            st.session_state.generated_story = story_data
            st.success("✅ Story generated! Please review below.")
    
    # Step 1: Story Review
    if st.session_state.generated_story and not st.session_state.story_approved:
        st.header("📖 Step 1: Review Story")
        st.markdown("Please review the generated story and approve it to proceed with image generation.")
        
        pages = st.session_state.generated_story.get("pages", [])
        st.subheader("Story Pages")
        
        for i, page in enumerate(pages):
            with st.expander(f"📄 Page {page.get('page_number', i+1)}"):
                st.write("**Story Text:**")
                st.info(page.get("text", ""))
                st.write("**Image Prompt:**")
                st.caption(page.get("image_prompt", ""))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve Story", type="primary", use_container_width=True):
                st.session_state.story_approved = True
                st.rerun()
        with col2:
            if st.button("🔄 Regenerate Story", use_container_width=True):
                st.session_state.generated_story = None
                st.rerun()
    
    # Step 2: Image Generation with Review
    if st.session_state.generated_story and st.session_state.story_approved:
        pages = st.session_state.generated_story.get("pages", [])
        total_pages = len(pages)
        approved_count = len([k for k, v in st.session_state.image_approvals.items() if v])
        
        st.header("🎨 Step 2: Generate & Review Images")
        st.progress(approved_count / total_pages if total_pages > 0 else 0)
        st.caption(f"Approved: {approved_count}/{total_pages} images")
        
        # Generate images that haven't been generated yet
        if len(st.session_state.generated_images) < total_pages:
            with st.spinner(f"Generating image {len(st.session_state.generated_images) + 1}/{total_pages}..."):
                page_idx = len(st.session_state.generated_images)
                page = pages[page_idx]
                image_prompt = page.get("image_prompt", "")
                img = generate_image_with_imagen(api_key, image_prompt)
                st.session_state.generated_images.append(img)
                st.rerun()
        
        # Show images for review
        for i, page in enumerate(pages):
            if i >= len(st.session_state.generated_images):
                break
                
            is_approved = st.session_state.image_approvals.get(i, False)
            
            with st.container():
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader(f"Page {page.get('page_number', i+1)}")
                    st.write("**Story Text:**", page.get("text", ""))
                    st.image(st.session_state.generated_images[i], use_container_width=True)
                
                with col2:
                    st.write("")  # Spacing
                    if is_approved:
                        st.success("✅ Approved")
                        if st.button(f"🔄 Regenerate Image {i+1}", key=f"regen_{i}"):
                            # Remove approval and regenerate
                            del st.session_state.image_approvals[i]
                            # Remove this image and regenerate
                            st.session_state.generated_images = st.session_state.generated_images[:i]
                            st.rerun()
                    else:
                        col_approve, col_regen = st.columns(2)
                        with col_approve:
                            if st.button("✅ Approve", key=f"approve_{i}", type="primary"):
                                st.session_state.image_approvals[i] = True
                                st.rerun()
                        with col_regen:
                            if st.button("🔄 Regenerate", key=f"regenerate_{i}"):
                                # Remove this image and regenerate
                                st.session_state.generated_images = st.session_state.generated_images[:i]
                                st.rerun()
                
                st.divider()
        
        # Check if all images are approved
        if approved_count == total_pages and total_pages > 0:
            st.session_state.all_images_approved = True
    
    # Step 3: Generate PDF
    if (st.session_state.generated_story and 
        st.session_state.story_approved and 
        st.session_state.all_images_approved and
        len(st.session_state.generated_images) > 0):
        
        if st.session_state.pdf_path is None or not os.path.exists(st.session_state.pdf_path):
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
        
        st.header("📚 Step 3: Download Your Storybook")
        st.success("🎉 All content approved! Your storybook is ready to download.")
        
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
            
            # Preview of final pages
            st.subheader("Final Preview")
            pages = st.session_state.generated_story.get("pages", [])
            for i, page in enumerate(pages):
                if i < len(st.session_state.generated_images):
                    with st.expander(f"📄 Page {page.get('page_number', i+1)}"):
                        st.write("**Text:**", page.get("text", ""))
                        st.image(st.session_state.generated_images[i], use_container_width=True)
        else:
            st.warning("PDF not available")

if __name__ == "__main__":
    main()

