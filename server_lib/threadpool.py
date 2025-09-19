"""Simple bounded thread pool for socket handling."""

from __future__ import annotations

import logging
import threading
from queue import Queue, Full, Empty
from threading import Thread, Event
from typing import Callable, Any, Optional


class ThreadPool:
    def __init__(self, num_workers: int = 4, queue_max: int = 64):
        self._tasks: Queue[tuple[Callable[..., Any], tuple, dict]] = Queue(maxsize=queue_max)
        self._stop = Event()
        self._logger = logging.getLogger("threadpool")
        self._workers = [Thread(target=self._worker, daemon=True, name=f"worker-{i}") for i in range(num_workers)]
        for w in self._workers:
            w.start()
        self._logger.info(f"Thread pool started with {num_workers} workers, queue max={queue_max}")

    def try_submit(self, fn: Callable[..., Any], *args, timeout: float = 0.0, **kwargs) -> bool:
        """Attempt to submit a task, return False if queue full within timeout."""
        try:
            self._tasks.put((fn, args, kwargs), timeout=timeout)
            self._logger.debug(f"Task queued, queue size: {self._tasks.qsize()}")
            return True
        except Full:
            self._logger.warning(f"Queue full, rejecting task")
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
        
        self._logger.info("Thread pool shutdown complete")

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
                    break
                    
                self._logger.debug(f"Worker {worker_name} processing task, queue size: {self._tasks.qsize()}")
                
                try:
                    fn(*args, **kwargs)
                except Exception as e:
                    self._logger.error(f"Worker {worker_name} task failed: {e}")
                    # Ensure any socket connections are closed on exception
                    if len(args) > 0 and hasattr(args[0], 'close'):
                        try:
                            args[0].close()  # Close socket if first arg is a socket
                        except Exception:
                            pass
                finally:
                    self._logger.debug(f"Worker {worker_name} task completed")
                    
            except Empty:
                continue
            finally:
                self._tasks.task_done()
        
        self._logger.debug(f"Worker {worker_name} shutting down")