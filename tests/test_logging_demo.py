#!/usr/bin/env python3
"""
Demo script to show the detailed logging functionality.
"""

import sys
import time
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server_lib.logger import setup_logging, get_logger, log_thread_status

def demo_logging():
    """Demonstrate the logging functionality."""
    print("=" * 70)
    print("DETAILED LOGGING MODULE DEMO")
    print("=" * 70)
    print("This demo shows the enhanced logging functionality with:")
    print("- Timestamped log format: [YYYY-MM-DD HH:MM:SS] [Thread-Name] LEVEL: message")
    print("- Thread status tracking")
    print("- JSON logging capability")
    print("- Extra data support")
    print()
    
    # Setup logging with both text and JSON output
    logger = setup_logging(
        log_file="demo_server.log",
        json_log_file="demo_server.json",
        level=10  # DEBUG level
    )
    
    print("1. Basic logging with different levels:")
    print("-" * 40)
    logger.info("Server starting up")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.debug("Debug information: server configuration loaded")
    
    print("\n2. Logging with formatted strings:")
    print("-" * 40)
    logger.info("Server listening on %s:%d", "127.0.0.1", 8080)
    logger.warning("Thread pool queue at %d%% capacity", 75)
    logger.error("Failed to process request from %s: %s", "192.168.1.100", "Connection timeout")
    
    print("\n3. Logging with extra data:")
    print("-" * 40)
    logger.info("Request processed", extra_data={
        "method": "GET",
        "path": "/",
        "status": 200,
        "response_time": 0.05
    })
    logger.warning("High memory usage detected", extra_data={
        "memory_usage": "85%",
        "thread_count": 8,
        "queue_size": 15
    })
    
    print("\n4. Thread tracking and status:")
    print("-" * 40)
    
    # Register some threads
    logger.register_thread("MainThread", "main", {"port": 8080, "host": "127.0.0.1"})
    logger.register_thread("worker-1", "worker", {"queue_size": 32})
    logger.register_thread("worker-2", "worker", {"queue_size": 32})
    logger.register_thread("worker-3", "worker", {"queue_size": 32})
    
    # Update thread status
    logger.update_thread_status("worker-1", "busy", {"processing": "GET /api/users"})
    logger.update_thread_status("worker-2", "idle")
    logger.update_thread_status("worker-3", "busy", {"processing": "POST /api/data"})
    
    # Log thread status
    log_thread_status()
    
    print("\n5. Thread context manager demo:")
    print("-" * 40)
    
    def worker_task(worker_id):
        with logger.thread_context(f"worker-{worker_id}", "worker", {"task_id": worker_id}):
            logger.info("Worker %d starting task", worker_id)
            time.sleep(0.1)  # Simulate work
            logger.info("Worker %d completed task", worker_id)
    
    # Start some worker threads
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker_task, args=(i,))
        t.start()
        threads.append(t)
    
    # Wait for threads to complete
    for t in threads:
        t.join()
    
    print("\n6. Final thread status:")
    print("-" * 40)
    log_thread_status()
    
    print("\n7. Log file contents preview:")
    print("-" * 40)
    try:
        with open("demo_server.log", "r") as f:
            lines = f.readlines()
            print("Text log file (first 10 lines):")
            for line in lines[:10]:
                print(f"  {line.strip()}")
            if len(lines) > 10:
                print(f"  ... and {len(lines) - 10} more lines")
    except FileNotFoundError:
        print("Log file not found")
    
    print("\n8. JSON log file contents preview:")
    print("-" * 40)
    try:
        with open("demo_server.json", "r") as f:
            lines = f.readlines()
            print("JSON log file (first 3 entries):")
            import json
            for line in lines[:3]:
                entry = json.loads(line.strip())
                print(f"  {entry}")
    except FileNotFoundError:
        print("JSON log file not found")
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("Check 'demo_server.log' for text logs and 'demo_server.json' for JSON logs")
    print("=" * 70)
    
    # Cleanup
    logger.close()

if __name__ == "__main__":
    demo_logging()
