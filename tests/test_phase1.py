"""
Unit test suite for Phase 1: Tool-calling agent loop, registry, safety gates, and parser.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tools import (
    ConfirmationManager,
    TOOL_REGISTRY,
    discover_and_register_tools,
    execute_tool,
    get_tool,
    get_tool_schemas,
    pop_last_undo_action,
    record_undo_action,
    tool,
)
from modules.command_parser import CommandParser, _match_app_fuzzy
from modules.pc_control import PCController
from modules.utilities import Utilities
from core.brain import AIBrain


@pytest.fixture(autouse=True)
def setup_tools():
    """Ensure tools are discovered and confirmation state is reset before each test."""
    discover_and_register_tools()
    ConfirmationManager.clear()
    yield
    ConfirmationManager.clear()


def test_registry_discovery():
    """Verify that tools auto-register into TOOL_REGISTRY."""
    assert len(TOOL_REGISTRY) > 20
    essential_tools = [
        "open_app", "close_app", "get_diagnostics", "clean_ram",
        "organize_desktop", "undo_desktop_organize", "calculate_math",
        "set_volume", "take_screenshot", "shutdown_pc", "lock_pc"
    ]
    for t in essential_tools:
        assert t in TOOL_REGISTRY, f"Expected tool '{t}' in registry."


def test_tool_schema_generation():
    """Verify tool schemas follow OpenAI / Groq function-calling specification."""
    schemas = get_tool_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) > 0

    open_app_schema = next((s for s in schemas if s["function"]["name"] == "open_app"), None)
    assert open_app_schema is not None
    assert open_app_schema["type"] == "function"
    assert "parameters" in open_app_schema["function"]
    assert "properties" in open_app_schema["function"]["parameters"]
    assert "app_name" in open_app_schema["function"]["parameters"]["properties"]


def test_confirmation_gate_high_risk():
    """Verify high-risk tools are gated behind spoken confirmation."""
    # shutdown_pc has risk='high'
    result = execute_tool("shutdown_pc", {}, bypass_confirmation=False)
    assert result.startswith("CONFIRMATION_REQUIRED:")
    pending = ConfirmationManager.get_pending()
    assert pending is not None
    assert pending["tool"] == "shutdown_pc"

    # Test affirmative and negative intent classification
    assert ConfirmationManager.check_user_intent("haan kar do") == "confirm"
    assert ConfirmationManager.check_user_intent("yes") == "confirm"
    assert ConfirmationManager.check_user_intent("nahi mat karo") == "deny"
    assert ConfirmationManager.check_user_intent("cancel") == "deny"
    assert ConfirmationManager.check_user_intent("tell me a joke") is None


def test_undo_journal():
    """Verify undo journal correctly records and pops reversible actions."""
    test_data = {"moves": [{"src": "C:/fake/a.txt", "dest": "C:/fake/Images/a.txt"}]}
    record_undo_action("organize_desktop", test_data)

    entry = pop_last_undo_action()
    assert entry is not None
    assert entry["tool"] == "organize_desktop"
    assert entry["data"] == test_data


def test_honest_ram():
    """Verify clean_ram reports actual metrics without fake claims."""
    res = execute_tool("clean_ram")
    assert "Python GC freed" in res
    assert "System RAM:" in res
    assert "% utilized" in res


def test_calculate_math_tool():
    """Verify AST-safe math calculator evaluates expressions correctly."""
    res1 = execute_tool("calculate_math", {"expression": "25 * 4 + 10"})
    assert "110" in res1

    res2 = execute_tool("calculate_math", {"expression": "100 / 4"})
    assert "25" in res2

    # Malicious injection should be rejected safely
    bad = execute_tool("calculate_math", {"expression": "__import__('os').system('dir')"})
    assert "Could not calculate" in bad


def test_command_parser_fuzzy_matching():
    """Verify rapidfuzz resolves misspellings to correct app names."""
    assert _match_app_fuzzy("crome") == "chrome"
    assert _match_app_fuzzy("notepaddd") == "notepad"
    assert _match_app_fuzzy("spotifi") == "spotify"
    assert _match_app_fuzzy("calculater") == "calculator"


def test_command_parser_direct_routing():
    """Verify parser routes known commands directly to tools without LLM."""
    pc = PCController()
    utils = Utilities()
    parser = CommandParser(pc, utils)

    # Math
    res = parser.try_parse("calculate 15 * 3")
    assert res is not None
    assert "45" in res

    # RAM
    res = parser.try_parse("clean ram")
    assert res is not None
    assert "Python GC" in res


def test_agent_loop_with_mock_groq():
    """Verify brain agent loop processes tool_calls and returns synthesized reply."""
    brain = AIBrain()

    # Mock tool call response for step 1
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_test_123"
    mock_tool_call.function.name = "calculate_math"
    mock_tool_call.function.arguments = json.dumps({"expression": "7 * 8"})

    mock_choice_step1 = MagicMock()
    mock_choice_step1.message.content = None
    mock_choice_step1.message.tool_calls = [mock_tool_call]
    mock_resp_step1 = MagicMock()
    mock_resp_step1.choices = [mock_choice_step1]

    # Mock final text response for step 2
    mock_choice_step2 = MagicMock()
    mock_choice_step2.message.content = "Bhai, 7 * 8 ka answer 56 hota hai!"
    mock_choice_step2.message.tool_calls = None
    mock_resp_step2 = MagicMock()
    mock_resp_step2.choices = [mock_choice_step2]

    with patch.object(brain, "_call_groq_with_fallback", side_effect=[mock_resp_step1, mock_resp_step2]):
        reply = brain.think("7 multiplied by 8 kitna hoga?")
        assert "56" in reply
        assert "Bhai" in reply
