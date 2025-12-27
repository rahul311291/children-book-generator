# Print-on-Demand Children's Book Generator

A Streamlit web application that generates personalized children's storybooks in real-time using Google Gemini AI for text generation and Imagen for image generation.

## Features

### Custom Stories
- 📝 Interactive form to collect child details (name, age, gender, physical description)
- 🎨 AI-powered story generation with consistent character appearance
- 🖼️ Automatic image generation for each page
- 📄 PDF generation with professional layout (8.5x8.5 inches)
- 📱 Mobile-friendly interface
- 🌍 Support for English and Hindi languages

### Template Books (NEW!)
- 📚 Pre-designed book templates with professional content
- 👶 Personalize with child's name, age, gender, and photos
- 🎯 "When I Grow Up" template featuring 24 inspiring professions
- 🖼️ AI-generated images showing the child in each profession
- 💾 Stored in Supabase database for easy management
- ✨ Rhyming, age-appropriate text for each profession

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Supabase (for Template Books):**
   - Supabase database is already configured in `.env` file
   - Template data is already seeded in the database
   - No additional setup required for template books

3. **Get Google Gemini API Key:**
   - Visit https://makersuite.google.com/app/apikey
   - Create a new API key
   - Copy the key

4. **Run the application:**
   ```bash
   streamlit run main.py
   ```

5. **Access the app:**
   - Open your browser to the URL shown in the terminal (usually http://localhost:8501)
   - Select "Custom Story" or "Template Book" mode
   - Enter your API key in the sidebar (for image generation)
   - Fill in the required details
   - Click "Generate"

## Usage

### For Custom Stories:

1. Select "Custom Story" mode at the top
2. Enter your Google Gemini API key in the sidebar
3. Fill in the child's information:
   - Name (required)
   - Age (2-16 years)
   - Gender
   - Physical description (skin tone, hair, eyes, outfit)
   - Problem/Theme for the story (required)
   - Language preference
4. Click "Generate Story"
5. Wait for the story, images, and PDF to be generated
6. Download the PDF and print it on 8.5x8.5 inch paper

### For Template Books:

1. Select "Template Book" mode at the top
2. Choose a template (e.g., "When I Grow Up")
3. Enter child's information:
   - Name (required)
   - Age (2-16 years)
   - Gender (for pronouns)
4. Upload 3 photos of the child
5. Click "Generate My Personalized Book"
6. Preview all 24 profession pages
7. Generate images and PDF when ready
8. Download and print

For detailed information about template books, see [TEMPLATE_BOOKS_GUIDE.md](TEMPLATE_BOOKS_GUIDE.md)

## Technical Details

- **Frontend:** Streamlit
- **Text Generation:** Google Gemini 3.0 Pro
- **Image Generation:** Gemini 3 Pro Image Preview (Nano Banana Pro)
- **PDF Generation:** ReportLab
- **Page Size:** 8.5 x 8.5 inches (square format)
- **Layout:** 70% image (top), 30% text (bottom)

## Notes

- The app uses a "visual anchor" mechanism to ensure the main character looks consistent across all pages
- Images are generated with a 3D Pixar-style children's book aesthetic
- The PDF includes a dedication page at the beginning
- All generated content is stored temporarily and can be downloaded

## Troubleshooting

- If image generation fails, the app will retry once before using a placeholder
- Ensure you have a stable internet connection for API calls
- Make sure your API key has access to both Gemini and Imagen APIs
