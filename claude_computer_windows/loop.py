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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("claude_responses.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from .tools.computer import ComputerTool, ToolResult
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
* For the "computer" tool, valid actions are: "screenshot", "click", "type", "move", and "hotkey".
</IMPORTANT>"""


class ToolCollection:
    """Collection of tools that Claude can use."""
    
    def __init__(self):
        """Initialize the tool collection with Windows-appropriate tools."""
        self.tools = {
            "computer": ComputerTool(),
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
                            "enum": ["click", "screenshot", "type", "move", "hotkey"],
                            "description": "The action to perform on the computer"
                        },
                        "x": {"type": "integer", "description": "X coordinate for mouse actions"},
                        "y": {"type": "integer", "description": "Y coordinate for mouse actions"},
                        "text": {"type": "string", "description": "Text to type or hotkey to press"}
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
                else:
                    logger.info(f"Tool execution successful: {content_block['name']}")
                
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