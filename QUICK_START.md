# Quick Start Guide

## Step 1: Get Your Google Gemini API Key

1. Go to: https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key (you'll need this in the app)

## Step 2: Run the App

Open Terminal and run:

```bash
cd "/Users/rahulshah/Desktop/Business/Story book"
streamlit run main.py
```

Or if `streamlit` command doesn't work, try:

```bash
python3 -m streamlit run main.py
```

## Step 3: Use the App

1. The app will open in your browser automatically (usually at http://localhost:8501)
2. In the sidebar, paste your Google Gemini API key
3. Fill in the child's details
4. Click "Generate Story"
5. Wait for the storybook to be generated
6. Download the PDF and print it!

## Troubleshooting

- If `streamlit` command not found, use: `python3 -m streamlit run main.py`
- Make sure you have internet connection for API calls
- The API key needs access to both Gemini and Imagen APIs

