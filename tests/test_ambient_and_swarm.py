"""
tests/test_ambient_and_swarm.py
Unit and integration tests for Proactive Ambient Companion and Specialist Multi-Agent Swarm.
"""

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest

from core.agents import AgentSwarm, AnalystAgent, ResearcherAgent, WriterAgent
from core.ambient import AmbientCompanion
from core.brain import AIBrain
from core.memory import MemoryStore


# ── Proactive Ambient Companion Tests ───────────────────────────────────────


def test_ambient_work_watchdog():
    """Verify work watchdog alerts after sustained activity and resets on idle break."""
    mem = MemoryStore()
    ambient = AmbientCompanion(memory=mem, work_alert_minutes=120.0)
    alerts = []
    ambient.register_callback(lambda t, m: alerts.append((t, m)))

    # Simulate 2.5 hours of continuous work
    ambient._work_streak_start = time.time() - (150 * 60)
    ambient.check_work_duration(idle_seconds=5.0)
    assert len(alerts) == 1
    assert alerts[0][0] == "work_watchdog"
    assert "break" in alerts[0][1].lower()

    # Simulate 6-minute idle break -> resets streak
    ambient.check_work_duration(idle_seconds=360.0)
    assert (time.time() - ambient._work_streak_start) < 5.0


def test_ambient_schedule_radar():
    """Verify 10-minute pre-event radar alert triggers once per reminder."""
    mem = MemoryStore()
    now_ts = time.time()
    rem_id = mem.add_reminder("Ambient Test Meeting", due_timestamp=now_ts + 300)

    try:
        ambient = AmbientCompanion(memory=mem)
        alerts = []
        ambient.register_callback(lambda t, m: alerts.append((t, m)))

        ambient.check_upcoming_schedule(now_ts=now_ts)
        assert any(a[0] == "schedule_radar" and "Ambient Test Meeting" in a[1] for a in alerts)

        # Second pass should not duplicate alert for same reminder ID
        count_before = len(alerts)
        ambient.check_upcoming_schedule(now_ts=now_ts)
        assert len(alerts) == count_before
    finally:
        mem.delete_reminder(rem_id)


def test_ambient_hardware_warnings():
    """Verify proactive alerts on low unplugged battery and high RAM usage."""
    mem = MemoryStore()
    ambient = AmbientCompanion(memory=mem, battery_threshold=20, ram_threshold=90)
    alerts = []
    ambient.register_callback(lambda t, m: alerts.append((t, m)))

    mock_batt = SimpleNamespace(percent=15, power_plugged=False)
    mock_ram = SimpleNamespace(percent=94)

    with patch("core.ambient.psutil.sensors_battery", return_value=mock_batt), \
         patch("core.ambient.psutil.virtual_memory", return_value=mock_ram):
        ambient.check_hardware_health()

    types = [a[0] for a in alerts]
    assert "hardware_battery" in types
    assert "hardware_ram" in types


def test_ambient_workflow_habit_detection():
    """Verify recurring hourly app habits across 3+ days trigger a proactive suggestion."""
    mem = MemoryStore()
    test_hour = 23  # isolated test hour
    unique_app = "tuesday_habit_test_app_xyz"

    mem.log_habit(test_hour, unique_app, day_key="2026-11-20")
    mem.log_habit(test_hour, unique_app, day_key="2026-11-21")
    mem.log_habit(test_hour, unique_app, day_key="2026-11-22")

    ambient = AmbientCompanion(memory=mem)
    alerts = []
    ambient.register_callback(lambda t, m: alerts.append((t, m)))

    with patch("core.ambient.psutil.process_iter", return_value=[]):
        ambient.check_workflow_habits(active_proc="", current_hour=test_hour)

    assert any(a[0] == "habit_suggestion" and unique_app in a[1] for a in alerts)


# ── Specialist Multi-Agent Swarm Tests ──────────────────────────────────────


def test_swarm_query_detection():
    """Verify AgentSwarm detects comparison/research tasks and skips simple queries."""
    swarm = AgentSwarm()
    assert swarm.is_swarm_query("Find the best 3 mechanical keyboards under 5000 in India, compare their switches, and save a note") is True
    assert swarm.is_swarm_query("Compare Python vs Rust for backend APIs") is True
    assert swarm.is_swarm_query("Deep research on solid state batteries") is True

    assert swarm.is_swarm_query("open chrome") is False
    assert swarm.is_swarm_query("what time is it") is False


def test_swarm_full_pipeline_and_note_saving():
    """Verify Researcher -> Analyst -> Writer pipeline runs, saves note, and streams verdict."""
    mock_client = MagicMock()

    analyst_choice = MagicMock()
    analyst_choice.message.content = "1. Keychron K2 (Gateron Brown) - Rs 4999\n2. Royal Kludge RK61 - Rs 4200"
    writer_choice = MagicMock()
    writer_choice.message.content = "Sir, Keychron K2 aur RK61 best options hain 5000 ke andar, aur maine comparison note save kar diya hai."

    mock_client.create_chat_completion.side_effect = [
        MagicMock(choices=[analyst_choice]),
        MagicMock(choices=[writer_choice]),
    ]

    mem = MemoryStore()
    swarm = AgentSwarm(client=mock_client, memory=mem)
    statuses = []
    sentences = []

    with patch("core.agents.perform_live_web_search", return_value="Keychron K2 mechanical keyboard review 4999"):
        verdict = swarm.run_swarm(
            "Find the best 3 mechanical keyboards under 5000, compare switches, and save a note",
            on_status=lambda s: statuses.append(s),
            on_sentence=lambda c: sentences.append(c),
        )

    assert "Keychron K2" in verdict
    assert any("ResearcherAgent" in s for s in statuses)
    assert any("AnalystAgent" in s for s in statuses)
    assert any("WriterAgent" in s for s in statuses)
    assert len(sentences) > 0

    # Verify note was persisted
    notes = mem.get_notes(query="mechanical keyboards")
    assert len(notes) >= 1
    mem.delete_note(str(notes[0]["id"]))


def test_brain_routes_research_to_swarm():
    """Verify AIBrain.think routes comparison/research requests to AgentSwarm."""
    brain = AIBrain()
    with patch.object(brain.swarm, "run_swarm", return_value="Swarm verdict delivered, Sir.") as mock_swarm:
        reply = brain.think("Compare MacBook Air M3 vs ThinkPad X1 Carbon")
        assert reply == "Swarm verdict delivered, Sir."
        mock_swarm.assert_called_once()
