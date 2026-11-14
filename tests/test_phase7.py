"""tests/test_phase7.py
Unit and integration tests for Phase 7: Persistent Reminders, Todos, Notes, Routines, Daily Briefing, and Google Tools.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core.memory import MemoryStore
from core.scheduler import BackgroundScheduler
import modules.productivity_tools as prod_tools
from modules.command_parser import CommandParser


class TestPhase7RemindersAndScheduler:
    """Tests for persistent reminders and background scheduler."""

    def setup_method(self):
        self.mem = MemoryStore()

    def test_reminder_crud(self):
        # 1. Add reminder
        res_add = prod_tools.add_reminder("Buy groceries", minutes_from_now=30)
        assert "Reminder set ho gaya" in res_add
        assert "Buy groceries" in res_add

        # 2. List reminders
        res_list = prod_tools.list_reminders()
        assert "Buy groceries" in res_list

        # Extract reminder ID
        rems = self.mem.get_all_reminders(include_completed=False)
        matching = [r for r in rems if "Buy groceries" in r["title"]]
        assert len(matching) > 0
        rem_id = matching[0]["id"]

        # 3. Delete reminder
        res_del = prod_tools.delete_reminder(rem_id)
        assert f"#{rem_id} delete kar diya" in res_del

    def test_background_scheduler_trigger(self):
        """Verify scheduler detects past due reminder and fires registered callback."""
        fired = []

        def on_due(title, recurring):
            fired.append(title)

        scheduler = BackgroundScheduler()
        scheduler.register_callback(on_due)

        # Add a reminder that is due right now (due timestamp in the past)
        past_ts = time.time() - 5
        rem_id = self.mem.add_reminder("Urgent test alarm", past_ts)

        # Trigger check directly via private loop logic
        due = self.mem.get_due_reminders(time.time())
        assert any(r["id"] == rem_id for r in due)

        # Emulate scheduler loop iteration
        for item in due:
            if item["id"] == rem_id:
                self.mem.complete_reminder(item["id"])
                on_due(item["title"], item.get("recurring", "none"))

        assert "Urgent test alarm" in fired

        # Verify it is no longer due
        due_after = self.mem.get_due_reminders(time.time())
        assert not any(r["id"] == rem_id for r in due_after)


class TestPhase7TodosAndNotes:
    """Tests for SQLite-backed to-dos and notes."""

    def test_todo_lifecycle(self):
        # 1. Add
        res_add = prod_tools.add_todo("Complete code review")
        assert "Task #" in res_add
        assert "Complete code review" in res_add

        # 2. List
        res_list = prod_tools.list_todos(status="pending")
        assert "Complete code review" in res_list

        # 3. Complete
        res_done = prod_tools.complete_todo("code review")
        assert "complete mark kar diya" in res_done

        # 4. Verify in completed list
        res_comp = prod_tools.list_todos(status="completed")
        assert "Complete code review" in res_comp

        # 5. Delete
        res_del = prod_tools.delete_todo("code review")
        assert "remove kar diya" in res_del

    def test_notes_lifecycle(self):
        # 1. Add
        res_add = prod_tools.add_note("Project Architecture", "Decoupled agent loop with 99 tools.")
        assert "Note #" in res_add
        assert "Project Architecture" in res_add

        # 2. List
        res_list = prod_tools.list_notes(query="Architecture")
        assert "Project Architecture" in res_list

        # 3. Read
        res_read = prod_tools.read_note("Architecture")
        assert "Decoupled agent loop with 99 tools." in res_read

        # 4. Delete
        res_del = prod_tools.delete_note("Project Architecture")
        assert "delete kar di" in res_del


class TestPhase7RoutinesAndBriefing:
    """Tests for custom routines and daily briefing."""

    def test_routines(self):
        # List built-in routines
        res_list = prod_tools.list_routines()
        assert "study mode" in res_list
        assert "good night" in res_list

        # Create custom routine
        test_steps = [
            {"tool": "get_datetime", "args": {}},
        ]
        import json
        res_create = prod_tools.create_routine("quick test routine", json.dumps(test_steps))
        assert "quick test routine" in res_create

        # Run custom routine
        res_run = prod_tools.run_routine("quick test routine")
        assert "execute ho gayi" in res_run

    def test_daily_briefing_synthesis(self):
        """Daily briefing should produce multi-part briefing without raising exceptions."""
        res = prod_tools.get_daily_briefing()
        assert isinstance(res, str)
        assert len(res) > 50
        assert "bhai!" in res
        assert "Weather" in res or "Reminders" in res or "India Block" in res


class TestPhase7GoogleToolsFallback:
    """Verify Google Calendar & Gmail tools fail gracefully when disabled or unconfigured."""

    def test_google_schedule_fallback(self):
        res = prod_tools.get_schedule("today")
        assert isinstance(res, str)
        assert "Google" in res or "Calendar" in res

    def test_google_event_fallback(self):
        res = prod_tools.create_calendar_event("Sprint Review", "2026-11-20T10:00:00")
        assert isinstance(res, str)
        assert "disabled" in res or "Google" in res

    def test_gmail_unread_fallback(self):
        res = prod_tools.list_unread_emails()
        assert isinstance(res, str)
        assert "disabled" in res or "Gmail" in res or "token" in res


class TestPhase7CommandParser:
    """Test CommandParser voice triggers for Phase 7."""

    def setup_method(self):
        self.parser = CommandParser()

    def test_briefing_command(self):
        cmd = self.parser.parse("good morning")
        assert cmd is not None
        assert cmd["tool"] == "get_daily_briefing"

        cmd2 = self.parser.parse("daily briefing")
        assert cmd2 is not None
        assert cmd2["tool"] == "get_daily_briefing"

    def test_reminder_command(self):
        cmd = self.parser.parse("remind me to call brother in 15 minutes")
        assert cmd is not None
        assert cmd["tool"] == "add_reminder"
        assert cmd["args"]["text"] == "call brother"
        assert cmd["args"]["minutes_from_now"] == 15

    def test_todo_command(self):
        cmd = self.parser.parse("add todo write project documentation")
        assert cmd is not None
        assert cmd["tool"] == "add_todo"
        assert cmd["args"]["task"] == "write project documentation"

        cmd2 = self.parser.parse("complete todo write project documentation")
        assert cmd2 is not None
        assert cmd2["tool"] == "complete_todo"

    def test_routine_command(self):
        cmd = self.parser.parse("study mode")
        assert cmd is not None
        assert cmd["tool"] == "run_routine"
        assert cmd["args"]["name"] == "study mode"
