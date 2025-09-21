# app.py - HUGGING FACE SPACES ENTRY POINT
"""
Entry point for Hugging Face Spaces deployment
This file is required by Hugging Face for Streamlit apps
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))

# Import and run the main dashboard  
from app_ui.home import main

if __name__ == "__main__":
    main()
