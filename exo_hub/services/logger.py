import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import traceback
from ..config import LOG_LEVEL, LOG_FILE, DEBUG

class CustomFormatter(logging.Formatter):
    """Custom formatter with color support and structured logging."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, use_color: bool = True, use_json: bool = False):
        self.use_color = use_color
        self.use_json = use_json
        
        if use_json:
            super().__init__()
        else:
            format_string = (
                "%(asctime)s | %(name)-20s | %(levelname)-8s | "
                "%(filename)s:%(lineno)d | %(message)s"
            )
            super().__init__(format_string, datefmt='%Y-%m-%d %H:%M:%S')
    
    def format(self, record):
        if self.use_json:
            return self._format_json(record)
        else:
            return self._format_text(record)
    
    def _format_json(self, record):
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)
    
    def _format_text(self, record):
        """Format log record as colored text."""
        formatted = super().format(record)
        
        if self.use_color and sys.stderr.isatty():
            level_color = self.COLORS.get(record.levelname, '')
            reset_color = self.COLORS['RESET']
            return f"{level_color}{formatted}{reset_color}"
        
        return formatted

class ExoStackLogger:
    """Centralized logging service for ExoStack."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up logging configuration."""
        # Create logs directory if it doesn't exist
        log_dir = Path(LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Console handler with color
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if DEBUG else logging.INFO)
        console_formatter = CustomFormatter(use_color=True, use_json=False)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = CustomFormatter(use_color=False, use_json=True)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_log_file = str(Path(LOG_FILE).with_suffix('.error.log'))
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
        
        # Set specific logger levels
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        
        # Log startup message
        logger = logging.getLogger(__name__)
        logger.info("ExoStack logging system initialized")
        logger.info(f"Log level: {LOG_LEVEL}")
        logger.info(f"Log file: {LOG_FILE}")
        logger.info(f"Debug mode: {DEBUG}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance."""
        return logging.getLogger(name)
    
    def log_request(self, request_id: str, method: str, path: str, 
                   client_ip: str, user_agent: str = None):
        """Log HTTP request."""
        logger = logging.getLogger('exo.requests')
        extra_fields = {
            'request_id': request_id,
            'method': method,
            'path': path,
            'client_ip': client_ip,
            'user_agent': user_agent
        }
        
        # Add extra fields to log record
        record = logger.makeRecord(
            logger.name, logging.INFO, '', 0,
            f"HTTP {method} {path} from {client_ip}",
            (), None
        )
        record.extra_fields = extra_fields
        logger.handle(record)
    
    def log_task_event(self, task_id: str, event: str, node_id: str = None, 
                      details: dict = None):
        """Log task-related events."""
        logger = logging.getLogger('exo.tasks')
        extra_fields = {
            'task_id': task_id,
            'event': event,
            'node_id': node_id,
            'details': details or {}
        }
        
        message = f"Task {event}: {task_id}"
        if node_id:
            message += f" on node {node_id}"
        
        record = logger.makeRecord(
            logger.name, logging.INFO, '', 0, message, (), None
        )
        record.extra_fields = extra_fields
        logger.handle(record)
    
    def log_node_event(self, node_id: str, event: str, details: dict = None):
        """Log node-related events."""
        logger = logging.getLogger('exo.nodes')
        extra_fields = {
            'node_id': node_id,
            'event': event,
            'details': details or {}
        }
        
        message = f"Node {event}: {node_id}"
        
        record = logger.makeRecord(
            logger.name, logging.INFO, '', 0, message, (), None
        )
        record.extra_fields = extra_fields
        logger.handle(record)
    
    def log_performance(self, operation: str, duration: float, 
                       metadata: dict = None):
        """Log performance metrics."""
        logger = logging.getLogger('exo.performance')
        extra_fields = {
            'operation': operation,
            'duration_seconds': duration,
            'metadata': metadata or {}
        }
        
        message = f"Operation {operation} took {duration:.3f}s"
        
        record = logger.makeRecord(
            logger.name, logging.INFO, '', 0, message, (), None
        )
        record.extra_fields = extra_fields
        logger.handle(record)
    
    def log_error(self, error: Exception, context: str = None, 
                 extra_data: dict = None):
        """Log errors with context."""
        logger = logging.getLogger('exo.errors')
        extra_fields = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'extra_data': extra_data or {}
        }
        
        message = f"Error in {context}: {error}" if context else f"Error: {error}"
        
        record = logger.makeRecord(
            logger.name, logging.ERROR, '', 0, message, (), None
        )
        record.extra_fields = extra_fields
        logger.handle(record)

# Global logger instance
logger_service = ExoStackLogger()

# Convenience functions
def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance."""
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    return logger_service.get_logger(name)

def log_request(request_id: str, method: str, path: str, client_ip: str, 
               user_agent: str = None):
    """Log HTTP request."""
    logger_service.log_request(request_id, method, path, client_ip, user_agent)

def log_task_event(task_id: str, event: str, node_id: str = None, 
                  details: dict = None):
    """Log task-related events."""
    logger_service.log_task_event(task_id, event, node_id, details)

def log_node_event(node_id: str, event: str, details: dict = None):
    """Log node-related events."""
    logger_service.log_node_event(node_id, event, details)

def log_performance(operation: str, duration: float, metadata: dict = None):
    """Log performance metrics."""
    logger_service.log_performance(operation, duration, metadata)

def log_error(error: Exception, context: str = None, extra_data: dict = None):
    """Log errors with context."""
    logger_service.log_error(error, context, extra_data)
