"""
Entry point for running the Claude Computer Windows app.
"""

import subprocess
import sys
import os
import platform
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

if __name__ == "__main__":
    # Check if running on Windows
    if platform.system() != "Windows":
        print("This application is designed to run on Windows only.")
        print(f"Detected platform: {platform.system()}")
        sys.exit(1)
    
    # Launch the Streamlit app
    script_dir = os.path.dirname(os.path.abspath(__file__))
    streamlit_path = os.path.join(script_dir, "streamlit_app.py")
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", streamlit_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Application terminated by user.")
        sys.exit(0)