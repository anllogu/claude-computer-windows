"""
Windows implementation of computer control tools for Claude.
Uses PyAutoGUI and Pillow for mouse/keyboard control and screenshots.
"""

import asyncio
import base64
import io
import os
import time
import logging
from datetime import datetime
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

# Set up logger
logger = logging.getLogger(__name__)

# Base output directory
BASE_OUTPUT_DIR = "logs/screenshots"

# Current session directory (to be initialized in ComputerTool.__init__)
SESSION_DIR = ""


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
        """Initialize the computer tool with fixed screen dimensions (1920x1080)."""
        # Use fixed screen size of 1920x1080
        self.width = 1920
        self.height = 1080
        
        # Get actual screen size for logging purposes
        actual_screen_size = pyautogui.size()
        
        # Fix scale factor to 1.0
        self.scale_factor = 1.0
        
        logger.info(f"Using fixed screen dimensions: {self.width}x{self.height}")
        logger.info(f"Actual screen dimensions: {actual_screen_size.width}x{actual_screen_size.height}")
        logger.info(f"Using fixed scale factor: {self.scale_factor}")
        
        # Create base screenshots directory
        os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
        
        # Create session-specific directory with date only format YYMMDD
        now = datetime.now()
        session_timestamp = now.strftime("%y%m%d")
        self.session_dir = os.path.join(BASE_OUTPUT_DIR, session_timestamp)
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Create a session-specific log file
        self.conversation_log_path = os.path.join(self.session_dir, "conversation.log")
        
        # Add a separator in the log file for new app sessions
        with open(self.conversation_log_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n\n{'#' * 80}\n")
            f.write(f"# {timestamp} - NEW SESSION STARTED\n")
            f.write(f"{'#' * 80}\n\n")
        
        logger.info(f"Screenshots will be saved to: {self.session_dir}")
        logger.info(f"Conversation log will be saved to: {self.conversation_log_path}")
        logger.info(f"Screen resolution: {self.width}x{self.height}, scale factor: {self.scale_factor}")
        
        # Configure screenshot delay - default 0.5s but can be overridden by env var or command line
        default_delay = 0.5
        env_delay = os.getenv("SCREENSHOT_DELAY", default_delay)
        try:
            self._screenshot_delay = float(env_delay)
        except (ValueError, TypeError):
            self._screenshot_delay = default_delay
            
        logger.info(f"Screenshot delay set to: {self._screenshot_delay} seconds")

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
        elif action == "double_click":
            x = kwargs.get("x")
            y = kwargs.get("y")
            if x is None or y is None:
                raise ToolError("Both x and y coordinates are required for double click action")
            return await self.handle_double_click(x, y)
        elif action == "scroll":
            x = kwargs.get("x")
            y = kwargs.get("y")
            direction = kwargs.get("direction", "down")
            amount = kwargs.get("amount", 3)
            if direction not in ["up", "down", "left", "right"]:
                raise ToolError("Direction must be one of: up, down, left, right")
            return await self.handle_scroll(x=x, y=y, direction=direction, amount=amount)
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
        elif action == "set_scale_factor":
            # We're using fixed scale factor, but keep this action for compatibility
            return ToolResult(output="Using fixed scale factor of 1.0. This command has no effect.")
        else:
            raise ToolError(f"Invalid action: {action}")
            
    def _adjust_coordinates(self, x: int, y: int):
        """
        Adjust coordinates to match actual screen resolution.
        
        Args:
            x: The x coordinate from the image
            y: The y coordinate from the image
            
        Returns:
            Tuple of adjusted coordinates
        """
        # Based on the example of bottom-right pixel (1438,812 -> should be 1920,1080)
        # Calculate the scaling factors needed
        x_scale = 1920 / 1438
        y_scale = 1080 / 812
        
        # Apply scaling to coordinates
        adjusted_x = int(x * x_scale)
        adjusted_y = int(y * y_scale)
        
        # Log both original and adjusted coordinates
        logger.info(f"Original coordinates: ({x}, {y})")
        logger.info(f"Adjusted coordinates: ({adjusted_x}, {adjusted_y}) [x_scale={x_scale:.2f}, y_scale={y_scale:.2f}]")
        
        return adjusted_x, adjusted_y
        
    async def handle_click(self, x: int, y: int):
        """Handle mouse click at specific coordinates."""
        # Adjust coordinates based on screen scaling
        adjusted_x, adjusted_y = self._adjust_coordinates(x, y)
        
        # Log the action with both original and adjusted coordinates
        logger.info(f"Clicking at: {x},{y} (adjusted to {adjusted_x},{adjusted_y})")
        
        # Perform the click at the adjusted coordinates
        pyautogui.click(adjusted_x, adjusted_y)
        return await self.take_screenshot()
        
    async def handle_double_click(self, x: int, y: int):
        """Handle mouse double click at specific coordinates."""
        # Adjust coordinates based on screen scaling
        adjusted_x, adjusted_y = self._adjust_coordinates(x, y)
        
        # Log the action with both original and adjusted coordinates
        logger.info(f"Double clicking at: {x},{y} (adjusted to {adjusted_x},{adjusted_y})")
        
        # Perform the double click at the adjusted coordinates
        pyautogui.doubleClick(adjusted_x, adjusted_y)
        return await self.take_screenshot()
        
    async def handle_move(self, x: int, y: int):
        """Handle mouse movement to specific coordinates."""
        # Adjust coordinates based on screen scaling
        adjusted_x, adjusted_y = self._adjust_coordinates(x, y)
        
        # Log the action
        logger.info(f"Moving to: {x},{y} (adjusted to {adjusted_x},{adjusted_y})")
        
        # Move to the adjusted coordinates
        pyautogui.moveTo(adjusted_x, adjusted_y)
        return await self.take_screenshot()
        
    async def handle_hotkey(self, text: str):
        """Handle keyboard hotkey press."""
        # Split the hotkey string by '+' and press the keys together
        keys = text.split('+')
        pyautogui.hotkey(*keys)
        return await self.take_screenshot()
        
    async def handle_scroll(self, x: int = None, y: int = None, direction: str = "down", amount: int = 3):
        """Handle scrolling at specific coordinates with specified direction and amount."""
        # If coordinates are provided, move to that position first
        if x is not None and y is not None:
            # Adjust coordinates based on screen scaling
            adjusted_x, adjusted_y = self._adjust_coordinates(x, y)
            logger.info(f"Moving to position before scrolling: {x},{y} (adjusted to {adjusted_x},{adjusted_y})")
            pyautogui.moveTo(adjusted_x, adjusted_y)
        
        # Multiply amount by a factor to make scrolling more noticeable
        scroll_factor = 100  # This can be adjusted based on testing
        scroll_amount = amount * scroll_factor
        
        # Log the action
        logger.info(f"Scrolling {direction} with amount {amount} (adjusted to {scroll_amount})")
        
        # Perform the scrolling
        if direction == "up":
            pyautogui.scroll(scroll_amount)  # Positive values scroll up
        elif direction == "down":
            pyautogui.scroll(-scroll_amount)  # Negative values scroll down
        elif direction == "left":
            pyautogui.hscroll(-scroll_amount)  # Negative values scroll left
        elif direction == "right":
            pyautogui.hscroll(scroll_amount)  # Positive values scroll right
            
        return await self.take_screenshot()
    
    async def take_screenshot(self):
        """Take a screenshot and return as base64 encoded PNG."""
        # Wait the configured delay time before taking the screenshot
        logger.info(f"Waiting {self._screenshot_delay} seconds before taking screenshot...")
        await asyncio.sleep(self._screenshot_delay)
        
        screenshot = pyautogui.screenshot()
        
        # Create screenshot filename with timestamp only (no prefix)
        now = datetime.now()
        filename = f"{now.strftime('%y%m%d_%H%M%S')}.png"
        output_path = os.path.join(self.session_dir, filename)
        screenshot.save(output_path)
        
        # Log the screenshot path
        logger.info(f"Screenshot saved: {output_path}")
        
        # Convert to base64
        buffered = io.BytesIO()
        screenshot.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return ToolResult(output=f"Screenshot taken: {filename}", base64_image=img_str)
    
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
        # Adjust coordinates based on screen scaling
        adjusted_x, adjusted_y = self._adjust_coordinates(x, y)
        
        if action == "mouse_move":
            # Move mouse to position
            logger.info(f"Moving mouse to: {x},{y} (adjusted to {adjusted_x},{adjusted_y})")
            pyautogui.moveTo(adjusted_x, adjusted_y)
            return await self.take_screenshot()
        elif action == "left_click_drag":
            # Click and drag from current position to target
            current_x, current_y = pyautogui.position()
            logger.info(f"Dragging from {current_x},{current_y} to {x},{y} (adjusted to {adjusted_x},{adjusted_y})")
            pyautogui.dragTo(adjusted_x, adjusted_y, button='left')
            return await self.take_screenshot()
    
    async def handle_mouse_click(self, action, **kwargs):
        """Handle mouse click actions."""
        coordinate = kwargs.get("coordinate")
        key = kwargs.get("key")
        
        # Move mouse if coordinates provided
        if coordinate and len(coordinate) == 2:
            x, y = coordinate
            # Adjust coordinates based on screen scaling
            adjusted_x, adjusted_y = self._adjust_coordinates(x, y)
            logger.info(f"Moving to before click: {x},{y} (adjusted to {adjusted_x},{adjusted_y})")
            pyautogui.moveTo(adjusted_x, adjusted_y)
        
        # Handle key modifiers
        modifiers_active = False
        if key:
            logger.info(f"Pressing modifier key: {key}")
            pyautogui.keyDown(key)
            modifiers_active = True
        
        # Perform click action
        if action == "left_click":
            logger.info("Performing left click")
            pyautogui.click(button='left')
        elif action == "right_click":
            logger.info("Performing right click")
            pyautogui.click(button='right')
        elif action == "middle_click":
            logger.info("Performing middle click")
            pyautogui.click(button='middle')
        elif action == "double_click":
            logger.info("Performing double click")
            pyautogui.click(button='left', clicks=2, interval=0.1)
        elif action == "triple_click":
            logger.info("Performing triple click")
            pyautogui.click(button='left', clicks=3, interval=0.1)
        
        # Release modifiers
        if modifiers_active:
            logger.info(f"Releasing modifier key: {key}")
            pyautogui.keyUp(key)
        
        # Return screenshot after action
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