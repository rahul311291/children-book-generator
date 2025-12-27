"""
Streamlit app entry point
Some deployment platforms look for streamlit_app.py
This file simply imports and runs main.py
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run main
from main import main

if __name__ == "__main__":
    main()
