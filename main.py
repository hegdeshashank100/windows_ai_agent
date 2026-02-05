"""
Windows AI Agent - Main Application Entry Point
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Optional

# Add src directory to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import after path setup
from PyQt6.QtWidgets import QApplication
from src.ui.chat_window import ChatWindow, main as ui_main
from src.core.agent import WindowsAIAgent
from src.core.intent_recognition import IntentRecognizer
from src.core.memory_manager import MemoryManager
from src.automation.windows_automation import WindowsAutomation
from src.utils.config import config
from src.utils.code_executor import CodeExecutor

from loguru import logger


def setup_logging():
    """Setup application logging"""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "agent.log"
    
    # Remove default logger
    logger.remove()
    
    # Add file logging
    logger.add(
        log_file,
        rotation="10 MB",
        retention="7 days",
        level=config.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        backtrace=True,
        diagnose=True
    )
    
    # Add console logging if debug mode
    if config.debug_mode:
        logger.add(
            sys.stderr,
            level="DEBUG",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )
    else:
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
            colorize=True
        )


class IntegratedWindowsAgent:
    """Integrated Windows AI Agent with all components"""
    
    def __init__(self):
        self.automation = None
        self.intent_recognizer = None
        self.code_executor = None
        self.agent = None
        self.memory_manager = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all agent components"""
        try:
            # Initialize memory manager first
            self.memory_manager = MemoryManager()
            logger.info("Memory manager initialized")
            
            # Initialize Windows automation
            self.automation = WindowsAutomation(safe_mode=True)
            logger.info("Windows automation initialized")
            
            # Initialize intent recognizer
            self.intent_recognizer = IntentRecognizer(self.automation)
            logger.info("Intent recognizer initialized")
            
            # Initialize code executor
            if config.enable_code_execution:
                self.code_executor = CodeExecutor()
                logger.info("Code executor initialized")
            
            # Initialize main agent
            self.agent = WindowsAIAgent()
            
            # Register additional capabilities
            self._register_enhanced_capabilities()
            
            logger.info("Integrated Windows Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent components: {e}")
            raise
    
    def _register_enhanced_capabilities(self):
        """Register enhanced capabilities that integrate multiple components"""
        
        # Code execution capability
        if self.code_executor:
            self.agent.register_capability(
                "execute_code",
                "Execute Python code safely in a sandbox environment",
                self._handle_code_execution,
                category="code"
            )
        
        # Intent-based automation
        self.agent.register_capability(
            "intent_automation",
            "Perform desktop automation based on natural language intents",
            self._handle_intent_automation,
            category="automation"
        )
        
        # Advanced screenshot with analysis
        self.agent.register_capability(
            "advanced_screenshot", 
            "Take screenshot with optional image analysis",
            self._handle_advanced_screenshot,
            category="automation"
        )
        
        # System monitoring
        self.agent.register_capability(
            "system_monitor",
            "Advanced system monitoring and performance analysis", 
            self._handle_system_monitor,
            category="system"
        )
    
    async def _handle_code_execution(self, message: str):
        """Handle code execution requests"""
        try:
            # Extract code from message (look for code blocks)
            import re
            code_pattern = r'```(?:python)?\s*(.*?)\s*```'
            match = re.search(code_pattern, message, re.DOTALL)
            
            if match:
                code = match.group(1).strip()
            else:
                # If no code blocks, assume the entire message is code
                # after removing common prefixes
                code = message
                for prefix in ["run this code:", "execute:", "run:", "python:"]:
                    if code.lower().startswith(prefix):
                        code = code[len(prefix):].strip()
                        break
            
            if not code:
                return {
                    "success": False,
                    "message": "No code found to execute. Please provide Python code in ```python code blocks or after 'run this code:'"
                }
            
            # Execute the code
            result = self.code_executor.execute(code, mode="safe")
            
            if result["success"]:
                output_msg = f"✅ **Code executed successfully!**\n\n"
                if result["output"]:
                    output_msg += f"**Output:**\n```\n{result['output']}\n```\n\n"
                if result["variables"]:
                    output_msg += f"**Variables created:**\n"
                    for name, value in result["variables"].items():
                        output_msg += f"• `{name}` = {repr(value)}\n"
                output_msg += f"\n⏱️ *Execution time: {result['execution_time']:.3f}s*"
                
                return {
                    "success": True,
                    "message": output_msg,
                    "data": result
                }
            else:
                error_msg = f"❌ **Code execution failed:**\n\n"
                error_msg += f"```\n{result['error']}\n```"
                
                return {
                    "success": False,
                    "message": error_msg,
                    "data": result
                }
                
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            return {
                "success": False,
                "message": f"Error handling code execution: {str(e)}"
            }
    
    async def _handle_intent_automation(self, message: str):
        """Handle intent-based automation requests"""
        try:
            # Parse intent from message
            parsed_intent = await self.intent_recognizer.parse_intent(message)
            
            if parsed_intent and parsed_intent.confidence > 0.6:
                # Execute the intent
                result = await self.intent_recognizer.execute_intent(parsed_intent)
                
                if result["success"]:
                    return {
                        "success": True,
                        "message": f"✅ **{parsed_intent.intent.name}**: {result['message']}",
                        "data": {
                            "intent": parsed_intent.intent.name,
                            "confidence": parsed_intent.confidence,
                            "result": result
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ **{parsed_intent.intent.name} failed**: {result['message']}"
                    }
            else:
                return {
                    "success": False,
                    "message": "I couldn't understand that automation request. Try being more specific, like 'take a screenshot' or 'open calculator'."
                }
                
        except Exception as e:
            logger.error(f"Intent automation error: {e}")
            return {
                "success": False,
                "message": f"Error processing automation request: {str(e)}"
            }
    
    async def _handle_advanced_screenshot(self, message: str):
        """Handle advanced screenshot requests"""
        try:
            # Take screenshot
            result = self.automation.take_screenshot()
            
            if result["success"]:
                # Save to desktop with timestamp
                import time
                desktop_path = Path.home() / "Desktop"
                screenshot_path = desktop_path / f"ai_screenshot_{int(time.time())}.png"
                
                # Save the screenshot
                if self.automation.last_screenshot:
                    self.automation.last_screenshot.save(screenshot_path)
                
                return {
                    "success": True,
                    "message": f"📸 **Screenshot captured!**\n\n📁 Saved to: `{screenshot_path}`\n📏 Size: {result['size'][0]}×{result['size'][1]} pixels",
                    "data": {
                        "path": str(screenshot_path),
                        "size": result["size"],
                        "timestamp": result["timestamp"]
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ Screenshot failed: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            logger.error(f"Advanced screenshot error: {e}")
            return {
                "success": False,
                "message": f"Error taking screenshot: {str(e)}"
            }
    
    async def _handle_system_monitor(self, message: str):
        """Handle system monitoring requests"""
        try:
            # Get comprehensive system info
            metrics = self.automation.get_system_metrics()
            screen_size = self.automation.get_screen_size()
            mouse_pos = self.automation.get_mouse_position()
            
            # Get running processes (top 10 by memory)
            processes = self.automation.get_running_processes()
            top_processes = sorted(processes, key=lambda p: p.get('memory_mb', 0), reverse=True)[:10]
            
            # Format system info
            info_msg = "💻 **System Monitor Report**\n\n"
            
            # Performance metrics
            info_msg += "**📊 Performance:**\n"
            info_msg += f"• CPU Usage: {metrics.get('cpu_percent', 'N/A')}%\n"
            
            if 'memory' in metrics:
                mem = metrics['memory']
                total_gb = mem.get('total', 0) / (1024**3)
                available_gb = mem.get('available', 0) / (1024**3)
                info_msg += f"• Memory: {available_gb:.1f} GB free / {total_gb:.1f} GB total ({mem.get('percent', 0):.1f}% used)\n"
            
            if 'disk' in metrics:
                disk = metrics['disk']
                total_gb = disk.get('total', 0) / (1024**3)
                free_gb = disk.get('free', 0) / (1024**3)
                info_msg += f"• Disk: {free_gb:.1f} GB free / {total_gb:.1f} GB total ({disk.get('percent', 0):.1f}% used)\n"
            
            # Display info
            info_msg += f"\n**🖥️ Display:**\n"
            info_msg += f"• Resolution: {screen_size[0]}×{screen_size[1]}\n"
            info_msg += f"• Mouse Position: {mouse_pos[0]}, {mouse_pos[1]}\n"
            
            # Top processes
            info_msg += f"\n**🔝 Top Processes (by memory):**\n"
            for proc in top_processes[:5]:
                info_msg += f"• {proc['name']}: {proc['memory_mb']:.1f} MB ({proc['cpu_percent']:.1f}% CPU)\n"
            
            return {
                "success": True,
                "message": info_msg,
                "data": {
                    "metrics": metrics,
                    "screen_size": screen_size,
                    "mouse_position": mouse_pos,
                    "top_processes": top_processes
                }
            }
            
        except Exception as e:
            logger.error(f"System monitor error: {e}")
            return {
                "success": False,
                "message": f"Error getting system information: {str(e)}"
            }
    
    async def process_message(self, message: str, context: Optional[dict] = None) -> str:
        """Process a message through the AI-powered integrated agent"""
        try:
            # Get memory context for this message
            memory_context = self.memory_manager.get_context_for_message(message)
            
            # Use Gemini to intelligently understand the user's intent and decide action
            ai_analysis = await self._analyze_user_intent(message, memory_context)
            
            # If Gemini determined this should be an immediate action, execute it
            if ai_analysis.get("should_execute_action"):
                action_result = await self._execute_intelligent_action(ai_analysis, message, memory_context)
                if action_result:
                    self.memory_manager.add_conversation(message, action_result, ai_analysis.get("intent_type"))
                    return action_result
            
            # Try traditional intent recognition as backup
            if self.intent_recognizer:
                parsed_intent = await self.intent_recognizer.parse_intent(message)
                if parsed_intent and parsed_intent.confidence > 0.4:
                    result = await self.intent_recognizer.execute_intent(parsed_intent)
                    if result["success"]:
                        # Add to memory with intelligent context
                        if parsed_intent.intent.name == "create_file":
                            file_path = result.get("data", {}).get("path", "")
                            if file_path:
                                self.memory_manager.add_file_memory(
                                    file_path, 
                                    Path(file_path).suffix or "txt",
                                    message
                                )
                        
                        # Be more conversational in response
                        action_msg = result["message"]
                        if parsed_intent.intent.name == "create_file":
                            response = f"✅ Done! I've {action_msg.lower()}. The file is ready for you to use."
                        elif parsed_intent.intent.name == "open_application":
                            response = f"✅ {action_msg} You should see it opening now."
                        elif parsed_intent.intent.name == "take_screenshot":
                            response = f"📸 {action_msg} Check your desktop for the screenshot."
                        else:
                            response = f"✅ {action_msg}"
                        
                        # Add to memory
                        self.memory_manager.add_conversation(message, response, parsed_intent.intent.name)
                        return response
                    else:
                        # If intent execution failed, try to handle it intelligently
                        logger.warning(f"Intent execution failed: {result.get('message', 'Unknown error')}")
                        error_msg = result.get('message', 'Unknown error')
                        # Still provide a helpful response
                        response = f"I tried to execute your request but encountered an issue: {error_msg}. Let me know if you'd like me to try a different approach."
                        self.memory_manager.add_conversation(message, response)
                        return response
            
            # Check for code execution requests
            if self.code_executor and any(keyword in message.lower() for keyword in 
                                        ["run this code", "execute", "python code", "```"]):
                result = await self._handle_code_execution(message)
                return result["message"]
            
            # Use AI to understand if this is an action request that we should execute
            if await self._should_execute_as_action(message):
                # Let AI suggest the action and then execute it
                ai_response = await self.agent.process_message(
                    f"The user said: '{message}'. This seems like they want me to perform an action on their Windows PC. "
                    f"Should I create a file, open an application, take a screenshot, or perform another automation task? "
                    f"If yes, please respond with EXECUTE followed by the exact command I should run (like 'create file example.html in desktop with html code').", 
                    context
                )
                
                if "EXECUTE" in ai_response:
                    # Extract the command and try to execute it
                    command = ai_response.split("EXECUTE", 1)[1].strip()
                    parsed_intent = await self.intent_recognizer.parse_intent(command)
                    if parsed_intent and parsed_intent.confidence > 0.3:
                        result = await self.intent_recognizer.execute_intent(parsed_intent)
                        if result["success"]:
                            return f"✅ I understood your request and {result['message'].lower()}!"
                
            # Fall back to intelligent AI conversation with full context awareness
            intelligent_response = await self._generate_intelligent_response(message, memory_context, context)
            self.memory_manager.add_conversation(message, intelligent_response)
            return intelligent_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    async def _analyze_user_intent(self, message: str, memory_context: dict) -> dict:
        """Use Gemini to intelligently analyze user intent and determine action"""
        
        # Build context-aware prompt for Gemini
        context_info = ""
        if memory_context.get('recent_files'):
            files_list = [f"- {f['filename']} ({f['type']}) at {f['path']}" for f in memory_context['recent_files'][:3]]
            context_info += f"Recent files I created:\n" + "\n".join(files_list) + "\n\n"
        
        if memory_context.get('recent_actions'):
            actions_list = [f"- {a['action']}: {a['details']}" for a in memory_context['recent_actions'][-3:]]
            context_info += f"Recent actions:\n" + "\n".join(actions_list) + "\n\n"
        
        analysis_prompt = f"""You are an intelligent Windows desktop assistant. Analyze this user message and determine the best response strategy.

User message: "{message}"

Current context:
{context_info}

CRITICAL: Distinguish between these actions:
- "open [application name]" = launch_app (e.g., "open WhatsApp", "open Chrome", "open calculator")
- "open [browser] and search for [query]" = browser_search (e.g., "open chrome and search for AI news")
- "open whatsapp and message [contact]" = whatsapp_message (e.g., "open whatsapp message john")
- "email [recipient]" or "compose email to [person]" = email_compose (e.g., "email sarah about meeting")
- "open [file reference]" = open_file (e.g., "open that file", "open it", "open the HTML")
- "create [filename]" = create_file
- "take screenshot" = screenshot
- "show system info" = system_info

Common applications: WhatsApp, Chrome, Firefox, Edge, Notepad, Calculator, Word, Excel, PowerPoint, Outlook, Teams, Zoom, Spotify, etc.

Analyze the message and respond with a JSON object:
{{
    "user_intent": "brief description of what user wants",
    "should_execute_action": true/false,
    "action_type": "create_file|open_file|launch_app|browser_search|whatsapp_message|telegram_message|discord_message|email_compose|file_operations|media_control|screenshot|system_info|conversation|other",
    "confidence": 0.0-1.0,
    "parameters": {{"app_name": "for launch_app", "browser": "for browser_search", "query": "for search", "contact": "for messaging apps", "message": "for messages", "recipient": "for email", "subject": "for email", "filename": "for files", "location": "for create_file", "channel_or_user": "for discord", "operation": "for file ops", "action": "for media", "media": "for media control"}},
    "response_style": "direct|conversational|detailed|helpful",
    "suggested_response": "what I should say to the user"
}}

EXAMPLES:
- "open whats app" → {{"action_type": "launch_app", "parameters": {{"app_name": "whatsapp"}}}}
- "open chrome and search for python tutorials" → {{"action_type": "browser_search", "parameters": {{"browser": "chrome", "query": "python tutorials"}}}}
- "open whatsapp message john" → {{"action_type": "whatsapp_message", "parameters": {{"contact": "john"}}}}
- "email sarah about meeting" → {{"action_type": "email_compose", "parameters": {{"recipient": "sarah", "subject": "meeting"}}}}
- "open that file" → {{"action_type": "open_file", "parameters": {{}}}}
- "create test.html" → {{"action_type": "create_file", "parameters": {{"filename": "test.html"}}}}

Be intelligent about context - if user says "open it" and I recently created a file, they mean open that file.
If user mentions a known application name after "open", it's definitely launch_app."""

        try:
            ai_response = await self.agent.process_message(analysis_prompt)
            
            # Try to extract JSON from response
            import json
            import re
            
            # Find JSON in the response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return analysis
            else:
                # Fallback analysis
                return {
                    "user_intent": "general conversation",
                    "should_execute_action": False,
                    "action_type": "conversation",
                    "confidence": 0.3,
                    "parameters": {},
                    "response_style": "conversational",
                    "suggested_response": ai_response
                }
                
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
            return {
                "user_intent": "unknown",
                "should_execute_action": False,
                "action_type": "conversation",
                "confidence": 0.1,
                "parameters": {},
                "response_style": "conversational", 
                "suggested_response": "I'm not sure what you'd like me to do. Could you be more specific?"
            }
    
    async def _execute_intelligent_action(self, analysis: dict, original_message: str, memory_context: dict) -> Optional[str]:
        """Execute actions based on AI analysis"""
        action_type = analysis.get("action_type")
        parameters = analysis.get("parameters", {})
        
        try:
            if action_type == "create_file":
                # Extract file creation parameters intelligently
                filename = parameters.get("filename", "document.txt")
                location = parameters.get("location", "")
                content_type = parameters.get("content_type", "text")
                
                # Use intent recognizer to create file
                if self.intent_recognizer:
                    # Build a standardized command for intent recognition
                    command = f"create file {filename}"
                    if location:
                        command += f" in {location}"
                    if content_type != "text":
                        command += f" with {content_type} content"
                    
                    parsed_intent = await self.intent_recognizer.parse_intent(command)
                    if parsed_intent:
                        result = await self.intent_recognizer.execute_intent(parsed_intent)
                        if result["success"]:
                            file_path = result.get("data", {}).get("path", "")
                            if file_path:
                                self.memory_manager.add_file_memory(
                                    file_path, 
                                    Path(file_path).suffix or "txt",
                                    original_message
                                )
                            return f"✅ Perfect! I've created {Path(file_path).name} for you. {analysis.get('suggested_response', 'The file is ready to use!')}"
            
            elif action_type == "open_file":
                # Handle file opening intelligently
                recent_files = memory_context.get('recent_files', [])
                
                if recent_files:
                    target_file = None
                    filename_hint = parameters.get("filename", "").lower()
                    
                    if filename_hint:
                        # Find specific file
                        for file_info in recent_files:
                            if filename_hint in file_info['filename'].lower():
                                target_file = file_info
                                break
                    else:
                        # Use most recent file
                        target_file = recent_files[0]
                    
                    if target_file:
                        try:
                            import os
                            os.startfile(target_file['path'])
                            
                            self.memory_manager.add_action('file_opened', {
                                'path': target_file['path'],
                                'filename': target_file['filename'],
                                'method': 'ai_command'
                            }, importance=4)
                            
                            return f"🚀 Opened {target_file['filename']} for you! {analysis.get('suggested_response', 'It should appear now.')}"
                        except Exception as e:
                            return f"❌ Couldn't open the file: {str(e)}"
                
                return "I don't have any recent files to open. Could you create a file first?"
            
            elif action_type == "launch_app":
                app_name = parameters.get("app_name", "")
                if app_name and self.intent_recognizer:
                    command = f"open {app_name}"
                    parsed_intent = await self.intent_recognizer.parse_intent(command)
                    if parsed_intent:
                        result = await self.intent_recognizer.execute_intent(parsed_intent)
                        if result["success"]:
                            return f"🎯 {result['message']} {analysis.get('suggested_response', 'Launching now!')}"
            
            elif action_type == "browser_search":
                browser = parameters.get("browser", "edge")
                query = parameters.get("query", "")
                if query and self.intent_recognizer:
                    # Direct call to browser search handler
                    result = await self.intent_recognizer._handle_browser_search(
                        self.automation, 
                        {"browser": browser, "query": query}
                    )
                    if result["success"]:
                        self.memory_manager.add_action('browser_search', {
                            'browser': browser,
                            'query': query,
                            'search_url': result.get('data', {}).get('search_url', '')
                        }, importance=3)
                        return f"🔍 {result['message']} {analysis.get('suggested_response', 'Search results should appear shortly!')}"
            
            elif action_type == "whatsapp_message":
                contact = parameters.get("contact", "")
                message_text = parameters.get("message", "")
                if contact and self.intent_recognizer:
                    # Direct call to WhatsApp message handler
                    result = await self.intent_recognizer._handle_whatsapp_message(
                        self.automation, 
                        {"contact": contact, "message": message_text}
                    )
                    if result["success"]:
                        self.memory_manager.add_action('whatsapp_message', {
                            'contact': contact,
                            'message': message_text,
                            'status': 'prepared'
                        }, importance=4)
                        return f"💬 {result['message']} {analysis.get('suggested_response', 'WhatsApp is ready for your message!')}"
            
            elif action_type == "email_compose":
                recipient = parameters.get("recipient", "")
                subject = parameters.get("subject", "")
                message_text = parameters.get("message", "")
                if recipient and self.intent_recognizer:
                    # Direct call to email compose handler
                    result = await self.intent_recognizer._handle_email_compose(
                        self.automation, 
                        {"recipient": recipient, "subject": subject, "message": message_text}
                    )
                    if result["success"]:
                        self.memory_manager.add_action('email_compose', {
                            'recipient': recipient,
                            'subject': subject,
                            'message': message_text,
                            'status': 'composed'
                        }, importance=4)
                        return f"📧 {result['message']} {analysis.get('suggested_response', 'Email composer is ready!')}"
            
            elif action_type == "telegram_message":
                contact = parameters.get("contact", "")
                message_text = parameters.get("message", "")
                if contact and self.intent_recognizer:
                    result = await self.intent_recognizer._handle_telegram_message(
                        self.automation, 
                        {"contact": contact, "message": message_text}
                    )
                    if result["success"]:
                        self.memory_manager.add_action('telegram_message', {
                            'contact': contact,
                            'message': message_text,
                            'status': 'prepared'
                        }, importance=4)
                        return f"📱 {result['message']} {analysis.get('suggested_response', 'Telegram is ready for your message!')}"

            elif action_type == "discord_message":
                channel_or_user = parameters.get("channel_or_user", "")
                message_text = parameters.get("message", "")
                if channel_or_user and self.intent_recognizer:
                    result = await self.intent_recognizer._handle_discord_message(
                        self.automation, 
                        {"channel_or_user": channel_or_user, "message": message_text}
                    )
                    if result["success"]:
                        self.memory_manager.add_action('discord_message', {
                            'channel_or_user': channel_or_user,
                            'message': message_text,
                            'status': 'prepared'
                        }, importance=4)
                        return f"🎮 {result['message']} {analysis.get('suggested_response', 'Discord is ready for your message!')}"

            elif action_type == "file_operations":
                operation = parameters.get("operation", "")
                source = parameters.get("source", "")
                destination = parameters.get("destination", "")
                filename = parameters.get("filename", "")
                if operation and self.intent_recognizer:
                    result = await self.intent_recognizer._handle_file_operations(
                        self.automation, 
                        {"operation": operation, "source": source, "destination": destination, "filename": filename}
                    )
                    if result["success"]:
                        self.memory_manager.add_action('file_operation', {
                            'operation': operation,
                            'source': source,
                            'destination': destination,
                            'filename': filename
                        }, importance=3)
                        return f"📁 {result['message']} {analysis.get('suggested_response', 'File operation completed!')}"

            elif action_type == "media_control":
                action = parameters.get("action", "")
                app = parameters.get("app", "")
                media = parameters.get("media", "")
                if action and self.intent_recognizer:
                    result = await self.intent_recognizer._handle_media_control(
                        self.automation, 
                        {"action": action, "app": app, "media": media}
                    )
                    if result["success"]:
                        self.memory_manager.add_action('media_control', {
                            'action': action,
                            'app': app,
                            'media': media
                        }, importance=2)
                        return f"🎵 {result['message']} {analysis.get('suggested_response', 'Media control executed!')}"

            elif action_type == "screenshot":
                if self.intent_recognizer:
                    parsed_intent = await self.intent_recognizer.parse_intent("take screenshot")
                    if parsed_intent:
                        result = await self.intent_recognizer.execute_intent(parsed_intent)
                        if result["success"]:
                            return f"📸 {result['message']} {analysis.get('suggested_response', 'Screenshot captured!')}"
            
            # If we get here, action execution failed
            return None
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return None
    
    async def _generate_intelligent_response(self, message: str, memory_context: dict, context: Optional[dict] = None) -> str:
        """Generate an intelligent, context-aware response using Gemini"""
        
        # Build comprehensive context for Gemini
        context_prompt = f"""You are an advanced Windows AI assistant with desktop automation capabilities. You are helpful, intelligent, and proactive.

User message: "{message}"

My capabilities include:
- Creating and managing files (HTML, Python, text, etc.)
- Taking screenshots and desktop automation  
- Launching applications and managing windows
- System monitoring and information
- Running Python code safely
- Having natural conversations

Current context:"""

        if memory_context.get('recent_files'):
            context_prompt += f"\n\nRecent files I created:"
            for file_info in memory_context['recent_files'][:3]:
                context_prompt += f"\n- {file_info['filename']} ({file_info['type']}) at {file_info['path']}"
                context_prompt += f"\n  Created for: {file_info['intent']}"

        if memory_context.get('recent_actions'):
            context_prompt += f"\n\nRecent actions I performed:"
            for action in memory_context['recent_actions'][-3:]:
                context_prompt += f"\n- {action['action']}: {action['details']}"

        context_prompt += f"""

Instructions for response:
- Be conversational and helpful, not robotic
- If user wants me to do something I can do, offer to do it immediately
- Use my memory and context to understand references like "that file", "open it", etc.
- Be proactive but ask for clarification if truly ambiguous
- Show personality and intelligence in your responses
- If I can perform an action, offer to do it rather than just explaining how

Respond naturally and helpfully to the user's message."""

        try:
            response = await self.agent.process_message(context_prompt, context)
            return response
        except Exception as e:
            logger.error(f"Intelligent response generation failed: {e}")
            return "I apologize, but I'm having trouble processing your request right now. Could you try rephrasing it?"
    
    async def _handle_contextual_commands(self, message: str, memory_context: dict) -> Optional[str]:
        """Handle commands that depend on conversation context/memory"""
        message_lower = message.lower().strip()
        recent_files = memory_context.get('recent_files', [])
        
        # Handle file opening requests - be VERY aggressive about detecting these
        open_triggers = ['open', 'show', 'view', 'launch', 'start', 'run', 'execute', 'display']
        reference_words = ['that', 'the', 'it', 'this', 'file', 'html', 'document', 'webpage', 'page']
        
        # Check if this is an open command
        has_open_trigger = any(trigger in message_lower for trigger in open_triggers)
        has_reference = any(ref in message_lower for ref in reference_words)
        
        # Super simple commands like "open this", "show it", "launch that"
        if has_open_trigger and (has_reference or len(message_lower.split()) <= 3):
            if recent_files:
                latest_file = recent_files[0]
                file_path = latest_file['path']
                
                # Try to open the file immediately
                try:
                    import subprocess
                    import os
                    
                    # Use Windows start command to open with default application
                    if os.name == 'nt':  # Windows
                        os.startfile(file_path)
                    else:
                        subprocess.run(['start', file_path], shell=True)
                    
                    # Update memory that we opened this file
                    self.memory_manager.add_action('file_opened', {
                        'path': file_path,
                        'filename': latest_file['filename'],
                        'method': 'context_command'
                    }, importance=3)
                    
                    return f"✅ Opened {latest_file['filename']} for you! It should appear now."
                except Exception as e:
                    return f"❌ Couldn't open the file: {str(e)}"
        
        # Handle specific filename mentions
        if has_open_trigger and recent_files:
            for file_info in recent_files:
                # Check if filename or extension is mentioned
                filename_parts = [
                    file_info['filename'].lower(),
                    file_info['filename'].lower().replace('.html', ''),
                    file_info['filename'].lower().replace('.txt', ''),
                    file_info['filename'].lower().replace('.py', '')
                ]
                
                if any(part in message_lower for part in filename_parts):
                    try:
                        import os
                        os.startfile(file_info['path'])
                        
                        # Update memory
                        self.memory_manager.add_action('file_opened', {
                            'path': file_info['path'],
                            'filename': file_info['filename'],
                            'method': 'filename_match'
                        }, importance=3)
                        
                        return f"✅ Opened {file_info['filename']} for you!"
                    except Exception as e:
                        return f"❌ Couldn't open {file_info['filename']}: {str(e)}"
        
        # Handle "show me" requests about recent files
        if any(phrase in message_lower for phrase in ['show me', 'what did', 'what files', 'recent']):
            recent_files = memory_context.get('recent_files', [])
            if recent_files:
                file_list = "\n".join([f"• {f['filename']} ({f['type']}) - {f['intent']}" for f in recent_files[:5]])
                return f"📁 Here are your recent files:\n{file_list}\n\nJust say 'open [filename]' to open any of them!"
        
        return None
    
    def _build_context_prompt(self, message: str, memory_context: dict) -> str:
        """Build a context-aware prompt for the AI"""
        context_parts = [message]
        
        # Add recent file context
        if memory_context.get('recent_files'):
            files_info = [f"{f['filename']} ({f['type']})" for f in memory_context['recent_files'][:3]]
            context_parts.append(f"\nRecently created files: {', '.join(files_info)}")
        
        # Add suggestions
        if memory_context.get('suggestions'):
            context_parts.append(f"\nContext: {'; '.join(memory_context['suggestions'])}")
        
        return " ".join(context_parts)
    
    async def _should_execute_as_action(self, message: str) -> bool:
        """Determine if the message is an action request that should be executed"""
        action_indicators = [
            "create", "make", "generate", "build", "write",
            "open", "launch", "start", "run",
            "take screenshot", "screenshot", "capture",
            "click", "type", "minimize", "close",
            "file", "folder", "document"
        ]
        
        # Check for action verbs and file/app related terms
        message_lower = message.lower()
        has_action_verb = any(verb in message_lower for verb in ["create", "make", "generate", "open", "launch", "take"])
        has_object = any(obj in message_lower for obj in ["file", "html", "document", "app", "application", "screenshot"])
        
        return has_action_verb and has_object
    
    @property
    def is_configured(self) -> bool:
        """Check if the agent is properly configured"""
        return (
            self.agent and 
            self.agent.is_configured and 
            self.automation is not None and
            self.intent_recognizer is not None
        )


def main():
    """Main application entry point"""
    try:
        # Setup logging
        setup_logging()
        logger.info("Starting Windows AI Agent")
        
        # Check configuration
        if not config.google_api_key:
            logger.error("Google API key not found. Please set GOOGLE_API_KEY in .env file")
            print("❌ Error: Google API key not found!")
            print("Please create a .env file and set GOOGLE_API_KEY=your_api_key_here")
            return 1
        
        # Initialize integrated agent (this will be used by the UI)
        integrated_agent = IntegratedWindowsAgent()
        logger.info("Integrated agent initialized")
        
        # Start GUI with integrated agent
        logger.info("Starting GUI application")
        exit_code = ui_main(integrated_agent)
        
        logger.info(f"Application exited with code {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Critical error: {e}")
        print(f"❌ Critical error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())