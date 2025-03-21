"""
Setup script for the Claude Computer Windows package.
"""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

# Add optional API mode dependencies
api_mode_requirements = [
    "fastapi>=0.100.0",
    "uvicorn>=0.22.0",
    "pydantic>=2.0.0"
]

setup(
    name="claude-computer-windows",
    version="0.1.0",
    description="Windows-native implementation of Claude Computer Use",
    author="Based on Anthropic's Computer Use Demo",
    packages=find_packages(),
    install_requires=requirements,
    extras_require={
        "api": api_mode_requirements,
        "all": api_mode_requirements,
    },
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "claude-computer=claude_computer_windows.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
    ],
)