"""
Configuration management for Windows AI Agent
"""

import os
from typing import Any, Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv
import yaml
from loguru import logger


class Config:
    """Configuration manager for the Windows AI Agent"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or Path(__file__).parent.parent.parent
        self._load_environment()
        self._config_data = self._load_config_files()
        
    def _load_environment(self):
        """Load environment variables from .env file"""
        env_file = Path(self.config_path) / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"Loaded environment from {env_file}")
        else:
            logger.warning(f"No .env file found at {env_file}")
    
    def _load_config_files(self) -> Dict[str, Any]:
        """Load configuration from YAML files"""
        config_dir = Path(self.config_path) / "config"
        config_data = {}
        
        if config_dir.exists():
            for config_file in config_dir.glob("*.yaml"):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        config_data[config_file.stem] = data
                        logger.info(f"Loaded config from {config_file}")
                except Exception as e:
                    logger.error(f"Failed to load config {config_file}: {e}")
        
        return config_data
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with environment variable precedence"""
        # First check environment variables
        env_value = os.getenv(key.upper())
        if env_value is not None:
            return self._convert_type(env_value)
        
        # Then check config files
        for config_name, config_data in self._config_data.items():
            if key in config_data:
                return config_data[key]
        
        return default
    
    def _convert_type(self, value: str) -> Any:
        """Convert string environment variables to appropriate types"""
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False
        elif value.isdigit():
            return int(value)
        elif self._is_float(value):
            return float(value)
        else:
            return value
    
    def _is_float(self, value: str) -> bool:
        """Check if string can be converted to float"""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    @property
    def google_api_key(self) -> str:
        """Get Google API key"""
        return self.get("GOOGLE_API_KEY", "")
    
    @property
    def gemini_model(self) -> str:
        """Get Gemini model name"""
        return self.get("GEMINI_MODEL", "gemini-1.5-pro")
    
    @property
    def gemini_temperature(self) -> float:
        """Get Gemini temperature setting"""
        return float(self.get("GEMINI_TEMPERATURE", 0.7))
    
    @property
    def gemini_max_tokens(self) -> int:
        """Get Gemini max tokens"""
        return int(self.get("GEMINI_MAX_TOKENS", 8192))
    
    @property
    def debug_mode(self) -> bool:
        """Get debug mode setting"""
        return bool(self.get("DEBUG_MODE", False))
    
    @property
    def log_level(self) -> str:
        """Get logging level"""
        return self.get("LOG_LEVEL", "INFO")
    
    @property
    def enable_code_execution(self) -> bool:
        """Get code execution setting"""
        return bool(self.get("ENABLE_CODE_EXECUTION", True))
    
    @property
    def enable_desktop_automation(self) -> bool:
        """Get desktop automation setting"""
        return bool(self.get("ENABLE_DESKTOP_AUTOMATION", True))
    
    @property
    def max_conversation_history(self) -> int:
        """Get max conversation history"""
        return int(self.get("MAX_CONVERSATION_HISTORY", 100))
    
    @property
    def window_width(self) -> int:
        """Get window width"""
        return int(self.get("WINDOW_WIDTH", 1200))
    
    @property
    def window_height(self) -> int:
        """Get window height"""
        return int(self.get("WINDOW_HEIGHT", 800))
    
    @property
    def theme(self) -> str:
        """Get UI theme"""
        return self.get("THEME", "dark")
    
    @property
    def allowed_modules(self) -> List[str]:
        """Get allowed modules for code execution"""
        modules = self.get("ALLOWED_MODULES", "os,sys,math,datetime,json,re,random")
        if isinstance(modules, str):
            return [m.strip() for m in modules.split(",")]
        return modules
    
    @property
    def sandbox_timeout(self) -> int:
        """Get sandbox timeout in seconds"""
        return int(self.get("SANDBOX_TIMEOUT", 30))


# Global config instance
config = Config()