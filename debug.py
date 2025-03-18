"""
Debug script to test Claude API tools integration.
"""
import os
import sys
import asyncio
from anthropic import Anthropic

# Simple test script that just creates a client and makes a request
async def test_claude_tools():
    # Get API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        api_key = input("Please enter your Anthropic API key: ")
    
    print("Creating Anthropic client...")
    client = Anthropic(api_key=api_key)
    
    # Define a minimal tools setup
    tools = [
        {
            "type": "bash_20250124",
            "name": "bash"
        }
    ]
    
    print("Making API request with tools...")
    try:
        response = await client.beta.messages.acreate(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": "Hello! Can you run a simple command like 'dir' to list files?"
                }
            ],
            tools=tools
        )
        print("Success! Response received.")
        print(f"Content: {response.content[0].text}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")

if __name__ == "__main__":
    asyncio.run(test_claude_tools())