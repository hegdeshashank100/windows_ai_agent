"""
Windows AI Agent - Advanced Desktop Assistant with Gemini Integration

A sophisticated AI agent that provides intelligent Windows desktop automation,
natural language interaction, and safe code execution capabilities.

Author: AI Assistant
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"
__description__ = "Advanced Windows AI Agent with Gemini Integration"

from .core.agent import WindowsAIAgent
from .core.gemini_client import GeminiClient
from .ui.chat_window import ChatWindow
from .utils.config import Config

__all__ = [
    'WindowsAIAgent',
    'GeminiClient', 
    'ChatWindow',
    'Config'
]