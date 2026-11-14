"""core/scheduler.py
Background reminder and recurring task scheduler that runs across dialogue turns and idle states.
"""

import threading
import time
from typing import Callable, Optional, List, Dict, Any

from core.memory import MemoryStore


class BackgroundScheduler:
    """Threaded scheduler checking SQLite persistent reminders every few seconds."""

    _instance: Optional["BackgroundScheduler"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BackgroundScheduler, cls).__new__(cls)
                cls._instance._init_scheduler()
            return cls._instance

    def _init_scheduler(self):
        self.memory = MemoryStore()
        self._callbacks: List[Callable[[str, str], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_callback(self, cb: Callable[[str, str], None]):
        """Register a callback fn(title: str, recurring: str) to be invoked when a reminder is due."""
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def start(self):
        """Start the background check loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="SchedulerThread")
        self._thread.start()

    def stop(self):
        """Stop scheduler."""
        self._running = False

    def _loop(self):
        """Check due reminders in SQLite every 4 seconds."""
        while self._running:
            try:
                now_ts = time.time()
                due_items = self.memory.get_due_reminders(now_ts)
                for item in due_items:
                    rem_id = item["id"]
                    title = item["title"]
                    recurring = item.get("recurring", "none")

                    # Mark completed / reschedule before firing callbacks to prevent duplicate triggers
                    self.memory.complete_reminder(rem_id)

                    for cb in self._callbacks:
                        try:
                            cb(title, recurring)
                        except Exception as cb_err:
                            print(f"[Scheduler] Callback error: {cb_err}")

            except Exception as e:
                print(f"[Scheduler] Loop error: {e}")

            time.sleep(4)
