"""
Google Gemini API client for Windows AI Agent
"""

import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
from pathlib import Path
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from loguru import logger
import json
import time
from dataclasses import dataclass, asdict
from functools import wraps


@dataclass
class Message:
    """Represents a conversation message"""
    role: str  # 'user' or 'model'
    content: str
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GeminiClient:
    """Google Gemini API client with conversation management"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
        self.api_key = api_key
        self.model_name = model_name
        self.conversation_history: List[Message] = []
        self.model = None
        self.chat_session = None
        
        # Configure the API
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self._initialize_model()
        else:
            logger.error("No Google API key provided")
    
    def _initialize_model(self):
        """Initialize the Gemini model"""
        try:
            # Safety settings - more permissive for desktop automation
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Generation config - Use config values with fallbacks
            try:
                from ..utils.config import config
            except ImportError:
                from utils.config import config
            
            # Gemini 2.0 Flash supports larger context - optimize settings
            max_tokens = getattr(config, 'gemini_max_tokens', 8192)
            if self.model_name.startswith('gemini-2.0'):
                # Gemini 2.0 models support up to 32k tokens
                max_tokens = min(max_tokens, 32768)
            
            generation_config = {
                "temperature": getattr(config, 'gemini_temperature', 0.7),
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": max_tokens,
            }
            
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config,
                safety_settings=safety_settings,
                system_instruction=self._get_system_instruction()
            )
            
            self.chat_session = self.model.start_chat(history=[])
            logger.info(f"Initialized Gemini model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None
    
    def _get_system_instruction(self) -> str:
        """Get the system instruction for the AI agent"""
        return """You are an advanced Windows desktop AI assistant with the following capabilities:

CORE FUNCTIONS:
- Natural language conversation and help
- Windows desktop automation and control
- File system operations and management
- System information and monitoring  
- Safe Python code execution in sandbox
- Screenshot capture and image analysis
- Application control and window management

PERSONALITY:
- Professional but friendly and approachable
- Helpful and proactive in solving problems
- Clear and concise in explanations
- Always prioritize user safety and privacy

CAPABILITIES YOU CAN USE:
1. DESKTOP AUTOMATION: Control windows, click buttons, type text, navigate applications
2. FILE OPERATIONS: Create, read, modify, organize files and folders
3. SYSTEM COMMANDS: Execute safe system commands and retrieve information
4. CODE EXECUTION: Run Python code safely in a restricted environment
5. SCREENSHOTS: Capture and analyze screen content
6. APPLICATION CONTROL: Open, close, manage running applications

RESPONSE FORMAT:
- For simple questions: Provide direct, helpful answers
- For actions: Explain what you'll do, then provide the action details
- For code: Offer to run it safely and explain what it does
- For complex tasks: Break them down into clear steps

SAFETY GUIDELINES:
- Never perform destructive actions without explicit confirmation
- Always explain potentially risky operations before executing
- Use sandbox environment for all code execution
- Respect user privacy and data security
- Ask for clarification when requests are ambiguous

EXAMPLE INTERACTIONS:
User: "Take a screenshot"
Response: "I'll capture a screenshot of your current screen and save it. Let me do that for you."

User: "Calculate 15% tip on $47.50"  
Response: "I'll calculate that for you: 15% tip on $47.50 is $7.13, making the total $54.63."

User: "Open calculator and compute 25 * 47"
Response: "I'll open the Windows Calculator app and perform that calculation for you."

Remember: You are a powerful desktop assistant, so be confident in your abilities while remaining safe and helpful."""

    async def send_message(self, message: str, context: Optional[Dict] = None) -> str:
        """Send a message to Gemini and get response"""
        if not self.model or not self.chat_session:
            return "Sorry, I'm not properly configured. Please check the API key and try again."
        
        # Input validation
        if not message or not message.strip():
            return "I didn't receive a message to process. Please try again."
        
        if len(message) > 50000:  # Reasonable limit
            return "That message is too long. Please try breaking it into smaller parts."
        
        try:
            # Add user message to history
            user_msg = Message(role="user", content=message)
            self.conversation_history.append(user_msg)
            
            # Enhance message with intelligent context awareness
            full_message = self._build_intelligent_prompt(message, context)
            
            # Send to Gemini
            response = await asyncio.to_thread(
                self.chat_session.send_message, 
                full_message
            )
            
            # Extract response text
            response_text = response.text
            
            # Add model response to history
            model_msg = Message(role="model", content=response_text)
            self.conversation_history.append(model_msg)
            
            # Trim history if it gets too long
            self._trim_history()
            
            logger.info(f"Sent message to Gemini, got response: {len(response_text)} chars")
            return response_text
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle specific API errors
            if "quota" in error_msg or "limit" in error_msg:
                logger.error(f"API quota/limit exceeded: {e}")
                return "I'm currently experiencing high demand. Please try again in a moment, or check your API quota."
            elif "rate" in error_msg or "429" in error_msg:
                logger.error(f"Rate limited: {e}")
                return "I'm sending requests too quickly. Let me slow down and try again in a moment."
            elif "invalid" in error_msg and "api" in error_msg:
                logger.error(f"Invalid API key: {e}")
                return "There seems to be an issue with my configuration. Please check the API key settings."
            elif "network" in error_msg or "connection" in error_msg:
                logger.error(f"Network error: {e}")
                return "I'm having trouble connecting to the AI service. Please check your internet connection."
            else:
                logger.error(f"Failed to send message to Gemini: {e}")
                return f"I encountered an error while processing your request: {str(e)}"
    
    async def stream_message(self, message: str, context: Optional[Dict] = None) -> AsyncGenerator[str, None]:
        """Send message and stream the response"""
        if not self.model or not self.chat_session:
            yield "Sorry, I'm not properly configured. Please check the API key."
            return
        
        try:
            # Add user message to history
            user_msg = Message(role="user", content=message)
            self.conversation_history.append(user_msg)
            
            # Prepare message with context
            full_message = message
            if context:
                context_str = self._format_context(context)
                full_message = f"{context_str}\n\nUser request: {message}"
            
            # Stream response - Fix: Handle streaming properly
            response_parts = []
            
            def stream_generator():
                return self.chat_session.send_message(full_message, stream=True)
            
            # Get the streaming response in a thread
            stream_response = await asyncio.to_thread(stream_generator)
            
            # Process each chunk
            for chunk in stream_response:
                if hasattr(chunk, 'text') and chunk.text:
                    response_parts.append(chunk.text)
                    yield chunk.text
            
            # Add complete response to history
            complete_response = "".join(response_parts)
            if complete_response:  # Only add if we got a response
                model_msg = Message(role="model", content=complete_response)
                self.conversation_history.append(model_msg)
            
            self._trim_history()
            
        except Exception as e:
            logger.error(f"Failed to stream message: {e}")
            yield f"Error: {str(e)}"
    
    def _build_intelligent_prompt(self, message: str, context: dict) -> str:
        """Build an intelligent, context-aware prompt for Gemini"""
        
        # Start with system context
        prompt_parts = [
            "I am an advanced AI assistant integrated into a Windows desktop automation system.",
            "I can create files, open applications, take screenshots, manage the desktop, and have intelligent conversations.",
            "I should be helpful, proactive, and understand context from previous interactions.",
            ""
        ]
        
        # Add conversation context if available
        if hasattr(self, 'conversation_history') and self.conversation_history:
            recent_messages = self.conversation_history[-4:]  # Last 2 exchanges
            if recent_messages:
                prompt_parts.append("Recent conversation context:")
                for msg in recent_messages:
                    role_emoji = "👤" if msg.role == "user" else "🤖"
                    prompt_parts.append(f"{role_emoji} {msg.role}: {msg.content[:200]}")
                prompt_parts.append("")
        
        # Add memory context if provided
        if context:
            context_str = self._format_intelligent_context(context)
            if context_str:
                prompt_parts.append(context_str)
                prompt_parts.append("")
        
        # Add the current user message
        prompt_parts.append(f"User's current request: {message}")
        prompt_parts.append("")
        prompt_parts.append("Instructions:")
        prompt_parts.append("- Respond naturally and conversationally")
        prompt_parts.append("- Be proactive about offering to help with actions I can perform")
        prompt_parts.append("- Use context to understand references like 'that file', 'open it', etc.")
        prompt_parts.append("- If user wants an action, offer to do it immediately")
        prompt_parts.append("- Be intelligent and helpful, not robotic")
        
        return "\n".join(prompt_parts)
    
    def _format_intelligent_context(self, context: dict) -> str:
        """Format context in an intelligent, readable way for Gemini"""
        context_parts = []
        
        # Recent files context
        if context.get('recent_files'):
            context_parts.append("📁 Files I recently created:")
            for file_info in context['recent_files'][:3]:
                context_parts.append(f"  • {file_info['filename']} ({file_info['type']}) - {file_info['created_ago']}")
                if file_info.get('intent'):
                    context_parts.append(f"    Purpose: {file_info['intent']}")
        
        # Recent actions context
        if context.get('recent_actions'):
            context_parts.append("⚡ Recent actions I performed:")
            for action in context['recent_actions'][-3:]:
                action_type = action.get('action', 'unknown')
                time_ago = action.get('time_ago', 'recently')
                context_parts.append(f"  • {action_type} - {time_ago}")
        
        # User patterns context
        if context.get('user_patterns'):
            patterns = context['user_patterns']
            if patterns.get('preferred_locations') or patterns.get('file_types'):
                context_parts.append("📊 User preferences I've learned:")
                
                if patterns.get('file_types'):
                    top_types = sorted(patterns['file_types'].items(), key=lambda x: x[1], reverse=True)[:2]
                    context_parts.append(f"  • Often creates: {', '.join([t[0] for t in top_types])}")
                
                if patterns.get('preferred_locations'):
                    top_locations = sorted(patterns['preferred_locations'].items(), key=lambda x: x[1], reverse=True)[:2]
                    location_names = [Path(loc).name or "desktop" for loc, _ in top_locations]
                    context_parts.append(f"  • Preferred locations: {', '.join(location_names)}")
        
        # Smart suggestions
        if context.get('smart_suggestions'):
            context_parts.append("💡 Relevant context:")
            for suggestion in context['smart_suggestions'][:2]:
                context_parts.append(f"  • {suggestion}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _format_context(self, context: Dict) -> str:
        """Format context information for the model"""
        # Use intelligent context formatting if it's the new context format
        if context and isinstance(context, dict) and any(key in context for key in ['recent_files', 'recent_actions', 'user_patterns']):
            return self._format_intelligent_context(context)
        
        # Fallback to old format for backward compatibility
        context_parts = ["CONTEXT INFORMATION:"]
        
        if "system_info" in context:
            context_parts.append(f"System: {context['system_info']}")
        
        if "current_window" in context:
            context_parts.append(f"Active window: {context['current_window']}")
        
        if "recent_actions" in context:
            context_parts.append(f"Recent actions: {context['recent_actions']}")
        
        if "screen_info" in context:
            context_parts.append(f"Screen info: {context['screen_info']}")
        
        return "\n".join(context_parts)
    
    def _trim_history(self, max_messages: int = 100):
        """Trim conversation history to prevent memory issues"""
        if len(self.conversation_history) > max_messages:
            # Keep the first few messages (system context) and recent messages
            keep_start = 2
            keep_recent = max_messages - keep_start
            
            if len(self.conversation_history) > keep_start:
                self.conversation_history = (
                    self.conversation_history[:keep_start] + 
                    self.conversation_history[-keep_recent:]
                )
            
            logger.info(f"Trimmed conversation history to {len(self.conversation_history)} messages")
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        if self.chat_session:
            self.chat_session = self.model.start_chat(history=[])
        logger.info("Cleared conversation history")
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history as list of dictionaries"""
        return [msg.to_dict() for msg in self.conversation_history]
    
    def save_history(self, filepath: str):
        """Save conversation history to file"""
        try:
            history_data = {
                "model": self.model_name,
                "timestamp": time.time(),
                "messages": self.get_history()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved conversation history to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def load_history(self, filepath: str):
        """Load conversation history from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            self.conversation_history = [
                Message(**msg) for msg in history_data.get("messages", [])
            ]
            
            logger.info(f"Loaded conversation history from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
    
    @property
    def is_configured(self) -> bool:
        """Check if the client is properly configured"""
        return self.model is not None and self.chat_session is not None
    
    async def _retry_api_call(self, func, *args, max_retries: int = 3, **kwargs):
        """Retry API calls with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                
                # Don't retry on certain errors
                if "invalid" in error_msg and "api" in error_msg:
                    raise e  # API key issues
                if "quota" in error_msg:
                    raise e  # Quota exceeded
                
                # Retry on network/transient errors
                if attempt < max_retries - 1 and ("network" in error_msg or "timeout" in error_msg or "503" in error_msg):
                    wait_time = (2 ** attempt) + 1  # Exponential backoff
                    logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise e
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_name": self.model_name,
            "is_configured": self.is_configured,
            "history_length": len(self.conversation_history),
            "api_key_set": bool(self.api_key)
        }