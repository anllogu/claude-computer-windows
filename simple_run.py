"""
A very simple version of the Claude Computer Windows app using a simpler tools implementation.
"""
import os
import sys
import asyncio
import base64
from datetime import datetime
import io
import streamlit as st
import pyautogui
from anthropic import Anthropic
from anthropic.types import MessageParam

class ToolResult:
    """Result from a tool execution."""
    def __init__(self, output=None, error=None, base64_image=None):
        self.output = output
        self.error = error
        self.base64_image = base64_image

async def take_screenshot():
    """Take a screenshot and return as base64 encoded PNG."""
    screenshot = pyautogui.screenshot()
    
    # Convert to base64
    buffered = io.BytesIO()
    screenshot.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return ToolResult(output="Screenshot taken", base64_image=img_str)

async def handle_computer_action(action, x=None, y=None, text=None):
    """Handle computer actions."""
    if action == "screenshot":
        return await take_screenshot()
    elif action == "click" and x is not None and y is not None:
        pyautogui.click(x, y)
        return await take_screenshot()
    elif action == "move" and x is not None and y is not None:
        pyautogui.moveTo(x, y)
        return await take_screenshot()
    elif action == "type" and text:
        pyautogui.write(text)
        return await take_screenshot()
    elif action == "hotkey" and text:
        keys = text.split('+')
        pyautogui.hotkey(*keys)
        return await take_screenshot()
    else:
        return ToolResult(error=f"Invalid action or missing parameters")

async def run_powershell(command):
    """Run a PowerShell command."""
    try:
        import subprocess
        process = await asyncio.create_subprocess_exec(
            "powershell.exe", "-Command", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
        stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
        
        if process.returncode != 0:
            return ToolResult(output=stdout_str, error=f"Command failed: {stderr_str}")
        
        return ToolResult(output=stdout_str)
    except Exception as e:
        return ToolResult(error=f"Error executing command: {str(e)}")

async def main():
    st.title("Simple Claude Computer Windows")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    with st.sidebar:
        api_key = st.text_input("Anthropic API Key", type="password")
        st.checkbox("Hide Images", key="hide_images", value=False)
        
        if st.button("Reset"):
            st.session_state.messages = []
            st.rerun()
    
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        elif message["role"] == "assistant":
            st.chat_message("assistant").write(message["content"])
        elif message["role"] == "tool":
            with st.chat_message("tool"):
                tool_result = message["result"]
                if tool_result.output:
                    st.code(tool_result.output)
                if tool_result.error:
                    st.error(tool_result.error)
                if tool_result.base64_image and not st.session_state.hide_images:
                    st.image(base64.b64decode(tool_result.base64_image))
    
    prompt = st.chat_input("Ask Claude to control your computer...")
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        if not api_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
            return
        
        with st.spinner("Claude is thinking..."):
            client = Anthropic(api_key=api_key)
            
            # Convert messages to the format expected by the API
            api_messages = []
            for msg in st.session_state.messages:
                if msg["role"] != "tool":
                    api_messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Define simple functions
            functions = [
                {
                    "name": "take_screenshot",
                    "description": "Take a screenshot of the current screen",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "click_mouse",
                    "description": "Click the mouse at the specified coordinates",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "x": {"type": "integer", "description": "X coordinate"},
                            "y": {"type": "integer", "description": "Y coordinate"}
                        },
                        "required": ["x", "y"]
                    }
                },
                {
                    "name": "type_text",
                    "description": "Type the given text",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to type"}
                        },
                        "required": ["text"]
                    }
                },
                {
                    "name": "run_powershell",
                    "description": "Run a PowerShell command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command to run"}
                        },
                        "required": ["command"]
                    }
                }
            ]
            
            # Make API request
            try:
                response = await client.beta.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    max_tokens=1000,
                    messages=api_messages,
                    tools=functions
                )
                
                # Process response
                assistant_message = {"role": "assistant", "content": ""}
                
                for content in response.content:
                    if content.type == "text":
                        assistant_message["content"] += content.text
                        st.chat_message("assistant").write(content.text)
                    elif content.type == "tool_use":
                        tool_name = content.name
                        tool_input = content.input
                        
                        # Execute the appropriate tool
                        if tool_name == "take_screenshot":
                            result = await take_screenshot()
                        elif tool_name == "click_mouse":
                            result = await handle_computer_action("click", tool_input.get("x"), tool_input.get("y"))
                        elif tool_name == "type_text":
                            result = await handle_computer_action("type", text=tool_input.get("text"))
                        elif tool_name == "run_powershell":
                            result = await run_powershell(tool_input.get("command"))
                        else:
                            result = ToolResult(error=f"Unknown tool: {tool_name}")
                        
                        # Display tool result
                        with st.chat_message("tool"):
                            if result.output:
                                st.code(result.output)
                            if result.error:
                                st.error(result.error)
                            if result.base64_image and not st.session_state.hide_images:
                                st.image(base64.b64decode(result.base64_image))
                        
                        # Add tool result to messages
                        st.session_state.messages.append({"role": "tool", "result": result})
                
                # Add assistant message to messages
                if assistant_message["content"]:
                    st.session_state.messages.append(assistant_message)
                
            except Exception as e:
                st.error(f"Error: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())