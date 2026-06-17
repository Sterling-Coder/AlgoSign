"""Tiny background scheduler — runs jobs on a cadence without anyone on the page.

This is what makes alerts and the prediction track record possible: a daemon
thread that wakes every `interval` seconds and runs each registered job. No
APScheduler, no Celery, no Redis — one thread, a list of callables. At our scale
(scan a few dozen symbols every couple minutes) that's all it takes.

Each job is wrapped so one job raising never kills the loop or the other jobs.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

log = logging.getLogger("algosign.scheduler")

_jobs: list[tuple[str, Callable[[], None], int]] = []  # (name, fn, every_seconds)
_thread: threading.Thread | None = None
_stop = threading.Event()
_TICK = 15  # base loop granularity in seconds


def register(name: str, fn: Callable[[], None], every_seconds: int) -> None:
    """Register a job to run every `every_seconds`. Call before start()."""
    _jobs.append((name, fn, every_seconds))


def _run_loop() -> None:
    last_run: dict[str, float] = {}
    while not _stop.is_set():
        now = time.time()
        for name, fn, every in _jobs:
            if now - last_run.get(name, 0) >= every:
                last_run[name] = now
                try:
                    fn()
                except Exception:  # one bad job must not kill the scheduler
                    log.exception("scheduler job %s failed", name)
        _stop.wait(_TICK)


def start() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_run_loop, name="scheduler", daemon=True)
    _thread.start()
    log.info("scheduler started with %d job(s)", len(_jobs))


def stop() -> None:
    _stop.set()
    if _thread:
        _thread.join(timeout=2)
