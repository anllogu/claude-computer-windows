"""
Windows CMD/PowerShell execution tool for Claude.
Provides a way to execute shell commands on Windows.
"""

import asyncio
import os
import subprocess
from typing import Literal

from .computer import ToolError, ToolResult


class CmdTool:
    """Tool for executing commands in Windows command prompt or PowerShell."""
    
    def __init__(self, use_powershell=True):
        """Initialize the CMD tool.
        
        Args:
            use_powershell: If True, uses PowerShell; otherwise uses CMD.
        """
        self.use_powershell = use_powershell
        self.shell = "powershell.exe" if use_powershell else "cmd.exe"
        self.timeout = 30.0  # Default timeout in seconds
    
    async def __call__(self, *, command: str, timeout: float = None):
        """Execute a command using the Windows shell.
        
        Args:
            command: The command to execute.
            timeout: Optional timeout in seconds.
        
        Returns:
            ToolResult with command output or error.
        """
        if not command:
            raise ToolError("Command cannot be empty")
        
        # Check for dangerous commands
        disallowed = ["format", "deltree", "fdisk", "diskpart", "reg delete"]
        if any(cmd in command.lower() for cmd in disallowed):
            raise ToolError(f"Disallowed command detected: {command}")
            
        # Run with appropriate shell
        timeout = timeout or self.timeout
        try:
            # Use different parameters depending on shell type
            if self.use_powershell:
                process = await asyncio.create_subprocess_exec(
                    self.shell,
                    "-Command",
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    self.shell,
                    "/c",
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
                
                # Decode output
                stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
                stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
                
                if process.returncode != 0:
                    # Command executed but reported an error
                    return ToolResult(
                        output=stdout_str,
                        error=f"Command failed with exit code {process.returncode}: {stderr_str}"
                    )
                
                return ToolResult(output=stdout_str, error=stderr_str if stderr_str else None)
                
            except asyncio.TimeoutError:
                # Try to kill the process if it times out
                try:
                    process.kill()
                except:
                    pass
                return ToolResult(error=f"Command timed out after {timeout} seconds")
                
        except Exception as e:
            return ToolResult(error=f"Failed to execute command: {str(e)}")


class PowerShellTool(CmdTool):
    """Tool specifically for executing PowerShell commands."""
    
    def __init__(self):
        """Initialize with PowerShell as the shell."""
        super().__init__(use_powershell=True)