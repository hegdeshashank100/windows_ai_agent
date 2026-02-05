"""
Windows Desktop Automation Manager
"""

import time
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import json
import base64
from io import BytesIO

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("Warning: pyautogui not available - GUI automation disabled")

try:
    import win32gui
    import win32con
    import win32process
    WIN32_AVAILABLE = True
except ImportError as e:
    WIN32_AVAILABLE = False
    win32gui = None
    win32con = None
    win32process = None
    print(f"Warning: win32 modules not available - window management disabled: {e}")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available - process management disabled")

try:
    from PIL import Image
    import cv2
    import numpy as np
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    print("Warning: Image processing libraries not available")

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    """Information about a window"""
    hwnd: int
    title: str
    class_name: str
    rect: Tuple[int, int, int, int]  # left, top, right, bottom
    is_visible: bool
    is_active: bool
    process_name: str


@dataclass 
class ScreenRegion:
    """Screen region coordinates"""
    x: int
    y: int
    width: int
    height: int


class WindowsAutomation:
    """Windows desktop automation and control"""
    
    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode
        self.last_screenshot = None
        self.last_screenshot_time = 0
        
        # Check dependencies
        self.pyautogui_available = PYAUTOGUI_AVAILABLE
        self.win32_available = WIN32_AVAILABLE
        self.psutil_available = PSUTIL_AVAILABLE
        
        # Configure pyautogui for safety
        if self.pyautogui_available:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
        
        logger.info(f"Windows automation initialized (safe_mode: {safe_mode})")
        logger.info(f"Dependencies - PyAutoGUI: {self.pyautogui_available}, Win32: {self.win32_available}, PSUtil: {self.psutil_available}")
    
    # Screenshot and Image Analysis
    
    def take_screenshot(self, region: Optional[ScreenRegion] = None, save_path: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot of the screen or region"""
        if not self.pyautogui_available:
            return {"success": False, "error": "PyAutoGUI not available for screenshots"}
        
        try:
            if region:
                screenshot = pyautogui.screenshot(region=(region.x, region.y, region.width, region.height))
            else:
                screenshot = pyautogui.screenshot()
            
            self.last_screenshot = screenshot
            self.last_screenshot_time = time.time()
            
            result = {
                "success": True,
                "timestamp": self.last_screenshot_time,
                "size": screenshot.size,
                "format": "PNG"
            }
            
            if save_path:
                # Ensure directory exists
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                screenshot.save(save_path)
                result["saved_path"] = save_path
                logger.info(f"Screenshot saved to {save_path}")
            else:
                # Convert to base64 for embedding
                buffer = BytesIO()
                screenshot.save(buffer, format="PNG")
                result["image_data"] = base64.b64encode(buffer.getvalue()).decode()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return {"success": False, "error": str(e)}
    
    def find_image_on_screen(self, template_path: str, confidence: float = 0.8) -> Optional[Dict[str, Any]]:
        """Find an image template on the screen"""
        if not self.pyautogui_available:
            return {"found": False, "error": "PyAutoGUI not available for image recognition"}
        
        try:
            # Check if template file exists
            if not Path(template_path).exists():
                return {"found": False, "error": f"Template image not found: {template_path}"}
            
            location = pyautogui.locateOnScreen(template_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                return {
                    "found": True,
                    "location": {
                        "left": location.left,
                        "top": location.top,
                        "width": location.width,
                        "height": location.height
                    },
                    "center": {"x": center.x, "y": center.y}
                }
            return {"found": False}
            
        except Exception as e:
            logger.error(f"Error finding image: {e}")
            return {"found": False, "error": str(e)}
    
    # Mouse and Keyboard Control
    
    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
        """Click at specified coordinates"""
        if not self.pyautogui_available:
            return {"success": False, "error": "PyAutoGUI not available for mouse control"}
        
        try:
            if self.safe_mode and not self._is_safe_coordinate(x, y):
                return {"success": False, "error": "Coordinate outside safe area"}
            
            # Validate button parameter
            valid_buttons = ["left", "right", "middle"]
            if button not in valid_buttons:
                return {"success": False, "error": f"Invalid button: {button}. Must be one of {valid_buttons}"}
            
            # Validate clicks parameter
            if clicks < 1 or clicks > 10:
                return {"success": False, "error": "Clicks must be between 1 and 10"}
            
            pyautogui.click(x, y, clicks=clicks, button=button)
            logger.info(f"Clicked at ({x}, {y}) with {button} button, {clicks} clicks")
            
            return {"success": True, "action": f"clicked at ({x}, {y})"}
            
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return {"success": False, "error": str(e)}
    
    def type_text(self, text: str, interval: float = 0.01) -> Dict[str, Any]:
        """Type text with specified interval between keystrokes"""
        if not self.pyautogui_available:
            return {"success": False, "error": "PyAutoGUI not available for keyboard input"}
        
        try:
            # Validate input
            if not isinstance(text, str):
                return {"success": False, "error": "Text must be a string"}
            
            if len(text) > 10000:  # Reasonable limit
                return {"success": False, "error": "Text too long (max 10,000 characters)"}
            
            if interval < 0 or interval > 1:
                return {"success": False, "error": "Interval must be between 0 and 1 seconds"}
            
            pyautogui.write(text, interval=interval)
            logger.info(f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            return {"success": True, "text_length": len(text)}
            
        except Exception as e:
            logger.error(f"Type text failed: {e}")
            return {"success": False, "error": str(e)}
    
    def press_key(self, key: str) -> Dict[str, Any]:
        """Press a single key or key combination"""
        if not self.pyautogui_available:
            return {"success": False, "error": "PyAutoGUI not available for keyboard input"}
        
        try:
            # Validate key parameter
            if not key or not isinstance(key, str):
                return {"success": False, "error": "Key must be a non-empty string"}
            
            # List of safe keys (you can expand this)
            safe_keys = [
                'enter', 'space', 'tab', 'backspace', 'delete', 'esc', 'up', 'down', 'left', 'right',
                'home', 'end', 'pageup', 'pagedown', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8',
                'f9', 'f10', 'f11', 'f12', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k',
                'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'
            ]
            
            key_lower = key.lower()
            if self.safe_mode and key_lower not in safe_keys:
                return {"success": False, "error": f"Key '{key}' not allowed in safe mode"}
            
            pyautogui.press(key)
            logger.info(f"Pressed key: {key}")
            
            return {"success": True, "key": key}
            
        except Exception as e:
            logger.error(f"Key press failed: {e}")
            return {"success": False, "error": str(e)}
    
    def hotkey(self, *keys) -> Dict[str, Any]:
        """Press a combination of keys simultaneously"""
        if not self.pyautogui_available:
            return {"success": False, "error": "PyAutoGUI not available for keyboard input"}
        
        try:
            # Validate keys
            if not keys:
                return {"success": False, "error": "No keys provided"}
            
            if len(keys) > 4:  # Reasonable limit for key combinations
                return {"success": False, "error": "Too many keys in combination (max 4)"}
            
            for key in keys:
                if not isinstance(key, str) or not key:
                    return {"success": False, "error": "All keys must be non-empty strings"}
            
            # Safe key combinations
            safe_modifiers = ['ctrl', 'alt', 'shift', 'win', 'cmd']
            if self.safe_mode:
                # Allow common safe combinations
                keys_lower = [k.lower() for k in keys]
                has_modifier = any(mod in keys_lower for mod in safe_modifiers)
                if not has_modifier and len(keys) > 1:
                    return {"success": False, "error": "Multi-key combinations require a modifier in safe mode"}
            
            pyautogui.hotkey(*keys)
            logger.info(f"Pressed hotkey: {'+'.join(keys)}")
            
            return {"success": True, "hotkey": "+".join(keys)}
            
        except Exception as e:
            logger.error(f"Hotkey failed: {e}")
            return {"success": False, "error": str(e)}
    
    def key_combination(self, keys: List[str]) -> Dict[str, Any]:
        """Press a combination of keys (alias for hotkey)"""
        return self.hotkey(*keys)
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 1.0) -> Dict[str, Any]:
        """Drag from start coordinates to end coordinates"""
        if not self.pyautogui_available:
            return {"success": False, "error": "PyAutoGUI not available for drag operations"}
        
        try:
            # Validate coordinates
            screen_width, screen_height = pyautogui.size()
            
            if not (0 <= start_x <= screen_width and 0 <= start_y <= screen_height):
                return {"success": False, "error": f"Start coordinates ({start_x}, {start_y}) out of screen bounds"}
            
            if not (0 <= end_x <= screen_width and 0 <= end_y <= screen_height):
                return {"success": False, "error": f"End coordinates ({end_x}, {end_y}) out of screen bounds"}
            
            # Validate duration
            if duration < 0 or duration > 10:
                return {"success": False, "error": "Duration must be between 0 and 10 seconds"}
            
            # Check for reasonable drag distance (prevent accidental large moves)
            drag_distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
            
            if self.safe_mode:
                if not (self._is_safe_coordinate(start_x, start_y) and self._is_safe_coordinate(end_x, end_y)):
                    return {"success": False, "error": "Coordinates outside safe area"}
                
                # Additional safe mode limits
                if drag_distance > 200:
                    return {"success": False, "error": "Large drag operations disabled in safe mode"}
            
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
            logger.info(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            
            return {"success": True, "start": (start_x, start_y), "end": (end_x, end_y)}
            
        except Exception as e:
            logger.error(f"Drag failed: {e}")
            return {"success": False, "error": str(e)}
    
    # Window Management
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active window"""
        if not self.win32_available:
            logger.warning("Win32 API not available for window operations")
            return None
        
        try:
            hwnd = win32gui.GetForegroundWindow()
            return self._get_window_info(hwnd)
            
        except Exception as e:
            logger.error(f"Failed to get active window: {e}")
            return None
    
    def get_all_windows(self) -> List[WindowInfo]:
        """Get information about all visible windows"""
        if not self.win32_available:
            logger.warning("Win32 API not available for window operations")
            return []
        
        windows = []
        
        def enum_windows_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                window_info = self._get_window_info(hwnd)
                if window_info and window_info.title:
                    windows.append(window_info)
            return True
        
        try:
            win32gui.EnumWindows(enum_windows_callback, None)
            logger.info(f"Found {len(windows)} visible windows")
            return windows
            
        except Exception as e:
            logger.error(f"Failed to enumerate windows: {e}")
            return []
    
    def find_window(self, title_pattern: str = None, class_name: str = None) -> List[WindowInfo]:
        """Find windows matching title pattern or class name"""
        if not self.win32_available:
            logger.warning("Win32 API not available for window operations")
            return []
        
        # Input validation
        if not title_pattern and not class_name:
            logger.warning("No search criteria provided for window search")
            return []
        
        if title_pattern and not isinstance(title_pattern, str):
            logger.error("Title pattern must be a string")
            return []
        
        if class_name and not isinstance(class_name, str):
            logger.error("Class name must be a string")
            return []
        
        matching_windows = []
        all_windows = self.get_all_windows()
        
        for window in all_windows:
            match = True
            
            if title_pattern and title_pattern.lower() not in window.title.lower():
                match = False
            
            if class_name and class_name.lower() != window.class_name.lower():
                match = False
            
            if match:
                matching_windows.append(window)
        
        logger.info(f"Found {len(matching_windows)} windows matching criteria")
        return matching_windows
    
    def activate_window(self, hwnd: int) -> Dict[str, Any]:
        """Activate (bring to front) a window"""
        if not self.win32_available:
            return {"success": False, "error": "Win32 API not available for window operations"}
        
        # Input validation
        if not isinstance(hwnd, int) or hwnd <= 0:
            return {"success": False, "error": "Invalid window handle"}
        
        try:
            # Check if window exists
            if not win32gui.IsWindow(hwnd):
                return {"success": False, "error": "Window no longer exists"}
            
            win32gui.SetForegroundWindow(hwnd)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            logger.info(f"Activated window with handle {hwnd}")
            return {"success": True, "hwnd": hwnd}
            
        except Exception as e:
            logger.error(f"Failed to activate window {hwnd}: {e}")
            return {"success": False, "error": str(e)}
    
    def minimize_window(self, hwnd: int) -> Dict[str, Any]:
        """Minimize a window"""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            
            logger.info(f"Minimized window with handle {hwnd}")
            return {"success": True, "hwnd": hwnd}
            
        except Exception as e:
            logger.error(f"Failed to minimize window: {e}")
            return {"success": False, "error": str(e)}
    
    def close_window(self, hwnd: int) -> Dict[str, Any]:
        """Close a window"""
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            
            logger.info(f"Sent close message to window {hwnd}")
            return {"success": True, "hwnd": hwnd}
            
        except Exception as e:
            logger.error(f"Failed to close window: {e}")
            return {"success": False, "error": str(e)}
    
    # Application Management
    
    def launch_application(self, path: str, args: List[str] = None) -> Dict[str, Any]:
        """Launch an application"""
        try:
            cmd = [path]
            if args:
                cmd.extend(args)
            
            process = subprocess.Popen(cmd, shell=True)
            
            logger.info(f"Launched application: {path}")
            return {
                "success": True,
                "pid": process.pid,
                "path": path
            }
            
        except Exception as e:
            logger.error(f"Failed to launch application: {e}")
            return {"success": False, "error": str(e)}
    
    def get_running_processes(self) -> List[Dict[str, Any]]:
        """Get list of running processes"""
        if not self.psutil_available:
            logger.warning("psutil not available for process operations")
            return []
        
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': proc.info['cpu_percent'] or 0.0,
                        'memory_mb': round(proc.info['memory_info'].rss / 1024 / 1024, 2) if proc.info['memory_info'] else 0.0
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            logger.info(f"Retrieved {len(processes)} running processes")
            return processes
            
        except Exception as e:
            logger.error(f"Failed to get processes: {e}")
            return []
    
    def kill_process(self, pid: int) -> Dict[str, Any]:
        """Kill a process by PID"""
        if not self.psutil_available:
            return {"success": False, "error": "psutil not available for process operations"}
        
        # Input validation
        if not isinstance(pid, int) or pid <= 0:
            return {"success": False, "error": "Invalid process ID"}
        
        try:
            # Check if process exists
            if not psutil.pid_exists(pid):
                return {"success": False, "error": f"Process {pid} does not exist"}
            
            process = psutil.Process(pid)
            process_name = process.name()
            
            if self.safe_mode:
                # Don't allow killing critical system processes
                critical_processes = ['explorer.exe', 'winlogon.exe', 'csrss.exe', 'smss.exe', 'wininit.exe', 'lsass.exe']
                if process_name.lower() in [p.lower() for p in critical_processes]:
                    return {"success": False, "error": f"Cannot kill critical system process: {process_name}"}
            
            process.terminate()
            
            logger.info(f"Terminated process {process_name} with PID {pid}")
            return {"success": True, "pid": pid, "name": process_name}
            
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process {pid} no longer exists"}
        except psutil.AccessDenied:
            return {"success": False, "error": f"Access denied to kill process {pid}"}
        except Exception as e:
            logger.error(f"Failed to kill process: {e}")
            return {"success": False, "error": str(e)}
    
    # System Information
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions"""
        if not self.pyautogui_available:
            logger.warning("PyAutoGUI not available for screen info")
            return (1920, 1080)  # Fallback default
        
        try:
            return pyautogui.size()
        except Exception as e:
            logger.error(f"Failed to get screen size: {e}")
            return (1920, 1080)  # Fallback default
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        if not self.pyautogui_available:
            logger.warning("PyAutoGUI not available for mouse position")
            return (0, 0)  # Fallback default
        
        try:
            return pyautogui.position()
        except Exception as e:
            logger.error(f"Failed to get mouse position: {e}")
            return (0, 0)  # Fallback default
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        if not self.psutil_available:
            logger.warning("psutil not available for system metrics")
            return {"error": "System metrics not available"}
        
        try:
            # Get system drive (usually C: on Windows)
            import os
            system_drive = os.getenv('SystemDrive', 'C:') + '\\'
            
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),  # Shorter interval for responsiveness
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent
                },
                "disk": {
                    "total": psutil.disk_usage(system_drive).total,
                    "free": psutil.disk_usage(system_drive).free,
                    "percent": psutil.disk_usage(system_drive).percent
                }
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"error": f"System metrics failed: {str(e)}"}
    
    # Utility Methods
    
    def _get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        """Get detailed information about a window"""
        if not self.win32_available:
            return None
        
        try:
            if not win32gui.IsWindow(hwnd):
                return None
            
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            is_visible = win32gui.IsWindowVisible(hwnd)
            is_active = win32gui.GetForegroundWindow() == hwnd
            
            # Get process name - only if psutil is available
            process_name = "Unknown"
            if self.psutil_available:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    process_name = process.name()
                except:
                    process_name = "Unknown"
            
            return WindowInfo(
                hwnd=hwnd,
                title=title,
                class_name=class_name,
                rect=rect,
                is_visible=is_visible,
                is_active=is_active,
                process_name=process_name
            )
            
        except Exception as e:
            logger.error(f"Failed to get window info for {hwnd}: {e}")
            return None
    
    def _is_safe_coordinate(self, x: int, y: int) -> bool:
        """Check if coordinates are in a safe area (not system critical areas)"""
        if not self.safe_mode:
            return True
        
        screen_width, screen_height = self.get_screen_size()
        
        # Avoid taskbar area (bottom 40 pixels)
        if y > screen_height - 40:
            return False
        
        # Avoid top system area (top 10 pixels)
        if y < 10:
            return False
        
        # Ensure coordinates are on screen
        if x < 0 or x > screen_width or y < 0 or y > screen_height:
            return False
        
        return True
    
    def set_safe_mode(self, enabled: bool):
        """Enable or disable safe mode"""
        self.safe_mode = enabled
        logger.info(f"Safe mode {'enabled' if enabled else 'disabled'}")
    
    def wait(self, seconds: float):
        """Wait for specified number of seconds"""
        time.sleep(seconds)
        
    def get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
        """Get RGB color of pixel at coordinates"""
        try:
            return pyautogui.pixel(x, y)
        except Exception as e:
            logger.error(f"Failed to get pixel color: {e}")
            return (0, 0, 0)