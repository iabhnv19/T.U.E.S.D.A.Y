import json
from unittest.mock import MagicMock, patch
import pytest

from core.brain import AIBrain
from core.tools import execute_tool
from modules.command_parser import (
    CommandParser,
    normalize_command_text,
    has_action_intent,
)
from modules.pc_control import PCController
from modules.utilities import Utilities


def test_normalize_command_text():
    """Verify conversational prefixes, fillers, and suffixes are cleanly stripped."""
    assert normalize_command_text("tuesday please open chrome") == "open chrome"
    assert normalize_command_text("bhai volume 50 kar do") == "volume 50"
    assert normalize_command_text("acha suno gaana roko") == "gaana roko"
    assert normalize_command_text("ek kaam karo screenshot lo na") == "screenshot lo"
    assert normalize_command_text("tuesday mausam kaisa hai") == "mausam kaisa hai"
    assert normalize_command_text("hey tuesday can you please clean ram") == "clean ram"
    assert normalize_command_text("bhai tuesday mute karo") == "mute"


def test_has_action_intent():
    """Verify tool detection correctly separates action queries from pure conversational chit-chat."""
    # Action queries -> True
    assert has_action_intent("open chrome") is True
    assert has_action_intent("what is on my screen") is True
    assert has_action_intent("calculate 10 * 5") is True
    assert has_action_intent("7 multiplied by 8 kitna hoga?") is True
    assert has_action_intent("remind me in 10 minutes") is True
    assert has_action_intent("bhai volume badhao") is True
    assert has_action_intent("organize my desktop") is True
    assert has_action_intent("read file notes.txt") is True

    # Conversational chat -> False
    assert has_action_intent("tell me a joke") is False
    assert has_action_intent("who was Albert Einstein?") is False
    assert has_action_intent("what is quantum computing?") is False
    assert has_action_intent("tum kaisi ho?") is False
    assert has_action_intent("explain the theory of relativity") is False
    assert has_action_intent("life ka purpose kya hai?") is False


def test_command_parser_conversational_wrappers():
    """Verify parser directly handles commands even when spoken with heavy conversational fillers."""
    pc = PCController()
    utils = Utilities()
    parser = CommandParser(pc, utils)

    # Conversational math
    res = parser.try_parse("tuesday calculate 10 + 25 please")
    assert res is not None
    assert "35" in res

    # Conversational RAM clean
    res = parser.try_parse("bhai ek kaam karo clean ram kar do")
    assert res is not None
    assert "Python GC" in res

    # Pure conversational query returns None (routes to AI chatbot)
    res = parser.try_parse("who is Tony Stark?")
    assert res is None


def test_brain_skips_tools_for_conversational_chat():
    """Verify AIBrain passes tools=None to LLM for conversational chit-chat queries."""
    brain = AIBrain()

    mock_choice = MagicMock()
    mock_choice.message.content = "Main bilkul badhiya hoon, tum sunao!"
    mock_choice.message.tool_calls = None
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]

    with patch.object(brain.client, "create_chat_completion", return_value=mock_resp) as mock_complete:
        reply = brain.think("Hello Tuesday, tum kaisi ho?")
        assert "badhiya" in reply.lower()
        # Verify tools was passed as None (zero token overhead!)
        mock_complete.assert_called_once()
        _, kwargs = mock_complete.call_args
        assert kwargs.get("tools") is None


def test_brain_attaches_tools_for_action_queries():
    """Verify AIBrain dynamically attaches tool schemas when an action is requested."""
    brain = AIBrain()

    mock_choice = MagicMock()
    mock_choice.message.content = "Folder organize kar diya boss."
    mock_choice.message.tool_calls = None
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]

    with patch.object(brain.client, "create_chat_completion", return_value=mock_resp) as mock_complete:
        brain.think("Can you organize my downloads folder?")
        mock_complete.assert_called_once()
        _, kwargs = mock_complete.call_args
        assert kwargs.get("tools") is not None
        assert len(kwargs["tools"]) > 0
