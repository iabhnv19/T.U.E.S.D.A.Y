"""
tests/test_planner.py
Unit and integration tests for the Autonomous ReAct Planner.
"""

from unittest.mock import MagicMock, patch
import pytest

from core.brain import AIBrain
from core.planner import ReActPlanner, Plan, PlanStep
from modules.command_parser import CommandParser
from modules.pc_control import PCController
from modules.utilities import Utilities


@pytest.fixture
def planner():
    mock_client = MagicMock()
    return ReActPlanner(client=mock_client)


def test_is_complex_goal_detection(planner):
    """Verify planner accurately distinguishes complex multi-step goals from atomic commands."""
    # Multi-step queries -> True
    assert planner.is_complex_goal("open vscode and then set volume to 20") is True
    assert planner.is_complex_goal("setup my coding workspace") is True
    assert planner.is_complex_goal("chrome kholo aur fir mute kardo") is True
    assert planner.is_complex_goal("prepare everything for tomorrow's meeting") is True
    assert planner.is_complex_goal("clean up and organize my desktop") is True
    assert planner.is_complex_goal("launch notepad and then take a screenshot") is True

    # Simple atomic commands -> False
    assert planner.is_complex_goal("open chrome") is False
    assert planner.is_complex_goal("volume 50") is False
    assert planner.is_complex_goal("take screenshot") is False
    assert planner.is_complex_goal("who is Tony Stark?") is False
    assert planner.is_complex_goal("mausam kaisa hai") is False
    assert planner.is_complex_goal("") is False


def test_tool_catalog_construction(planner):
    """Verify tool catalog generates compact descriptions and excludes destructive tools."""
    catalog = planner.get_tool_catalog()
    assert "- open_app" in catalog
    assert "- set_volume" in catalog
    assert "- take_screenshot" in catalog
    # Verify destructive tools are excluded from autonomous chaining catalog
    assert "shutdown_pc" not in catalog
    assert "restart_pc" not in catalog


def test_plan_json_parsing(planner):
    """Verify robust parsing of model-generated JSON plan with thought and steps."""
    raw_response = """```json
    {
        "thought": "Open editor and configure audio for focus.",
        "steps": [
            {"step": 1, "action": "open_app", "args": {"app_name": "notepad"}, "purpose": "Launch notes"},
            {"step": 2, "action": "set_volume", "args": {"percent": 15}, "purpose": "Set quiet volume"}
        ]
    }
    ```"""

    plan = planner._parse_plan_json("Setup study session", raw_response)
    assert plan is not None
    assert plan.goal == "Setup study session"
    assert "Open editor" in plan.thought
    assert len(plan.steps) == 2
    assert plan.steps[0].action == "open_app"
    assert plan.steps[0].args == {"app_name": "notepad"}
    assert plan.steps[1].action == "set_volume"


def test_react_execute_goal_cycle():
    """Verify full plan generation, step execution, and final synthesis."""
    mock_client = MagicMock()

    # 1st call: generate_plan response
    plan_json = """{
        "thought": "Prepare workspace by setting volume and taking note.",
        "steps": [
            {"step": 1, "action": "volume_mute", "args": {}, "purpose": "Mute distracting audio"},
            {"step": 2, "action": "clean_ram", "args": {}, "purpose": "Free up memory"}
        ]
    }"""
    mock_choice1 = MagicMock()
    mock_choice1.message.content = plan_json
    mock_resp1 = MagicMock(choices=[mock_choice1])

    # 2nd call: synthesize final response
    mock_choice2 = MagicMock()
    mock_choice2.message.content = "All set Sir! Maine volume mute kar diya aur memory optimize kar di."
    mock_resp2 = MagicMock(choices=[mock_choice2])

    mock_client.create_chat_completion.side_effect = [mock_resp1, mock_resp2]

    planner = ReActPlanner(client=mock_client)

    status_updates = []
    sentence_chunks = []

    result = planner.execute_goal(
        "Setup quiet coding mode",
        on_status=lambda s: status_updates.append(s),
        on_sentence=lambda ch: sentence_chunks.append(ch),
    )

    assert "volume mute" in result.lower() or "memory" in result.lower()
    assert len(status_updates) > 0
    assert any("Mute distracting audio" in s for s in status_updates)
    assert len(sentence_chunks) > 0


def test_self_correction_on_error():
    """Verify planner detects step failure and executes corrective action."""
    mock_client = MagicMock()

    failed_step = PlanStep(
        step=1,
        action="open_app",
        args={"app_name": "invalid_xyz_program"},
        purpose="Open editor",
        status="running",
        result="Error executing open_app: invalid_xyz_program not found",
    )

    # Corrective action from LLM
    corr_json = """{
        "action": "open_app",
        "args": {"app_name": "notepad"},
        "purpose": "Fallback to standard notepad"
    }"""
    mock_choice = MagicMock()
    mock_choice.message.content = corr_json
    mock_client.create_chat_completion.return_value = MagicMock(choices=[mock_choice])

    planner = ReActPlanner(client=mock_client)
    corrected = planner._self_correct(failed_step, "Open an editor", [])

    assert corrected is not None
    assert corrected.action == "open_app"
    assert corrected.args == {"app_name": "notepad"}
    assert "notepad" in corrected.purpose.lower()


def test_command_parser_delegates_multistep_to_planner():
    """Verify CommandParser bypasses fast single regex when a multi-step chain is detected."""
    pc = PCController()
    utils = Utilities()
    brain = AIBrain()
    parser = CommandParser(pc, utils, brain)

    # Single command is handled locally
    assert parser.try_parse("mute") is not None

    # Multi-step conjunction returns None so it delegates to ReAct planner
    assert parser.try_parse("open chrome and then mute volume") is None
    assert parser.try_parse("open notepad aur fir volume 20 karo") is None


def test_brain_routes_complex_goal_to_planner():
    """Verify AIBrain.think detects multi-step goal and routes to planner.execute_goal."""
    brain = AIBrain()

    with patch.object(brain.planner, "execute_goal", return_value="Autonomous goal completed, Sir.") as mock_exec:
        reply = brain.think("setup my environment and then mute audio")
        assert reply == "Autonomous goal completed, Sir."
        mock_exec.assert_called_once()
