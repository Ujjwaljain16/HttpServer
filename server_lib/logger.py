"""
Detailed logging module for the HTTP server.

Provides consistent, timestamped logging with thread status tracking
and optional JSON output to files.
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager


class ServerLogger:
    """Enhanced logger for the HTTP server with custom formatting and thread tracking."""
    
    def __init__(self, name: str = "server", log_file: Optional[str] = None, 
                 json_log_file: Optional[str] = None, level: int = logging.INFO):
        """Initialize the server logger.
        
        Args:
            name: Logger name
            log_file: Optional file path for text logs
            json_log_file: Optional file path for JSON logs
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.name = name
        self.log_file = log_file
        self.json_log_file = json_log_file
        self.level = level
        
        # Thread tracking
        self._active_threads: Dict[str, Dict[str, Any]] = {}
        self._thread_lock = threading.Lock()
        
        # Setup logger
        self._setup_logger()
        
        # JSON log file handle
        self._json_file_handle = None
        if json_log_file:
            self._setup_json_logging()
    
    def _setup_logger(self) -> None:
        """Setup the underlying logger with custom formatting."""
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.level)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create formatter
        formatter = logging.Formatter(
            '[%(asctime)s] [%(threadName)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(self.level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _setup_json_logging(self) -> None:
        """Setup JSON logging to file."""
        if self.json_log_file:
            try:
                # Ensure directory exists
                Path(self.json_log_file).parent.mkdir(parents=True, exist_ok=True)
                self._json_file_handle = open(self.json_log_file, 'a', encoding='utf-8')
            except Exception as e:
                # Fallback to console logging if file creation fails
                self.logger.warning(f"Failed to create JSON log file {self.json_log_file}: {e}")
                self._json_file_handle = None
    
    def _log_json(self, level: str, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a message in JSON format to file."""
        if not self._json_file_handle:
            return
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "thread_name": threading.current_thread().name,
            "level": level,
            "message": message,
            "logger": self.name
        }
        
        if extra_data:
            log_entry.update(extra_data)
        
        try:
            self._json_file_handle.write(json.dumps(log_entry) + '\n')
            self._json_file_handle.flush()
        except Exception as e:
            # Fallback to regular logging if JSON logging fails
            self.logger.error(f"Failed to write JSON log: {e}")
    
    def debug(self, message: str, *args, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a debug message."""
        if args and not extra_data:
            formatted_message = message % args
        else:
            formatted_message = message
        self.logger.debug(formatted_message)
        if self._json_file_handle:
            self._log_json("DEBUG", formatted_message, extra_data)
    
    def info(self, message: str, *args, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an info message."""
        if args and not extra_data:
            formatted_message = message % args
        else:
            formatted_message = message
        self.logger.info(formatted_message)
        if self._json_file_handle:
            self._log_json("INFO", formatted_message, extra_data)
    
    def warning(self, message: str, *args, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning message."""
        if args and not extra_data:
            formatted_message = message % args
        else:
            formatted_message = message
        self.logger.warning(formatted_message)
        if self._json_file_handle:
            self._log_json("WARNING", formatted_message, extra_data)
    
    def error(self, message: str, *args, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an error message."""
        if args and not extra_data:
            formatted_message = message % args
        else:
            formatted_message = message
        self.logger.error(formatted_message)
        if self._json_file_handle:
            self._log_json("ERROR", formatted_message, extra_data)
    
    def critical(self, message: str, *args, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a critical message."""
        if args and not extra_data:
            formatted_message = message % args
        else:
            formatted_message = message
        self.logger.critical(formatted_message)
        if self._json_file_handle:
            self._log_json("CRITICAL", formatted_message, extra_data)
    
    def register_thread(self, thread_name: str, thread_type: str = "worker", 
                       additional_info: Optional[Dict[str, Any]] = None) -> None:
        """Register a thread for tracking.
        
        Args:
            thread_name: Name of the thread
            thread_type: Type of thread (worker, main, etc.)
            additional_info: Additional information about the thread
        """
        with self._thread_lock:
            self._active_threads[thread_name] = {
                "type": thread_type,
                "start_time": time.time(),
                "status": "active",
                "info": additional_info or {}
            }
    
    def unregister_thread(self, thread_name: str) -> None:
        """Unregister a thread from tracking."""
        with self._thread_lock:
            if thread_name in self._active_threads:
                del self._active_threads[thread_name]
    
    def update_thread_status(self, thread_name: str, status: str, 
                           additional_info: Optional[Dict[str, Any]] = None) -> None:
        """Update thread status.
        
        Args:
            thread_name: Name of the thread
            status: New status (active, idle, busy, etc.)
            additional_info: Additional information to update
        """
        with self._thread_lock:
            if thread_name in self._active_threads:
                self._active_threads[thread_name]["status"] = status
                if additional_info:
                    self._active_threads[thread_name]["info"].update(additional_info)
    
    def log_thread_status(self) -> None:
        """Log current thread status (active/total threads)."""
        with self._thread_lock:
            total_threads = len(self._active_threads)
            active_threads = sum(1 for t in self._active_threads.values() if t["status"] == "active")
            
            self.info(f"Thread status: {active_threads}/{total_threads} active")
            
            # Log detailed thread information
            if self.logger.isEnabledFor(logging.DEBUG):
                for thread_name, info in self._active_threads.items():
                    uptime = time.time() - info["start_time"]
                    self.debug(f"Thread {thread_name}: {info['type']} - {info['status']} (uptime: {uptime:.1f}s)")
    
    def get_thread_stats(self) -> Dict[str, Any]:
        """Get current thread statistics.
        
        Returns:
            Dictionary with thread statistics
        """
        with self._thread_lock:
            total_threads = len(self._active_threads)
            active_threads = sum(1 for t in self._active_threads.values() if t["status"] == "active")
            
            thread_types = {}
            for info in self._active_threads.values():
                thread_type = info["type"]
                thread_types[thread_type] = thread_types.get(thread_type, 0) + 1
            
            return {
                "total_threads": total_threads,
                "active_threads": active_threads,
                "thread_types": thread_types,
                "threads": dict(self._active_threads)
            }
    
    @contextmanager
    def thread_context(self, thread_name: str, thread_type: str = "worker", 
                      additional_info: Optional[Dict[str, Any]] = None):
        """Context manager for automatic thread registration/unregistration.
        
        Args:
            thread_name: Name of the thread
            thread_type: Type of thread
            additional_info: Additional information about the thread
        """
        self.register_thread(thread_name, thread_type, additional_info)
        try:
            yield
        finally:
            self.unregister_thread(thread_name)
    
    def close(self) -> None:
        """Close the logger and cleanup resources."""
        if self._json_file_handle:
            self._json_file_handle.close()
            self._json_file_handle = None
        
        # Close all handlers
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.close()


# Global logger instance
_global_logger: Optional[ServerLogger] = None


def get_logger(name: str = "server") -> ServerLogger:
    """Get or create a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        ServerLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = ServerLogger(name)
    return _global_logger


def setup_logging(log_file: Optional[str] = None, json_log_file: Optional[str] = None, 
                 level: int = logging.INFO) -> ServerLogger:
    """Setup global logging configuration.
    
    Args:
        log_file: Optional file path for text logs
        json_log_file: Optional file path for JSON logs
        level: Logging level
        
    Returns:
        Configured ServerLogger instance
    """
    global _global_logger
    _global_logger = ServerLogger("server", log_file, json_log_file, level)
    return _global_logger


def log_thread_status() -> None:
    """Log current thread status using the global logger."""
    if _global_logger:
        _global_logger.log_thread_status()


# Convenience functions for backward compatibility
def debug(message: str, *args, extra_data: Optional[Dict[str, Any]] = None) -> None:
    """Log a debug message using the global logger."""
    get_logger().debug(message, *args, extra_data=extra_data)


def info(message: str, *args, extra_data: Optional[Dict[str, Any]] = None) -> None:
    """Log an info message using the global logger."""
    get_logger().info(message, *args, extra_data=extra_data)


def warning(message: str, *args, extra_data: Optional[Dict[str, Any]] = None) -> None:
    """Log a warning message using the global logger."""
    get_logger().warning(message, *args, extra_data=extra_data)


def error(message: str, *args, extra_data: Optional[Dict[str, Any]] = None) -> None:
    """Log an error message using the global logger."""
    get_logger().error(message, *args, extra_data=extra_data)


def critical(message: str, *args, extra_data: Optional[Dict[str, Any]] = None) -> None:
    """Log a critical message using the global logger."""
    get_logger().critical(message, *args, extra_data=extra_data)
