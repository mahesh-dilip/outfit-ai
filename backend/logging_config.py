"""
Logging Configuration for Outfit AI
Provides structured logging with JSON format for better log aggregation
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
import os


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class StandardFormatter(logging.Formatter):
    """
    Standard human-readable formatter for development
    """
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging(
    level: str = None,
    json_format: bool = False,
    log_file: str = None
) -> None:
    """
    Configure logging for the application
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (True) or standard format (False)
        log_file: Optional file path for logging to file
    """
    # Get level from environment or use default
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    
    # Get format preference from environment
    if json_format is None:
        json_format = os.getenv("LOG_FORMAT", "standard").lower() == "json"
    
    # Choose formatter
    formatter = JSONFormatter() if json_format else StandardFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Silence noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("vertexai").setLevel(logging.ERROR)
    logging.getLogger("alembic").setLevel(logging.WARNING)
    
    root_logger.info(
        f"Logging configured: level={level}, json_format={json_format}, file={log_file or 'None'}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module
    
    Args:
        name: Usually __name__ of the calling module
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Custom log levels for specific events
LOG_EVENTS = {
    "AUTH_SUCCESS": "User authenticated successfully",
    "AUTH_FAILURE": "Authentication failed",
    "ITEM_CREATED": "Wardrobe item created",
    "ITEM_UPDATED": "Wardrobe item updated",
    "ITEM_DELETED": "Wardrobe item deleted",
    "ITEMS_BULK_DELETED": "Wardrobe items bulk deleted",
    "ITEM_WORN": "Wardrobe item marked as worn",
    "RECOMMENDATION_GENERATED": "Outfit recommendation generated",
    "RECOMMENDATION_FAILED": "Outfit recommendation failed",
    "GCS_UPLOAD_SUCCESS": "Image uploaded to GCS",
    "GCS_UPLOAD_FAILED": "GCS upload failed",
    "VECTOR_INDEX_UPDATED": "Vector index updated with new item",
    "DATABASE_ERROR": "Database operation failed",
}


def log_event(logger: logging.Logger, event_name: str, **kwargs) -> None:
    """
    Log a specific event with structured data
    
    Args:
        logger: Logger instance
        event_name: Event name from LOG_EVENTS
        **kwargs: Additional context data
    """
    message = LOG_EVENTS.get(event_name, event_name)
    extra_fields = {
        "event": event_name,
        **kwargs
    }
    
    # Create a LogRecord with extra fields
    logger.info(message, extra={"extra_fields": extra_fields})

