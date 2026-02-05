"""
Main Windows AI Agent class - orchestrates all components
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import time
import json
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

# Module-level logger (replacement for loguru)
logger = logging.getLogger("windows_ai_agent")
logger.propagate = False

from .gemini_client import GeminiClient, Message
from ..utils.config import config


@dataclass
class AgentCapability:
    """Represents an agent capability/skill"""
    name: str
    description: str
    handler: Callable
    requires_confirmation: bool = False
    category: str = "general"


@dataclass 
class ActionResult:
    """Result of an agent action"""
    success: bool
    message: str
    data: Optional[Dict] = None
    requires_followup: bool = False


class WindowsAIAgent:
    """Main AI agent that coordinates all functionality"""
    
    def __init__(self, config_override: Optional[Dict] = None):
        self.config = config
        if config_override:
            # Apply config overrides
            for key, value in config_override.items():
                setattr(self.config, key, value)
        
        # Initialize components
        self.gemini_client = None
        self.capabilities: Dict[str, AgentCapability] = {}
        self.action_history: List[Dict] = []
        self.context_data: Dict = {}
        self.is_running = False
        
        # Initialize logger
        self._setup_logging()
        
        # Initialize Gemini client
        self._initialize_gemini()
        
    def _setup_logging(self):
        """Setup logging configuration"""
        log_file = Path(self.config.config_path) / "logs" / "agent.log"
        log_file.parent.mkdir(exist_ok=True)
        
        # Configure file handler with rotation (10 MB) and keep up to 7 backups
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=10 * 1024 * 1024,
            backupCount=7,
            encoding="utf-8"
        )
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d | %(message)s", "%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        file_level = getattr(logging, str(self.config.log_level).upper(), logging.INFO)
        file_handler.setLevel(file_level)
        
        # Clear existing handlers to avoid duplicate logs
        if logger.handlers:
            for h in list(logger.handlers):
                logger.removeHandler(h)
        
        logger.addHandler(file_handler)
        logger.setLevel(file_level)
        
        if self.config.debug_mode:
            # Add console handler for debug output
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.DEBUG)
            logger.addHandler(console_handler)
    
    def _initialize_gemini(self):
        """Initialize Gemini client"""
        try:
            if not self.config.google_api_key:
                logger.error("Google API key not found in configuration")
                return
            
            self.gemini_client = GeminiClient(
                api_key=self.config.google_api_key,
                model_name=self.config.gemini_model
            )
            
            if self.gemini_client.is_configured:
                logger.info("Gemini client initialized successfully")
            else:
                logger.error("Failed to initialize Gemini client")
                
        except Exception as e:
            logger.error(f"Error initializing Gemini: {e}")
    
    def _register_default_capabilities(self):
        """Register default agent capabilities"""
        
        # Basic conversation
        self.register_capability(
            "chat",
            "General conversation and questions",
            self._handle_chat,
            category="communication"
        )
        
        # System information
        self.register_capability(
            "system_info",
            "Get system information and status",
            self._handle_system_info,
            category="system"
        )
        
        # Help and capabilities
        self.register_capability(
            "help",
            "Show available commands and capabilities",
            self._handle_help,
            category="utility"
        )
        
        # Clear conversation
        self.register_capability(
            "clear",
            "Clear conversation history",
            self._handle_clear,
            category="utility"
        )
        
        logger.info(f"Registered {len(self.capabilities)} default capabilities")
    
    def register_capability(
        self, 
        name: str, 
        description: str, 
        handler: Callable, 
        requires_confirmation: bool = False,
        category: str = "general"
    ):
        """Register a new capability"""
        capability = AgentCapability(
            name=name,
            description=description,
            handler=handler,
            requires_confirmation=requires_confirmation,
            category=category
        )
        
        self.capabilities[name] = capability
        logger.debug(f"Registered capability: {name}")
    
    async def process_message(self, message: str, user_context: Optional[Dict] = None) -> str:
        """Process a user message and return response"""
        try:
            if not self.gemini_client or not self.gemini_client.is_configured:
                return "I'm sorry, but I'm not properly configured. Please check the API key and restart."
            
            # Log the interaction
            self._log_interaction("user", message)
            
            # Prepare context
            full_context = self._build_context(user_context)
            
            # Check for specific capability requests
            capability_result = await self._check_capabilities(message)
            if capability_result:
                response = capability_result.message
            else:
                # Send to Gemini for general conversation
                response = await self.gemini_client.send_message(message, full_context)
            
            # Log the response
            self._log_interaction("agent", response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    async def stream_response(self, message: str, user_context: Optional[Dict] = None):
        """Stream response for real-time conversation"""
        try:
            if not self.gemini_client or not self.gemini_client.is_configured:
                yield "I'm sorry, but I'm not properly configured."
                return
            
            self._log_interaction("user", message)
            
            full_context = self._build_context(user_context)
            
            # Check for capabilities first
            capability_result = await self._check_capabilities(message)
            if capability_result:
                yield capability_result.message
                return
            
            # Stream from Gemini
            response_parts = []
            async for chunk in self.gemini_client.stream_message(message, full_context):
                response_parts.append(chunk)
                yield chunk
            
            # Log complete response
            complete_response = "".join(response_parts)
            self._log_interaction("agent", complete_response)
            
        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield f"Error: {str(e)}"
    
    async def _check_capabilities(self, message: str) -> Optional[ActionResult]:
        """Check if message matches specific capabilities"""
        message_lower = message.lower().strip()
        
        # Simple keyword matching for now - could be enhanced with NLP
        capability_keywords = {
            "help": ["help", "what can you do", "commands", "capabilities"],
            "clear": ["clear", "reset", "new conversation", "start over"],
            "system_info": ["system info", "computer info", "system status", "pc info"]
        }
        
        for capability_name, keywords in capability_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                if capability_name in self.capabilities:
                    capability = self.capabilities[capability_name]
                    try:
                        result = await capability.handler(message)
                        return result
                    except Exception as e:
                        logger.error(f"Error executing capability {capability_name}: {e}")
                        return ActionResult(
                            success=False,
                            message=f"Error executing {capability_name}: {str(e)}"
                        )
        
        return None
    
    def _build_context(self, user_context: Optional[Dict] = None) -> Dict:
        """Build context for the AI model"""
        context = {
            "agent_info": {
                "capabilities": list(self.capabilities.keys()),
                "system_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "conversation_length": len(self.gemini_client.conversation_history) if self.gemini_client else 0
            }
        }
        
        # Add stored context
        context.update(self.context_data)
        
        # Add user-provided context
        if user_context:
            context.update(user_context)
        
        return context
    
    def _log_interaction(self, role: str, content: str):
        """Log user/agent interactions"""
        interaction = {
            "timestamp": time.time(),
            "role": role,
            "content": content[:200] + "..." if len(content) > 200 else content
        }
        
        self.action_history.append(interaction)
        
        # Keep only recent history
        if len(self.action_history) > self.config.max_conversation_history:
            self.action_history = self.action_history[-self.config.max_conversation_history:]
    
    # Default capability handlers
    
    async def _handle_chat(self, message: str) -> ActionResult:
        """Handle general chat - this shouldn't normally be called directly"""
        return ActionResult(
            success=True,
            message="This is handled by the main conversation flow."
        )
    
    async def _handle_help(self, message: str) -> ActionResult:
        """Show available capabilities"""
        help_text = "🤖 **Windows AI Agent - Available Capabilities**\n\n"
        
        # Group capabilities by category
        by_category = {}
        for cap_name, capability in self.capabilities.items():
            category = capability.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(capability)
        
        for category, capabilities in by_category.items():
            help_text += f"**{category.title()}:**\n"
            for cap in capabilities:
                help_text += f"• {cap.name}: {cap.description}\n"
            help_text += "\n"
        
        help_text += "💡 **Tips:**\n"
        help_text += "• Just type naturally - I understand conversational requests\n"
        help_text += "• Ask me to 'take a screenshot', 'open calculator', etc.\n"
        help_text += "• I can run Python code safely in a sandbox environment\n"
        help_text += "• Type 'clear' to reset our conversation\n"
        
        return ActionResult(success=True, message=help_text)
    
    async def _handle_clear(self, message: str) -> ActionResult:
        """Clear conversation history"""
        if self.gemini_client:
            self.gemini_client.clear_history()
        
        self.action_history = []
        self.context_data = {}
        
        return ActionResult(
            success=True,
            message="✅ Conversation cleared! Starting fresh. How can I help you?"
        )
    
    async def _handle_system_info(self, message: str) -> ActionResult:
        """Get basic system information"""
        import platform

        # Try to import psutil; if not available, fall back to platform/OS-specific methods
        try:
            import psutil  # type: ignore
        except Exception:
            psutil = None

        try:
            # Determine total memory in GB using psutil if available, otherwise use fallbacks
            if psutil:
                mem_gb = f"{psutil.virtual_memory().total // (1024**3)} GB"
            else:
                mem_gb = "unknown (psutil not available)"
                try:
                    if platform.system() == "Windows":
                        # Use GlobalMemoryStatusEx on Windows
                        import ctypes

                        class MEMORYSTATUSEX(ctypes.Structure):
                            _fields_ = [
                                ("dwLength", ctypes.c_uint32),
                                ("dwMemoryLoad", ctypes.c_uint32),
                                ("ullTotalPhys", ctypes.c_uint64),
                                ("ullAvailPhys", ctypes.c_uint64),
                                ("ullTotalPageFile", ctypes.c_uint64),
                                ("ullAvailPageFile", ctypes.c_uint64),
                                ("ullTotalVirtual", ctypes.c_uint64),
                                ("ullAvailVirtual", ctypes.c_uint64),
                                ("ullAvailExtendedVirtual", ctypes.c_uint64),
                            ]

                        mem = MEMORYSTATUSEX()
                        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
                        mem_gb = f"{mem.ullTotalPhys // (1024**3)} GB"
                    else:
                        # Try reading /proc/meminfo on Unix-like systems
                        with open("/proc/meminfo", "r") as f:
                            for line in f:
                                if line.startswith("MemTotal:"):
                                    parts = line.split()
                                    kb = int(parts[1])
                                    mem_gb = f"{kb // (1024**2)} GB"
                                    break
                except Exception:
                    # If fallback methods fail, leave memory as unknown
                    mem_gb = "unknown (psutil not available)"

            info = {
                "OS": f"{platform.system()} {platform.release()}",
                "Architecture": platform.architecture()[0],
                "Processor": platform.processor(),
                "Memory": mem_gb,
                "Python": platform.python_version()
            }
            
            info_text = "💻 **System Information:**\n\n"
            for key, value in info.items():
                info_text += f"**{key}:** {value}\n"
            
            return ActionResult(success=True, message=info_text)
            
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Error getting system info: {str(e)}"
            )
    
    # Utility methods
    
    def set_context(self, key: str, value: Any):
        """Set context data"""
        self.context_data[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context data"""
        return self.context_data.get(key, default)
    
    def get_capabilities(self) -> List[str]:
        """Get list of capability names"""
        return list(self.capabilities.keys())
    
    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history"""
        if self.gemini_client:
            return self.gemini_client.get_history()
        return []
    
    def save_conversation(self, filepath: str):
        """Save conversation to file"""
        if self.gemini_client:
            self.gemini_client.save_history(filepath)
    
    def load_conversation(self, filepath: str):
        """Load conversation from file"""
        if self.gemini_client:
            self.gemini_client.load_history(filepath)
    
    @property
    def is_configured(self) -> bool:
        """Check if agent is properly configured"""
        return (
            self.gemini_client is not None and 
            self.gemini_client.is_configured
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status information"""
        return {
            "is_configured": self.is_configured,
            "capabilities_count": len(self.capabilities),
            "conversation_length": len(self.get_conversation_history()),
            "gemini_model": self.config.gemini_model,
            "debug_mode": self.config.debug_mode
        }