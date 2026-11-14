import os
import subprocess
import time
import json
import ctypes
import shutil
import socket
import gc
from pathlib import Path
from typing import Optional

import pyautogui
import psutil
import pyperclip

from core.config import Config

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3


class PCController:
    """Handles Windows automation, window snapping, media, and diagnostics."""

    @staticmethod
    def open_app(app_name: str) -> str:
        """Launch an application or URL scheme."""
        app_map = {
            "chrome": "chrome",
            "google chrome": "chrome",
            "browser": "chrome",
            "firefox": "firefox",
            "notepad": "notepad",
            "calculator": "calc",
            "calc": "calc",
            "explorer": "explorer",
            "file explorer": "explorer",
            "files": "explorer",
            "cmd": "cmd",
            "command prompt": "cmd",
            "terminal": "wt",
            "windows terminal": "wt",
            "powershell": "powershell",
            "task manager": "taskmgr",
            "settings": "ms-settings:",
            "control panel": "control",
            "paint": "mspaint",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "spotify": "spotify",
            "discord": "discord",
            "vscode": "code",
            "vs code": "code",
            "visual studio code": "code",
            "vlc": "vlc",
            "obs": "obs64",
            "steam": "steam",
            "snipping tool": "snippingtool",
        }

        target = app_map.get(app_name.lower(), app_name)
        try:
            if ":" in target:
                os.startfile(target)
            else:
                subprocess.Popen(
                    target,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            return f"Opening {app_name}."
        except Exception as e:
            return f"Couldn't open {app_name}: {e}"

    @staticmethod
    def close_app(app_name: str) -> str:
        """Terminate a running process by name."""
        process_map = {
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "notepad": "notepad.exe",
            "explorer": "explorer.exe",
            "spotify": "spotify.exe",
            "discord": "discord.exe",
            "vscode": "Code.exe",
            "vs code": "Code.exe",
            "vlc": "vlc.exe",
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
        }

        process_name = process_map.get(app_name.lower(), f"{app_name}.exe")
        killed = False
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == process_name.lower():
                    proc.terminate()
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return f"Closed {app_name}." if killed else f"{app_name} doesn't appear to be running."

    @staticmethod
    def empty_recycle_bin() -> str:
        """Silently empty the Windows Recycle Bin."""
        try:
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            return "Recycle bin emptied."
        except Exception as e:
            return f"Could not empty recycle bin: {e}"

    @staticmethod
    def get_quick_briefing() -> str:
        """Daily summary: date, time, battery, RAM load, and current weather."""
        now = time.strftime("%A, %B %d, %I:%M %p")
        batt = psutil.sensors_battery()
        batt_str = f"{batt.percent}%" if batt else "Plugged in"
        ram = psutil.virtual_memory().percent

        import urllib.request
        try:
            req = urllib.request.Request("https://wttr.in/?format=%C+%t", headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                w = resp.read().decode().strip()
        except Exception:
            w = "Unavailable"

        return f"Briefing: Today is {now}. Battery at {batt_str}. Memory load {ram}%. Current weather: {w}."

    @staticmethod
    def get_full_diagnostics() -> str:
        """Detailed system telemetry including CPU, RAM, C: disk, and top memory consumers."""
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        c_drive = psutil.disk_usage("C:")
        free_gb = round(c_drive.free / (1024**3), 1)

        procs = []
        for p in psutil.process_iter(["name", "memory_info"]):
            try:
                mem = p.info["memory_info"].rss / (1024 * 1024)
                name = p.info["name"]
                if name and not name.lower().startswith(("system", "registry")):
                    procs.append((name, mem))
            except Exception:
                pass
        procs.sort(key=lambda x: x[1], reverse=True)
        top_apps = [name + f" ({int(mem)} MB)" for name, mem in procs[:2]]
        top_str = f" Top processes: {', '.join(top_apps)}." if top_apps else ""

        battery = psutil.sensors_battery()
        bat_str = ""
        if battery:
            bat_str = f" Battery at {battery.percent}% ({'Plugged in' if battery.power_plugged else 'On battery'})."

        return (
            f"Diagnostics: CPU at {cpu}%, RAM {ram.percent}% used "
            f"({int(ram.used/(1024**3))}/{int(ram.total/(1024**3))} GB). "
            f"C: drive has {free_gb} GB free.{bat_str}{top_str}"
        )

    @staticmethod
    def clean_ram() -> str:
        """Trim working sets and collect garbage to free up memory."""
        gc.collect()
        try:
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
        except Exception:
            pass
        ram = psutil.virtual_memory()
        return f"Memory optimization complete. Current RAM usage is at {ram.percent}% ({int(ram.available/(1024**3))} GB available)."

    @staticmethod
    def get_network_radar() -> str:
        """Check local subnet IP, public IP, and ping latency."""
        import urllib.request, re
        local_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass

        pub_ip = "Unknown"
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=2.5) as r:
                pub_ip = r.read().decode().strip()
        except Exception:
            pass

        ping_str = ""
        try:
            r = subprocess.run(["ping", "-n", "1", "8.8.8.8"], capture_output=True, text=True, timeout=3)
            m = re.search(r"time[=<](\d+)ms", r.stdout, re.I)
            if m:
                ping_str = f" Ping latency is {m.group(1)} ms."
        except Exception:
            pass

        return f"Network Radar: Local IP is {local_ip}, Public IP is {pub_ip}.{ping_str} Connection is active."

    @staticmethod
    def organize_desktop() -> str:
        """Scan Desktop and move loose files into categorized folders."""
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            return "Desktop folder not found."

        categories = {
            "Images": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"],
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".pptx"],
            "Installers": [".exe", ".msi", ".zip", ".rar", ".7z", ".tar", ".gz"],
            "Media": [".mp4", ".mkv", ".mp3", ".wav", ".avi", ".mov"]
        }

        moved_count = 0
        for item in desktop.iterdir():
            if item.is_dir() or item.name.startswith(".") or item.suffix.lower() in [".lnk", ".url", ".ini"]:
                continue

            ext = item.suffix.lower()
            target_folder = None
            for cat_name, extensions in categories.items():
                if ext in extensions:
                    target_folder = desktop / cat_name
                    break

            if target_folder:
                target_folder.mkdir(exist_ok=True)
                dest = target_folder / item.name
                if dest.exists():
                    dest = target_folder / f"{item.stem}_{int(time.time())}{item.suffix}"
                try:
                    shutil.move(str(item), str(dest))
                    moved_count += 1
                except Exception:
                    pass

        if moved_count > 0:
            return f"Desktop organized! Cleaned and categorized {moved_count} files into neat folders."
        return "Desktop is already clean and organized."

    # Browser tab navigation
    @staticmethod
    def new_tab() -> str:
        pyautogui.hotkey("ctrl", "t")
        return "Opened new browser tab."

    @staticmethod
    def close_tab() -> str:
        pyautogui.hotkey("ctrl", "w")
        return "Closed tab."

    @staticmethod
    def reopen_tab() -> str:
        pyautogui.hotkey("ctrl", "shift", "t")
        return "Reopened closed tab."

    @staticmethod
    def scroll_down(amount: int = 400) -> str:
        pyautogui.scroll(-amount)
        return "Scrolled down."

    @staticmethod
    def scroll_up(amount: int = 400) -> str:
        pyautogui.scroll(amount)
        return "Scrolled up."

    @staticmethod
    def toggle_fullscreen() -> str:
        pyautogui.press("f11")
        return "Toggled fullscreen."

    @staticmethod
    def open_history() -> str:
        pyautogui.hotkey("ctrl", "h")
        return "Opened browser history."

    @staticmethod
    def open_downloads() -> str:
        pyautogui.hotkey("ctrl", "j")
        return "Opened downloads."

    # Media controls
    @staticmethod
    def media_play_pause() -> str:
        pyautogui.press("playpause")
        return "Toggled play/pause."

    @staticmethod
    def media_next() -> str:
        pyautogui.press("nexttrack")
        return "Skipped to next track."

    @staticmethod
    def media_previous() -> str:
        pyautogui.press("prevtrack")
        return "Went to previous track."

    @staticmethod
    def volume_up(amount: int = 5) -> str:
        for _ in range(amount):
            pyautogui.press("volumeup")
        return f"Volume increased by {amount * 2}%."

    @staticmethod
    def volume_down(amount: int = 5) -> str:
        for _ in range(amount):
            pyautogui.press("volumedown")
        return f"Volume decreased by {amount * 2}%."

    @staticmethod
    def volume_mute() -> str:
        pyautogui.press("volumemute")
        return "Toggled mute."

    @staticmethod
    def set_volume_percent(percent: int) -> str:
        """Set Windows master audio volume to a specific percentage (0-100)."""
        target = max(0, min(100, int(percent)))
        old_pause = pyautogui.PAUSE
        try:
            pyautogui.PAUSE = 0.005
            for _ in range(50):
                pyautogui.press("volumedown")
            steps = target // 2
            for _ in range(steps):
                pyautogui.press("volumeup")
        finally:
            pyautogui.PAUSE = old_pause
        return f"Volume set to {target}%."

    @staticmethod
    def focus_window(app_name: str) -> str:
        """Bring target window to the foreground."""
        target_map = {
            "chrome": "Google Chrome",
            "vscode": "Visual Studio Code",
            "vs code": "Visual Studio Code",
            "code": "Visual Studio Code",
            "spotify": "Spotify",
            "notepad": "Notepad",
            "terminal": "Terminal",
            "explorer": "File Explorer",
        }
        title = target_map.get(app_name.lower().strip(), app_name)
        try:
            # WScript AppActivate brings window to front
            cmd = f'powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).AppActivate(\'{title}\')"'
            subprocess.run(cmd, shell=True, capture_output=True, timeout=2)
            return f"Switched to {title}."
        except Exception:
            return f"Could not focus {app_name}."

    @staticmethod
    def open_settings(page: str = "") -> str:
        """Open specific Windows 10/11 Settings page."""
        page_clean = page.lower().strip()
        scheme_map = {
            "bluetooth": "ms-settings:bluetooth",
            "wifi": "ms-settings:network-wifi",
            "network": "ms-settings:network",
            "sound": "ms-settings:sound",
            "audio": "ms-settings:sound",
            "display": "ms-settings:display",
            "brightness": "ms-settings:display",
            "battery": "ms-settings:batterysaver",
            "power": "ms-settings:powersleep",
            "apps": "ms-settings:appsfeatures",
            "update": "ms-settings:windowsupdate",
            "windows update": "ms-settings:windowsupdate",
            "privacy": "ms-settings:privacy",
        }
        target_uri = scheme_map.get(page_clean, "ms-settings:")
        try:
            os.startfile(target_uri)
            return f"Opened Windows {page_clean or 'Settings'}."
        except Exception as e:
            return f"Could not open settings: {e}"

    # Screenshots and recordings
    @staticmethod
    def take_screenshot(filename: str = "screenshot.png") -> str:
        save_path = Config.PROJECT_ROOT / filename
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(str(save_path))
            return f"Screenshot saved to {save_path}."
        except Exception as e:
            return f"Screenshot failed: {e}"

    @staticmethod
    def start_screen_recording() -> str:
        """Trigger native Windows Game Bar screen recording (Win + Alt + R)."""
        pyautogui.hotkey("win", "alt", "r")
        return "Screen recording started via Windows Game Bar (Win+Alt+R). Recordings save to Videos\\Captures."

    @staticmethod
    def stop_screen_recording() -> str:
        """Stop Windows Game Bar screen recording."""
        pyautogui.hotkey("win", "alt", "r")
        return "Screen recording stopped. Saved to Videos\\Captures folder."

    @staticmethod
    def toggle_screen_recording() -> str:
        pyautogui.hotkey("win", "alt", "r")
        return "Screen recording toggled (Win+Alt+R). Saved to Videos\\Captures."

    # Windows power controls
    @staticmethod
    def lock_pc() -> str:
        ctypes.windll.user32.LockWorkStation()
        return "PC locked."

    @staticmethod
    def shutdown_pc() -> str:
        os.system("shutdown /s /t 30")
        return "Shutdown scheduled in 30 seconds. Say 'cancel shutdown' to abort."

    @staticmethod
    def restart_pc() -> str:
        os.system("shutdown /r /t 30")
        return "Restart scheduled in 30 seconds."

    @staticmethod
    def cancel_shutdown() -> str:
        os.system("shutdown /a")
        return "Shutdown cancelled."

    @staticmethod
    def set_brightness(level: int) -> str:
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(level)
            return f"Brightness set to {level}%."
        except Exception as e:
            return f"Couldn't set brightness: {e}"

    # Window snapping and virtual desktops
    @staticmethod
    def snap_left() -> str:
        pyautogui.hotkey("win", "left")
        return "Snapped window left."

    @staticmethod
    def snap_right() -> str:
        pyautogui.hotkey("win", "right")
        return "Snapped window right."

    @staticmethod
    def toggle_task_view() -> str:
        pyautogui.hotkey("win", "tab")
        return "Toggled Task View."

    @staticmethod
    def new_virtual_desktop() -> str:
        pyautogui.hotkey("win", "ctrl", "d")
        return "Created new virtual desktop."

    @staticmethod
    def close_virtual_desktop() -> str:
        pyautogui.hotkey("win", "ctrl", "f4")
        return "Closed virtual desktop."

    @staticmethod
    def next_virtual_desktop() -> str:
        pyautogui.hotkey("win", "ctrl", "right")
        return "Switched to next virtual desktop."

    @staticmethod
    def prev_virtual_desktop() -> str:
        pyautogui.hotkey("win", "ctrl", "left")
        return "Switched to previous virtual desktop."

    @staticmethod
    def minimize_window() -> str:
        pyautogui.hotkey("win", "down")
        return "Window minimized."

    @staticmethod
    def maximize_window() -> str:
        pyautogui.hotkey("win", "up")
        return "Window maximized."

    @staticmethod
    def minimize_all() -> str:
        pyautogui.hotkey("win", "d")
        return "All windows minimized."

    @staticmethod
    def switch_window() -> str:
        pyautogui.hotkey("alt", "tab")
        return "Switched window."

    @staticmethod
    def close_window() -> str:
        pyautogui.hotkey("alt", "F4")
        return "Window closed."

    # Browser searches
    @staticmethod
    def open_url(url: str) -> str:
        import webbrowser
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened {url}."

    @staticmethod
    def search_google(query: str) -> str:
        import webbrowser
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        return f"Searching Google for '{query}'."

    @staticmethod
    def search_youtube(query: str) -> str:
        import webbrowser
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        webbrowser.open(url)
        return f"Searching YouTube for '{query}'."

    # Clipboard utilities
    @staticmethod
    def copy_text() -> str:
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.2)
        return "Copied to clipboard."

    @staticmethod
    def paste_text() -> str:
        pyautogui.hotkey("ctrl", "v")
        return "Pasted from clipboard."

    @staticmethod
    def read_clipboard() -> str:
        try:
            content = pyperclip.paste()
            if content:
                return content[:600]
            return "Clipboard is empty."
        except Exception:
            return "Couldn't read clipboard."

    @staticmethod
    def set_clipboard(text: str) -> str:
        pyperclip.copy(text)
        return "Text copied to clipboard."

    @staticmethod
    def type_text(text: str) -> str:
        """Paste text via clipboard for instant typing without keystroke lag."""
        if not text:
            return "Nothing to type."
        try:
            pyperclip.copy(text)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
            return f"Typed: {text[:50]}..."
        except Exception:
            pyautogui.write(text, interval=0.02)
            return f"Typed: {text[:50]}..."

    @staticmethod
    def open_notepad_and_write(text: str) -> str:
        """Open Notepad and write the specified text."""
        subprocess.Popen("notepad.exe")
        time.sleep(0.8)
        if text:
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        return f"Opened Notepad and wrote: {text[:60]}..."

    @staticmethod
    def save_current_url_or_link() -> str:
        """Copy active browser URL and log to saved_links.txt."""
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.3)

        url = pyperclip.paste().strip()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        notes_file = Config.PROJECT_ROOT / "saved_links.txt"
        with open(notes_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {url}\n")

        subprocess.Popen(["notepad.exe", str(notes_file)])
        return f"Link copied and saved to notes: {url}"

    @staticmethod
    def press_key(key: str) -> str:
        pyautogui.press(key)
        return f"Pressed {key}."

    @staticmethod
    def hotkey(*keys) -> str:
        pyautogui.hotkey(*keys)
        return f"Pressed {'+'.join(keys)}."

    def execute_action(self, action: dict) -> str:
        """Map action payload from AI output to PC methods."""
        action_name = action.get("action", "")
        target = action.get("target", "")
        value = action.get("value", "")

        action_map = {
            "open_app": lambda: self.open_app(target),
            "close_app": lambda: self.close_app(target),
            "open_url": lambda: self.open_url(target),
            "search_google": lambda: self.search_google(target),
            "search_youtube": lambda: self.search_youtube(target),
            "play_pause": lambda: self.media_play_pause(),
            "next_track": lambda: self.media_next(),
            "previous_track": lambda: self.media_previous(),
            "volume_up": lambda: self.volume_up(int(value) if value else 5),
            "volume_down": lambda: self.volume_down(int(value) if value else 5),
            "mute": lambda: self.volume_mute(),
            "screenshot": lambda: self.take_screenshot(),
            "record_screen": lambda: self.toggle_screen_recording(),
            "start_record": lambda: self.start_screen_recording(),
            "stop_record": lambda: self.stop_screen_recording(),
            "diagnostics": lambda: self.get_full_diagnostics(),
            "network_radar": lambda: self.get_network_radar(),
            "organize_desktop": lambda: self.organize_desktop(),
            "clean_ram": lambda: self.clean_ram(),
            "snap_left": lambda: self.snap_left(),
            "snap_right": lambda: self.snap_right(),
            "task_view": lambda: self.toggle_task_view(),
            "new_virtual_desktop": lambda: self.new_virtual_desktop(),
            "close_virtual_desktop": lambda: self.close_virtual_desktop(),
            "next_virtual_desktop": lambda: self.next_virtual_desktop(),
            "prev_virtual_desktop": lambda: self.prev_virtual_desktop(),
            "lock": lambda: self.lock_pc(),
            "shutdown": lambda: self.shutdown_pc(),
            "restart": lambda: self.restart_pc(),
            "cancel_shutdown": lambda: self.cancel_shutdown(),
            "brightness": lambda: self.set_brightness(int(value) if value else 50),
            "system_info": lambda: self.get_full_diagnostics(),
            "minimize": lambda: self.minimize_window(),
            "maximize": lambda: self.maximize_window(),
            "minimize_all": lambda: self.minimize_all(),
            "switch_window": lambda: self.switch_window(),
            "close_window": lambda: self.close_window(),
            "copy": lambda: self.copy_text(),
            "paste": lambda: self.paste_text(),
            "read_clipboard": lambda: self.read_clipboard(),
            "set_clipboard": lambda: self.set_clipboard(target),
            "type_text": lambda: self.type_text(target or value),
            "notepad_write": lambda: self.open_notepad_and_write(target or value),
            "save_link": lambda: self.save_current_url_or_link(),
            "press_key": lambda: self.press_key(target),
            "hotkey": lambda: self.hotkey(*target.split("+")),
            "open_website": lambda: self.open_url(target),
            "set_volume": lambda: self.set_volume_percent(int(value or target or 50)),
            "focus_window": lambda: self.focus_window(target),
            "open_settings": lambda: self.open_settings(target),
        }

        handler = action_map.get(action_name)
        if handler:
            return handler()
        return f"Unknown action: {action_name}"
