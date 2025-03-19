"""
Streamlit interface for Claude Computer Use on Windows.
Simplified version of the original streamlit.py.
"""

import asyncio
import base64
import os
from contextlib import contextmanager
from datetime import datetime
from enum import StrEnum
from typing import cast

from dotenv import load_dotenv

import httpx
import streamlit as st
from anthropic import RateLimitError
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
)

from claude_computer_windows.loop import ToolVersion, sampling_loop, log_conversation, SESSION_LOG_PATH, LOG_FILE
from claude_computer_windows.tools.computer import ToolResult


class Sender(StrEnum):
    USER = "user"
    BOT = "assistant"
    TOOL = "tool"


# Default model for Claude 3.7 Sonnet
DEFAULT_MODEL = "claude-3-7-sonnet-20250219"

# Warning text for security
WARNING_TEXT = "⚠️ Security Alert: Use caution when giving Claude control of your computer. Be ready to close the browser tab if needed."


def setup_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if "model" not in st.session_state:
        st.session_state.model = os.getenv("MODEL_NAME", DEFAULT_MODEL)
    if "auth_validated" not in st.session_state:
        st.session_state.auth_validated = False
    if "responses" not in st.session_state:
        st.session_state.responses = {}
    if "tools" not in st.session_state:
        st.session_state.tools = {}
    if "custom_system_prompt" not in st.session_state:
        st.session_state.custom_system_prompt = ""
    if "hide_images" not in st.session_state:
        st.session_state.hide_images = False
    if "in_sampling_loop" not in st.session_state:
        st.session_state.in_sampling_loop = False
    if "output_tokens" not in st.session_state:
        st.session_state.output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "4096"))


async def main():
    """Main Streamlit app."""
    # Load environment variables from .env file
    load_dotenv()
    setup_state()

    st.title("Claude Computer Use - Windows Version")
    
    # Display API configuration info
    st.info(f"Using API configuration from .env file. Model: {st.session_state.model}\nTools: computer, bash (PowerShell), read_file, str_replace_editor (for files), edit_file")
    
    if "error_message" in st.session_state:
        st.error(st.session_state.error_message)
        del st.session_state.error_message

    st.warning(WARNING_TEXT)

    with st.sidebar:
        st.text_input(
            "Model",
            key="model",
            disabled=True,
            help="Claude model to use (configured via .env file)"
        )

        st.text_area(
            "Custom System Prompt Suffix",
            key="custom_system_prompt",
            help="Additional instructions to append to the system prompt."
        )

        st.checkbox("Hide screenshots", key="hide_images")
        
        st.number_input("Max Output Tokens", key="output_tokens", min_value=1024, max_value=128000, step=1024, disabled=True)

        if st.button("Reset Chat", type="primary"):
            st.session_state.messages = []
            st.session_state.tools = {}
            st.session_state.responses = {}
            st.rerun()

    if not st.session_state.auth_validated:
        if not st.session_state.api_key:
            st.session_state.error_message = "API key not found. Please check your .env file and ensure ANTHROPIC_API_KEY is set properly."
            st.rerun()
        st.session_state.auth_validated = True

    chat, http_logs = st.tabs(["Chat", "HTTP Exchange Logs"])
    
    new_message = st.chat_input("Type a message to send to Claude...")

    with chat:
        # Render past messages
        for message in st.session_state.messages:
            if isinstance(message["content"], str):
                _render_message(message["role"], message["content"])
            elif isinstance(message["content"], list):
                for block in message["content"]:
                    if isinstance(block, dict) and block["type"] == "tool_result":
                        _render_message(
                            Sender.TOOL, st.session_state.tools.get(block["tool_use_id"], {})
                        )
                    else:
                        _render_message(
                            message["role"],
                            cast(BetaContentBlockParam | ToolResult, block),
                        )

        # Render API responses in the HTTP tab
        for identity, (request, response) in st.session_state.responses.items():
            _render_api_response(request, response, identity, http_logs)

        # Handle new user message
        if new_message:
            # Log user message
            log_conversation("user", new_message, SESSION_LOG_PATH)
            
            st.session_state.messages.append({
                "role": Sender.USER,
                "content": [
                    BetaTextBlockParam(type="text", text=new_message),
                ],
            })
            _render_message(Sender.USER, new_message)

            try:
                with track_sampling_loop():
                    # Run the agent sampling loop
                    st.session_state.messages = await sampling_loop(
                        system_prompt_suffix=st.session_state.custom_system_prompt,
                        model=st.session_state.model,
                        api_key=st.session_state.api_key,
                        messages=st.session_state.messages,
                        output_callback=lambda block: _render_message(Sender.BOT, block),
                        tool_output_callback=lambda result, tool_id: _handle_tool_output(result, tool_id),
                        api_response_callback=lambda req, resp, err: _handle_api_response(req, resp, err, http_logs),
                        max_tokens=st.session_state.output_tokens,
                        tool_version=ToolVersion.CLAUDE_37_SONNET,
                    )
            except Exception as e:
                st.error(f"Error during conversation: {str(e)}")


def _handle_tool_output(result: ToolResult, tool_id: str):
    """Store tool output in session state and render it."""
    st.session_state.tools[tool_id] = result
    _render_message(Sender.TOOL, result)


def _handle_api_response(
    request: httpx.Request,
    response: httpx.Response | object | None,
    error: Exception | None,
    tab
):
    """Handle API response, storing it and rendering if there's an error."""
    response_id = datetime.now().isoformat()
    st.session_state.responses[response_id] = (request, response)
    
    if error:
        _render_error(error)
    
    _render_api_response(request, response, response_id, tab)


def _render_api_response(
    request: httpx.Request,
    response: httpx.Response | object | None,
    response_id: str,
    tab
):
    """Render an API response in the HTTP logs tab."""
    with tab:
        with st.expander(f"Request/Response ({response_id})"):
            st.markdown(f"`{request.method} {request.url}`")
            for k, v in request.headers.items():
                st.markdown(f"`{k}: {v}`")
            st.json(request.read().decode() if hasattr(request, 'read') else "{}")
            
            st.markdown("---")
            
            if isinstance(response, httpx.Response):
                st.markdown(f"`{response.status_code}`")
                for k, v in response.headers.items():
                    st.markdown(f"`{k}: {v}`")
                st.json(response.text)
            else:
                st.write(response)


def _render_error(error: Exception):
    """Render an error message."""
    if isinstance(error, RateLimitError):
        body = "You have been rate limited."
        if hasattr(error, 'response') and error.response.headers.get("retry-after"):
            retry_after = int(error.response.headers.get("retry-after", "60"))
            body += f" Retry after {retry_after} seconds."
    else:
        body = str(error)
    
    st.error(f"**{error.__class__.__name__}**\n\n{body}")


def _render_message(
    sender: Sender,
    message: str | BetaContentBlockParam | ToolResult,
):
    """Render a message in the chat interface."""
    # Skip empty messages or hidden images
    is_tool_result = not isinstance(message, (str, dict))
    if not message or (
        is_tool_result
        and st.session_state.hide_images
        and not hasattr(message, "error")
        and not hasattr(message, "output")
    ):
        return
        
    with st.chat_message(sender):
        if is_tool_result:
            # It's a tool result
            message = cast(ToolResult, message)
            if message.output:
                st.code(message.output)
            if message.error:
                st.error(message.error)
            if message.base64_image and not st.session_state.hide_images:
                st.image(base64.b64decode(message.base64_image))
        elif isinstance(message, dict):
            # It's a content block
            if message["type"] == "text":
                st.write(message["text"])
            elif message["type"] == "tool_use":
                st.code(f'Tool Use: {message["name"]}\nInput: {message["input"]}')
            else:
                # Only expected types are text and tool_use
                st.error(f'Unexpected response type {message["type"]}')
        else:
            # It's a plain string
            st.markdown(message)


@contextmanager
def track_sampling_loop():
    """Context manager to track when we're in the sampling loop."""
    st.session_state.in_sampling_loop = True
    try:
        yield
    finally:
        st.session_state.in_sampling_loop = False


if __name__ == "__main__":
    asyncio.run(main())