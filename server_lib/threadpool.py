"""Simple bounded thread pool for socket handling."""

from __future__ import annotations

import logging
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
        self._stop.set()
        for _ in self._workers:
            self._tasks.put_nowait((lambda: None, (), {}))
        if wait:
            for w in self._workers:
                w.join()

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                fn, args, kwargs = self._tasks.get(timeout=0.5)
            except Empty:
                continue
            try:
                self._logger.debug(f"Worker {self._worker.__name__} processing task")
                fn(*args, **kwargs)
            finally:
                self._tasks.task_done()
                self._logger.debug(f"Task completed, queue size: {self._tasks.qsize()}")