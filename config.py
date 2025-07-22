"""
Configuration management for RabbitMQ LLM Chat Platform.
Provides centralized, secure configuration handling.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Centralized configuration management with environment variable support."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration from environment variables and optional config file.
        
        Args:
            config_file: Optional path to JSON configuration file
        """
        self._config: Dict[str, Any] = {}
        self._load_defaults()
        
        if config_file and Path(config_file).exists():
            self._load_from_file(config_file)
        
        self._load_from_environment()
    
    def _load_defaults(self) -> None:
        """Load default configuration values."""
        self._config = {
            'rabbitmq': {
                'host': 'localhost',
                'port': 5672,
                'username': 'guest',
                'password': 'guest',
                'virtual_host': '/',
                'exchange': 'llm_chat',
                'queue_prefix': 'chat_room_',
                'connection_timeout': 30,
                'heartbeat': 600
            },
            'web': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': False,
                'secret_key': 'dev-key-change-in-production'
            },
            'database': {
                'uri': 'sqlite:///app.db',
                'track_modifications': False
            },
            'llm': {
                'max_tokens': 1000,
                'temperature': 0.7,
                'timeout': 30,
                'providers': {
                    'openai': {
                        'api_key': '',
                        'models': ['gpt-4', 'gpt-3.5-turbo']
                    },
                    'anthropic': {
                        'api_key': '',
                        'models': ['claude-3-sonnet', 'claude-3-haiku']
                    }
                }
            },
            'security': {
                'rate_limit': {
                    'enabled': True,
                    'requests_per_minute': 60,
                    'burst': 10
                },
                'cors': {
                    'enabled': True,
                    'origins': ['http://localhost:3000', 'http://127.0.0.1:3000']
                }
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'app.log',
                'max_bytes': 10485760,  # 10MB
                'backup_count': 5
            }
        }
    
    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                self._deep_update(self._config, file_config)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load config file {config_file}: {e}")
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            # RabbitMQ
            'RABBITMQ_HOST': ('rabbitmq', 'host'),
            'RABBITMQ_PORT': ('rabbitmq', 'port'),
            'RABBITMQ_USERNAME': ('rabbitmq', 'username'),
            'RABBITMQ_PASSWORD': ('rabbitmq', 'password'),
            'RABBITMQ_VHOST': ('rabbitmq', 'virtual_host'),
            'RABBITMQ_EXCHANGE': ('rabbitmq', 'exchange'),
            
            # Web
            'WEB_HOST': ('web', 'host'),
            'WEB_PORT': ('web', 'port'),
            'WEB_DEBUG': ('web', 'debug'),
            'SECRET_KEY': ('web', 'secret_key'),
            
            # Database
            'DATABASE_URI': ('database', 'uri'),
            
            # LLM APIs
            'OPENAI_API_KEY': ('llm', 'providers', 'openai', 'api_key'),
            'ANTHROPIC_API_KEY': ('llm', 'providers', 'anthropic', 'api_key'),
            'CLAUDE_API_KEY': ('llm', 'providers', 'anthropic', 'api_key'),  # Alias
            
            # Logging
            'LOG_LEVEL': ('logging', 'level'),
            'LOG_FILE': ('logging', 'file'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(config_path, self._convert_value(value))
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
        """Deep update of nested dictionaries."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _set_nested_value(self, path: tuple, value: Any) -> None:
        """Set a nested dictionary value using a tuple path."""
        current = self._config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', '1', 'yes', 'on'):
            return True
        elif value.lower() in ('false', '0', 'no', 'off'):
            return False
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def get(self, *path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            *path: Configuration path (e.g., 'rabbitmq', 'host')
            default: Default value if path not found
            
        Returns:
            Configuration value or default
        """
        current = self._config
        try:
            for key in path:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def get_rabbitmq_config(self) -> Dict[str, Any]:
        """Get RabbitMQ connection configuration."""
        return self._config['rabbitmq'].copy()
    
    def get_web_config(self) -> Dict[str, Any]:
        """Get web server configuration."""
        return self._config['web'].copy()
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self._config['database'].copy()
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self._config['llm'].copy()
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self._config['logging'].copy()
    
    def validate(self) -> list:
        """
        Validate configuration and return list of issues.
        
        Returns:
            List of validation error messages
        """
        issues = []
        
        # Check for production-ready secret key
        if self.get('web', 'secret_key') == 'dev-key-change-in-production':
            issues.append("SECRET_KEY must be changed for production use")
        
        # Check for default RabbitMQ credentials
        if (self.get('rabbitmq', 'username') == 'guest' and 
            self.get('rabbitmq', 'password') == 'guest'):
            issues.append("Default RabbitMQ credentials should be changed for production")
        
        # Check for missing API keys
        openai_key = self.get('llm', 'providers', 'openai', 'api_key')
        anthropic_key = self.get('llm', 'providers', 'anthropic', 'api_key')
        
        if not openai_key and not anthropic_key:
            issues.append("At least one LLM provider API key should be configured")
        
        return issues


# Global configuration instance
config = Config()