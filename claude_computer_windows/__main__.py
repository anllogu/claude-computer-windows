"""
Entry point for running the Claude Computer Windows app.
Supports both Streamlit GUI mode and API-only mode.
"""

import subprocess
import sys
import os
import platform
import argparse
import asyncio
import json
import httpx
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the API-only functionality
from claude_computer_windows.loop import (
    sampling_loop, ToolVersion, log_conversation, ToolResult
)
from anthropic.types.beta import (
    BetaMessageParam, BetaContentBlockParam, BetaTextBlockParam, BetaToolResultBlockParam
)

async def run_claude_computer(
    prompt: str,
    api_key: str,
    model: str = "claude-3-7-sonnet-20250219",
    max_tokens: int = 4096,
    system_prompt_suffix: str = ""
) -> Dict[str, Any]:
    """
    Run Claude Computer with a single prompt and return the results.
    This is a simplified API endpoint that runs a complete session and returns the results.
    
    Args:
        prompt: The user prompt to process
        api_key: Anthropic API key
        model: Model to use
        max_tokens: Maximum tokens for the response
        system_prompt_suffix: Additional system prompt instructions
        
    Returns:
        Results of the execution including only the final assistant response
    """
    # Initialize the conversation
    messages: List[BetaMessageParam] = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt}
        ],
    }]
    
    # Track tool outputs and screenshots
    tool_outputs = {}
    screenshots = []
    
    # Define callbacks
    def output_callback(block: BetaContentBlockParam):
        """Callback for Claude's output."""
        # We'll only use this to track output during execution, but won't use it for the final result
        pass
    
    def tool_output_callback(result: ToolResult, tool_id: str):
        """Callback for tool outputs."""
        output_data = {
            "tool_id": tool_id,
            "output": result.output,
            "error": result.error
        }
        
        # If there's a screenshot, save it separately
        if result.base64_image:
            screenshot_index = len(screenshots)
            screenshots.append(result.base64_image)
            output_data["screenshot_index"] = screenshot_index
        
        tool_outputs[tool_id] = output_data
    
    def api_response_callback(request, response, error):
        """API response callback - not used for this simplified version."""
        pass
    
    try:
        # Run the sampling loop
        final_messages = await sampling_loop(
            system_prompt_suffix=system_prompt_suffix,
            model=model,
            api_key=api_key,
            messages=messages,
            output_callback=output_callback,
            tool_output_callback=tool_output_callback,
            api_response_callback=api_response_callback,
            max_tokens=max_tokens,
            tool_version=ToolVersion.CLAUDE_37_SONNET,
        )
        
        # Extract only the last assistant message
        last_assistant_message = ""
        for message in reversed(final_messages):
            if message["role"] == "assistant":
                for content in message["content"]:
                    if isinstance(content, dict) and content.get("type") == "text":
                        # Found the last assistant response, use this as the result
                        last_assistant_message = content.get("text", "")
                # Once we find the first assistant message (going backwards), we stop
                break
        
        # Create the result with only the final message
        result = {
            "response": last_assistant_message,
            "screenshots": screenshots
        }
        
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {str(e)}"
        }


def main():
    """Main entry point for the application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Claude Computer Windows")
    parser.add_argument("--screenshot-delay", type=float, default=os.getenv("SCREENSHOT_DELAY", 0.5),
                        help="Delay in seconds between action and screenshot (default: 0.5)")
    parser.add_argument("--api-only", action="store_true", 
                        help="Run in API-only mode without Streamlit interface")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port to run the API server on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Host to bind the API server to (default: 0.0.0.0)")
    args = parser.parse_args()
    
    # Set screenshot delay in environment for other processes to access
    os.environ["SCREENSHOT_DELAY"] = str(args.screenshot_delay)
    
    # Check if running on Windows
    if platform.system() != "Windows":
        print("This application is designed to run on Windows only.")
        print(f"Detected platform: {platform.system()}")
        sys.exit(1)
    
    # Run in API-only mode or GUI mode
    if args.api_only:
        # Check if API key is set
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("API key not found. Please set ANTHROPIC_API_KEY in your environment or .env file.")
            sys.exit(1)
        
        # Import FastAPI components if needed
        try:
            from fastapi import FastAPI, HTTPException, Body
            from pydantic import BaseModel
            import uvicorn
        except ImportError:
            print("API mode requires FastAPI and uvicorn. Install with:")
            print("pip install fastapi uvicorn")
            sys.exit(1)
        
        # Define API model
        class PromptRequest(BaseModel):
            prompt: str
        
        # Create FastAPI app
        app = FastAPI(title="Claude Computer Windows API")
        
        @app.post("/api/run")
        async def run_prompt(prompt_request: PromptRequest):
            """Run a single prompt through Claude Computer and return the results."""
            model = os.getenv("MODEL_NAME", "claude-3-7-sonnet-20250219")
            max_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "4096"))
            
            result = await run_claude_computer(
                prompt=prompt_request.prompt,
                api_key=api_key,
                model=model,
                max_tokens=max_tokens
            )
            
            return result
        
        # Create a simple POST endpoint that accepts raw text
        @app.post("/api/run-text", response_model=Dict[str, Any])
        async def run_text_prompt(prompt: str = Body(..., media_type="text/plain")):
            """Run a simple text prompt through Claude Computer."""
            model = os.getenv("MODEL_NAME", "claude-3-7-sonnet-20250219")
            max_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "4096"))
            
            result = await run_claude_computer(
                prompt=prompt,
                api_key=api_key,
                model=model,
                max_tokens=max_tokens
            )
            
            return result
        
        # Run the FastAPI server
        print(f"Starting API server on {args.host}:{args.port}")
        print("API endpoints:")
        print("  POST /api/run - Run Claude with JSON payload {\"prompt\": \"your command\"}")
        print("  POST /api/run-text - Run Claude with plain text prompt")
        uvicorn.run(app, host=args.host, port=args.port)
    else:
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


if __name__ == "__main__":
    main()