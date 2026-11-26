"""
core/ambient.py
Proactive Ambient Intelligence — Anticipatory Companion for T.U.E.S.D.A.Y.
Monitors work duration, upcoming schedule/reminders, hardware health (battery/RAM),
and recurring workflow habits in a lightweight background thread (<1% CPU).
"""

import ctypes
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set

import psutil

from core.memory import MemoryStore


def _get_idle_seconds_windows() -> float:
    """Return system-wide user idle time in seconds on Windows via GetLastInputInfo."""
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return 0.0


def _get_active_process_name() -> Optional[str]:
    """Return lowercase process name of the currently focused foreground window."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value:
            proc = psutil.Process(pid.value)
            name = proc.name().lower()
            if name.endswith(".exe"):
                name = name[:-4]
            # Ignore system shell / Tuesday itself
            if name not in ("explorer", "searchhost", "shellexperiencehost", "python", "pythonw", "cmd", "conhost"):
                return name
    except Exception:
        pass
    return None


class AmbientCompanion:
    """
    Lightweight anticipatory background daemon that proactively nudges the user:
    1. Contextual Work Watchdog (continuous work without break)
    2. Meeting & Schedule Radar (10-min pre-event warning)
    3. Hardware / Battery Watchdog (low battery <20%, high RAM >90%)
    4. Workflow Habit Automation (detects recurring hourly app routines)
    """

    def __init__(
        self,
        memory: Optional[MemoryStore] = None,
        poll_interval: float = 30.0,
        work_alert_minutes: float = 120.0,
        battery_threshold: int = 20,
        ram_threshold: int = 90,
    ):
        self.memory = memory or MemoryStore()
        self.poll_interval = poll_interval
        self.work_alert_seconds = work_alert_minutes * 60.0
        self.battery_threshold = battery_threshold
        self.ram_threshold = ram_threshold

        self._callbacks: List[Callable[[str, str], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # State & Cooldowns
        self._work_streak_start: float = time.time()
        self._last_alert_times: Dict[str, float] = {}
        self._alerted_reminder_ids: Set[int] = set()
        self._suggested_habit_hours: Set[int] = set()

    def register_callback(self, cb: Callable[[str, str], None]):
        """Register callback fn(alert_type: str, message: str)."""
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def _emit(self, alert_type: str, message: str):
        """Dispatch proactive alert to all registered listeners."""
        for cb in self._callbacks:
            try:
                cb(alert_type, message)
            except Exception as e:
                print(f"[Ambient] Callback error: {e}")

    def _can_alert(self, key: str, cooldown_seconds: float) -> bool:
        """Enforce cooldown between repeated alerts of the same type."""
        now = time.time()
        last = self._last_alert_times.get(key, 0.0)
        if now - last >= cooldown_seconds:
            self._last_alert_times[key] = now
            return True
        return False

    def start(self):
        """Start background monitoring thread."""
        if self._running:
            return
        self._running = True
        self._work_streak_start = time.time()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="AmbientCompanionThread")
        self._thread.start()

    def stop(self):
        """Stop background monitoring thread."""
        self._running = False

    def _loop(self):
        """Main polling loop."""
        while self._running:
            try:
                self.run_checks_once()
            except Exception as e:
                print(f"[Ambient] Check error: {e}")
            time.sleep(self.poll_interval)

    def run_checks_once(self):
        """Execute one full pass of all 4 ambient intelligence checks."""
        self.check_work_duration()
        self.check_upcoming_schedule()
        self.check_hardware_health()
        self.check_workflow_habits()

    # ── 1. Contextual Work Watchdog ─────────────────────────────────────────

    def check_work_duration(self, idle_seconds: Optional[float] = None):
        """Alert if user has been continuously active beyond threshold without a 5-min break."""
        idle = _get_idle_seconds_windows() if idle_seconds is None else idle_seconds
        now = time.time()

        # Reset streak if user stepped away for >= 5 minutes
        if idle >= 300.0:
            self._work_streak_start = now
            return

        elapsed = now - self._work_streak_start
        if elapsed >= self.work_alert_seconds:
            if self._can_alert("work_break", cooldown_seconds=3600.0):
                hours = round(elapsed / 3600.0, 1)
                self._emit(
                    "work_watchdog",
                    f"Sir, aap lagataar {hours} ghante se kaam kar rahe hain. Kya 5 minute ka coffee ya stretch break le lein?"
                )

    # ── 2. Meeting & Schedule Radar ─────────────────────────────────────────

    def check_upcoming_schedule(self, now_ts: Optional[float] = None):
        """Alert 10 minutes before due reminders/events."""
        ts = now_ts or time.time()
        try:
            reminders = self.memory.get_all_reminders(include_completed=False)
            for rem in reminders:
                rem_id = rem["id"]
                if rem_id in self._alerted_reminder_ids:
                    continue
                delta = rem["due_timestamp"] - ts
                if 0 < delta <= 600:
                    self._alerted_reminder_ids.add(rem_id)
                    mins = max(1, int(round(delta / 60)))
                    title = rem["title"]
                    self._emit(
                        "schedule_radar",
                        f"Sir, '{title}' {mins} minute mein start hone wala hai. Kya main notes open karke system audio mute kar doon?"
                    )
        except Exception:
            pass

    # ── 3. Hardware & Battery Watchdog ──────────────────────────────────────

    def check_hardware_health(self):
        """Proactively warn on low battery (<20% unplugged) or high RAM (>90%)."""
        try:
            battery = psutil.sensors_battery()
            if battery is not None and not battery.power_plugged:
                if battery.percent <= self.battery_threshold:
                    if self._can_alert("low_battery", cooldown_seconds=900.0):
                        self._emit(
                            "hardware_battery",
                            f"Sir, battery {int(battery.percent)}% par aa gayi hai, charger connect kar lijiye."
                        )
        except Exception:
            pass

        try:
            mem = psutil.virtual_memory()
            if mem.percent >= self.ram_threshold:
                if self._can_alert("high_ram", cooldown_seconds=1200.0):
                    self._emit(
                        "hardware_ram",
                        f"Sir, RAM usage {int(mem.percent)}% cross ho gaya hai. Kya main memory optimize kar doon?"
                    )
        except Exception:
            pass

    # ── 4. Workflow Habit Automation ────────────────────────────────────────

    def check_workflow_habits(self, active_proc: Optional[str] = None, current_hour: Optional[int] = None):
        """Log active app by hour and suggest automation if recurring daily pattern is detected."""
        hour = datetime.now().hour if current_hour is None else current_hour
        proc = active_proc if active_proc is not None else _get_active_process_name()

        if proc:
            try:
                self.memory.log_habit(hour, proc)
            except Exception:
                pass

        if hour not in self._suggested_habit_hours:
            try:
                frequent_apps = self.memory.get_frequent_habits(hour, min_days=3)
                if frequent_apps:
                    # Check which frequent apps are not currently running
                    running_procs = {
                        p.info["name"].lower().replace(".exe", "")
                        for p in psutil.process_iter(["name"])
                        if p.info.get("name")
                    }
                    missing = [app for app in frequent_apps[:3] if app not in running_procs]
                    if missing:
                        self._suggested_habit_hours.add(hour)
                        apps_str = " aur ".join(missing)
                        self._emit(
                            "habit_suggestion",
                            f"Sir, aam taur par is time aap {apps_str} open karte hain. Kya main aapka workspace ready kar doon?"
                        )
            except Exception:
                pass
