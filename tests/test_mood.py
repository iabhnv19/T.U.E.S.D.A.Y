"""
tests/test_mood.py
Unit tests for the Mood-Adaptive Personality Engine.
"""

from unittest.mock import MagicMock, patch
import pytest

from core.brain import AIBrain
from core.memory import MemoryStore
from core.mood import MoodEngine
from modules.command_parser import CommandParser
from modules.pc_control import PCController
from modules.utilities import Utilities


@pytest.fixture
def memory_store(tmp_path):
    """Provide clean in-memory or temp SQLite store."""
    mem = MemoryStore()
    return mem


@pytest.fixture
def mood_engine(memory_store):
    return MoodEngine(memory_store)


def test_mood_detection_categories(mood_engine):
    """Verify emotion lexicon accurately detects primary emotions in English and Hinglish."""
    # Frustrated
    mood, score = mood_engine.detect_mood("Ye software crash ho raha hai dimag kharab ho gaya!")
    assert mood == "frustrated"
    assert score < -0.5

    # Stressed
    mood, score = mood_engine.detect_mood("Deadline kal subah hai bohot tension ho rahi hai")
    assert mood == "stressed"
    assert score < -0.3

    # Tired
    mood, score = mood_engine.detect_mood("aaj bohot thak gaya hoon neend aa rahi hai")
    assert mood == "tired"
    assert score < 0.0

    # Sad
    mood, score = mood_engine.detect_mood("feeling lonely and depressed today")
    assert mood == "sad"
    assert score < -0.4

    # Happy
    mood, score = mood_engine.detect_mood("Project launch successful ho gaya mast maza aa gaya!")
    assert mood == "happy"
    assert score > 0.5

    # Relaxed
    mood, score = mood_engine.detect_mood("just chilling peacefully on my bed")
    assert mood == "relaxed"
    assert score > 0.3

    # Neutral
    mood, score = mood_engine.detect_mood("what is the weather in Delhi?")
    assert mood == "neutral"
    assert score == 0.0


def test_time_of_day_context(mood_engine):
    """Verify time-of-day returns valid periods and behavior descriptions."""
    period, vibe = mood_engine.get_time_of_day_context()
    assert period in ("morning", "afternoon", "evening", "late_night")
    assert len(vibe) > 10


def test_prompt_injection_structure(mood_engine):
    """Verify prompt injection contains required mood metadata and guidance."""
    injection = mood_engine.get_prompt_injection("I am so stressed about my exam")
    assert "[CURRENT_MOOD & CONTEXT ADAPTATION]" in injection
    assert "STRESSED" in injection
    assert "Tone Instruction:" in injection
    assert "Time of Day Vibe" in injection
    assert "Sir/Boss" in injection


def test_mood_logging_and_summary(mood_engine, memory_store):
    """Verify mood logs persist in SQLite and compute summary statistics."""
    # Log several simulated user interactions
    mood_engine.record_mood("I am so happy and excited today!")
    mood_engine.record_mood("Everything is going great and awesome!")
    mood_engine.record_mood("Feeling a bit tired and sleepy")
    mood_engine.record_mood("Standard query: check files")

    summary = mood_engine.get_mood_summary(days=1)
    assert "Over the last 1 days" in summary
    assert "Positive" in summary
    assert "recorded interactions" in summary


def test_brain_mood_integration():
    """Verify AIBrain records mood and handles mood history queries."""
    brain = AIBrain()

    # Mood history inquiry triggers fast reply
    res = brain.think("How was my mood this week?")
    assert "mood analysis" in res.lower() or "over the last" in res.lower() or "logs" in res.lower()


def test_command_parser_mood_routing():
    """Verify CommandParser directly routes mood inquiries to get_mood_summary tool."""
    pc = PCController()
    utils = Utilities()
    parser = CommandParser(pc, utils)

    res = parser.try_parse("how was my mood this week")
    assert res is not None
    assert ("over the last" in res.lower() or "mood" in res.lower())
