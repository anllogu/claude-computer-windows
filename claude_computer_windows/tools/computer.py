"""
Windows implementation of computer control tools for Claude.
Uses PyAutoGUI and Pillow for mouse/keyboard control and screenshots.
"""

import asyncio
import base64
import io
import os
import time
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypedDict, cast, get_args
from uuid import uuid4

import pyautogui
from PIL import Image

# Configure PyAutoGUI for safety
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1  # Add small delay between actions

# Define action types
Action = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "screenshot",
    "cursor_position",
    "left_mouse_down",
    "left_mouse_up",
    "scroll",
    "hold_key",
    "wait",
    "triple_click",
]

ScrollDirection = Literal["up", "down", "left", "right"]

OUTPUT_DIR = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "claude_outputs")


class ToolError(Exception):
    """Raised when a tool encounters an error."""
    def __init__(self, message):
        self.message = message


class ToolResult:
    """Represents the result of a tool execution."""
    def __init__(self, output=None, error=None, base64_image=None, system=None):
        self.output = output
        self.error = error
        self.base64_image = base64_image
        self.system = system
    
    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        new_result = ToolResult(
            output=self.output,
            error=self.error,
            base64_image=self.base64_image,
            system=self.system
        )
        for key, value in kwargs.items():
            setattr(new_result, key, value)
        return new_result


class Resolution(TypedDict):
    """Screen resolution definition."""
    width: int
    height: int


class ComputerTool:
    """
    A tool that allows the agent to interact with the screen, keyboard, and mouse on Windows.
    Uses PyAutoGUI and other Windows-specific libraries instead of Linux tools.
    """

    def __init__(self):
        """Initialize the computer tool with screen dimensions."""
        # Get actual screen size
        screen_size = pyautogui.size()
        self.width = screen_size.width
        self.height = screen_size.height
        
        # Create output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Configure screenshot delay
        self._screenshot_delay = 0.5

    async def __call__(self, *, action: str, **kwargs):
        """Execute the requested computer action."""
        
        # Simplified actions to match our tool schema
        if action == "screenshot":
            return await self.take_screenshot()
        elif action == "click":
            x = kwargs.get("x")
            y = kwargs.get("y")
            if x is None or y is None:
                raise ToolError("Both x and y coordinates are required for click action")
            return await self.handle_click(x, y)
        elif action == "move":
            x = kwargs.get("x")
            y = kwargs.get("y")
            if x is None or y is None:
                raise ToolError("Both x and y coordinates are required for move action")
            return await self.handle_move(x, y)
        elif action == "type":
            text = kwargs.get("text")
            if not text:
                raise ToolError("text parameter is required for type action")
            return await self.handle_typing(text=text)
        elif action == "hotkey":
            text = kwargs.get("text")
            if not text:
                raise ToolError("text parameter is required for hotkey action")
            return await self.handle_hotkey(text=text)
        else:
            raise ToolError(f"Invalid action: {action}")
            
    async def handle_click(self, x: int, y: int):
        """Handle mouse click at specific coordinates."""
        pyautogui.click(x, y)
        await asyncio.sleep(self._screenshot_delay)
        return await self.take_screenshot()
        
    async def handle_move(self, x: int, y: int):
        """Handle mouse movement to specific coordinates."""
        pyautogui.moveTo(x, y)
        return await self.take_screenshot()
        
    async def handle_hotkey(self, text: str):
        """Handle keyboard hotkey press."""
        # Split the hotkey string by '+' and press the keys together
        keys = text.split('+')
        pyautogui.hotkey(*keys)
        return await self.take_screenshot()
    
    async def take_screenshot(self):
        """Take a screenshot and return as base64 encoded PNG."""
        screenshot = pyautogui.screenshot()
        
        # Save to file and also encode to base64
        output_path = os.path.join(OUTPUT_DIR, f"screenshot_{uuid4().hex}.png")
        screenshot.save(output_path)
        
        # Convert to base64
        buffered = io.BytesIO()
        screenshot.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return ToolResult(output="Screenshot taken", base64_image=img_str)
    
    async def get_cursor_position(self):
        """Get the current position of the cursor."""
        x, y = pyautogui.position()
        return ToolResult(output=f"X={x},Y={y}")
    
    async def handle_mouse_movement(self, action, **kwargs):
        """Handle mouse movement actions."""
        coordinate = kwargs.get("coordinate")
        if not coordinate or len(coordinate) != 2:
            raise ToolError("coordinate must be a tuple of [x, y]")
        
        x, y = coordinate
        if action == "mouse_move":
            # Move mouse to position
            pyautogui.moveTo(x, y)
            return await self.take_screenshot()
        elif action == "left_click_drag":
            # Click and drag from current position to target
            current_x, current_y = pyautogui.position()
            pyautogui.dragTo(x, y, button='left')
            return await self.take_screenshot()
    
    async def handle_mouse_click(self, action, **kwargs):
        """Handle mouse click actions."""
        coordinate = kwargs.get("coordinate")
        key = kwargs.get("key")
        
        # Move mouse if coordinates provided
        if coordinate and len(coordinate) == 2:
            x, y = coordinate
            pyautogui.moveTo(x, y)
        
        # Handle key modifiers
        modifiers_active = False
        if key:
            pyautogui.keyDown(key)
            modifiers_active = True
        
        # Perform click action
        if action == "left_click":
            pyautogui.click(button='left')
        elif action == "right_click":
            pyautogui.click(button='right')
        elif action == "middle_click":
            pyautogui.click(button='middle')
        elif action == "double_click":
            pyautogui.click(button='left', clicks=2, interval=0.1)
        elif action == "triple_click":
            pyautogui.click(button='left', clicks=3, interval=0.1)
        
        # Release modifiers
        if modifiers_active:
            pyautogui.keyUp(key)
        
        # Return screenshot after action
        await asyncio.sleep(self._screenshot_delay)
        return await self.take_screenshot()
    
    async def handle_mouse_updown(self, action):
        """Handle mouse button up/down actions."""
        if action == "left_mouse_down":
            pyautogui.mouseDown(button='left')
        elif action == "left_mouse_up":
            pyautogui.mouseUp(button='left')
        
        return await self.take_screenshot()
    
    async def handle_key(self, **kwargs):
        """Handle keyboard key press actions."""
        text = kwargs.get("text")
        if not text:
            raise ToolError("text parameter is required for key action")
        
        pyautogui.press(text)
        return await self.take_screenshot()
    
    async def handle_typing(self, **kwargs):
        """Handle keyboard typing actions."""
        text = kwargs.get("text")
        if not text:
            raise ToolError("text parameter is required for type action")
        
        pyautogui.write(text, interval=0.01)
        return await self.take_screenshot()
    
    async def handle_scroll(self, **kwargs):
        """Handle scrolling actions."""
        scroll_direction = kwargs.get("scroll_direction")
        scroll_amount = kwargs.get("scroll_amount", 1)
        coordinate = kwargs.get("coordinate")
        
        if not scroll_direction:
            raise ToolError("scroll_direction is required ('up', 'down', 'left', or 'right')")
        
        if not isinstance(scroll_amount, int) or scroll_amount < 0:
            raise ToolError("scroll_amount must be a non-negative integer")
        
        # Move to coordinate if provided
        if coordinate and len(coordinate) == 2:
            x, y = coordinate
            pyautogui.moveTo(x, y)
        
        # Perform scroll
        if scroll_direction == "up":
            pyautogui.scroll(scroll_amount)
        elif scroll_direction == "down":
            pyautogui.scroll(-scroll_amount)
        elif scroll_direction == "left":
            pyautogui.hscroll(-scroll_amount)
        elif scroll_direction == "right":
            pyautogui.hscroll(scroll_amount)
        
        return await self.take_screenshot()
    
    async def handle_hold_key(self, **kwargs):
        """Handle key hold actions."""
        text = kwargs.get("text")
        duration = kwargs.get("duration")
        
        if not text:
            raise ToolError("text parameter is required for hold_key action")
        
        if not duration or not isinstance(duration, (int, float)) or duration < 0:
            raise ToolError("duration must be a positive number")
        
        if duration > 10:
            raise ToolError("duration too long (maximum 10 seconds)")
        
        # Press key, wait, and release
        pyautogui.keyDown(text)
        await asyncio.sleep(duration)
        pyautogui.keyUp(text)
        
        return await self.take_screenshot()
    
    async def handle_wait(self, **kwargs):
        """Handle wait actions."""
        duration = kwargs.get("duration")
        
        if not duration or not isinstance(duration, (int, float)) or duration < 0:
            raise ToolError("duration must be a positive number")
        
        if duration > 10:
            raise ToolError("duration too long (maximum 10 seconds)")
        
        await asyncio.sleep(duration)
        return await self.take_screenshot()