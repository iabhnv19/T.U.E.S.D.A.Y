"""
Data-driven zero-latency command parser for T.U.E.S.D.A.Y.
Maps spoken user requests directly to registered @tool actions via regex and rapidfuzz.
"""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from core.tools import ConfirmationManager, execute_tool, get_tool
from modules.pc_control import PCController
from modules.utilities import Utilities

KNOWN_APPS = [
    "chrome", "google chrome", "browser", "firefox", "notepad", "calculator", "calc",
    "explorer", "file explorer", "cmd", "command prompt", "terminal", "powershell",
    "task manager", "settings", "control panel", "paint", "word", "excel",
    "powerpoint", "spotify", "discord", "vscode", "vs code", "visual studio code",
    "vlc", "obs", "steam", "snipping tool"
]

# Pre-frozen set for fast O(1) lookup instead of linear scan
_KNOWN_APPS_SET = frozenset(KNOWN_APPS)


def _match_app_fuzzy(raw_name: str) -> str:
    """Resolve spoken app names or typos using rapidfuzz string similarity."""
    clean = raw_name.lower().strip()
    if not clean:
        return raw_name
    # Fast exact check before expensive fuzzy scoring
    if clean in _KNOWN_APPS_SET:
        return clean
    match = process.extractOne(clean, KNOWN_APPS, scorer=fuzz.ratio)
    if match and match[1] >= 75:
        return match[0]
    return clean


# ── Pre-compiled normalizer patterns (compiled once at import, not per call) ──
_RE_WAKEWORD = re.compile(r"^(?:hey\s+|hi\s+|hello\s+|ok\s+|okay\s+)?tuesday[,:\s]*", re.IGNORECASE)
_RE_TUESDAY_INLINE = re.compile(r"^tuesday[,:\s]*", re.IGNORECASE)
_COMPILED_PREFIX_PATTERNS = [
    re.compile(r"^(?:please|kripya|kindly)\s+", re.IGNORECASE),
    re.compile(r"^(?:can\s+you|could\s+you|would\s+you)(?:\s+please)?\s+", re.IGNORECASE),
    re.compile(r"^(?:bhai|yaar|dost|bro|sir|boss)\s+", re.IGNORECASE),
    re.compile(r"^(?:suno|sun|achha\s+suno|achha|acha|zara|zarra|dekh|dekho)\s+", re.IGNORECASE),
    re.compile(r"^(?:ek\s+kaam\s+karo|ek\s+kaam\s+kar|ek\s+cheez\s+karo)\s+", re.IGNORECASE),
    re.compile(r"^(?:just|jaldi\s+se|fatfat|jaldi)\s+", re.IGNORECASE),
    re.compile(r"^(?:mujhe|meri|mera)\s+", re.IGNORECASE),
    re.compile(r"^(?:yes|yeah|yep|sure|haan|ha|ok|okay)\s+", re.IGNORECASE),
    re.compile(r"^(?:i\s+need|i\s+want|give\s+me|show\s+me|start\s+with|begin\s+with|provide|tell\s+me)(?:\s+a|\s+an|\s+the|\s+me)?\s+", re.IGNORECASE),
    re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE),
]
_COMPILED_SUFFIX_PATTERNS = [
    re.compile(r"\s+(?:please|kindly)$", re.IGNORECASE),
    re.compile(r"\s+(?:na|yaar|bhai|bro|boss)$", re.IGNORECASE),
    re.compile(r"\s+(?:jaldi|turant|fast|now)$", re.IGNORECASE),
    re.compile(r"\s+(?:kardo|kar\s+do|karna|karo)$", re.IGNORECASE),
]
_RE_MATH_EXPR = re.compile(r"\d+\s*[\+\-\*\/\^x÷]\s*\d+")
_ACTION_PHRASES = ["kar do", "khol do", "band karo", "chala do", "likh do", "bata do mausam", "yaad rakhna", "bhool jao"]


def normalize_command_text(text: str) -> str:
    """
    Clean conversational filler words, assistant names, and polite phrasing from spoken text.
    E.g.: 'Tuesday please open chrome' -> 'open chrome'
          'Bhai volume 50 kar do' -> 'volume 50'
          'Acha suno gaana roko' -> 'gaana roko'
    """
    if not text:
        return ""
    clean = text.lower().strip()

    # Strip wake-word / greeting prefixes
    clean = _RE_WAKEWORD.sub("", clean).strip()

    # Iteratively strip conversational lead-ins
    changed = True
    while changed:
        old = clean
        for pat in _COMPILED_PREFIX_PATTERNS:
            clean = pat.sub("", clean).strip()
        # In case wake-word followed filler e.g. "bhai tuesday open chrome"
        clean = _RE_TUESDAY_INLINE.sub("", clean).strip()
        changed = (old != clean)

    # Strip trailing polite tags or colloquial endings
    for spat in _COMPILED_SUFFIX_PATTERNS:
        clean = spat.sub("", clean).strip()

    return clean


ACTION_KEYWORDS = {
    # Apps & Execution
    "open", "launch", "start", "run", "close", "kill", "quit", "exit", "focus", "switch",
    "kholo", "khol", "chalao", "chala", "band", "hatao", "rok", "roko",
    # Screen & Vision & OCR
    "screen", "screenshot", "ocr", "click", "button", "type", "field", "window",
    "maximize", "minimize", "snap", "controls", "desktop", "padho", "read", "dekho",
    # Media & Audio & System
    "volume", "awaaz", "mute", "unmute", "brightness", "media", "music", "gaana",
    "song", "play", "pause", "skip", "next", "previous", "track",
    # Hardware & Diagnostics
    "shutdown", "restart", "reboot", "lock", "ram", "cpu", "specs", "network", "ping", "ip", "battery",
    # Productivity
    "reminder", "remind", "alarm", "timer", "todo", "task", "note", "routine", "briefing", "brief", "mood",
    "schedule", "email", "mail", "unread", "calendar",
    # Files & Storage
    "file", "folder", "directory", "files", "zip", "compress", "move", "rename", "delete",
    "summarize", "docx", "pdf", "organize", "trash", "recycle",
    # Math & Computation
    "calculate", "computation", "compute", "multiplied", "multiply", "divide", "divided",
    "plus", "minus", "hisab", "math",
    # Action verbs
    "kardo", "kar do", "banao", "likho", "dikhado", "dikhao", "dhundo",
}


def has_action_intent(text: str) -> bool:
    """
    Determine if a spoken text indicates an intent to execute a PC/OS/productivity tool.
    Returns False for pure conversational queries (e.g. 'Tell me a joke', 'Who is Iron Man?').
    """
    if not text:
        return False
    lower = text.lower()
    words = set(re.findall(r"\b\w+\b", lower))
    if words & ACTION_KEYWORDS:
        return True
    # Math expressions like "7 * 8" or "15 + 20"
    if _RE_MATH_EXPR.search(lower):
        return True
    return any(p in lower for p in _ACTION_PHRASES)


class CommandParser:
    """Pre-processes spoken queries with table-driven pattern matching and direct tool invocation."""

    def __init__(self, pc: Optional[PCController] = None, utils: Optional[Utilities] = None, brain=None):
        self.pc = pc or PCController()
        self.utils = utils or Utilities()
        self.brain = brain
        self._build_command_table()

    def _build_command_table(self):
        """Construct table of compiled regex patterns mapped to tool names and argument builders."""
        self._exact_commands: Dict[str, Tuple[str, Dict[str, Any]]] = {
            # Media playback
            "play": ("media_play_pause", {}),
            "pause": ("media_play_pause", {}),
            "play pause": ("media_play_pause", {}),
            "pause music": ("media_play_pause", {}),
            "play music": ("media_play_pause", {}),
            "chalao": ("media_play_pause", {}),
            "gaana chalao": ("media_play_pause", {}),
            "gaana bajao": ("media_play_pause", {}),
            "gaana chala do": ("media_play_pause", {}),
            "music chalao": ("media_play_pause", {}),
            "roko": ("media_play_pause", {}),
            "gaana roko": ("media_play_pause", {}),
            "gaana rok do": ("media_play_pause", {}),
            "music roko": ("media_play_pause", {}),
            "pause karo": ("media_play_pause", {}),
            "play karo": ("media_play_pause", {}),
            "next": ("media_next", {}),
            "next track": ("media_next", {}),
            "next song": ("media_next", {}),
            "skip": ("media_next", {}),
            "agla gaana": ("media_next", {}),
            "agla song": ("media_next", {}),
            "agla": ("media_next", {}),
            "previous": ("media_previous", {}),
            "previous track": ("media_previous", {}),
            "previous song": ("media_previous", {}),
            "prev": ("media_previous", {}),
            "pichla gaana": ("media_previous", {}),
            "pichla song": ("media_previous", {}),
            "mute": ("volume_mute", {}),
            "unmute": ("volume_mute", {}),
            "shant": ("volume_mute", {}),
            "awaaz band": ("volume_mute", {}),
            "mute audio": ("volume_mute", {}),
            "mute karo": ("volume_mute", {}),
            "unmute karo": ("volume_mute", {}),

            # Volume steps
            "volume up": ("volume_up", {"amount": 5}),
            "awaaz badhao": ("volume_up", {"amount": 5}),
            "volume badhao": ("volume_up", {"amount": 5}),
            "volume badha do": ("volume_up", {"amount": 5}),
            "increase volume": ("volume_up", {"amount": 5}),
            "sound badhao": ("volume_up", {"amount": 5}),
            "awaaz tez karo": ("volume_up", {"amount": 5}),
            "volume down": ("volume_down", {"amount": 5}),
            "awaaz kam karo": ("volume_down", {"amount": 5}),
            "volume kam karo": ("volume_down", {"amount": 5}),
            "volume kam kar do": ("volume_down", {"amount": 5}),
            "decrease volume": ("volume_down", {"amount": 5}),
            "sound kam karo": ("volume_down", {"amount": 5}),
            "awaaz dheere karo": ("volume_down", {"amount": 5}),

            # Window layout
            "snap left": ("snap_left", {}),
            "left snap": ("snap_left", {}),
            "snap right": ("snap_right", {}),
            "right snap": ("snap_right", {}),
            "maximize": ("maximize_window", {}),
            "bada karo": ("maximize_window", {}),
            "fullscreen": ("maximize_window", {}),
            "minimize": ("minimize_window", {}),
            "chhota karo": ("minimize_window", {}),
            "minimize all": ("minimize_all", {}),
            "show desktop": ("minimize_all", {}),
            "desktop dikhao": ("minimize_all", {}),
            "task view": ("toggle_task_view", {}),
            "new desktop": ("new_virtual_desktop", {}),
            "close desktop": ("close_virtual_desktop", {}),
            "next desktop": ("next_virtual_desktop", {}),
            "previous desktop": ("prev_virtual_desktop", {}),

            # Screen & Diagnostics
            "screenshot": ("take_screenshot", {}),
            "screen shot": ("take_screenshot", {}),
            "take screenshot": ("take_screenshot", {}),
            "take a screenshot": ("take_screenshot", {}),
            "screenshot lo": ("take_screenshot", {}),
            "screenshot le lo": ("take_screenshot", {}),
            "screenshot kheencho": ("take_screenshot", {}),
            "screenshot kheench do": ("take_screenshot", {}),
            "start recording": ("start_screen_recording", {}),
            "record screen": ("start_screen_recording", {}),
            "screen recording start": ("start_screen_recording", {}),
            "stop recording": ("stop_screen_recording", {}),
            "screen recording stop": ("stop_screen_recording", {}),
            "recording band karo": ("stop_screen_recording", {}),
            "system info": ("get_diagnostics", {}),
            "diagnostics": ("get_diagnostics", {}),
            "pc specs": ("get_diagnostics", {}),
            "clean ram": ("clean_ram", {}),
            "free ram": ("clean_ram", {}),
            "ram saaf karo": ("clean_ram", {}),
            "optimize ram": ("clean_ram", {}),
            "network radar": ("get_network_radar", {}),
            "my ip": ("get_network_radar", {}),
            "ping": ("get_network_radar", {}),

            # Desktop organize & undo
            "organize desktop": ("organize_desktop", {}),
            "desktop saaf karo": ("organize_desktop", {}),
            "clean desktop": ("organize_desktop", {}),
            "desktop organize karo": ("organize_desktop", {}),
            "undo desktop": ("undo_desktop_organize", {}),
            "undo organize": ("undo_desktop_organize", {}),
            "undo that": ("undo_desktop_organize", {}),
            "undo": ("undo_desktop_organize", {}),

            # High risk controls
            "lock pc": ("lock_pc", {}),
            "pc lock karo": ("lock_pc", {}),
            "lock screen": ("lock_pc", {}),
            "shutdown": ("shutdown_pc", {}),
            "shutdown pc": ("shutdown_pc", {}),
            "pc band karo": ("shutdown_pc", {}),
            "restart pc": ("restart_pc", {}),
            "reboot": ("restart_pc", {}),
            "cancel shutdown": ("cancel_shutdown", {}),
            "shutdown roko": ("cancel_shutdown", {}),
            "empty recycle bin": ("empty_recycle_bin", {}),
            "recycle bin saaf karo": ("empty_recycle_bin", {}),

            # Utilities
            "weather": ("get_weather", {}),
            "mausam kaisa hai": ("get_weather", {}),
            "news": ("get_news", {}),
            "headlines": ("get_news", {}),
            "aaj ki news": ("get_news", {}),
            "breaking news": ("get_news", {}),
            "current time": ("get_datetime", {}),
            "time kya hua": ("get_datetime", {}),
            "what time is it": ("get_datetime", {}),
            "save this link": ("save_browser_link", {}),
            "save link": ("save_browser_link", {}),

            # Long-term Memory & Mood
            "what do you know about me": ("recall_facts", {}),
            "who am i": ("recall_facts", {}),
            "mere baare mein kya janti ho": ("recall_facts", {}),
            "kya yaad hai mere baare mein": ("recall_facts", {}),
            "recall facts": ("recall_facts", {}),
            "how was my mood this week": ("get_mood_summary", {"days": 7}),
            "my mood this week": ("get_mood_summary", {"days": 7}),
            "mood history": ("get_mood_summary", {"days": 7}),
            "mood summary": ("get_mood_summary", {"days": 7}),
            "mera mood kaisa tha": ("get_mood_summary", {"days": 7}),
            "mera mood kaisa raha": ("get_mood_summary", {"days": 7}),

            # Phase 4 Screen & OCR
            "what's on my screen": ("analyze_screen", {}),
            "what is on my screen": ("analyze_screen", {}),
            "screen dekho": ("analyze_screen", {}),
            "analyze screen": ("analyze_screen", {}),
            "active window": ("get_active_window", {}),
            "focused window": ("get_active_window", {}),
            "read this text": ("get_selected_text", {}),
            "selected text": ("get_selected_text", {}),
            "read screen": ("read_screen_text", {}),
            "screen text": ("read_screen_text", {}),
            "screen padho": ("read_screen_text", {}),
            "list controls": ("list_window_controls", {}),
            "window controls": ("list_window_controls", {}),

            # Phase 5 Files
            "undo file": ("undo_file_action", {}),
            "undo move": ("undo_file_action", {}),
            "undo file action": ("undo_file_action", {}),

            # Phase 6 Browser
            "close browser": ("browser_close", {}),
            "browser band karo": ("browser_close", {}),

            # Phase 7 Productivity & Daily Briefing
            "daily briefing": ("get_daily_briefing", {}),
            "good morning": ("get_daily_briefing", {}),
            "morning briefing": ("get_daily_briefing", {}),
            "briefing": ("get_daily_briefing", {}),
            "quick brief": ("get_daily_briefing", {}),
            "quick briefing": ("get_daily_briefing", {}),
            "brief": ("get_daily_briefing", {}),
            "daily brief": ("get_daily_briefing", {}),
            "morning brief": ("get_daily_briefing", {}),
            "give me a brief": ("get_daily_briefing", {}),
            "give me a briefing": ("get_daily_briefing", {}),
            "give me a quick brief": ("get_daily_briefing", {}),
            "need a quick brief": ("get_daily_briefing", {}),
            "i need a quick brief": ("get_daily_briefing", {}),
            "start briefing": ("get_daily_briefing", {}),
            "aaj ka update": ("get_daily_briefing", {}),
            "list reminders": ("list_reminders", {}),
            "show reminders": ("list_reminders", {}),
            "reminders dikhao": ("list_reminders", {}),
            "list todos": ("list_todos", {}),
            "my tasks": ("list_todos", {}),
            "to do list": ("list_todos", {}),
            "kya kaam hai": ("list_todos", {}),
            "list notes": ("list_notes", {}),
            "my notes": ("list_notes", {}),
            "notes dikhao": ("list_notes", {}),
            "list routines": ("list_routines", {}),
            "available routines": ("list_routines", {}),
            "study mode": ("run_routine", {"name": "study mode"}),
            "focus mode": ("run_routine", {"name": "focus mode"}),
            "good night": ("run_routine", {"name": "good night"}),
            "my schedule": ("get_schedule", {"day": "today"}),
            "today's schedule": ("get_schedule", {"day": "today"}),
            "unread emails": ("list_unread_emails", {}),
            "check emails": ("list_unread_emails", {}),
            "check mail": ("list_unread_emails", {}),
            "analyze screen": ("analyze_screen", {}),
            "what is on my screen": ("analyze_screen", {}),
            "what's on my screen": ("analyze_screen", {}),
            "read screen text": ("read_screen_text", {}),
            "read screen": ("read_screen_text", {}),
        }

        # Table of regex patterns for parameter extraction
        self._pattern_table: List[Tuple[re.Pattern, str, Callable[[re.Match], Dict[str, Any]]]] = [
            # Volume percent
            (
                re.compile(r"(?:set volume to|volume karo|awaaz karo)\s+(\d+)(?:%| percent)?", re.I),
                "set_volume",
                lambda m: {"percent": int(m.group(1))},
            ),
            (
                re.compile(r"^volume\s+(\d+)$", re.I),
                "set_volume",
                lambda m: {"percent": int(m.group(1))},
            ),
            # Screen brightness
            (
                re.compile(r"(?:set brightness to|brightness karo)\s+(\d+)", re.I),
                "set_brightness",
                lambda m: {"level": int(m.group(1))},
            ),
            # Web searches
            (
                re.compile(r"(?:search google for|google search|search on google|google par search karo|google karo)\s+(.+)", re.I),
                "search_google",
                lambda m: {"query": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:search youtube for|youtube search|search on youtube|youtube par search karo|play on youtube|youtube pe chalao)\s+(.+)", re.I),
                "search_youtube",
                lambda m: {"query": m.group(1).strip()},
            ),
            # Weather with city
            (
                re.compile(r"(?:weather in|weather of|mausam)\s+([a-zA-Z\s]+)", re.I),
                "get_weather",
                lambda m: {"city": m.group(1).strip()},
            ),
            # News with topic
            (
                re.compile(r"(?:news about|khabar)\s+([a-zA-Z0-9\s]+)", re.I),
                "get_news",
                lambda m: {"query": m.group(1).strip(), "count": 4},
            ),
            # Notepad write
            (
                re.compile(r"(?:open notepad (?:and|&) write|notepad kholo aur likho|write in notepad)\s+(.+)", re.I),
                "notepad_write",
                lambda m: {"text": m.group(1).strip()},
            ),
            # Timers
            (
                re.compile(r"(?:set a? timer for|timer lagao)\s+(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)", re.I),
                "set_timer",
                self._extract_timer_args,
            ),
            # Math
            (
                re.compile(r"(?:calculate|compute|hisab karo)\s+([\d\s\+\-\*\/\^\(\)\.\%x÷]+)", re.I),
                "calculate_math",
                lambda m: {"expression": m.group(1).strip()},
            ),
            # Settings
            (
                re.compile(r"(?:open|launch)\s+([a-zA-Z]+)\s+settings", re.I),
                "open_settings",
                lambda m: {"page": m.group(1).strip()},
            ),
            # Phase 4 Screen & UI actions
            (
                re.compile(r"(?:click on|click button|button dabao|click)\s+(.+)", re.I),
                "click_button",
                lambda m: {"button_name": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:type|likho)\s+(.+?)\s+into\s+(.+)", re.I),
                "type_into_field",
                lambda m: {"text": m.group(1).strip(), "field_name": m.group(2).strip()},
            ),
            # Phase 5 File & Knowledge actions
            (
                re.compile(r"(?:search files? for|find files?|file dhundo|search file)\s+(.+)", re.I),
                "search_files",
                lambda m: {"query": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:read file|file padho)\s+(.+)", re.I),
                "read_file_content",
                lambda m: {"file_path": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:summarize file|file summarize karo)\s+(.+)", re.I),
                "summarize_file",
                lambda m: {"file_path": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:zip folder|compress folder|zip karo)\s+(.+)", re.I),
                "zip_folder",
                lambda m: {"folder_path": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:open file|file kholo)\s+(.+)", re.I),
                "open_file",
                lambda m: {"file_path": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:index folder|folder index karo)\s+(.+)", re.I),
                "index_folder",
                lambda m: {"folder_path": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:ask docs|ask documents|search docs)\s+(.+)", re.I),
                "ask_documents",
                lambda m: {"query": m.group(1).strip()},
            ),
            # Phase 6 Browser actions
            (
                re.compile(r"(?:open browser to|browse to|open url)\s+(.+)", re.I),
                "browser_open",
                lambda m: {"url": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:browser search|search in browser)\s+(.+)", re.I),
                "browser_search",
                lambda m: {"query": m.group(1).strip()},
            ),
            # OCR Screen Action patterns
            (
                re.compile(r"(?:click on text|click text|screen pe click karo|click text on screen)\s+(.+)", re.I),
                "click_text_on_screen",
                lambda m: {"text": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:find text|find on screen|screen pe dhoondo)\s+(.+)", re.I),
                "find_text_on_screen",
                lambda m: {"query": m.group(1).strip()},
            ),
            # Phase 7 Productivity patterns
            (
                re.compile(r"^(?:(?:i\s+need|give\s+me|show\s+me|start\s+with|begin\s+with)\s+)?(?:a\s+)?(?:quick\s+|daily\s+|morning\s+)?brief(?:ing)?(?:\s+please|\s+sir|\s+boss)?$", re.I),
                "get_daily_briefing",
                lambda m: {},
            ),
            (
                re.compile(r"(?:remind me to|reminder lagao)\s+(.+?)\s+in\s+(\d+)\s*(?:minutes?|mins?)", re.I),
                "add_reminder",
                lambda m: {"text": m.group(1).strip(), "minutes_from_now": int(m.group(2))},
            ),
            (
                re.compile(r"(?:remind me to|reminder lagao)\s+(.+?)\s+at\s+([\d:]+\s*(?:am|pm)?)", re.I),
                "add_reminder",
                lambda m: {"text": m.group(1).strip(), "due_time": m.group(2).strip()},
            ),
            (
                re.compile(r"(?:add todo|add task|task jodo)\s+(.+)", re.I),
                "add_todo",
                lambda m: {"task": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:complete todo|done task|task complete karo)\s+(.+)", re.I),
                "complete_todo",
                lambda m: {"task": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:add note|take note|note likho)\s+(.+)", re.I),
                "add_note",
                lambda m: {"title": m.group(1).strip()[:30], "content": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:run routine|start routine|routine chalao)\s+(.+)", re.I),
                "run_routine",
                lambda m: {"name": m.group(1).strip()},
            ),
            # App focus / switch
            (
                re.compile(r"(?:switch to|focus|go to)\s+(.+)", re.I),
                "focus_window",
                lambda m: {"app_name": _match_app_fuzzy(m.group(1))},
            ),
            # App open / launch
            (
                re.compile(r"(?:open|launch|start|run)\s+(.+)", re.I),
                "open_app",
                lambda m: {"app_name": _match_app_fuzzy(m.group(1))},
            ),
            (
                re.compile(r"(.+?)\s+(?:kholo|khol do|chalao|start karo|open karo)", re.I),
                "open_app",
                lambda m: {"app_name": _match_app_fuzzy(m.group(1))},
            ),
            # App close / kill
            (
                re.compile(r"(?:close|kill|quit|stop|exit)\s+(.+)", re.I),
                "close_app",
                lambda m: {"app_name": _match_app_fuzzy(m.group(1))},
            ),
            (
                re.compile(r"(.+?)\s+(?:band karo|band kardo|hatao)", re.I),
                "close_app",
                lambda m: {"app_name": _match_app_fuzzy(m.group(1))},
            ),
            # Memory patterns
            (
                re.compile(r"(?:remember\s+(?:that\s+)?|yaad\s+rakhna\s+(?:ki\s+)?)\s*(.+)", re.I),
                "remember_fact",
                lambda m: {"fact": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:forget\s+(?:that\s+)?|bhool\s+jao\s+(?:ki\s+)?)\s*(.+)", re.I),
                "forget_fact",
                lambda m: {"key_or_fact": m.group(1).strip()},
            ),
            (
                re.compile(r"(?:search memory for|search past conversations for)\s+(.+)", re.I),
                "search_memory",
                lambda m: {"query": m.group(1).strip()},
            ),
            # Mood patterns
            (
                re.compile(r"(?:how was my mood|mera mood kaisa tha|my mood in the last|mood in past)\s*(\d+)?\s*(?:days|din)?", re.I),
                "get_mood_summary",
                lambda m: {"days": int(m.group(1)) if m.group(1) else 7},
            ),
        ]

    def _extract_timer_args(self, match: re.Match) -> Dict[str, Any]:
        val = int(match.group(1))
        unit = match.group(2).lower()
        if unit.startswith("m"):
            secs = val * 60
        elif unit.startswith("h"):
            secs = val * 3600
        else:
            secs = val
        return {"seconds": secs, "label": f"{val} {unit} Timer"}

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse command and return dict with 'tool' and 'args' without executing."""
        clean = text.lower().strip()
        if not clean:
            return None

        candidates = [clean]
        norm = normalize_command_text(clean)
        if norm and norm != clean:
            candidates.append(norm)

        for candidate in candidates:
            if candidate in self._exact_commands:
                tool_name, args = self._exact_commands[candidate]
                return {"tool": tool_name, "args": args}
            for pattern, tool_name, arg_fn in self._pattern_table:
                m = pattern.search(candidate)
                if m:
                    try:
                        args = arg_fn(m)
                        return {"tool": tool_name, "args": args}
                    except Exception:
                        return {"tool": tool_name, "args": {}}

        # ── 4. Fuzzy Command Matcher ──────────────────────────────────
        for candidate in candidates:
            if len(candidate) >= 4 and has_action_intent(candidate):
                match = process.extractOne(candidate, list(self._exact_commands.keys()), scorer=fuzz.ratio)
                if match and match[1] >= 80:
                    tool_name, args = self._exact_commands[match[0]]
                    return {"tool": tool_name, "args": args}

        return None

    def try_parse(self, text: str) -> Optional[str]:
        """
        Check for direct commands before hitting Groq API.
        Executes registered @tool actions directly on match.
        """
        clean = text.lower().strip()
        if not clean:
            return None

        # ── 1. Check Safety Confirmation Gate ─────────────────────────────
        pending = ConfirmationManager.get_pending()
        if pending:
            intent = ConfirmationManager.check_user_intent(clean)
            if intent == "confirm":
                ConfirmationManager.clear()
                result = execute_tool(
                    pending["tool"],
                    pending.get("args", {}),
                    bypass_confirmation=True,
                )
                return f"Confirmed. Executed {pending['tool'].replace('_', ' ')}: {result}"
            elif intent == "deny":
                ConfirmationManager.clear()
                return "Cancelled. Action aborted."

        candidates = [clean]
        norm = normalize_command_text(clean)
        if norm and norm != clean:
            candidates.append(norm)

        for candidate in candidates:
            # ── 2. Check Exact Match Commands ─────────────────────────────
            if candidate in self._exact_commands:
                tool_name, args = self._exact_commands[candidate]
                return execute_tool(tool_name, args)

            # ── 3. Check Regex Pattern Table ──────────────────────────────
            for pattern, tool_name, arg_fn in self._pattern_table:
                m = pattern.search(candidate)
                if m:
                    # If notepad write is creative/long-form essay, delegate to AI brain
                    if tool_name == "notepad_write":
                        content = m.group(1).lower()
                        if any(k in content for k in ["paragraph", "essay", "story", "lines on", "about", "article", "poem"]):
                            return None

                    # Ignore sleep commands from app opening
                    if tool_name in ("open_app", "focus_window"):
                        target = m.group(1).strip().lower()
                        if target in ("sleep", "so jao", "bed", "listening"):
                            return None

                    try:
                        args = arg_fn(m)
                        return execute_tool(tool_name, args)
                    except Exception as e:
                        return f"Error running {tool_name}: {e}"

        # ── 4. Fuzzy Command Matcher ──────────────────────────────────
        for candidate in candidates:
            if len(candidate) >= 4 and has_action_intent(candidate):
                match = process.extractOne(candidate, list(self._exact_commands.keys()), scorer=fuzz.ratio)
                if match and match[1] >= 80:
                    tool_name, args = self._exact_commands[match[0]]
                    return execute_tool(tool_name, args)

        return None
