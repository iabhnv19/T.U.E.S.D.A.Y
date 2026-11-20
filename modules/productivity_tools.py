"""modules/productivity_tools.py
Phase 7: Productivity, persistent reminders, todos, notes, daily briefing, custom routines, and Google OAuth tools.
"""

import json
import os
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from core.config import Config
from core.memory import MemoryStore
from core.tools import tool, execute_tool

ROUTINES_FILE = Config.PROJECT_ROOT / "memory" / "routines.json"


def _ensure_routines_file():
    """Ensure routines.json exists with built-in default routines."""
    if not ROUTINES_FILE.exists():
        ROUTINES_FILE.parent.mkdir(parents=True, exist_ok=True)
        default_routines = {
            "study mode": [
                {"tool": "minimize_all", "args": {}},
                {"tool": "open_app", "args": {"app_name": "notepad"}},
                {"tool": "set_volume", "args": {"percent": 20}},
                {"tool": "set_timer", "args": {"seconds": 1500, "label": "Pomodoro Study"}},
            ],
            "focus mode": [
                {"tool": "minimize_all", "args": {}},
                {"tool": "set_volume", "args": {"percent": 15}},
                {"tool": "set_timer", "args": {"seconds": 1800, "label": "Deep Focus"}},
            ],
            "good night": [
                {"tool": "volume_mute", "args": {}},
                {"tool": "set_brightness", "args": {"level": 15}},
            ],
        }
        try:
            with open(ROUTINES_FILE, "w", encoding="utf-8") as f:
                json.dump(default_routines, f, indent=2)
        except Exception:
            pass


_ensure_routines_file()


# ── Persistent Reminders & Alarms ─────────────────────────────────────────

@tool(
    name="add_reminder",
    description="Set a persistent reminder in SQLite that survives restarts. Accepts minutes_from_now or exact time (e.g. '18:30').",
    params_schema={
        "text": {
            "type": "string",
            "description": "What to remind the user about.",
        },
        "minutes_from_now": {
            "type": "integer",
            "description": "Number of minutes from now to trigger the reminder.",
        },
        "due_time": {
            "type": "string",
            "description": "Optional exact time string like '18:30' or '6:00 pm'.",
        },
        "recurring": {
            "type": "string",
            "description": "Recurrence pattern: 'none', 'daily', or 'weekly'. Default is 'none'.",
        },
    },
    risk="low",
)
def add_reminder(
    text: str,
    minutes_from_now: Optional[int] = None,
    due_time: Optional[str] = None,
    recurring: str = "none",
) -> str:
    """Save persistent reminder."""
    target_ts = time.time()
    now = datetime.now()

    if minutes_from_now and minutes_from_now > 0:
        target_ts = time.time() + (minutes_from_now * 60)
        due_str = (now + timedelta(minutes=minutes_from_now)).strftime("%I:%M %p")
    elif due_time:
        # Parse exact time format
        try:
            clean_time = due_time.strip().upper()
            parsed_dt = None
            for fmt in ["%H:%M", "%I:%M %p", "%I:%M%p", "%I %p"]:
                try:
                    t = datetime.strptime(clean_time, fmt).time()
                    parsed_dt = datetime.combine(now.date(), t)
                    break
                except ValueError:
                    continue

            if parsed_dt:
                if parsed_dt <= now:
                    parsed_dt += timedelta(days=1)
                target_ts = parsed_dt.timestamp()
                due_str = parsed_dt.strftime("%I:%M %p")
            else:
                target_ts = time.time() + 300
                due_str = "5 minutes mein"
        except Exception:
            target_ts = time.time() + 300
            due_str = "5 minutes mein"
    else:
        target_ts = time.time() + 300
        due_str = "5 minutes mein"

    mem = MemoryStore()
    rem_id = mem.add_reminder(text, target_ts, recurring=recurring)
    rec_str = f" ({recurring} recurring)" if recurring and recurring != "none" else ""
    return f"Reminder set ho gaya Sir! ID #{rem_id}: '{text}' at {due_str}{rec_str}."


@tool(
    name="list_reminders",
    description="List active and upcoming persistent reminders.",
    params_schema={
        "include_completed": {
            "type": "boolean",
            "description": "Whether to also include completed reminders.",
        }
    },
    risk="low",
)
def list_reminders(include_completed: bool = False) -> str:
    """Fetch reminders from SQLite."""
    mem = MemoryStore()
    rems = mem.get_all_reminders(include_completed=include_completed)
    if not rems:
        return "Koi active reminders schedule nahi hain Sir."

    lines = []
    for r in rems:
        due_dt = datetime.fromtimestamp(r["due_timestamp"]).strftime("%d %b %I:%M %p")
        status = " (Done)" if r.get("is_completed") else ""
        rec = f" [{r['recurring']}]" if r.get("recurring") and r["recurring"] != "none" else ""
        lines.append(f"#{r['id']}: '{r['title']}' at {due_dt}{rec}{status}")

    return f"Found {len(lines)} reminder(s):\n" + "\n".join(lines)


@tool(
    name="delete_reminder",
    description="Cancel or delete a reminder by its numeric ID.",
    params_schema={
        "reminder_id": {
            "type": "integer",
            "description": "The ID number of the reminder to delete.",
        }
    },
    risk="low",
)
def delete_reminder(reminder_id: int) -> str:
    """Remove reminder from SQLite."""
    mem = MemoryStore()
    success = mem.delete_reminder(reminder_id)
    if success:
        return f"Reminder #{reminder_id} delete kar diya Sir."
    return f"Reminder #{reminder_id} nahi mila."


# ── To-Do List Management ─────────────────────────────────────────────────

@tool(
    name="add_todo",
    description="Add a task to the persistent to-do list.",
    params_schema={
        "task": {
            "type": "string",
            "description": "Description of the task to add.",
        }
    },
    risk="low",
)
def add_todo(task: str) -> str:
    """Add new task to to-do list."""
    mem = MemoryStore()
    todo_id = mem.add_todo(task)
    return f"Task #{todo_id} add kar diya: '{task}'."


@tool(
    name="list_todos",
    description="List tasks from the to-do list (pending, completed, or all).",
    params_schema={
        "status": {
            "type": "string",
            "description": "Status filter: 'pending', 'completed', or 'all'. Defaults to 'pending'.",
        }
    },
    risk="low",
)
def list_todos(status: str = "pending") -> str:
    """Fetch to-dos from SQLite."""
    mem = MemoryStore()
    todos = mem.get_todos(status=status)
    if not todos:
        return f"To-do list mein koi {status} tasks nahi hain!"

    lines = []
    for t in todos:
        check = "✓" if t["is_completed"] else "☐"
        lines.append(f"{check} #{t['id']}: {t['task']}")

    return f"To-Do List ({status}):\n" + "\n".join(lines)


@tool(
    name="complete_todo",
    description="Mark a task as completed in the to-do list by its ID or keyword match.",
    params_schema={
        "task": {
            "type": "string",
            "description": "Task ID number (e.g. '1') or keyword from the task name.",
        }
    },
    risk="low",
)
def complete_todo(task: str) -> str:
    """Mark task as done."""
    mem = MemoryStore()
    res = mem.complete_todo(task)
    if res:
        return f"Shabash! '{task}' complete mark kar diya."
    return f"Matching pending task nahi mila: '{task}'."


@tool(
    name="delete_todo",
    description="Delete a task from the to-do list by its ID or keyword.",
    params_schema={
        "task": {
            "type": "string",
            "description": "Task ID number or keyword to delete.",
        }
    },
    risk="low",
)
def delete_todo(task: str) -> str:
    """Delete task."""
    mem = MemoryStore()
    if mem.delete_todo(task):
        return f"Task '{task}' list se remove kar diya."
    return f"Task '{task}' nahi mila delete karne ke liye."


# ── Notes Management ──────────────────────────────────────────────────────

@tool(
    name="add_note",
    description="Save a persistent note with title and text content.",
    params_schema={
        "title": {
            "type": "string",
            "description": "Short title or topic for the note.",
        },
        "content": {
            "type": "string",
            "description": "Full text body of the note.",
        },
    },
    risk="low",
)
def add_note(title: str, content: str) -> str:
    """Store note in SQLite."""
    mem = MemoryStore()
    note_id = mem.add_note(title, content)
    return f"Note #{note_id} save kar li: '{title}'."


@tool(
    name="list_notes",
    description="List all saved notes, optionally searching by keyword.",
    params_schema={
        "query": {
            "type": "string",
            "description": "Optional search keyword to filter notes.",
        }
    },
    risk="low",
)
def list_notes(query: Optional[str] = None) -> str:
    """Fetch saved notes."""
    mem = MemoryStore()
    notes = mem.get_notes(query=query)
    if not notes:
        return "Koi notes save nahi mile."

    lines = []
    for n in notes:
        snippet = n["content"][:60] + "..." if len(n["content"]) > 60 else n["content"]
        lines.append(f"#{n['id']} '{n['title']}': {snippet}")

    return f"Saved Notes ({len(notes)}):\n" + "\n".join(lines)


@tool(
    name="read_note",
    description="Read the complete text of a specific note by ID or title.",
    params_schema={
        "title_or_id": {
            "type": "string",
            "description": "Note ID number or title keyword.",
        }
    },
    risk="low",
)
def read_note(title_or_id: str) -> str:
    """Retrieve full note body."""
    mem = MemoryStore()
    note = mem.read_note(title_or_id)
    if not note:
        return f"Note '{title_or_id}' nahi mili."
    return f"Note #{note['id']} — {note['title']}:\n\n{note['content']}"


@tool(
    name="delete_note",
    description="Delete a note by ID or title.",
    params_schema={
        "title_or_id": {
            "type": "string",
            "description": "Note ID or title keyword.",
        }
    },
    risk="low",
)
def delete_note(title_or_id: str) -> str:
    """Remove note from SQLite."""
    mem = MemoryStore()
    if mem.delete_note(title_or_id):
        return f"Note '{title_or_id}' delete kar di."
    return f"Note '{title_or_id}' nahi mili."


# ── Custom Named Routines ─────────────────────────────────────────────────

@tool(
    name="create_routine",
    description="Create or update a custom automation sequence (routine) by name.",
    params_schema={
        "name": {
            "type": "string",
            "description": "Routine name (e.g. 'coding session', 'relax mode').",
        },
        "actions_json": {
            "type": "string",
            "description": "JSON array of action objects [{\"tool\": \"open_app\", \"args\": {\"app_name\": \"vscode\"}}, ...]",
        },
    },
    risk="medium",
)
def create_routine(name: str, actions_json: str) -> str:
    """Create custom automation routine."""
    _ensure_routines_file()
    try:
        actions = json.loads(actions_json)
        if not isinstance(actions, list):
            return "Actions must be a JSON array of tool step objects."

        routines = {}
        if ROUTINES_FILE.exists():
            with open(ROUTINES_FILE, "r", encoding="utf-8") as f:
                routines = json.load(f)

        routine_key = name.lower().strip()
        routines[routine_key] = actions

        with open(ROUTINES_FILE, "w", encoding="utf-8") as f:
            json.dump(routines, f, indent=2)

        return f"Routine '{routine_key}' save ho gayi! Isme {len(actions)} steps hain. (Bolo 'run {routine_key}' to trigger)."
    except Exception as e:
        return f"Routine save karne mein error aaya: {e}"


@tool(
    name="run_routine",
    description="Execute a pre-configured automation sequence (e.g. 'study mode', 'focus mode', 'good night').",
    params_schema={
        "name": {
            "type": "string",
            "description": "Name of the routine to execute.",
        }
    },
    risk="medium",
)
def run_routine(name: str) -> str:
    """Execute named routine steps sequentially."""
    _ensure_routines_file()
    if not ROUTINES_FILE.exists():
        return "Routines file nahi mili."

    try:
        with open(ROUTINES_FILE, "r", encoding="utf-8") as f:
            routines = json.load(f)

        key = name.lower().strip()
        matched_key = None
        for k in routines:
            if key in k or k in key:
                matched_key = k
                break

        if not matched_key:
            available = ", ".join(routines.keys())
            return f"Routine '{name}' nahi mili. Available routines: {available}."

        steps = routines[matched_key]
        results = []
        for step in steps:
            tool_name = step.get("tool")
            tool_args = step.get("args", {})
            if tool_name:
                res = execute_tool(tool_name, tool_args, bypass_confirmation=False)
                results.append(f"{tool_name}: {res}")

        return f"Routine '{matched_key}' execute ho gayi! Steps executed ({len(results)}):\n" + "\n".join(results)
    except Exception as e:
        return f"Routine run karte waqt error: {e}"


@tool(
    name="list_routines",
    description="List all available automated routines.",
    params_schema={},
    risk="low",
)
def list_routines() -> str:
    """List defined routines."""
    _ensure_routines_file()
    try:
        with open(ROUTINES_FILE, "r", encoding="utf-8") as f:
            routines = json.load(f)
        if not routines:
            return "Koi custom routines defined nahi hain."
        items = [f"- {name} ({len(steps)} steps)" for name, steps in routines.items()]
        return "Available Routines:\n" + "\n".join(items)
    except Exception as e:
        return f"Error reading routines: {e}"


# ── Daily Briefing & India Block ──────────────────────────────────────────

def _fetch_cricket_news() -> str:
    """Fetch live cricket updates via keyless Google News Cricket RSS."""
    try:
        url = "https://news.google.com/rss/search?q=cricket+india&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        if items:
            headlines = [f"🏏 {it.find('title').text.split(' - ')[0]}" for it in items[:2] if it.find("title") is not None]
            return "\n".join(headlines)
    except Exception:
        pass
    return "🏏 Cricket updates filhal unavailable hain."


@tool(
    name="get_daily_briefing",
    description="Generate a complete 'Good Morning' daily briefing: weather, calendar/todos, reminders, top headlines, and India cricket/news.",
    params_schema={},
    risk="low",
)
def get_daily_briefing() -> str:
    """Synthesize complete morning briefing."""
    sections: List[str] = []
    now = datetime.now()
    greeting_time = "Good Morning" if now.hour < 12 else ("Good Afternoon" if now.hour < 17 else "Good Evening")
    sections.append(f"🌅 {greeting_time} Sir! Here is your daily briefing for {now.strftime('%A, %d %B %Y')}:\n")

    # 1. Weather
    try:
        from modules.web_search import fetch_live_weather
        city = Config.WEATHER_CITY or "Amritsar"
        weather_info = fetch_live_weather(city)
        if weather_info and "Unable" not in weather_info:
            sections.append(f"🌤️ Weather ({city}):\n{weather_info}\n")
    except Exception:
        pass

    # 2. Pending Reminders
    try:
        mem = MemoryStore()
        rems = mem.get_all_reminders(include_completed=False)
        if rems:
            rem_lines = [f"• {r['title']} ({datetime.fromtimestamp(r['due_timestamp']).strftime('%I:%M %p')})" for r in rems[:3]]
            sections.append(f"⏰ Upcoming Reminders ({len(rems)}):\n" + "\n".join(rem_lines) + "\n")
        else:
            sections.append("⏰ Reminders: Aaj koi urgent reminder scheduled nahi hai.\n")
    except Exception:
        pass

    # 3. Pending To-Dos
    try:
        mem = MemoryStore()
        todos = mem.get_todos(status="pending")
        if todos:
            todo_lines = [f"• #{t['id']}: {t['task']}" for t in todos[:3]]
            sections.append(f"📋 Pending Tasks ({len(todos)}):\n" + "\n".join(todo_lines) + "\n")
        else:
            sections.append("📋 To-Do: All tasks are clear!\n")
    except Exception:
        pass

    # 4. Top Headlines
    try:
        from modules.web_search import fetch_live_news
        news = fetch_live_news("top stories", count=2)
        if news:
            sections.append(f"📰 Top Headlines:\n{news}\n")
    except Exception:
        pass

    # 5. India Block (Cricket & Local news)
    try:
        cricket = _fetch_cricket_news()
        sections.append(f"🇮🇳 India Block:\n{cricket}\n")
    except Exception:
        pass

    # 6. Google Schedule (if enabled)
    if os.getenv("ENABLE_GOOGLE", "false").lower() in ("true", "1", "yes"):
        try:
            sched = get_schedule(day="today")
            sections.append(f"📅 Google Calendar:\n{sched}\n")
        except Exception:
            pass

    return "\n".join(sections).strip()


# ── Google Calendar & Gmail (OAuth behind .env flag) ──────────────────────

def _is_google_enabled() -> bool:
    """Check if Google integration is enabled in .env."""
    return os.getenv("ENABLE_GOOGLE", "false").lower().strip() in ("true", "1", "yes")


@tool(
    name="get_schedule",
    description="Retrieve Google Calendar events for a given day ('today', 'tomorrow', or YYYY-MM-DD).",
    params_schema={
        "day": {
            "type": "string",
            "description": "Day to check: 'today', 'tomorrow', or 'YYYY-MM-DD'.",
        }
    },
    risk="low",
)
def get_schedule(day: str = "today") -> str:
    """Fetch calendar schedule."""
    if not _is_google_enabled():
        return "Google Calendar integration .env mein disabled hai (ENABLE_GOOGLE=false). Isko enable karne ke liye .env update karein."

    creds_path = Config.PROJECT_ROOT / "credentials.json"
    if not creds_path.exists():
        return "Bhai, Google Calendar ke liye 'credentials.json' project root folder mein rakhna zaroori hai."

    try:
        # Standard Google Calendar API hook
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        token_path = Config.PROJECT_ROOT / "memory" / "google_token.json"
        if not token_path.exists():
            return "Google OAuth token nahi mila. Pehle CLI se sign-in complete karein."

        creds = Credentials.from_authorized_user_file(str(token_path))
        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow()
        if day.lower() == "tomorrow":
            start_dt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + "Z"
            end_dt = (now + timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat() + "Z"
        else:
            start_dt = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
            end_dt = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary", timeMin=start_dt, timeMax=end_dt,
            maxResults=10, singleEvents=True, orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])

        if not events:
            return f"No events found for {day} on your Google Calendar."

        lines = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date"))
            lines.append(f"• {start}: {e.get('summary', 'Untitled Event')}")

        return f"Google Calendar Events ({day}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Google Calendar read karne mein error: {e}"


@tool(
    name="create_calendar_event",
    description="Create an event on Google Calendar.",
    params_schema={
        "title": {
            "type": "string",
            "description": "Event title or meeting subject.",
        },
        "start_time": {
            "type": "string",
            "description": "Start time ISO string (e.g. '2026-11-15T15:00:00').",
        },
        "duration_minutes": {
            "type": "integer",
            "description": "Meeting duration in minutes (default 60).",
        },
    },
    risk="medium",
)
def create_calendar_event(title: str, start_time: str, duration_minutes: int = 60) -> str:
    """Create event on calendar."""
    if not _is_google_enabled():
        return "Google integration disabled (ENABLE_GOOGLE=false)."
    token_path = Config.PROJECT_ROOT / "memory" / "google_token.json"
    if not token_path.exists():
        return "Google OAuth token nahi mila. Google account connect karein."

    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(token_path))
        service = build("calendar", "v3", credentials=creds)

        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        }
        created = service.events().insert(calendarId="primary", body=event).execute()
        return f"Event created: '{title}' on {start_time} (Link: {created.get('htmlLink', '')})."
    except Exception as e:
        return f"Event create karne mein error aaya: {e}"


@tool(
    name="list_unread_emails",
    description="List latest unread emails from Gmail with sender and subject.",
    params_schema={
        "max_results": {
            "type": "integer",
            "description": "Maximum number of unread emails to retrieve (default 5).",
        }
    },
    risk="low",
)
def list_unread_emails(max_results: int = 5) -> str:
    """Fetch unread Gmail threads."""
    if not _is_google_enabled():
        return "Gmail integration disabled (ENABLE_GOOGLE=false in .env)."
    token_path = Config.PROJECT_ROOT / "memory" / "google_token.json"
    if not token_path.exists():
        return "Gmail OAuth token missing hai. Connect your Google account."

    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(token_path))
        service = build("gmail", "v1", credentials=creds)

        results = service.users().messages().list(userId="me", q="is:unread", maxResults=max_results).execute()
        messages = results.get("messages", [])

        if not messages:
            return "Gmail mein koi unread emails nahi hain Sir!"

        lines = []
        for msg in messages:
            m_data = service.users().messages().get(userId="me", id=msg["id"], format="metadata").execute()
            headers = m_data.get("payload", {}).get("headers", [])
            subj = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
            lines.append(f"• ID {msg['id']}: '{subj}' from {sender}")

        return f"Unread Emails ({len(messages)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Gmail check karne mein error: {e}"


@tool(
    name="summarize_email",
    description="Fetch and summarize the content of an email by its message ID.",
    params_schema={
        "email_id": {
            "type": "string",
            "description": "Gmail message ID.",
        }
    },
    risk="low",
)
def summarize_email(email_id: str) -> str:
    """Read email snippet and summarize."""
    if not _is_google_enabled():
        return "Gmail integration disabled (ENABLE_GOOGLE=false)."
    token_path = Config.PROJECT_ROOT / "memory" / "google_token.json"
    if not token_path.exists():
        return "Gmail credentials not found."

    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(token_path))
        service = build("gmail", "v1", credentials=creds)

        msg = service.users().messages().get(userId="me", id=email_id, format="snippet").execute()
        snippet = msg.get("snippet", "")
        return f"Email #{email_id} summary:\n{snippet}"
    except Exception as e:
        return f"Email summarize karne mein error: {e}"


@tool(
    name="draft_email_reply",
    description="Create a draft email reply in Gmail (draft only, never sends automatically).",
    params_schema={
        "email_id": {
            "type": "string",
            "description": "Target email message ID to draft a reply for.",
        },
        "reply_text": {
            "type": "string",
            "description": "Draft message body.",
        },
    },
    risk="medium",
)
def draft_email_reply(email_id: str, reply_text: str) -> str:
    """Create a draft reply."""
    if not _is_google_enabled():
        return "Gmail integration disabled (ENABLE_GOOGLE=false)."
    token_path = Config.PROJECT_ROOT / "memory" / "google_token.json"
    if not token_path.exists():
        return "Gmail credentials not found."

    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        import base64
        from email.mime.text import MIMEText

        creds = Credentials.from_authorized_user_file(str(token_path))
        service = build("gmail", "v1", credentials=creds)

        message = MIMEText(reply_text)
        message["Subject"] = "Re: Follow up"
        raw_msg = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw_msg, "threadId": email_id}}
        ).execute()

        return f"Draft reply created successfully (Draft ID: {draft.get('id', '')}). Aap Gmail khol kar review kar sakte ho."
    except Exception as e:
        return f"Draft create karne mein error aaya: {e}"
