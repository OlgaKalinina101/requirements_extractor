"""Logging configuration for the application.

This module provides centralized logging setup with support for both
console and file output. Handles formatting, levels, and logger lifecycle.

Functions:
    setup_logger: Configure and return a logger with console and file handlers.
    get_logger: Retrieve an existing logger by name.
"""

# Standard library imports
import logging
import sys
from pathlib import Path
from typing import Optional, Union


def setup_logger(
    name: str = "pdf_requirements_extractor",
    log_file: Optional[Path] = None,
    level: Union[int, str] = logging.INFO,
    format_string: Optional[str] = None
) -> logging.Logger:
    """Set up and configure logger with console and optional file output.
    
    Creates a logger with formatted console output and optional file logging.
    Automatically creates log directory if needed. Removes existing handlers
    to prevent duplicate log entries.
    
    Args:
        name: Logger name for identification. Defaults to package name.
        log_file: Optional path to log file. If provided, creates file handler.
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) as int or string.
        format_string: Custom format string. If None, uses default format with
            timestamp, logger name, level, file location, and message.
    
    Returns:
        Configured logger instance ready for use.
        
    Example:
        >>> logger = setup_logger(
        ...     name="myapp",
        ...     log_file=Path("logs/app.log"),
        ...     level=logging.DEBUG
        ... )
        >>> logger.info("Application started")
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Default format with timestamp, name, level, location, and message
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )
    
    formatter = logging.Formatter(format_string)
    
    # Console handler - outputs to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log file specified)
    if log_file:
        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file handler with UTF-8 encoding
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "pdf_requirements_extractor") -> logging.Logger:
    """Get existing logger or create a new one with default settings.
    
    Retrieves a logger by name. If the logger doesn't exist, creates a
    new one with Python's default configuration.
    
    Args:
        name: Logger name to retrieve. Defaults to package name.
    
    Returns:
        Logger instance (existing or newly created).
        
    Example:
        >>> logger = get_logger("myapp")
        >>> logger.info("Using existing logger")
    """
    return logging.getLogger(name)
