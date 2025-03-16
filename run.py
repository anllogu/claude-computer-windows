"""
Simple runner script to launch the Claude Computer Windows app.
"""
import os
import sys
import subprocess
import importlib.util

# Check if required packages are installed
required_packages = ['streamlit', 'anthropic', 'pyautogui', 'httpx']
missing_packages = []

for package in required_packages:
    if importlib.util.find_spec(package) is None:
        missing_packages.append(package)

if missing_packages:
    print(f"Missing required packages: {', '.join(missing_packages)}")
    install = input("Do you want to install them now? (y/n): ")
    if install.lower() == 'y':
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    else:
        print("Cannot run without required packages.")
        sys.exit(1)

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up environment for running the streamlit app
os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))

# Ask for API key if not set
if 'ANTHROPIC_API_KEY' not in os.environ:
    api_key = input("Please enter your Anthropic API key: ")
    os.environ['ANTHROPIC_API_KEY'] = api_key

print("Starting Claude Computer Windows application...")
print("Note: Make sure you have a valid Anthropic API key with computer usage enabled")

# Run the streamlit app with absolute import mode
os.environ['STREAMLIT_APP_IMPORT_MODE'] = 'absolute'
subprocess.run([
    sys.executable, "-m", "streamlit", "run", 
    os.path.join("claude_computer_windows", "streamlit_app.py"),
    "--server.headless", "true"
])