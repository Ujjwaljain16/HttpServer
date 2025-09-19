"""Simple bounded thread pool for socket handling."""

from __future__ import annotations

import logging
from server_lib.logger import get_logger
import threading
from queue import Queue, Full, Empty
from threading import Thread, Event
from typing import Callable, Any, Optional


class ThreadPool:
    def __init__(self, num_workers: int = 4, queue_max: int = 64):
        self._tasks: Queue[tuple[Callable[..., Any], tuple, dict]] = Queue(maxsize=queue_max)
        self._stop = Event()
        self._logger = get_logger()
        self._workers = [Thread(target=self._worker, daemon=True, name=f"worker-{i}") for i in range(num_workers)]
        
        # Thread-safe counters
        self._lock = threading.Lock()
        self._tasks_completed = 0
        self._tasks_failed = 0
        
        for w in self._workers:
            w.start()
            # Register worker thread with logger
            self._logger.register_thread(w.name, "worker", {"queue_max": queue_max})
        self._logger.info(f"Thread pool started with {num_workers} workers, queue max={queue_max}")

    def try_submit(self, fn: Callable[..., Any], *args, timeout: float = 0.0, **kwargs) -> bool:
        """Attempt to submit a task, return False if queue full within timeout."""
        current_size = self._tasks.qsize()
        self._logger.debug(f"Attempting to queue task, current queue size: {current_size}/{self._tasks.maxsize}")
        
        try:
            self._tasks.put((fn, args, kwargs), timeout=timeout)
            self._logger.debug(f"Task queued successfully, queue size: {self._tasks.qsize()}")
            return True
        except Full:
            self._logger.warning(f"Queue full (size: {current_size}/{self._tasks.maxsize}), rejecting task")
            return False

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the thread pool gracefully.
        
        Sends sentinel values (None) to wake up workers and stop them.
        """
        self._logger.info("Shutting down thread pool...")
        self._stop.set()
        
        # Send sentinel values to wake up all workers
        for _ in self._workers:
            try:
                self._tasks.put_nowait((None, (), {}))
            except Full:
                # Queue is full, but workers will check _stop event
                pass
                
        if wait:
            for w in self._workers:
                w.join(timeout=2.0)  # Give workers 2 seconds to finish
                if w.is_alive():
                    self._logger.warning(f"Worker {w.name} did not shut down gracefully")
                else:
                    # Unregister worker thread
                    self._logger.unregister_thread(w.name)
        
        self._logger.info("Thread pool shutdown complete")
    
    def get_stats(self) -> dict:
        """Get thread pool statistics in a thread-safe manner."""
        with self._lock:
            return {
                "tasks_completed": self._tasks_completed,
                "tasks_failed": self._tasks_failed,
                "queue_size": self._tasks.qsize(),
                "queue_max": self._tasks.maxsize,
                "workers_active": len([w for w in self._workers if w.is_alive()])
            }

    def _worker(self) -> None:
        """Worker loop that processes tasks from the queue until shutdown."""
        worker_name = threading.current_thread().name
        self._logger.debug(f"Worker {worker_name} started")
        
        while not self._stop.is_set():
            try:
                fn, args, kwargs = self._tasks.get(timeout=0.5)
                
                # Check for sentinel (None function) indicating shutdown
                if fn is None:
                    self._logger.debug(f"Worker {worker_name} received shutdown sentinel")
                    self._tasks.task_done()  # Mark sentinel task as done
                    break
                    
                self._logger.debug(f"Worker {worker_name} processing task, queue size: {self._tasks.qsize()}")
                self._logger.update_thread_status(worker_name, "busy", {"queue_size": self._tasks.qsize()})
                
                try:
                    fn(*args, **kwargs)
                    # Thread-safe counter update
                    with self._lock:
                        self._tasks_completed += 1
                except Exception as e:
                    self._logger.error(f"Worker {worker_name} task failed: {e}")
                    # Thread-safe counter update
                    with self._lock:
                        self._tasks_failed += 1
                    # Ensure any socket connections are closed on exception
                    if len(args) > 0 and hasattr(args[0], 'close'):
                        try:
                            args[0].close()  # Close socket if first arg is a socket
                        except Exception:
                            pass
                finally:
                    self._logger.update_thread_status(worker_name, "idle")
                    self._logger.debug(f"Worker {worker_name} task completed")
                    self._tasks.task_done()  # Mark task as done after processing
                    
            except Empty:
                continue
        
        self._logger.debug(f"Worker {worker_name} shutting down")