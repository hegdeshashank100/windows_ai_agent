"""
Intent Recognition and Action Schema for Windows AI Agent
"""

import re
import json
import time
from typing import Dict, List, Optional, Any, Callable, Pattern
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from pathlib import Path

from loguru import logger
from ..automation.windows_automation import WindowsAutomation


class IntentCategory(Enum):
    """Categories of intents"""
    AUTOMATION = "automation"
    FILE_SYSTEM = "file_system"
    SYSTEM_INFO = "system_info"
    APPLICATION = "application"
    COMMUNICATION = "communication"
    CODE_EXECUTION = "code_execution"
    MEDIA = "media"
    UTILITY = "utility"


@dataclass
class IntentParameter:
    """Represents a parameter for an intent"""
    name: str
    type: str  # 'string', 'int', 'float', 'bool', 'path', 'coordinates'
    required: bool = True
    description: str = ""
    default: Any = None
    validation_pattern: Optional[str] = None


@dataclass
class Intent:
    """Represents a recognized intent with parameters"""
    name: str
    category: IntentCategory
    parameters: Dict[str, IntentParameter]
    patterns: List[str]  # Regex patterns for recognition
    handler: Optional[Callable] = None
    requires_confirmation: bool = False
    description: str = ""
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


@dataclass
class ParsedIntent:
    """Result of intent parsing"""
    intent: Intent
    extracted_params: Dict[str, Any]
    confidence: float
    raw_text: str


class IntentRecognizer:
    """Recognizes user intents from natural language"""
    
    def __init__(self, automation: WindowsAutomation):
        self.automation = automation
        self.intents: Dict[str, Intent] = {}
        self.compiled_patterns: Dict[str, List[Pattern]] = {}
        
        # Load default intents
        self._register_default_intents()
        
        logger.info(f"Intent recognizer initialized with {len(self.intents)} intents")
    
    def register_intent(self, intent: Intent, handler: Callable = None):
        """Register a new intent"""
        if handler:
            intent.handler = handler
        
        self.intents[intent.name] = intent
        
        # Compile regex patterns
        self.compiled_patterns[intent.name] = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in intent.patterns
        ]
        
        logger.debug(f"Registered intent: {intent.name}")
    
    async def parse_intent(self, text: str) -> Optional[ParsedIntent]:
        """Parse text and extract intent with parameters"""
        best_match = None
        best_confidence = 0.0
        
        for intent_name, intent in self.intents.items():
            for pattern in self.compiled_patterns[intent_name]:
                match = pattern.search(text)
                if match:
                    # Extract parameters from match groups
                    extracted_params = self._extract_parameters(intent, match, text)
                    
                    # Calculate confidence based on pattern specificity and parameter extraction
                    confidence = self._calculate_confidence(intent, match, extracted_params)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ParsedIntent(
                            intent=intent,
                            extracted_params=extracted_params,
                            confidence=confidence,
                            raw_text=text
                        )
        
        return best_match
    
    async def execute_intent(self, parsed_intent: ParsedIntent) -> Dict[str, Any]:
        """Execute a parsed intent"""
        if not parsed_intent.intent.handler:
            return {
                "success": False,
                "error": f"No handler registered for intent: {parsed_intent.intent.name}"
            }
        
        try:
            # Validate parameters
            validation_result = self._validate_parameters(parsed_intent)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Parameter validation failed: {validation_result['error']}"
                }
            
            # Add raw message to parameters for context
            params_with_context = parsed_intent.extracted_params.copy()
            params_with_context["_raw_message"] = parsed_intent.raw_text
            
            # Execute the intent
            if asyncio.iscoroutinefunction(parsed_intent.intent.handler):
                result = await parsed_intent.intent.handler(
                    self.automation, 
                    params_with_context
                )
            else:
                result = parsed_intent.intent.handler(
                    self.automation, 
                    params_with_context
                )
            
            logger.info(f"Executed intent: {parsed_intent.intent.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing intent {parsed_intent.intent.name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_parameters(self, intent: Intent, match: re.Match, text: str) -> Dict[str, Any]:
        """Extract parameters from regex match"""
        extracted = {}
        
        # Extract named groups from regex
        for param_name, param in intent.parameters.items():
            try:
                # Try to get from named group
                if param_name in match.groupdict():
                    value = match.group(param_name)
                    extracted[param_name] = self._convert_parameter_type(value, param.type)
                elif not param.required and param.default is not None:
                    extracted[param_name] = param.default
            except (IndexError, ValueError) as e:
                logger.warning(f"Failed to extract parameter {param_name}: {e}")
                if param.default is not None:
                    extracted[param_name] = param.default
        
        return extracted
    
    def _convert_parameter_type(self, value: str, param_type: str) -> Any:
        """Convert parameter value to appropriate type"""
        if value is None:
            return None
        
        try:
            if param_type == "int":
                return int(value)
            elif param_type == "float":
                return float(value)
            elif param_type == "bool":
                return value.lower() in ("true", "yes", "1", "on", "enable")
            elif param_type == "coordinates":
                # Parse coordinates like "100,200" or "x:100 y:200"
                coords = re.findall(r'\d+', value)
                if len(coords) >= 2:
                    return {"x": int(coords[0]), "y": int(coords[1])}
                return None
            elif param_type == "path":
                return Path(value)
            else:  # string
                return value
        except (ValueError, TypeError):
            return value
    
    def _calculate_confidence(self, intent: Intent, match: re.Match, extracted_params: Dict) -> float:
        """Calculate confidence score for intent match"""
        base_confidence = 0.7  # Base confidence for pattern match
        
        # Boost confidence based on parameter extraction
        required_params = [p for p in intent.parameters.values() if p.required]
        if required_params:
            extracted_required = sum(
                1 for param in required_params 
                if param.name in extracted_params and extracted_params[param.name] is not None
            )
            param_confidence = extracted_required / len(required_params)
            base_confidence += param_confidence * 0.3
        
        # Boost for exact matches
        if match.group(0).strip().lower() == match.string.strip().lower():
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _validate_parameters(self, parsed_intent: ParsedIntent) -> Dict[str, Any]:
        """Validate extracted parameters"""
        errors = []
        
        for param_name, param in parsed_intent.intent.parameters.items():
            value = parsed_intent.extracted_params.get(param_name)
            
            # Check required parameters
            if param.required and value is None:
                errors.append(f"Required parameter '{param_name}' is missing")
                continue
            
            # Validate pattern if specified
            if value and param.validation_pattern:
                if not re.match(param.validation_pattern, str(value)):
                    errors.append(f"Parameter '{param_name}' doesn't match required pattern")
        
        return {
            "valid": len(errors) == 0,
            "error": "; ".join(errors) if errors else None
        }
    
    def _register_default_intents(self):
        """Register default system intents"""
        
        # Screenshot intent
        screenshot_intent = Intent(
            name="take_screenshot",
            category=IntentCategory.AUTOMATION,
            parameters={
                "save_path": IntentParameter("save_path", "path", required=False, default="desktop")
            },
            patterns=[
                r"take\s+(?:a\s+)?screenshot(?:\s+(?:and\s+)?save\s+(?:it\s+)?(?:to\s+)?(?P<save_path>\S+))?",
                r"screenshot(?:\s+save\s+(?:to\s+)?(?P<save_path>\S+))?",
                r"capture\s+(?:the\s+)?screen(?:\s+(?:to\s+)?(?P<save_path>\S+))?"
            ],
            handler=self._handle_screenshot,
            description="Take a screenshot of the current screen",
            examples=[
                "take a screenshot",
                "screenshot and save to desktop",
                "capture the screen to C:/screenshots/image.png"
            ]
        )
        self.register_intent(screenshot_intent)
        
        # Click intent
        click_intent = Intent(
            name="click_coordinates",
            category=IntentCategory.AUTOMATION,
            parameters={
                "coordinates": IntentParameter("coordinates", "coordinates", required=True),
                "button": IntentParameter("button", "string", required=False, default="left"),
                "clicks": IntentParameter("clicks", "int", required=False, default=1)
            },
            patterns=[
                r"click\s+(?:at\s+)?(?P<coordinates>\d+[,\s]+\d+)(?:\s+(?P<button>left|right|middle))?(?:\s+(?P<clicks>\d+)\s+times?)?",
                r"(?P<button>left|right|middle)?\s*click\s+(?P<coordinates>\d+[,\s]+\d+)",
                r"click\s+(?P<coordinates>x\s*:\s*\d+\s+y\s*:\s*\d+)"
            ],
            handler=self._handle_click,
            description="Click at specific coordinates on the screen",
            examples=[
                "click at 500,300",
                "right click 100,200", 
                "click x:400 y:250"
            ]
        )
        self.register_intent(click_intent)
        
        # Type text intent
        type_intent = Intent(
            name="type_text",
            category=IntentCategory.AUTOMATION,
            parameters={
                "text": IntentParameter("text", "string", required=True),
                "interval": IntentParameter("interval", "float", required=False, default=0.01)
            },
            patterns=[
                r"type\s+[\"'](?P<text>.*?)[\"'](?:\s+with\s+interval\s+(?P<interval>\d+(?:\.\d+)?))?",
                r"write\s+[\"'](?P<text>.*?)[\"']",
                r"enter\s+(?:the\s+)?text\s+[\"'](?P<text>.*?)[\"']"
            ],
            handler=self._handle_type_text,
            description="Type specified text",
            examples=[
                "type \"Hello World\"",
                "write \"This is a test\"",
                "enter text \"My message\""
            ]
        )
        self.register_intent(type_intent)
        
        # Open application intent
        open_app_intent = Intent(
            name="open_application",
            category=IntentCategory.APPLICATION,
            parameters={
                "app_name": IntentParameter("app_name", "string", required=True)
            },
            patterns=[
                r"open\s+(?P<app_name>calculator|calc|notepad|explorer|chrome|firefox|edge|cmd|powershell|whatsapp|whats\s+app|discord|telegram|slack|teams|skype|zoom|spotify|vlc|photoshop|word|excel|powerpoint|outlook|photos|camera|mail|calendar|maps|store|weather|news|netflix|xbox|office|onedrive)",
                r"launch\s+(?P<app_name>calculator|calc|notepad|explorer|chrome|firefox|edge|cmd|powershell|whatsapp|whats\s+app|discord|telegram|slack|teams|skype|zoom|spotify|vlc|photoshop|word|excel|powerpoint|outlook|photos|camera|mail|calendar|maps|store|weather|news|netflix|xbox|office|onedrive)",
                r"start\s+(?P<app_name>calculator|calc|notepad|explorer|chrome|firefox|edge|cmd|powershell|whatsapp|whats\s+app|discord|telegram|slack|teams|skype|zoom|spotify|vlc|photoshop|word|excel|powerpoint|outlook|photos|camera|mail|calendar|maps|store|weather|news|netflix|xbox|office|onedrive)"
            ],
            handler=self._handle_open_application,
            description="Open common Windows applications",
            examples=[
                "open calculator",
                "launch notepad", 
                "start explorer",
                "open photos",
                "launch whatsapp",
                "start netflix",
                "open store",
                "launch teams"
            ]
        )
        self.register_intent(open_app_intent)
        
        # Window management intents
        minimize_intent = Intent(
            name="minimize_window",
            category=IntentCategory.AUTOMATION,
            parameters={
                "window_title": IntentParameter("window_title", "string", required=False)
            },
            patterns=[
                r"minimize(?:\s+(?:the\s+)?(?:window\s+)?(?P<window_title>.*?))?",
                r"minimize\s+all\s+windows"
            ],
            handler=self._handle_minimize_window,
            description="Minimize window(s)",
            examples=[
                "minimize",
                "minimize notepad",
                "minimize all windows"
            ]
        )
        self.register_intent(minimize_intent)
        
        # System info intent  
        system_info_intent = Intent(
            name="system_information",
            category=IntentCategory.SYSTEM_INFO,
            parameters={
                "info_type": IntentParameter("info_type", "string", required=False, default="general")
            },
            patterns=[
                r"(?:show|get|display)\s+system\s+(?:info|information)(?:\s+(?P<info_type>cpu|memory|disk|network))?",
                r"system\s+status",
                r"computer\s+(?:info|information)",
                r"pc\s+(?:info|specs|specifications)"
            ],
            handler=self._handle_system_info,
            description="Display system information and status",
            examples=[
                "show system info",
                "get system information cpu",
                "computer info"
            ]
        )
        self.register_intent(system_info_intent)
        
        # File operations
        create_file_intent = Intent(
            name="create_file",
            category=IntentCategory.FILE_SYSTEM,
            parameters={
                "filename": IntentParameter("filename", "path", required=True),
                "location": IntentParameter("location", "string", required=False, default=""),
                "content": IntentParameter("content", "string", required=False, default="")
            },
            patterns=[
                # Standard create file patterns
                r"create\s+(?:a\s+)?(?:new\s+)?(?:text\s+)?(?:html\s+)?file\s+(?:named\s+|called\s+)?(?P<filename>[\w.-]+)(?:\s+(?:in|on|at)\s+(?:the\s+)?(?:file\s+)?(?P<location>[^\"'\s]+|desktop|documents?|downloads?|[A-Za-z]:\\[^\"'\s]+))?(?:\s+(?:with\s+|and\s+add\s+|write\s+)(?:content\s+|some\s+|sample\s+.*?\s+|.*?\s+code\s+.*?\s+|.*?\s+inside\s+it\s+.*?\s+|.*?\s+along\s+with\s+.*?\s+)?(?:and\s+.*?\s+)?(?:[\"'](?P<content>.*?)[\"'])?)?",
                # HTML specific patterns
                r"create\s+(?P<filename>[\w.-]*\.html)\s+(?:file\s+)?(?:in\s+|at\s+)?(?P<location>[A-Za-z]:\\[^\"'\s]+|desktop|documents?|downloads?)?(?:\s+(?:write\s+|add\s+|with\s+)(?:some\s+)?(?:html\s+)?(?:code\s+)?(?:inside\s+it\s+)?(?:along\s+with\s+)?(?:best\s+)?(?:ui\s+)?.*?)?",
                # General patterns for any file type with location
                r"(?P<filename>[\w.-]+\.[a-z]+)\s+(?:file\s+)?(?:in\s+|at\s+)(?P<location>[A-Za-z]:\\[^\"'\s]+|desktop|documents?|downloads?)(?:\s+(?:with\s+|write\s+|add\s+).*?)?",
                # New file patterns
                r"new\s+(?:file\s+)?(?P<filename>[\w.-]+)(?:\s+(?:in|on|at)\s+(?P<location>[^\"'\s]+|desktop|documents?|downloads?|[A-Za-z]:\\[^\"'\s]+))?(?:\s+content\s+[\"'](?P<content>.*?)[\"'])?"
            ],
            handler=self._handle_create_file,
            description="Create a new file with optional content",
            examples=[
                "create file todo.txt",
                "create a new file called notes.txt with content \"My notes\"",
                "new file test.py"
            ]
        )
        self.register_intent(create_file_intent)
        
        # Open file intent
        open_file_intent = Intent(
            name="open_file",
            category=IntentCategory.FILE_SYSTEM,
            parameters={
                "target": IntentParameter("target", "string", required=False, default=""),
            },
            patterns=[
                r"open\s+(?:that|this|the)?\s*(?:file)?",
                r"(?:show|view|display|launch)\s+(?:that|this|the)?\s*(?:file|html|document|webpage)?",
                r"start\s+(?:that|this|the)?\s*(?:file|html|document)?",
                r"open\s+(?P<target>[\w.-]+)",
                r"launch\s+(?P<target>[\w.-]+)",
            ],
            handler=self._handle_open_file,
            description="Open recently created files",
            examples=[
                "open that file",
                "open this",
                "show the html file",
                "launch document"
            ]
        )
        self.register_intent(open_file_intent)
        
        # Compound application intents for advanced operations
        browser_search_intent = Intent(
            name="browser_search",
            category=IntentCategory.APPLICATION,
            parameters={
                "browser": IntentParameter("browser", "string", required=True),
                "query": IntentParameter("query", "string", required=True)
            },
            patterns=[
                r"open\s+(?P<browser>chrome|firefox|edge|browser)\s+and\s+search\s+(?:for\s+)?(?P<query>.+)",
                r"launch\s+(?P<browser>chrome|firefox|edge|browser)\s+and\s+search\s+(?:for\s+)?(?P<query>.+)",
                r"search\s+(?:for\s+)?(?P<query>.+)\s+(?:in|on|using)\s+(?P<browser>chrome|firefox|edge|browser)"
            ],
            handler=self._handle_browser_search,
            description="Open browser and search for something",
            examples=[
                "open chrome and search for python tutorials",
                "launch firefox and search for weather",
                "search for AI news in edge"
            ]
        )
        self.register_intent(browser_search_intent)
        
        # WhatsApp message intent
        whatsapp_message_intent = Intent(
            name="whatsapp_message",
            category=IntentCategory.APPLICATION,
            parameters={
                "contact": IntentParameter("contact", "string", required=True),
                "message": IntentParameter("message", "string", required=False)
            },
            patterns=[
                r"open\s+whats?app\s+(?:and\s+)?(?:send\s+)?message\s+to\s+(?P<contact>[^,]+)(?:\s+saying\s+(?P<message>.+))?",
                r"(?:send\s+)?message\s+to\s+(?P<contact>[^,]+)\s+(?:on\s+)?whats?app(?:\s+saying\s+(?P<message>.+))?",
                r"whats?app\s+(?P<contact>[^,]+)(?:\s+message\s+(?P<message>.+))?"
            ],
            handler=self._handle_whatsapp_message,
            description="Open WhatsApp and send message to contact",
            examples=[
                "open whatsapp and message john",
                "send message to mom on whatsapp saying hello",
                "whatsapp sarah message how are you"
            ]
        )
        self.register_intent(whatsapp_message_intent)
        
        # Telegram message intent
        telegram_message_intent = Intent(
            name="telegram_message",
            category=IntentCategory.APPLICATION,
            parameters={
                "contact": IntentParameter("contact", "string", required=True),
                "message": IntentParameter("message", "string", required=False)
            },
            patterns=[
                r"open\s+telegram\s+(?:and\s+)?(?:send\s+)?message\s+to\s+(?P<contact>[^,]+)(?:\s+saying\s+(?P<message>.+))?",
                r"(?:send\s+)?message\s+to\s+(?P<contact>[^,]+)\s+(?:on\s+)?telegram(?:\s+saying\s+(?P<message>.+))?",
                r"telegram\s+(?P<contact>[^,]+)(?:\s+message\s+(?P<message>.+))?"
            ],
            handler=self._handle_telegram_message,
            description="Open Telegram and send message to contact",
            examples=[
                "open telegram and message alice",
                "send message to bob on telegram saying hello",
                "telegram john message how's work"
            ]
        )
        self.register_intent(telegram_message_intent)
        
        # Discord message intent  
        discord_message_intent = Intent(
            name="discord_message",
            category=IntentCategory.APPLICATION,
            parameters={
                "channel_or_user": IntentParameter("channel_or_user", "string", required=True),
                "message": IntentParameter("message", "string", required=False)
            },
            patterns=[
                r"open\s+discord\s+(?:and\s+)?(?:send\s+)?message\s+to\s+(?P<channel_or_user>[^,]+)(?:\s+saying\s+(?P<message>.+))?",
                r"(?:send\s+)?message\s+to\s+(?P<channel_or_user>[^,]+)\s+(?:on\s+)?discord(?:\s+saying\s+(?P<message>.+))?",
                r"discord\s+(?P<channel_or_user>[^,]+)(?:\s+message\s+(?P<message>.+))?"
            ],
            handler=self._handle_discord_message,
            description="Open Discord and send message to channel or user",
            examples=[
                "open discord and message general channel",
                "send message to alex on discord saying good morning",
                "discord dev-team message meeting in 10 minutes"
            ]
        )
        self.register_intent(discord_message_intent)
        
        # File operations intent
        file_operations_intent = Intent(
            name="file_operations",
            category=IntentCategory.FILE_SYSTEM,
            parameters={
                "operation": IntentParameter("operation", "string", required=True),
                "source": IntentParameter("source", "string", required=False),
                "destination": IntentParameter("destination", "string", required=False),
                "filename": IntentParameter("filename", "string", required=False)
            },
            patterns=[
                r"(?P<operation>copy|move|delete|rename)\s+(?:file\s+)?(?P<source>[^\s]+)(?:\s+to\s+(?P<destination>.+))?",
                r"(?P<operation>search|find)\s+(?:file\s+)?(?P<filename>.+)",
                r"(?P<operation>backup|compress|extract)\s+(?P<source>.+)"
            ],
            handler=self._handle_file_operations,
            description="Perform file operations like copy, move, delete, search",
            examples=[
                "copy file document.txt to backup folder",
                "move image.jpg to pictures",
                "search file config.json",
                "delete old_file.tmp"
            ]
        )
        self.register_intent(file_operations_intent)
        
        # Media control intent
        media_control_intent = Intent(
            name="media_control",
            category=IntentCategory.MEDIA,
            parameters={
                "action": IntentParameter("action", "string", required=True),
                "app": IntentParameter("app", "string", required=False),
                "media": IntentParameter("media", "string", required=False)
            },
            patterns=[
                r"(?P<action>play|pause|stop|next|previous|skip)\s+(?:music|song|video)?(?:\s+(?:in|on)\s+(?P<app>spotify|vlc|youtube))?",
                r"(?P<action>volume)\s+(?P<media>up|down|mute)",
                r"(?:open\s+)?(?P<app>spotify|vlc)\s+(?:and\s+)?(?P<action>play)\s+(?P<media>.+)"
            ],
            handler=self._handle_media_control,
            description="Control media playback and volume",
            examples=[
                "play music",
                "pause spotify",
                "volume up",
                "next song",
                "open spotify and play jazz playlist"
            ]
        )
        self.register_intent(media_control_intent)
        
        # Email compose intent
        email_compose_intent = Intent(
            name="email_compose",
            category=IntentCategory.APPLICATION,
            parameters={
                "recipient": IntentParameter("recipient", "string", required=True),
                "subject": IntentParameter("subject", "string", required=False),
                "message": IntentParameter("message", "string", required=False)
            },
            patterns=[
                r"(?:open\s+)?(?:mail|email|outlook)\s+(?:and\s+)?(?:send\s+)?(?:email\s+)?to\s+(?P<recipient>[^,]+)(?:\s+subject\s+(?P<subject>[^,]+))?(?:\s+message\s+(?P<message>.+))?",
                r"compose\s+email\s+to\s+(?P<recipient>[^,]+)(?:\s+subject\s+(?P<subject>[^,]+))?(?:\s+saying\s+(?P<message>.+))?",
                r"email\s+(?P<recipient>[^,]+)(?:\s+about\s+(?P<subject>[^,]+))?(?:\s+message\s+(?P<message>.+))?"
            ],
            handler=self._handle_email_compose,
            description="Open email application and compose message",
            examples=[
                "email john about meeting tomorrow",
                "open outlook and send email to sarah subject project update",
                "compose email to boss saying task completed"
            ]
        )
        self.register_intent(email_compose_intent)
    
    # Intent Handlers
    
    async def _handle_screenshot(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle screenshot intent"""
        save_path = params.get("save_path")
        
        if save_path == "desktop":
            import os
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            save_path = os.path.join(desktop, f"screenshot_{int(time.time())}.png")
        
        result = automation.take_screenshot(save_path=save_path)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Screenshot saved to {result.get('saved_path', 'clipboard')}",
                "action": "screenshot_taken",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": f"Failed to take screenshot: {result.get('error', 'Unknown error')}"
            }
    
    async def _handle_click(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle click intent"""
        coords = params["coordinates"]
        button = params.get("button", "left")
        clicks = params.get("clicks", 1)
        
        result = automation.click(coords["x"], coords["y"], button=button, clicks=clicks)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Clicked at ({coords['x']}, {coords['y']}) with {button} button",
                "action": "click_performed",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": f"Click failed: {result.get('error', 'Unknown error')}"
            }
    
    async def _handle_type_text(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle type text intent"""
        text = params["text"]
        interval = params.get("interval", 0.01)
        
        result = automation.type_text(text, interval=interval)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}",
                "action": "text_typed",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": f"Type text failed: {result.get('error', 'Unknown error')}"
            }
    
    async def _handle_open_application(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle open application intent with Microsoft Store support"""
        app_name = params["app_name"].lower()
        
        import os
        import subprocess
        import glob
        
        # Normalize app name
        app_name = app_name.replace(" ", "")
        if "whats" in app_name and "app" in app_name:
            app_name = "whatsapp"
        
        # Microsoft Store package names (use explorer shell:appsFolder or start command)
        store_apps = {
            "calculator": "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App",
            "photos": "Microsoft.Windows.Photos_8wekyb3d8bbwe!App", 
            "camera": "Microsoft.WindowsCamera_8wekyb3d8bbwe!App",
            "mail": "microsoft.windowscommunicationsapps_8wekyb3d8bbwe!microsoft.windowslive.mail",
            "calendar": "microsoft.windowscommunicationsapps_8wekyb3d8bbwe!microsoft.windowslive.calendar",
            "maps": "Microsoft.WindowsMaps_8wekyb3d8bbwe!App",
            "store": "Microsoft.WindowsStore_8wekyb3d8bbwe!App",
            "weather": "Microsoft.BingWeather_8wekyb3d8bbwe!App",
            "news": "Microsoft.BingNews_8wekyb3d8bbwe!AppexNews",
            "whatsapp": "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!WhatsAppDesktop",
            "netflix": "4DF9E0F8.Netflix_mcm4njqhnhss8!Netflix.App",
            "spotify": "SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify",
            "discord": "53621F.Discord_g2ew6dge89m64!Discord",
            "telegram": "TelegramFZ.TelegramDesktop_t4wy6nh85nbc8!TelegramDesktop",
            "teams": "MicrosoftTeams_8wekyb3d8bbwe!MSTeams",
            "xbox": "Microsoft.XboxApp_8wekyb3d8bbwe!Microsoft.XboxApp",
            "office": "Microsoft.Office.Desktop_8wekyb3d8bbwe!Office",
            "onedrive": "Microsoft.SkyDrive_8wekyb3d8bbwe!Microsoft.SkyDrive",
            "skype": "Microsoft.SkypeApp_kzf8qxf38zg5c!App"
        }
        
        # Traditional executable paths
        traditional_apps = {
            "notepad": "notepad.exe", 
            "explorer": "explorer.exe",
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
            "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            "outlook": r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
            "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe"
        }
        
        # Try Microsoft Store app first
        if app_name in store_apps:
            try:
                # Use explorer shell:appsFolder to launch store app
                package_name = store_apps[app_name]
                subprocess.run([
                    "explorer.exe", 
                    f"shell:appsFolder\\{package_name}"
                ], check=True)
                
                return {
                    "success": True,
                    "message": f"Opened {app_name} (Microsoft Store)",
                    "action": "store_app_opened",
                    "data": {"package": package_name}
                }
            except Exception as e:
                # Fall through to try other methods
                pass
        
        # Try traditional executable
        if app_name in traditional_apps:
            app_path = traditional_apps[app_name]
            
            # Check if full path exists, otherwise try simple executable name
            if not os.path.exists(app_path) and app_path not in ["notepad.exe", "explorer.exe", "cmd.exe", "powershell.exe"]:
                # Try alternative locations
                alternatives = {
                    "chrome": [r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "chrome.exe"],
                    "firefox": [r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe", "firefox.exe"],
                    "edge": [r"C:\Windows\SystemApps\Microsoft.MicrosoftEdge_8wekyb3d8bbwe\MicrosoftEdge.exe", "msedge.exe"],
                    "vlc": [r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe", "vlc.exe"]
                }
                
                if app_name in alternatives:
                    for alt_path in alternatives[app_name]:
                        if os.path.exists(alt_path):
                            app_path = alt_path
                            break
            
            result = automation.launch_application(app_path)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Opened {app_name}",
                    "action": "application_opened",
                    "data": result
                }
        
        # Try finding app in WindowsApps folder (for store apps without known package name)
        try:
            windows_apps_path = r"C:\Program Files\WindowsApps"
            if os.path.exists(windows_apps_path):
                # Search for app folders matching the name
                search_patterns = [
                    f"*{app_name}*",
                    f"*{app_name.capitalize()}*"
                ]
                
                for pattern in search_patterns:
                    app_folders = glob.glob(os.path.join(windows_apps_path, pattern))
                    for folder in app_folders:
                        # Look for executable files
                        exe_files = glob.glob(os.path.join(folder, "*.exe"))
                        if exe_files:
                            try:
                                subprocess.run([exe_files[0]], check=True)
                                return {
                                    "success": True,
                                    "message": f"Opened {app_name} (found in WindowsApps)",
                                    "action": "windows_app_opened",
                                    "data": {"path": exe_files[0]}
                                }
                            except:
                                continue
        except:
            pass
        
        # Final fallback: try using start command with app name
        try:
            subprocess.run(["start", "", app_name], shell=True, check=True)
            return {
                "success": True,
                "message": f"Attempted to open {app_name} using start command",
                "action": "start_command_used",
                "data": {"method": "start_command"}
            }
        except:
            pass
        
        return {
            "success": False,
            "message": f"Could not find or launch application: {app_name}. Tried Microsoft Store, traditional paths, and system search."
        }
    
    async def _handle_minimize_window(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle minimize window intent"""
        window_title = params.get("window_title")
        
        if not window_title or window_title == "all":
            # Minimize all windows
            automation.hotkey("win", "m")
            return {
                "success": True,
                "message": "Minimized all windows",
                "action": "windows_minimized"
            }
        else:
            # Find and minimize specific window
            windows = automation.find_window(title_pattern=window_title)
            if windows:
                result = automation.minimize_window(windows[0].hwnd)
                if result["success"]:
                    return {
                        "success": True,
                        "message": f"Minimized window: {windows[0].title}",
                        "action": "window_minimized"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to minimize window: {result.get('error')}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"No window found with title: {window_title}"
                }
    
    async def _handle_system_info(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system info intent"""
        info_type = params.get("info_type", "general")
        
        metrics = automation.get_system_metrics()
        screen_size = automation.get_screen_size()
        
        info_text = "💻 **System Information:**\n\n"
        
        if info_type == "general" or info_type == "cpu":
            info_text += f"**CPU Usage:** {metrics.get('cpu_percent', 'N/A')}%\n"
        
        if info_type == "general" or info_type == "memory":
            memory = metrics.get('memory', {})
            if memory:
                total_gb = memory.get('total', 0) / (1024**3)
                available_gb = memory.get('available', 0) / (1024**3)
                info_text += f"**Memory:** {available_gb:.1f} GB available / {total_gb:.1f} GB total ({memory.get('percent', 0):.1f}% used)\n"
        
        if info_type == "general" or info_type == "disk":
            disk = metrics.get('disk', {})
            if disk:
                total_gb = disk.get('total', 0) / (1024**3)
                free_gb = disk.get('free', 0) / (1024**3)
                info_text += f"**Disk:** {free_gb:.1f} GB free / {total_gb:.1f} GB total ({disk.get('percent', 0):.1f}% used)\n"
        
        if info_type == "general":
            info_text += f"**Screen Resolution:** {screen_size[0]}x{screen_size[1]}\n"
        
        return {
            "success": True,
            "message": info_text,
            "action": "system_info_retrieved",
            "data": metrics
        }
    
    async def _handle_create_file(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle create file intent"""
        import os
        filename = str(params["filename"]).strip()
        location = params.get("location", None)
        if location is not None:
            location = str(location).strip().lower()
        content = params.get("content", "") or ""  # Handle None values
        raw_message = params.get("_raw_message", "")  # Get the original message if available
        
        # Intelligently generate content based on user request and file type
        if not content:
            # Check for content generation keywords in the original message
            content_keywords = ["write", "add", "code", "inside", "along with", "best ui", "sample", "html code"]
            should_generate_content = any(keyword in raw_message.lower() for keyword in content_keywords)
            
            if should_generate_content or filename.lower().endswith('.html') or 'html' in raw_message.lower():
                if filename.lower().endswith('.html') or 'html' in raw_message.lower():
                    # Generate enhanced HTML with modern styling
                    page_title = filename.replace('.html', '').replace('_', ' ').replace('-', ' ').title()
                    content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .container {{
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            max-width: 600px;
            text-align: center;
        }}
        
        h1 {{
            color: #4a5568;
            margin-bottom: 1rem;
            font-size: 2.5rem;
        }}
        
        p {{
            color: #718096;
            margin-bottom: 1.5rem;
            font-size: 1.1rem;
        }}
        
        .btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            font-size: 1rem;
            cursor: pointer;
            transition: transform 0.3s ease;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to {page_title}</h1>
        <p>This beautiful webpage was created by your Windows AI Agent with modern styling and best UI practices.</p>
        <button class="btn" onclick="alert('Hello from your AI Assistant!')">Click Me!</button>
    </div>
</body>
</html>'''
            elif filename.lower().endswith('.py'):
                content = '''# Sample Python code
print("Hello World!")

def main():
    """Main function"""
    print("This is a sample Python script created by Windows AI Agent.")

if __name__ == "__main__":
    main()
'''
        
        try:
            # Handle location mapping
            base_path = None
            if location:
                location_lower = location.lower()
                if location_lower == "desktop":
                    base_path = Path.home() / "Desktop"
                elif location_lower in ["documents", "document"]:
                    base_path = Path.home() / "Documents"
                elif location_lower in ["downloads", "download"]:
                    base_path = Path.home() / "Downloads"
                elif os.path.isabs(location) or ':\\' in location:
                    # Handle absolute paths like C:\Users\hegde\OneDrive\Desktop
                    base_path = Path(location)
                else:
                    # Try to use location as a relative directory path
                    base_path = Path(location)

            
            # Add appropriate extension if no extension provided
            if '.' not in filename:
                if 'html' in filename.lower() or 'html' in raw_message.lower():
                    filename = filename + '.html'
                elif 'python' in filename.lower() or '.py' in raw_message.lower():
                    filename = filename + '.py'
                elif 'javascript' in raw_message.lower() or 'js' in raw_message.lower():
                    filename = filename + '.js'
                else:
                    filename = filename + '.txt'
            
            # Construct file path
            if base_path and str(base_path) != '.' and base_path != Path('.'):
                file_path = base_path / filename
            else:
                # Default to current directory if no location specified
                file_path = Path.cwd() / filename
            
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            

            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Verify file was created
            if not file_path.exists():
                raise Exception(f"File was not created at {file_path}")
            
            # Get a readable parent path
            parent_display = str(file_path.parent)
            if parent_display == '.' or parent_display == '' or parent_display == 'None':
                parent_display = str(Path.cwd())
            elif not parent_display or parent_display == 'none':
                parent_display = str(Path.cwd())
            

            
            return {
                "success": True,
                "message": f"Created file '{file_path.name}' at {parent_display}",
                "action": "file_created",
                "data": {"path": str(file_path), "size": len(content)}
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create file: {str(e)}"
            }
    
    async def _handle_open_file(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle open file intent - opens recently created files"""
        target = params.get("target", "").strip()
        
        try:
            # Get memory manager from the main app (we'll need to pass it in somehow)
            # For now, let's use a simple approach - look for recent files in current directory
            import os
            import glob
            from pathlib import Path
            
            # Try to find recently created files
            current_dir = Path.cwd()
            desktop = Path.home() / "Desktop"
            onedrive_desktop = Path.home() / "OneDrive" / "Desktop"
            documents = Path.home() / "Documents"
            
            search_paths = [current_dir, desktop, documents]
            if onedrive_desktop.exists():
                search_paths.append(onedrive_desktop)
            
            recent_files = []
            for search_path in search_paths:
                if search_path.exists():
                    # Find HTML, text, and other files modified in last hour
                    for pattern in ["*.html", "*.txt", "*.py", "*.js", "*.css"]:
                        files = list(search_path.glob(pattern))
                        for file_path in files:
                            try:
                                mtime = file_path.stat().st_mtime
                                import time
                                if time.time() - mtime < 3600:  # Last hour
                                    recent_files.append((file_path, mtime))
                            except:
                                continue
            
            # Sort by modification time (most recent first)
            recent_files.sort(key=lambda x: x[1], reverse=True)
            
            if not recent_files:
                return {
                    "success": False,
                    "message": "No recent files found to open"
                }
            
            # If target specified, try to find matching file
            if target:
                for file_path, _ in recent_files:
                    if target.lower() in file_path.name.lower():
                        try:
                            os.startfile(str(file_path))
                            return {
                                "success": True,
                                "message": f"Opened {file_path.name}",
                                "action": "file_opened",
                                "data": {"path": str(file_path)}
                            }
                        except Exception as e:
                            return {
                                "success": False,
                                "message": f"Failed to open {file_path.name}: {str(e)}"
                            }
            
            # Open the most recent file
            most_recent_file = recent_files[0][0]
            try:
                os.startfile(str(most_recent_file))
                return {
                    "success": True,
                    "message": f"Opened {most_recent_file.name}",
                    "action": "file_opened",
                    "data": {"path": str(most_recent_file)}
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Failed to open {most_recent_file.name}: {str(e)}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error opening file: {str(e)}"
            }
    
    def get_intent_list(self) -> List[Dict[str, Any]]:
        """Get list of all registered intents"""
        return [
            {
                "name": intent.name,
                "category": intent.category.value,
                "description": intent.description,
                "examples": intent.examples,
                "requires_confirmation": intent.requires_confirmation
            }
            for intent in self.intents.values()
        ]
    
    def save_intents_schema(self, filepath: str):
        """Save intents schema to JSON file"""
        try:
            schema = {
                "intents": {
                    name: {
                        "category": intent.category.value,
                        "description": intent.description,
                        "patterns": intent.patterns,
                        "parameters": {
                            pname: {
                                "type": param.type,
                                "required": param.required,
                                "description": param.description,
                                "default": param.default
                            }
                            for pname, param in intent.parameters.items()
                        },
                        "examples": intent.examples,
                        "requires_confirmation": intent.requires_confirmation
                    }
                    for name, intent in self.intents.items()
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved intents schema to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save intents schema: {e}")
            
    def load_intents_schema(self, filepath: str):
        """Load intents schema from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            # TODO: Implement loading custom intents from schema
            logger.info(f"Loaded intents schema from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load intents schema: {e}")
            
    async def _handle_browser_search(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle browser search compound intent"""
        browser = params["browser"].lower()
        query = params["query"].strip()
        
        import time
        import urllib.parse
        
        # Browser executable mapping
        browser_apps = {
            "chrome": "chrome",
            "firefox": "firefox", 
            "edge": "edge",
            "browser": "edge"  # Default to Edge
        }
        
        browser_name = browser_apps.get(browser, "edge")
        
        try:
            # Launch browser first
            launch_result = await self._handle_open_application(automation, {"app_name": browser_name})
            
            if not launch_result["success"]:
                return {
                    "success": False,
                    "message": f"Failed to open {browser}: {launch_result.get('message', 'Unknown error')}"
                }
            
            # Wait for browser to load
            await asyncio.sleep(2)
            
            # Create search URL (using Google search)
            encoded_query = urllib.parse.quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
            # Type the search URL in address bar
            # Press Ctrl+L to focus address bar
            automation.key_combination(['ctrl', 'l'])
            await asyncio.sleep(0.5)
            
            # Type the search URL
            automation.type_text(search_url)
            await asyncio.sleep(0.5)
            
            # Press Enter to search
            automation.key_combination(['enter'])
            
            return {
                "success": True,
                "message": f"Opened {browser} and searched for '{query}'",
                "action": "browser_search_performed",
                "data": {
                    "browser": browser,
                    "query": query,
                    "search_url": search_url
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to perform browser search: {str(e)}"
            }
    
    async def _handle_whatsapp_message(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WhatsApp message compound intent"""
        contact = params["contact"].strip()
        message = params.get("message", "").strip()
        
        import time
        
        try:
            # Launch WhatsApp first
            launch_result = await self._handle_open_application(automation, {"app_name": "whatsapp"})
            
            if not launch_result["success"]:
                return {
                    "success": False,
                    "message": f"Failed to open WhatsApp: {launch_result.get('message', 'Unknown error')}"
                }
            
            # Wait for WhatsApp to load
            await asyncio.sleep(3)
            
            # Use Ctrl+F to open search
            automation.key_combination(['ctrl', 'f'])
            await asyncio.sleep(1)
            
            # Type contact name
            automation.type_text(contact)
            await asyncio.sleep(1)
            
            # Press Enter to select first result
            automation.key_combination(['enter'])
            await asyncio.sleep(1)
            
            # If message is provided, type it
            if message:
                automation.type_text(message)
                await asyncio.sleep(0.5)
                
                return {
                    "success": True,
                    "message": f"Opened WhatsApp, found {contact}, and typed message: '{message}'",
                    "action": "whatsapp_message_typed",
                    "data": {
                        "contact": contact,
                        "message": message,
                        "note": "Message typed but not sent automatically for safety"
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"Opened WhatsApp and navigated to {contact}'s chat",
                    "action": "whatsapp_contact_opened",
                    "data": {
                        "contact": contact
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to handle WhatsApp message: {str(e)}"
            }
    
    async def _handle_email_compose(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email compose compound intent"""
        recipient = params["recipient"].strip()
        subject = params.get("subject", "").strip()
        message = params.get("message", "").strip()
        
        import time
        
        try:
            # Launch Outlook/Mail app
            launch_result = await self._handle_open_application(automation, {"app_name": "outlook"})
            
            if not launch_result["success"]:
                # Try Mail app as fallback
                launch_result = await self._handle_open_application(automation, {"app_name": "mail"})
                
            if not launch_result["success"]:
                return {
                    "success": False,
                    "message": "Failed to open email application (tried Outlook and Mail)"
                }
            
            # Wait for email app to load
            await asyncio.sleep(3)
            
            # Use Ctrl+N to create new email
            automation.key_combination(['ctrl', 'n'])
            await asyncio.sleep(2)
            
            # Type recipient
            automation.type_text(recipient)
            await asyncio.sleep(0.5)
            
            # Move to subject field (Tab)
            automation.key_combination(['tab'])
            await asyncio.sleep(0.5)
            
            # Type subject if provided
            if subject:
                automation.type_text(subject)
            
            # Move to message body (Tab)
            automation.key_combination(['tab'])
            await asyncio.sleep(0.5)
            
            # Type message if provided
            if message:
                automation.type_text(message)
            
            compose_details = {
                "recipient": recipient,
                "subject": subject or "No subject",
                "message": message or "No message"
            }
            
            return {
                "success": True,
                "message": f"Opened email composer for {recipient}" + 
                          (f" with subject '{subject}'" if subject else "") +
                          (f" and message '{message[:50]}...'" if len(message) > 50 else f" and message '{message}'" if message else ""),
                "action": "email_composed",
                "data": {
                    **compose_details,
                    "note": "Email composed but not sent automatically for safety"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to compose email: {str(e)}"
            }
    
    async def _handle_telegram_message(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Telegram message compound intent"""
        contact = params["contact"].strip()
        message = params.get("message", "").strip()
        
        import time
        
        try:
            # Launch Telegram first
            launch_result = await self._handle_open_application(automation, {"app_name": "telegram"})
            
            if not launch_result["success"]:
                return {
                    "success": False,
                    "message": f"Failed to open Telegram: {launch_result.get('message', 'Unknown error')}"
                }
            
            # Wait for Telegram to load
            await asyncio.sleep(3)
            
            # Use Ctrl+K to open global search
            automation.key_combination(['ctrl', 'k'])
            await asyncio.sleep(1)
            
            # Type contact name
            automation.type_text(contact)
            await asyncio.sleep(1)
            
            # Press Enter to select first result
            automation.key_combination(['enter'])
            await asyncio.sleep(1)
            
            # If message is provided, type it
            if message:
                automation.type_text(message)
                await asyncio.sleep(0.5)
                
                return {
                    "success": True,
                    "message": f"Opened Telegram, found {contact}, and typed message: '{message}'",
                    "action": "telegram_message_typed",
                    "data": {
                        "contact": contact,
                        "message": message,
                        "note": "Message typed but not sent automatically for safety"
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"Opened Telegram and navigated to {contact}'s chat",
                    "action": "telegram_contact_opened",
                    "data": {
                        "contact": contact
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to handle Telegram message: {str(e)}"
            }
    
    async def _handle_discord_message(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Discord message compound intent"""
        channel_or_user = params["channel_or_user"].strip()
        message = params.get("message", "").strip()
        
        import time
        
        try:
            # Launch Discord first
            launch_result = await self._handle_open_application(automation, {"app_name": "discord"})
            
            if not launch_result["success"]:
                return {
                    "success": False,
                    "message": f"Failed to open Discord: {launch_result.get('message', 'Unknown error')}"
                }
            
            # Wait for Discord to load
            await asyncio.sleep(4)
            
            # Use Ctrl+K to open quick switcher
            automation.key_combination(['ctrl', 'k'])
            await asyncio.sleep(1)
            
            # Type channel or user name
            automation.type_text(channel_or_user)
            await asyncio.sleep(1)
            
            # Press Enter to select first result
            automation.key_combination(['enter'])
            await asyncio.sleep(1)
            
            # If message is provided, type it
            if message:
                automation.type_text(message)
                await asyncio.sleep(0.5)
                
                return {
                    "success": True,
                    "message": f"Opened Discord, navigated to {channel_or_user}, and typed message: '{message}'",
                    "action": "discord_message_typed",
                    "data": {
                        "channel_or_user": channel_or_user,
                        "message": message,
                        "note": "Message typed but not sent automatically for safety"
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"Opened Discord and navigated to {channel_or_user}",
                    "action": "discord_channel_opened",
                    "data": {
                        "channel_or_user": channel_or_user
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to handle Discord message: {str(e)}"
            }
    
    async def _handle_file_operations(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file operations"""
        operation = params["operation"].lower()
        source = params.get("source", "").strip()
        destination = params.get("destination", "").strip()
        filename = params.get("filename", "").strip()
        
        import os
        import shutil
        import glob
        from pathlib import Path
        
        try:
            if operation == "copy" and source and destination:
                # Copy file operation
                source_path = Path(source).expanduser()
                dest_path = Path(destination).expanduser()
                
                if source_path.exists():
                    if dest_path.is_dir():
                        shutil.copy2(source_path, dest_path / source_path.name)
                    else:
                        shutil.copy2(source_path, dest_path)
                    
                    return {
                        "success": True,
                        "message": f"Successfully copied {source} to {destination}",
                        "action": "file_copied",
                        "data": {"source": str(source_path), "destination": str(dest_path)}
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Source file {source} not found"
                    }
            
            elif operation == "search" and filename:
                # Search for file
                search_paths = [
                    Path.home() / "Desktop",
                    Path.home() / "Documents", 
                    Path.home() / "Downloads",
                    Path.cwd()
                ]
                
                found_files = []
                for search_path in search_paths:
                    if search_path.exists():
                        matches = list(search_path.rglob(f"*{filename}*"))
                        found_files.extend(matches[:5])  # Limit results
                
                if found_files:
                    files_info = [{"path": str(f), "size": f.stat().st_size} for f in found_files[:10]]
                    return {
                        "success": True,
                        "message": f"Found {len(found_files)} files matching '{filename}'",
                        "action": "files_found",
                        "data": {"files": files_info}
                    }
                else:
                    return {
                        "success": False,
                        "message": f"No files found matching '{filename}'"
                    }
            
            elif operation == "delete" and source:
                # Delete file operation
                file_path = Path(source).expanduser()
                if file_path.exists():
                    if file_path.is_file():
                        file_path.unlink()
                    else:
                        shutil.rmtree(file_path)
                    
                    return {
                        "success": True,
                        "message": f"Successfully deleted {source}",
                        "action": "file_deleted",
                        "data": {"path": str(file_path)}
                    }
                else:
                    return {
                        "success": False,
                        "message": f"File {source} not found"
                    }
            
            return {
                "success": False,
                "message": f"Unsupported file operation: {operation}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"File operation failed: {str(e)}"
            }
    
    async def _handle_media_control(self, automation: WindowsAutomation, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle media control operations"""
        action = params["action"].lower()
        app = params.get("app", "").lower()
        media = params.get("media", "").lower()
        
        import time
        
        try:
            # If specific app is mentioned, open it first
            if app in ["spotify", "vlc"]:
                launch_result = await self._handle_open_application(automation, {"app_name": app})
                if launch_result["success"]:
                    await asyncio.sleep(2)  # Wait for app to load
            
            # Global media key operations
            if action == "play":
                automation.press_key('playpause')
                return {
                    "success": True,
                    "message": f"Pressed play/pause" + (f" in {app}" if app else ""),
                    "action": "media_play_pause",
                    "data": {"action": "play", "app": app}
                }
            
            elif action == "pause":
                automation.press_key('playpause')
                return {
                    "success": True,
                    "message": f"Pressed pause" + (f" in {app}" if app else ""),
                    "action": "media_play_pause",
                    "data": {"action": "pause", "app": app}
                }
            
            elif action == "next":
                automation.press_key('nexttrack')
                return {
                    "success": True,
                    "message": f"Skipped to next track" + (f" in {app}" if app else ""),
                    "action": "media_next",
                    "data": {"action": "next", "app": app}
                }
            
            elif action == "previous":
                automation.press_key('prevtrack')
                return {
                    "success": True,
                    "message": f"Went to previous track" + (f" in {app}" if app else ""),
                    "action": "media_previous", 
                    "data": {"action": "previous", "app": app}
                }
            
            elif action == "volume":
                if media == "up":
                    automation.press_key('volumeup')
                elif media == "down":
                    automation.press_key('volumedown')
                elif media == "mute":
                    automation.press_key('volumemute')
                
                return {
                    "success": True,
                    "message": f"Volume {media}",
                    "action": "volume_control",
                    "data": {"action": "volume", "direction": media}
                }
            
            return {
                "success": False,
                "message": f"Unsupported media action: {action}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Media control failed: {str(e)}"
            }