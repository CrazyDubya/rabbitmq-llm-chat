"""
Centralized logging configuration for RabbitMQ LLM Chat Platform.
Provides structured logging with proper formatting and rotation.
"""

import logging
import logging.handlers
import sys
from typing import Optional
from pathlib import Path

from config import config


class Logger:
    """Centralized logging management."""
    
    _initialized = False
    _loggers = {}
    
    @classmethod
    def setup_logging(cls, log_level: Optional[str] = None) -> None:
        """
        Setup global logging configuration.
        
        Args:
            log_level: Override default log level
        """
        if cls._initialized:
            return
        
        log_config = config.get_logging_config()
        level = log_level or log_config['level']
        
        # Create logs directory if it doesn't exist
        log_file = log_config['file']
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper()))
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=log_config['max_bytes'],
                backupCount=log_config['backup_count']
            )
            file_formatter = logging.Formatter(log_config['format'])
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(getattr(logging, level.upper()))
            root_logger.addHandler(file_handler)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get logger instance for given name.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Logger instance
        """
        if not cls._initialized:
            cls.setup_logging()
        
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        
        return cls._loggers[name]


# Convenience function for getting logger
def get_logger(name: str = __name__) -> logging.Logger:
    """Get logger instance."""
    return Logger.get_logger(name)


# Setup logging on import
Logger.setup_logging()