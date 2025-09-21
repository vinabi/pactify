# streamlit_app.py - MAIN APP ENTRY POINT FOR STREAMLIT CLOUD
"""
Main entry point for Streamlit Cloud deployment
This file should be at the root of your repository for Streamlit Cloud to detect it
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

# Import and run the main dashboard
from app_ui.home import main

if __name__ == "__main__":
    main()
