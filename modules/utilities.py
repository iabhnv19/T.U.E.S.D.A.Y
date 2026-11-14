import threading
import time
from datetime import datetime
from typing import Optional
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import psutil

from core.config import Config


class Utilities:
    """System utilities, timers, calculations, and date/time helpers."""

    def __init__(self):
        self.active_timers: dict[str, threading.Timer] = {}
        self._timer_callback = None

    def set_timer_callback(self, callback):
        """Callback to execute when a timer fires."""
        self._timer_callback = callback

    def get_weather(self, city: str = None) -> str:
        """Fetch current weather via wttr.in."""
        city = city or Config.WEATHER_CITY or "Amritsar"
        try:
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=%l:+%C+%t+(Humidity:+%h,+Wind:+%w)"
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                text = resp.read().decode().strip()
                if text:
                    return text
        except Exception:
            pass
        return f"Could not retrieve weather for {city} right now."

    def get_news(self, query: str = None, count: int = 4) -> str:
        """Fetch news headlines from Google News RSS."""
        try:
            if query:
                encoded_q = urllib.parse.quote(query)
                url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-IN&gl=IN&ceid=IN:en"
            else:
                url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                tree = ET.parse(resp)
                items = tree.findall(".//item")[:count]
                if items:
                    headlines = []
                    for i, it in enumerate(items, 1):
                        title_el = it.find("title")
                        title_txt = title_el.text if title_el is not None else "News"
                        headlines.append(f"{i}. {title_txt}")
                    return "Top headlines:\n" + "\n".join(headlines)
        except Exception:
            pass
        return "Could not retrieve news headlines right now."

    def set_timer(self, seconds: int, label: str = "Timer") -> str:
        """Schedule a background countdown timer."""
        def timer_fire():
            msg = f"{label} — {seconds} seconds are up!"
            if self._timer_callback:
                self._timer_callback(msg)
            if label in self.active_timers:
                del self.active_timers[label]

        timer = threading.Timer(seconds, timer_fire)
        timer.daemon = True
        timer.start()
        self.active_timers[label] = timer

        if seconds >= 60:
            mins = seconds // 60
            secs = seconds % 60
            time_str = f"{mins} minute{'s' if mins != 1 else ''}"
            if secs:
                time_str += f" {secs} seconds"
        else:
            time_str = f"{seconds} seconds"

        return f"{label} set for {time_str}."

    def cancel_timer(self, label: str) -> str:
        if label in self.active_timers:
            self.active_timers[label].cancel()
            del self.active_timers[label]
            return f"{label} cancelled."
        return f"No active timer named '{label}'."

    @staticmethod
    def get_datetime() -> str:
        now = datetime.now()
        return now.strftime("It's %A, %B %d, %Y. The time is %I:%M %p.")

    @staticmethod
    def get_system_info() -> str:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()

        info = f"CPU: {cpu}% | RAM: {ram.percent}% ({ram.used // (1024**3)}/{ram.total // (1024**3)} GB) | Disk: {disk.percent}% used"
        if battery:
            info += f" | Battery: {battery.percent}%"
            info += " (Charging)" if battery.power_plugged else ""
        return info

    @staticmethod
    def calculate(expression: str) -> str:
        """Safely evaluate basic math expressions."""
        allowed = set("0123456789+-*/().% ")
        if not all(c in allowed for c in expression):
            return "Only numeric math expressions are supported."
        try:
            result = eval(expression)
            return f"{expression} = {result}"
        except Exception:
            return f"Couldn't calculate: {expression}"

    WEBSITE_MAP = {
        "youtube": "https://youtube.com",
        "google": "https://google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
        "reddit": "https://reddit.com",
        "twitter": "https://twitter.com",
        "x": "https://x.com",
    }

    def open_website(self, name: str) -> Optional[str]:
        return self.WEBSITE_MAP.get(name.lower().strip())
