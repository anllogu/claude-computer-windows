# Claude Code Assistant Configuration

## Build & Run Commands
```
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run the application
streamlit run claude_computer_windows/streamlit_app.py

# Run from command line entry point
python -m claude_computer_windows
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