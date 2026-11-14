"""
Standard tool definitions for T.U.E.S.D.A.Y.
Wraps PCController, Utilities, WebSearch, and system actions into OpenAI-compatible tools.
"""

import ast
import gc
import operator
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import ctypes
import psutil

from core.tools import tool, record_undo_action, pop_last_undo_action
from core.config import Config
from modules.pc_control import PCController
from modules.utilities import Utilities
from modules.web_search import perform_live_web_search

_utils_instance = Utilities()


# ── Applications & Windows ────────────────────────────────────────────────

@tool(
    name="open_app",
    description="Open a desktop application, software, or browser by name (e.g. chrome, notepad, spotify, calculator).",
    params_schema={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Name of application to launch."}
        },
        "required": ["app_name"]
    },
    risk="low"
)
def open_app(app_name: str) -> str:
    url = _utils_instance.open_website(app_name)
    if url:
        return PCController.open_url(url)
    return PCController.open_app(app_name)


@tool(
    name="close_app",
    description="Close or terminate a running application process by name.",
    params_schema={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Name of application to terminate."}
        },
        "required": ["app_name"]
    },
    risk="low"
)
def close_app(app_name: str) -> str:
    return PCController.close_app(app_name)


@tool(
    name="focus_window",
    description="Switch active focus to an open window or application by name.",
    params_schema={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Target window title or app name."}
        },
        "required": ["app_name"]
    },
    risk="low"
)
def focus_window(app_name: str) -> str:
    return PCController.focus_window(app_name)


@tool(
    name="snap_left",
    description="Snap the currently focused window to the left half of the screen.",
    risk="low"
)
def snap_left() -> str:
    return PCController.snap_left()


@tool(
    name="snap_right",
    description="Snap the currently focused window to the right half of the screen.",
    risk="low"
)
def snap_right() -> str:
    return PCController.snap_right()


@tool(
    name="maximize_window",
    description="Maximize the active window to fill the screen.",
    risk="low"
)
def maximize_window() -> str:
    return PCController.maximize_window()


@tool(
    name="minimize_window",
    description="Minimize the currently active window.",
    risk="low"
)
def minimize_window() -> str:
    return PCController.minimize_window()


@tool(
    name="minimize_all",
    description="Minimize all open windows and show the Windows Desktop.",
    risk="low"
)
def minimize_all() -> str:
    return PCController.minimize_all()


@tool(
    name="toggle_task_view",
    description="Open or toggle the Windows Task View / virtual desktops switcher.",
    risk="low"
)
def toggle_task_view() -> str:
    return PCController.toggle_task_view()


@tool(
    name="new_virtual_desktop",
    description="Create a new clean Windows virtual desktop.",
    risk="low"
)
def new_virtual_desktop() -> str:
    return PCController.new_virtual_desktop()


@tool(
    name="close_virtual_desktop",
    description="Close the currently active virtual desktop.",
    risk="low"
)
def close_virtual_desktop() -> str:
    return PCController.close_virtual_desktop()


@tool(
    name="next_virtual_desktop",
    description="Switch to the next virtual desktop on the right.",
    risk="low"
)
def next_virtual_desktop() -> str:
    return PCController.next_virtual_desktop()


@tool(
    name="prev_virtual_desktop",
    description="Switch to the previous virtual desktop on the left.",
    risk="low"
)
def prev_virtual_desktop() -> str:
    return PCController.prev_virtual_desktop()


@tool(
    name="open_settings",
    description="Open Windows Settings page (e.g. bluetooth, wifi, sound, display, battery, update).",
    params_schema={
        "type": "object",
        "properties": {
            "page": {"type": "string", "description": "Specific settings category or empty for main."}
        },
        "required": []
    },
    risk="low"
)
def open_settings(page: str = "") -> str:
    return PCController.open_settings(page)


# ── Audio & Media ─────────────────────────────────────────────────────────

@tool(
    name="set_volume",
    description="Set the master volume to an exact percentage (0 to 100).",
    params_schema={
        "type": "object",
        "properties": {
            "percent": {"type": "integer", "description": "Volume percentage from 0 to 100."}
        },
        "required": ["percent"]
    },
    risk="low"
)
def set_volume(percent: int) -> str:
    return PCController.set_volume_percent(percent)


@tool(
    name="volume_up",
    description="Increase master volume by a step amount.",
    params_schema={
        "type": "object",
        "properties": {
            "amount": {"type": "integer", "description": "Number of step increments (default 5)."}
        },
        "required": []
    },
    risk="low"
)
def volume_up(amount: int = 5) -> str:
    return PCController.volume_up(amount)


@tool(
    name="volume_down",
    description="Decrease master volume by a step amount.",
    params_schema={
        "type": "object",
        "properties": {
            "amount": {"type": "integer", "description": "Number of step decrements (default 5)."}
        },
        "required": []
    },
    risk="low"
)
def volume_down(amount: int = 5) -> str:
    return PCController.volume_down(amount)


@tool(
    name="volume_mute",
    description="Toggle audio mute on or off.",
    risk="low"
)
def volume_mute() -> str:
    return PCController.volume_mute()


@tool(
    name="media_play_pause",
    description="Play or pause current media playback (Spotify, YouTube, browser, media player).",
    risk="low"
)
def media_play_pause() -> str:
    return PCController.media_play_pause()


@tool(
    name="media_next",
    description="Skip to the next audio or video track.",
    risk="low"
)
def media_next() -> str:
    return PCController.media_next()


@tool(
    name="media_previous",
    description="Go back to the previous audio or video track.",
    risk="low"
)
def media_previous() -> str:
    return PCController.media_previous()


# ── System Diagnostics & Screen ───────────────────────────────────────────

@tool(
    name="get_diagnostics",
    description="Retrieve comprehensive system telemetry: CPU usage, RAM utilization, C: drive disk space, top processes, and battery status.",
    risk="low"
)
def get_diagnostics() -> str:
    return PCController.get_full_diagnostics()


@tool(
    name="get_network_radar",
    description="Inspect network status: local subnet IP, public WAN IP, and ping round-trip latency.",
    risk="low"
)
def get_network_radar() -> str:
    return PCController.get_network_radar()


@tool(
    name="take_screenshot",
    description="Capture a full screenshot of the screen and save to disk.",
    params_schema={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "Destination filename (default 'screenshot.png')."}
        },
        "required": []
    },
    risk="low"
)
def take_screenshot(filename: str = "screenshot.png") -> str:
    return PCController.take_screenshot(filename)


@tool(
    name="start_screen_recording",
    description="Start Windows Game Bar screen recording (Win + Alt + R).",
    risk="low"
)
def start_screen_recording() -> str:
    return PCController.start_screen_recording()


@tool(
    name="stop_screen_recording",
    description="Stop active screen recording and save video to Captures folder.",
    risk="low"
)
def stop_screen_recording() -> str:
    return PCController.stop_screen_recording()


@tool(
    name="toggle_screen_recording",
    description="Toggle screen recording on or off.",
    risk="low"
)
def toggle_screen_recording() -> str:
    return PCController.toggle_screen_recording()


@tool(
    name="clean_ram",
    description="Perform real memory optimization: run Python garbage collection and trim process working sets, reporting honest metrics.",
    risk="low"
)
def clean_ram() -> str:
    collected = gc.collect()
    try:
        ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
    except Exception:
        pass
    ram = psutil.virtual_memory()
    available_gb = round(ram.available / (1024**3), 2)
    return (
        f"Memory optimization complete. Python GC freed {collected} objects. "
        f"System RAM: {available_gb} GB available ({ram.percent}% utilized)."
    )


# ── File & Desktop Management with Undo ───────────────────────────────────

@tool(
    name="organize_desktop",
    description="Scan Desktop for loose files and organize them into categorized folders (Images, Documents, Installers, Media), logging moves to undo journal.",
    risk="high",
    confirmation_prompt="Bhai, kya sach mein Desktop ke saare files organize kar doon?"
)
def organize_desktop() -> str:
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        return "Desktop directory not found."

    categories = {
        "Images": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"],
        "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".pptx"],
        "Installers": [".exe", ".msi", ".zip", ".rar", ".7z", ".tar", ".gz"],
        "Media": [".mp4", ".mkv", ".mp3", ".wav", ".avi", ".mov"]
    }

    moves = []
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
                moves.append({"src": str(item), "dest": str(dest)})
            except Exception:
                pass

    if moves:
        record_undo_action("organize_desktop", {"moves": moves})
        return f"Desktop organized! Categorized {len(moves)} loose files into folders. (Say 'undo desktop' to reverse)."
    return "Desktop is already clean and organized."


@tool(
    name="undo_desktop_organize",
    description="Revert the last Desktop organization action by restoring moved files to their original locations.",
    risk="low"
)
def undo_desktop_organize() -> str:
    entry = pop_last_undo_action()
    if not entry or entry.get("tool") != "organize_desktop":
        return "No recent Desktop organization action found to undo."

    moves = entry.get("data", {}).get("moves", [])
    restored = 0
    for m in moves:
        src = Path(m["src"])
        dest = Path(m["dest"])
        if dest.exists():
            try:
                shutil.move(str(dest), str(src))
                restored += 1
            except Exception:
                pass

    return f"Desktop organization undone. Restored {restored} files back to Desktop."


# ── Note Writing, Clipboard & Browser ─────────────────────────────────────

@tool(
    name="notepad_write",
    description="Open Windows Notepad and type the specified text into it.",
    params_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to write into Notepad."}
        },
        "required": ["text"]
    },
    risk="low"
)
def notepad_write(text: str) -> str:
    return PCController.open_notepad_and_write(text)


@tool(
    name="search_google",
    description="Open browser and perform a Google web search for query.",
    params_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query terms."}
        },
        "required": ["query"]
    },
    risk="low"
)
def search_google(query: str) -> str:
    return PCController.search_google(query)


@tool(
    name="search_youtube",
    description="Open YouTube in browser and search for videos.",
    params_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Video search query."}
        },
        "required": ["query"]
    },
    risk="low"
)
def search_youtube(query: str) -> str:
    return PCController.search_youtube(query)


@tool(
    name="save_browser_link",
    description="Copy the active browser URL and save it to saved_links.txt notes.",
    risk="low"
)
def save_browser_link() -> str:
    return PCController.save_current_url_or_link()


# ── Information, Weather & News ───────────────────────────────────────────

@tool(
    name="get_weather",
    description="Fetch current weather condition and temperature for a city.",
    params_schema={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name (optional, defaults to configured city)."}
        },
        "required": []
    },
    risk="low"
)
def get_weather(city: Optional[str] = None) -> str:
    return _utils_instance.get_weather(city)


@tool(
    name="get_news",
    description="Fetch live news headlines from Google News RSS.",
    params_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Topic or keyword (e.g. 'tech', 'india', 'ai')."},
            "count": {"type": "integer", "description": "Number of headlines to return (default 4)."}
        },
        "required": []
    },
    risk="low"
)
def get_news(query: Optional[str] = None, count: int = 4) -> str:
    return _utils_instance.get_news(query, count)


@tool(
    name="get_datetime",
    description="Get current day, date, and local time.",
    risk="low"
)
def get_datetime() -> str:
    return _utils_instance.get_datetime()


# ── Timers & Math ─────────────────────────────────────────────────────────

@tool(
    name="set_timer",
    description="Set a countdown timer in seconds.",
    params_schema={
        "type": "object",
        "properties": {
            "seconds": {"type": "integer", "description": "Duration in seconds."},
            "label": {"type": "string", "description": "Timer label or purpose."}
        },
        "required": ["seconds"]
    },
    risk="low"
)
def set_timer(seconds: int, label: str = "Timer") -> str:
    return _utils_instance.set_timer(seconds, label)


@tool(
    name="cancel_timer",
    description="Cancel an active running timer by label.",
    params_schema={
        "type": "object",
        "properties": {
            "label": {"type": "string", "description": "Label of timer to cancel."}
        },
        "required": ["label"]
    },
    risk="low"
)
def cancel_timer(label: str) -> str:
    return _utils_instance.cancel_timer(label)


@tool(
    name="calculate_math",
    description="Safely evaluate a mathematical calculation expression.",
    params_schema={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Math expression (e.g. '45 * 12 + 10')."}
        },
        "required": ["expression"]
    },
    risk="low"
)
def calculate_math(expression: str) -> str:
    """Safe AST-based arithmetic expression evaluator."""
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type in operators:
                return operators[op_type](left, right)
            raise ValueError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op_type = type(node.op)
            if op_type in operators:
                return operators[op_type](operand)
            raise ValueError(f"Unsupported operator: {op_type}")
        else:
            raise ValueError("Invalid mathematical syntax.")

    try:
        clean_expr = expression.replace("^", "**").replace("x", "*").replace("÷", "/")
        tree = ast.parse(clean_expr, mode="eval")
        result = _eval(tree.body)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Could not calculate '{expression}': {e}"


# ── High-Risk Power & System Controls ─────────────────────────────────────

@tool(
    name="lock_pc",
    description="Lock the Windows PC workstation.",
    risk="high",
    confirmation_prompt="Bhai, kya sach mein PC lock kar doon?"
)
def lock_pc() -> str:
    return PCController.lock_pc()


@tool(
    name="shutdown_pc",
    description="Schedule a Windows PC shutdown in 30 seconds.",
    risk="high",
    confirmation_prompt="Bhai, kya sach mein PC shutdown kar doon?"
)
def shutdown_pc() -> str:
    return PCController.shutdown_pc()


@tool(
    name="restart_pc",
    description="Schedule a Windows PC restart in 30 seconds.",
    risk="high",
    confirmation_prompt="Bhai, kya sach mein PC restart kar doon?"
)
def restart_pc() -> str:
    return PCController.restart_pc()


@tool(
    name="cancel_shutdown",
    description="Abort a scheduled shutdown or restart.",
    risk="low"
)
def cancel_shutdown() -> str:
    return PCController.cancel_shutdown()


@tool(
    name="empty_recycle_bin",
    description="Silently empty the Windows Recycle Bin to reclaim storage.",
    risk="high",
    confirmation_prompt="Bhai, kya sach mein Recycle Bin empty kar doon? Files permanently delete ho jayengi."
)
def empty_recycle_bin() -> str:
    return PCController.empty_recycle_bin()


@tool(
    name="set_brightness",
    description="Adjust screen brightness to a percentage (0 to 100).",
    params_schema={
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "Brightness percentage from 0 to 100."}
        },
        "required": ["level"]
    },
    risk="low"
)
def set_brightness(level: int) -> str:
    return PCController.set_brightness(level)


# ── Long-Term Memory & Semantic Knowledge ─────────────────────────────────

@tool(
    name="remember_fact",
    description="Store a durable user fact into SQLite long-term memory (e.g. personal details, preferences, projects, schedules, dates).",
    params_schema={
        "type": "object",
        "properties": {
            "fact": {"type": "string", "description": "The exact fact statement to remember."},
            "key": {"type": "string", "description": "Short identifier key (optional, e.g. 'exam_date', 'girlfriend_name')."},
            "category": {"type": "string", "description": "Category: personal, work, preference, schedule, or general."}
        },
        "required": ["fact"]
    },
    risk="low"
)
def remember_fact(fact: str, key: Optional[str] = None, category: str = "general") -> str:
    from core.memory import MemoryStore
    return MemoryStore().save_fact(fact, key=key, category=category)


@tool(
    name="recall_facts",
    description="Recall stored durable user facts from SQLite database by category or keyword search.",
    params_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keyword to search in stored facts."},
            "category": {"type": "string", "description": "Optional category filter."}
        },
        "required": []
    },
    risk="low"
)
def recall_facts(query: Optional[str] = None, category: Optional[str] = None) -> str:
    from core.memory import MemoryStore
    facts = MemoryStore().recall_facts(category=category, query=query)
    if not facts:
        return "No matching user facts found in long-term memory."
    lines = [f"- [{f['category'].title()}] {f['key']}: {f['value']}" for f in facts]
    return "Stored user facts:\n" + "\n".join(lines)


@tool(
    name="forget_fact",
    description="Remove a specific user fact from long-term memory by key or keyword match.",
    params_schema={
        "type": "object",
        "properties": {
            "key_or_fact": {"type": "string", "description": "The key or text of the fact to forget."}
        },
        "required": ["key_or_fact"]
    },
    risk="low"
)
def forget_fact(key_or_fact: str) -> str:
    from core.memory import MemoryStore
    return MemoryStore().forget_fact(key_or_fact)


@tool(
    name="update_fact",
    description="Update an existing stored fact in SQLite with a new value.",
    params_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key of the fact to update."},
            "new_value": {"type": "string", "description": "New updated value."}
        },
        "required": ["key", "new_value"]
    },
    risk="low"
)
def update_fact(key: str, new_value: str) -> str:
    from core.memory import MemoryStore
    return MemoryStore().update_fact(key, new_value)


@tool(
    name="search_memory",
    description="Perform semantic vector search across all past dialogue turns in ChromaDB.",
    params_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The concept or question to look up in past conversations."},
            "limit": {"type": "integer", "description": "Number of relevant dialogue turns to return (default 3)."}
        },
        "required": ["query"]
    },
    risk="low"
)
def search_memory(query: str, limit: int = 3) -> str:
    from core.memory import MemoryStore
    return MemoryStore().search_memory(query, limit=limit)
