"""Simple bounded thread pool for socket handling."""

from __future__ import annotations

from queue import Queue, Full, Empty
from threading import Thread, Event
from typing import Callable, Any, Optional


class ThreadPool:
    def __init__(self, num_workers: int = 4, queue_max: int = 64):
        self._tasks: Queue[tuple[Callable[..., Any], tuple, dict]] = Queue(maxsize=queue_max)
        self._stop = Event()
        self._workers = [Thread(target=self._worker, daemon=True, name=f"worker-{i}") for i in range(num_workers)]
        for w in self._workers:
            w.start()

    def try_submit(self, fn: Callable[..., Any], *args, timeout: float = 0.0, **kwargs) -> bool:
        """Attempt to submit a task, return False if queue full within timeout."""
        try:
            self._tasks.put((fn, args, kwargs), timeout=timeout)
            return True
        except Full:
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
                fn(*args, **kwargs)
            finally:
                self._tasks.task_done()