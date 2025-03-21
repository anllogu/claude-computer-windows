# Claude Code Assistant Configuration

## Build & Run Commands
```
# Install dependencies
pip install -r requirements.txt

# Install in development mode (basic)
pip install -e .

# Install in development mode (with API support)
pip install -e ".[api]"

# Run the application with GUI
streamlit run claude_computer_windows/streamlit_app.py

# Run from command line entry point (GUI mode)
python -m claude_computer_windows

# Run in API-only mode (no GUI)
python -m claude_computer_windows --api-only

# API server options
python -m claude_computer_windows --api-only --port 8080 --host 127.0.0.1
```

## API Usage
When running in API-only mode, the application exposes simplified endpoints that accept a prompt and automatically execute the entire conversation:

- `POST /api/run`: Send a prompt as JSON
  ```json
  {
    "prompt": "Take a screenshot and click on the Start menu"
  }
  ```

- `POST /api/run-text`: Send a prompt as plain text (Content-Type: text/plain)
  ```
  Take a screenshot and click on the Start menu
  ```

The API returns only the final message and screenshots after complete execution:
```json
{
  "response": "I've taken a screenshot and clicked on the Start menu for you. The Start menu is now open.",
  "screenshots": [
    "base64_encoded_image_data..."
  ]
}

If there's an error, the response will look like:
```json
{
  "status": "error",
  "error": "ErrorType: Error message details"
}
```

## Code Style Guidelines
- **Imports**: Group standard library, third-party, and local imports; use absolute imports within the package
- **Formatting**: Type annotations for function parameters and returns; docstrings in Google style
- **Error Handling**: Use specific exceptions with descriptive messages; wrap external tool calls in try/except
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants
- **Tool Implementation**: Each tool should return `ToolResult` with appropriate output/error properties
- **Windows-specific**: Always validate file paths; use os.path for cross-platform compatibility

## Windows Development Notes
This is a Windows-specific implementation for Claude to interact with your computer via PyAutoGUI and PowerShell.