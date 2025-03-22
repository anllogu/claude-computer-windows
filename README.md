# Claude Computer Use Demo - Windows Version

This is a Windows-native implementation of the Claude Computer Use demo, allowing Claude to control your Windows computer without Docker or virtual machines.

## Features

- Control mouse, keyboard, and take screenshots directly on Windows
- Execute PowerShell commands
- Read and write files
- Simple Streamlit interface for interactive use
- API-only mode for programmatic access
- Works with Claude 3.5 Sonnet and Claude 3.7 Sonnet models

## Security Warning

⚠️ **CAUTION**: Computer use poses unique security risks. Claude will have control of your mouse and keyboard. Only run this demo when you can monitor the actions and be ready to close the application if necessary.

## Requirements

- Windows 10 or Windows 11
- Python 3.8 or higher
- Anthropic API key with access to Claude 3.5/3.7 Sonnet

## Installation

1. Clone this repository or download the Windows version files:

```
git clone https://github.com/your-username/claude-computer-windows.git
cd claude-computer-windows
```

2. Create a virtual environment (recommended):

```
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:

```
# Basic installation with GUI support
pip install -r requirements.txt

# For API-only mode
pip install -e ".[api]"
```

4. Create a `.env` file with your Anthropic API key:
```
cp .env.example .env
```

5. Edit the `.env` file with your actual API key and optionally customize other settings:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
# Optional custom settings
# MODEL_NAME=claude-3-7-sonnet-20250219
# MAX_OUTPUT_TOKENS=4096
# SCREENSHOT_DELAY=10  # Delay in seconds between action and screenshot
```

## Usage

1. Run the application in one of the following ways:

   a. With Streamlit GUI:
   ```
   streamlit run claude_computer_windows/streamlit_app.py
   ```

   b. Using the command line entry point (GUI mode):
   ```
   python -m claude_computer_windows

   # Run with custom screenshot delay (10 seconds)
   python -m claude_computer_windows --screenshot-delay 10
   ```

   c. In API-only mode (no GUI):
   ```
   python -m claude_computer_windows --api-only

   # With custom port and host
   python -m claude_computer_windows --api-only --port 8080 --host 127.0.0.1
   ```

2. Make sure you've set up the `.env` file as described above, as the API key configuration is only available via this file.

3. Start chatting with Claude. You can ask it to:
   - Take a screenshot (`Take a screenshot of my desktop`)
   - Control the mouse (`Click on the Start button`)
   - Type text (`Type "Hello World" in Notepad`)
   - Execute PowerShell commands (`List the files in my Downloads folder`)
   - Read and write files (`Read the file C:\\path\\to\\file.txt`)

## API Usage

When running in API-only mode, you can interact with the application programmatically:

1. Send a prompt as JSON:
```
POST /api/run
Content-Type: application/json

{
  "prompt": "Take a screenshot and click on the Start menu"
}
```

2. Send a prompt as plain text:
```
POST /api/run-text
Content-Type: text/plain

Take a screenshot and click on the Start menu
```

The API returns the final message and screenshots after execution:
```json
{
  "response": "I've taken a screenshot and clicked on the Start menu for you. The Start menu is now open.",
  "screenshots": [
    "base64_encoded_image_data..."
  ]
}
```

Error responses:
```json
{
  "status": "error",
  "error": "ErrorType: Error message details"
}
```

## Limitations

- Claude can only control what is visible on the screen
- Some system directories are restricted for security reasons
- Performance may vary depending on your system specifications
- Screenshots and interactions are limited to the main display

## Differences from Linux Version

This Windows version:
- Uses PyAutoGUI instead of xdotool for mouse/keyboard control
- Uses PowerShell instead of Bash for command execution
- Has simpler tool implementations tailored to Windows
- Doesn't require Docker or VNC server
- Runs directly on the host Windows system

## License

This project is licensed under the same terms as the original Claude Computer Use Demo.