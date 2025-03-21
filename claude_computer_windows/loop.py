"""
Agent loop for Claude computer use on Windows.
Simplified version of the original Linux loop.py.
"""

import asyncio
import os
import platform
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, cast

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import httpx
from anthropic import Anthropic, APIError, APIResponseValidationError, APIStatusError
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
)

# Configure logging
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}
log_level = log_levels.get(log_level_str, logging.INFO)

# Create logs directory
os.makedirs("logs", exist_ok=True)

# Create dated directory for logs
date_dir = datetime.now().strftime("%Y%m%d")
os.makedirs(f"logs/{date_dir}", exist_ok=True)

# Create log file with timestamp (sortable by ls -ltr)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"logs/{date_dir}/claude_{timestamp}.log"

# Set global variable for log file name
LOG_FILE = log_filename

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging level set to: {log_level_str}")
logger.info(f"Log file created at: {LOG_FILE}")

# Define conversation logging function
def log_conversation(role, content, session_log_path=None):
    """
    Log conversation message with role identifier to both main log and session log.
    
    Args:
        role: The role ("user" or "assistant")
        content: The message content (string or content blocks)
        session_log_path: Optional path to session-specific log file
    """
    role_prefix = "[USER]" if role == "user" else "[CLAUDE]"
    log_messages = []
    
    # Extract text messages based on content type
    if isinstance(content, list):
        # Handle content blocks
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                log_messages.append(f"{role_prefix} {block.get('text')}")
    elif isinstance(content, str):
        # Handle string content
        log_messages.append(f"{role_prefix} {content}")
    
    # Log to main log file
    for message in log_messages:
        logger.info(message)
    
    # Log to session-specific log file if path is provided
    if session_log_path and log_messages:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(session_log_path, "a", encoding="utf-8") as f:
                for message in log_messages:
                    f.write(f"{timestamp} - {message}\n")
        except Exception as e:
            logger.error(f"Failed to write to session log: {e}")

from .tools.computer import ComputerTool, ToolResult

# Global variable to store session log path
SESSION_LOG_PATH = None
from .tools.cmd import PowerShellTool
from .tools.file import ReadFileTool, WriteFileTool, EditFileTool


class ToolVersion(str, Enum):
    """Supported Claude tool versions."""
    CLAUDE_35_SONNET = "computer_use_20241022"
    CLAUDE_37_SONNET = "computer_use_20250124"


# Basic system prompt for Windows environment
SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
* You are utilizing a Windows {platform.release()} computer with internet access.
* You can control the mouse, keyboard, and view the screen through the custom "computer" tool.
* You can execute PowerShell commands using the "bash" tool to interact with the system.
* You can read files with the "read_file" tool.
* You can write files with the "str_replace_editor" tool and edit files with the "edit_file" tool, but access to system directories is restricted.
* The current date is {datetime.today().strftime('%A, %B %d, %Y')}.
</SYSTEM_CAPABILITY>

<IMPORTANT>
* Be careful when executing commands or editing files. Always confirm dangerous operations.
* Do not attempt to access system directories or files that may contain sensitive information.
* When using your PowerShell tool with commands that output large amounts of text, redirect into a file and read that file afterwards.
* For the "computer" tool, valid actions are: "screenshot", "click", "double_click", "scroll", "type", "move", "hotkey", and "set_scale_factor". If clicks aren't registering at the correct position, use set_scale_factor to adjust the DPI scaling.
</IMPORTANT>"""


class ToolCollection:
    """Collection of tools that Claude can use."""
    
    def __init__(self):
        """Initialize the tool collection with Windows-appropriate tools."""
        # Initialize computer tool first to get session log path
        computer_tool = ComputerTool()
        
        # Set global session log path
        global SESSION_LOG_PATH
        SESSION_LOG_PATH = computer_tool.conversation_log_path
        
        self.tools = {
            "computer": computer_tool,
            "bash": PowerShellTool(),  # Renamed for API compatibility
            "read_file": ReadFileTool(),
            "str_replace_editor": WriteFileTool(),  # Renamed for API compatibility
            "edit_file": EditFileTool(),
        }
    
    async def run(self, name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Run a tool with the given input.
        
        Args:
            name: The name of the tool to run.
            tool_input: The input parameters for the tool.
            
        Returns:
            ToolResult with the tool's output.
        """
        if name not in self.tools:
            return ToolResult(error=f"Unknown tool: {name}")
            
        try:
            return await self.tools[name](**tool_input)
        except Exception as e:
            return ToolResult(error=f"Error running tool {name}: {str(e)}")
    
    def to_params(self) -> list[dict]:
        """Convert tools to API parameters for Claude."""
        return [
            {
                "name": "computer", 
                "description": "Interact with the Windows computer using mouse, keyboard and screenshots",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["click", "double_click", "scroll", "screenshot", "type", "move", "hotkey", "set_scale_factor"],
                            "description": "The action to perform on the computer"
                        },
                        "x": {"type": "integer", "description": "X coordinate for mouse actions"},
                        "y": {"type": "integer", "description": "Y coordinate for mouse actions"},
                        "text": {"type": "string", "description": "Text to type or hotkey to press"},
                        "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "Direction for scroll action"},
                        "amount": {"type": "integer", "description": "Amount to scroll (default: 3)"},
                        "scale": {"type": "number", "description": "Scale factor value for set_scale_factor action"}
                    },
                    "required": ["action"]
                }
            },
            {
                "type": "bash_20250124",
                "name": "bash"
            },
            {
                "name": "read_file", 
                "description": "Read a file from the filesystem",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to read"}
                    },
                    "required": ["path"]
                }
            },
            {
                "type": "text_editor_20250124",
                "name": "str_replace_editor"
            },
            {
                "name": "edit_file", 
                "description": "Edit an existing file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to edit"},
                        "content": {"type": "string", "description": "New content for the file"}
                    },
                    "required": ["path", "content"]
                }
            }
        ]


async def sampling_loop(
    *,
    model: str,
    api_key: str,
    system_prompt_suffix: str,
    messages: list[BetaMessageParam],
    output_callback: Callable[[BetaContentBlockParam], None],
    tool_output_callback: Callable[[ToolResult, str], None],
    api_response_callback: Callable[[httpx.Request, httpx.Response | object | None, Exception | None], None],
    max_tokens: int = 4096,
    tool_version: ToolVersion = ToolVersion.CLAUDE_37_SONNET,
):
    """Agent loop for Claude computer use."""
    tool_collection = ToolCollection()
    system = BetaTextBlockParam(
        type="text",
        text=f"{SYSTEM_PROMPT}{' ' + system_prompt_suffix if system_prompt_suffix else ''}",
    )

    while True:
        # Ensure api_key is set
        if not api_key:
            raise ValueError("API key must be provided")
            
        client = Anthropic(api_key=api_key, max_retries=3)
        
        # Call the API
        try:
            raw_response = client.beta.messages.with_raw_response.create(
                max_tokens=max_tokens,
                messages=messages,
                model=model,
                system=[system],
                tools=tool_collection.to_params(),
            )
        except (APIStatusError, APIResponseValidationError) as e:
            api_response_callback(e.request, e.response, e)
            return messages
        except APIError as e:
            api_response_callback(e.request, e.body, e)
            return messages

        api_response_callback(
            raw_response.http_response.request, raw_response.http_response, None
        )

        response = raw_response.parse()
        logger.info(f"Received response from Claude API: {len(response.content)} content blocks")
        logger.debug(f"Raw response content: {response.content}")

        # Convert to the format expected by the application
        response_params = []
        for block in response.content:
            if block.type == "text":
                if block.text:
                    response_params.append(BetaTextBlockParam(type="text", text=block.text))
            else:
                # Handle tool use blocks
                response_params.append(cast(BetaContentBlockParam, block.model_dump()))

        # Log assistant message
        log_conversation("assistant", response_params, SESSION_LOG_PATH)
        
        messages.append({
            "role": "assistant",
            "content": response_params,
        })

        tool_result_content: list[BetaToolResultBlockParam] = []
        for content_block in response_params:
            output_callback(content_block)
            if content_block["type"] == "tool_use":
                logger.info(f"Tool execution: {content_block['name']} with input: {content_block['input']}")
                result = await tool_collection.run(
                    name=content_block["name"],
                    tool_input=cast(dict[str, Any], content_block["input"]),
                )
                
                # Log tool result
                if isinstance(result, ToolResult) and result.error:
                    logger.error(f"Tool execution error: {result.error}")
                    # Also log to session log
                    if SESSION_LOG_PATH:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        with open(SESSION_LOG_PATH, "a", encoding="utf-8") as f:
                            f.write(f"{timestamp} - [TOOL] {content_block['name']} error: {result.error}\n")
                else:
                    tool_output = result.output if hasattr(result, "output") and result.output else "No output"
                    logger.info(f"Tool execution successful: {content_block['name']} - {tool_output}")
                    # Also log to session log
                    if SESSION_LOG_PATH:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        with open(SESSION_LOG_PATH, "a", encoding="utf-8") as f:
                            f.write(f"{timestamp} - [TOOL] {content_block['name']} - {tool_output}\n")
                
                # Create tool result block
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": content_block["id"],
                    "content": _make_tool_result_content(result),
                    "is_error": result.error is not None,
                })
                
                tool_output_callback(result, content_block["id"])

        if not tool_result_content:
            logger.info("Conversation ended without tool usage")
            return messages

        logger.info(f"Adding {len(tool_result_content)} tool result(s) to messages")
        messages.append({"content": tool_result_content, "role": "user"})


def _make_tool_result_content(result: ToolResult) -> list[BetaContentBlockParam] | str:
    """Convert a ToolResult to the format expected by the API."""
    content = []
    
    if result.error:
        # If there's an error, return it as a string
        return result.error
    
    if result.output:
        content.append({
            "type": "text",
            "text": result.output,
        })
    
    if result.base64_image:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": result.base64_image,
            },
        })
    
    return content