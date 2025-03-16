"""
File manipulation tools for Windows.
Provides tools for reading, writing, and editing files.
"""

import os
from pathlib import Path

from .computer import ToolError, ToolResult


class FileTool:
    """Base class for file manipulation tools."""
    
    def validate_path(self, file_path):
        """Validate that a file path is safe to read/write."""
        # Convert to absolute path if not already
        file_path = os.path.abspath(file_path)
        
        # Check for dangerous paths
        system_paths = [
            os.environ.get("WINDIR", "C:\\Windows"),
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files")),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")),
            os.path.join(os.environ.get("SYSTEMROOT", "C:\\Windows"), "System32")
        ]
        
        for sys_path in system_paths:
            if file_path.lower().startswith(sys_path.lower()):
                raise ToolError(f"Access to system directory {sys_path} is not allowed")
        
        return file_path


class ReadFileTool(FileTool):
    """Tool for reading files on Windows."""
    
    async def __call__(self, *, path: str, offset: int = 0, limit: int = 2000):
        """Read a file from the filesystem.
        
        Args:
            file_path: The path to the file to read.
            offset: Line number to start reading from (0-based).
            limit: Maximum number of lines to read.
            
        Returns:
            ToolResult with the file contents or error.
        """
        try:
            file_path = self.validate_path(path)
            
            if not os.path.exists(file_path):
                return ToolResult(error=f"File not found: {file_path}")
                
            if not os.path.isfile(file_path):
                return ToolResult(error=f"Not a file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                # Skip to the requested offset
                for _ in range(offset):
                    if not f.readline():
                        break
                
                # Read the requested lines
                lines = []
                for _ in range(limit):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)
            
            # Format with line numbers starting at 1 + offset
            formatted_lines = []
            for i, line in enumerate(lines):
                line_num = i + 1 + offset
                formatted_lines.append(f"{line_num:5d}\t{line}")
            
            return ToolResult(output="".join(formatted_lines))
            
        except PermissionError:
            return ToolResult(error=f"Permission denied: {file_path}")
        except Exception as e:
            return ToolResult(error=f"Error reading file: {str(e)}")


class WriteFileTool(FileTool):
    """Tool for writing files on Windows."""
    
    async def __call__(self, *, file_path: str, content: str):
        """Write a file to the filesystem.
        
        Args:
            file_path: The path to the file to write.
            content: The content to write to the file.
            
        Returns:
            ToolResult with success message or error.
        """
        try:
            file_path = self.validate_path(file_path)
            
            # Create directory if it doesn't exist
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return ToolResult(output=f"Successfully wrote {len(content)} characters to {file_path}")
            
        except PermissionError:
            return ToolResult(error=f"Permission denied: {file_path}")
        except Exception as e:
            return ToolResult(error=f"Error writing file: {str(e)}")


class EditFileTool(FileTool):
    """Tool for editing existing files on Windows."""
    
    async def __call__(self, *, file_path: str, old_string: str, new_string: str):
        """Edit a file by replacing old_string with new_string.
        
        Args:
            file_path: The path to the file to edit.
            old_string: The text to replace.
            new_string: The text to replace it with.
            
        Returns:
            ToolResult with success message or error.
        """
        try:
            file_path = self.validate_path(file_path)
            
            # For new file creation
            if not old_string and os.path.dirname(file_path):
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_string)
                return ToolResult(output=f"Created new file {file_path}")
            
            if not os.path.exists(file_path):
                return ToolResult(error=f"File not found: {file_path}")
                
            if not os.path.isfile(file_path):
                return ToolResult(error=f"Not a file: {file_path}")
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Check if old_string exists
            if old_string not in content:
                return ToolResult(error=f"Old string not found in {file_path}")
            
            # Count occurrences to ensure uniqueness
            if content.count(old_string) > 1:
                return ToolResult(
                    error=f"Found multiple instances of the target text. Include more context to make it unique."
                )
            
            # Replace string
            new_content = content.replace(old_string, new_string)
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return ToolResult(output=f"Successfully edited {file_path}")
            
        except PermissionError:
            return ToolResult(error=f"Permission denied: {file_path}")
        except Exception as e:
            return ToolResult(error=f"Error editing file: {str(e)}")