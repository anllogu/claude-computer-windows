"""
Agent loop for Claude computer use on Windows.
Simplified version of the original Linux loop.py.
"""

import asyncio
import os
import platform
from datetime import datetime
from enum import Enum
from typing import Any, Callable, cast

import httpx
from anthropic import Anthropic, APIError, APIResponseValidationError, APIStatusError
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
)

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
* You can control the mouse, keyboard, and view the screen through computer use tools.
* You can execute PowerShell commands to interact with the system.
* You can read and write files, but access to system directories is restricted.
* The current date is {datetime.today().strftime('%A, %B %d, %Y')}.
</SYSTEM_CAPABILITY>

<IMPORTANT>
* Be careful when executing commands or editing files. Always confirm dangerous operations.
* Do not attempt to access system directories or files that may contain sensitive information.
* When using your PowerShell tool with commands that output large amounts of text, redirect into a file and read that file afterwards.
</IMPORTANT>"""


class ToolCollection:
    """Collection of tools that Claude can use."""
    
    def __init__(self):
        """Initialize the tool collection with Windows-appropriate tools."""
        self.tools = {
            "computer": ComputerTool(),
            "powershell": PowerShellTool(),
            "read_file": ReadFileTool(),
            "write_file": WriteFileTool(),
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
        # In a full implementation, this would define proper schemas
        # Simplified version for demo purposes
        return [
            {"name": "computer", "type": "computer_20250124", "display_width_px": 1920, "display_height_px": 1080},
            {"name": "powershell", "type": "function", "description": "Execute PowerShell commands on Windows"},
            {"name": "read_file", "type": "function", "description": "Read a file from the filesystem"},
            {"name": "write_file", "type": "function", "description": "Write a file to the filesystem"},
            {"name": "edit_file", "type": "function", "description": "Edit an existing file"}
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
                result = await tool_collection.run(
                    name=content_block["name"],
                    tool_input=cast(dict[str, Any], content_block["input"]),
                )
                
                # Create tool result block
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": content_block["id"],
                    "content": _make_tool_result_content(result),
                    "is_error": result.error is not None,
                })
                
                tool_output_callback(result, content_block["id"])

        if not tool_result_content:
            return messages

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