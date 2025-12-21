# Print-on-Demand Children's Book Generator

A Streamlit web application that generates personalized children's storybooks in real-time using Google Gemini AI for text generation and Imagen for image generation.

## Features

- 📝 Interactive form to collect child details (name, age, gender, physical description)
- 🎨 AI-powered story generation with consistent character appearance
- 🖼️ Automatic image generation for each page
- 📄 PDF generation with professional layout (8.5x8.5 inches)
- 📱 Mobile-friendly interface
- 🌍 Support for English and Hindi languages

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get Google Gemini API Key:**
   - Visit https://makersuite.google.com/app/apikey
   - Create a new API key
   - Copy the key

3. **Run the application:**
   ```bash
   streamlit run main.py
   ```

4. **Access the app:**
   - Open your browser to the URL shown in the terminal (usually http://localhost:8501)
   - Enter your API key in the sidebar
   - Fill in the child's details
   - Click "Generate Story"

## Usage

1. Enter your Google Gemini API key in the sidebar
2. Fill in the child's information:
   - Name (required)
   - Age (2-16 years)
   - Gender
   - Physical description (skin tone, hair, eyes, outfit)
   - Problem/Theme for the story (required)
   - Language preference
3. Click "Generate Story"
4. Wait for the story, images, and PDF to be generated
5. Download the PDF and print it on 8.5x8.5 inch paper

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
