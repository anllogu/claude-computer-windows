# Claude Computer Use Demo - Windows Version

This is a Windows-native implementation of the Claude Computer Use demo, allowing Claude to control your Windows computer without Docker or virtual machines.

## Features

- Control mouse, keyboard, and take screenshots directly on Windows
- Execute PowerShell commands
- Read and write files
- Simple Streamlit interface
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
pip install -r requirements.txt
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
```

## Usage

1. Run the Streamlit application:

```
streamlit run claude_computer_windows/streamlit_app.py
```

Alternatively, use the command line entry point:
```
python -m claude_computer_windows
```

2. Make sure you've set up the `.env` file as described above, as the API key configuration is only available via this file.

3. Start chatting with Claude. You can ask it to:
   - Take a screenshot (`Take a screenshot of my desktop`)
   - Control the mouse (`Click on the Start button`)
   - Type text (`Type "Hello World" in Notepad`)
   - Execute PowerShell commands (`List the files in my Downloads folder`)
   - Read and write files (`Read the file C:\\path\\to\\file.txt`)

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