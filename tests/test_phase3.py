"""
Unit test suite for Phase 3: SQLite structured facts, ChromaDB semantic memory, and auto-migration.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory import MemoryStore
from core.tools import execute_tool, get_tool, discover_and_register_tools
from modules.command_parser import CommandParser
from modules.pc_control import PCController
from modules.utilities import Utilities
from core.brain import AIBrain


@pytest.fixture(autouse=True)
def setup_memory():
    """Ensure tools and memory store are initialized cleanly."""
    discover_and_register_tools()
    store = MemoryStore()
    yield store


def test_sqlite_facts_crud(setup_memory):
    """Test saving, recalling, updating, and forgetting structured facts in SQLite."""
    store = setup_memory

    # Save
    res = store.save_fact("User is preparing for AI exam on 20th", key="exam_date", category="schedule")
    assert "Fact remembered" in res

    # Recall
    facts = store.recall_facts(category="schedule")
    assert len(facts) >= 1
    assert any(f["key"] == "exam_date" for f in facts)

    # Update
    up_res = store.update_fact("exam_date", "User exam rescheduled to 25th")
    assert "Updated" in up_res or "remembered" in up_res.lower()
    updated_facts = store.recall_facts(query="25th")
    assert len(updated_facts) >= 1

    # Forget
    del_res = store.forget_fact("exam_date")
    assert "Forgot" in del_res
    remaining = store.recall_facts(query="exam_date")
    assert len(remaining) == 0


def test_memory_tools_execution():
    """Verify memory tools execute cleanly through execute_tool."""
    # Tool: remember_fact
    res = execute_tool("remember_fact", {"fact": "My favorite programming language is Python", "key": "fav_lang", "category": "preference"})
    assert "Fact remembered" in res

    # Tool: recall_facts
    recall_res = execute_tool("recall_facts", {"query": "Python"})
    assert "fav_lang" in recall_res
    assert "Python" in recall_res

    # Tool: update_fact
    update_res = execute_tool("update_fact", {"key": "fav_lang", "new_value": "My favorite language is Rust"})
    assert "fav_lang" in update_res

    # Tool: forget_fact
    forget_res = execute_tool("forget_fact", {"key_or_fact": "fav_lang"})
    assert "Forgot" in forget_res


def test_chromadb_semantic_search(setup_memory):
    """Verify semantic search retrieves relevant dialogue turns."""
    store = setup_memory

    store.add_turn("user", "We decided to build the voice assistant using PyQt5 and Python.")
    store.add_turn("assistant", "Understood, PyQt5 will give us an OLED Dynamic Island overlay.")

    result = store.search_memory("What UI framework are we using for the assistant?", limit=2)
    assert "PyQt5" in result or "Past dialogue" in result


def test_command_parser_memory_commands():
    """Verify CommandParser intercepts spoken memory phrases."""
    pc = PCController()
    utils = Utilities()
    parser = CommandParser(pc, utils)

    # Spoken remember command
    res = parser.try_parse("remember that my dog's name is Bruno")
    assert res is not None
    assert "bruno" in res.lower()

    # Spoken recall command
    recall_res = parser.try_parse("what do you know about me")
    assert recall_res is not None
    assert "stored user facts" in recall_res.lower() or "bruno" in recall_res.lower()

    # Spoken forget command
    forget_res = parser.try_parse("forget that bruno")
    assert forget_res is not None
    assert "Forgot" in forget_res


def test_profile_summary_in_brain(setup_memory):
    """Verify profile facts are synthesized into the assistant prompt context."""
    store = setup_memory
    store.save_fact("User is a senior software engineer", key="job_title", category="personal")

    summary = store.get_profile_summary()
    assert "PERSISTENT USER PROFILE" in summary
    assert "senior software engineer" in summary


def test_privacy_guard_in_auto_extraction():
    """Verify fact extraction prompts strictly forbid sensitive credentials."""
    store = MemoryStore()
    mock_llm = MagicMock()

    # Pass dialogue containing sensitive data
    turns = [
        {"role": "user", "content": "My password is SuperSecret123 and credit card is 4111222233334444"},
        {"role": "assistant", "content": "I should not save this."}
    ]

    # Verify extraction method runs safely without throwing exceptions
    store._run_fact_extraction(mock_llm, "openai/gpt-oss-20b", turns)
    assert mock_llm.chat.completions.create.called
    call_args = mock_llm.chat.completions.create.call_args[1]
    prompt = call_args["messages"][1]["content"]
    assert "NEVER extract passwords, API keys, credit cards" in prompt
