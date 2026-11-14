"""tests/test_phase456.py
Comprehensive test suite for Phase 4 (Screen/UI), Phase 5 (Files/Knowledge), and Phase 6 (Browser).
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import core.tools as tools_module
from modules.command_parser import CommandParser
import modules.screen_tools as screen_tools
import modules.file_tools as file_tools
import modules.browser_tools as browser_tools


class TestPhase4ScreenTools:
    """Tests for Phase 4 screen understanding and UI automation tools."""

    def test_screen_tools_registered(self):
        """Verify all phase 4 tools are registered in TOOL_REGISTRY."""
        expected = [
            "get_active_window",
            "get_selected_text",
            "read_screen_text",
            "analyze_screen",
            "list_window_controls",
            "click_button",
            "type_into_field",
        ]
        for name in expected:
            t = tools_module.get_tool(name)
            assert t is not None, f"Tool {name} must be registered"
            assert t.name == name

    def test_get_active_window_safe(self):
        """get_active_window should return a string and never raise."""
        res = screen_tools.get_active_window()
        assert isinstance(res, str)
        assert len(res) > 0

    def test_get_selected_text_safe(self):
        """get_selected_text should safely return without raising exception."""
        res = screen_tools.get_selected_text()
        assert isinstance(res, str)

    def test_read_screen_text_safe(self):
        """read_screen_text should handle OCR safely."""
        res = screen_tools.read_screen_text()
        assert isinstance(res, str)


class TestPhase5FileTools:
    """Tests for Phase 5 file management, documents, and RAG knowledge."""

    def test_file_tools_registered(self):
        """Verify all phase 5 tools are registered."""
        expected = [
            "search_files",
            "read_file_content",
            "create_file",
            "move_file",
            "rename_file",
            "undo_file_action",
            "zip_folder",
            "open_file",
            "read_pdf",
            "read_docx",
            "summarize_file",
            "index_folder",
            "ask_documents",
        ]
        for name in expected:
            t = tools_module.get_tool(name)
            assert t is not None, f"Tool {name} must be registered"

    def test_file_create_read_rename_move_undo(self):
        """Test full file lifecycle with undo support."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_doc.txt"
            content = "Hello T.U.E.S.D.A.Y from Phase 5 test suite!"

            # 1. Create
            res_create = file_tools.create_file(str(test_file), content)
            assert "create kar di" in res_create
            assert test_file.exists()

            # 2. Read
            res_read = file_tools.read_file_content(str(test_file))
            assert content in res_read

            # 3. Rename with undo
            res_rename = file_tools.rename_file(str(test_file), "renamed_doc.txt")
            assert "Renamed" in res_rename
            renamed_file = Path(tmpdir) / "renamed_doc.txt"
            assert renamed_file.exists()
            assert not test_file.exists()

            # 4. Undo rename
            res_undo = file_tools.undo_file_action()
            assert "Undone" in res_undo
            assert test_file.exists()
            assert not renamed_file.exists()

            # 5. Move with undo
            subfolder = Path(tmpdir) / "sub"
            subfolder.mkdir()
            res_move = file_tools.move_file(str(test_file), str(subfolder))
            assert "Moved" in res_move
            moved_file = subfolder / "test_doc.txt"
            assert moved_file.exists()
            assert not test_file.exists()

            # 6. Undo move
            res_undo_move = file_tools.undo_file_action()
            assert "Undone" in res_undo_move
            assert test_file.exists()

    def test_zip_folder(self):
        """Test zip_folder tool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_dir = Path(tmpdir) / "to_zip"
            sample_dir.mkdir()
            (sample_dir / "sample.txt").write_text("Zip content", encoding="utf-8")

            res_zip = file_tools.zip_folder(str(sample_dir))
            assert "compressed successfully" in res_zip.lower()
            expected_zip = Path(tmpdir) / "to_zip.zip"
            assert expected_zip.exists()

    def test_docx_reading(self):
        """Test read_docx with python-docx."""
        import docx
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "sample.docx"
            doc = docx.Document()
            doc.add_paragraph("Testing python-docx integration in T.U.E.S.D.A.Y.")
            doc.save(str(doc_path))

            res = file_tools.read_docx(str(doc_path))
            assert "Testing python-docx integration" in res

    def test_search_files(self):
        """Test search_files returns matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "alpha_report.txt").write_text("Alpha", encoding="utf-8")
            (Path(tmpdir) / "beta_notes.pdf").write_text("Beta", encoding="utf-8")

            res = file_tools.search_files(query="alpha", root_dir=tmpdir)
            assert "alpha_report.txt" in res


class TestPhase6BrowserTools:
    """Tests for Phase 6 Playwright browser automation tools."""

    def test_browser_tools_registered(self):
        """Verify all phase 6 browser tools are registered."""
        expected = [
            "browser_open",
            "browser_search",
            "browser_click",
            "browser_type",
            "browser_extract_text",
            "browser_screenshot",
            "browser_download",
            "browser_close",
        ]
        for name in expected:
            t = tools_module.get_tool(name)
            assert t is not None, f"Tool {name} must be registered"

    def test_browser_safety_guard(self):
        """High-risk purchase words must be blocked from automatic click."""
        res = browser_tools.browser_click("Pay Now")
        assert "Security" in res or "allowed nahi" in res

    def test_browser_close_safe(self):
        """browser_close should execute cleanly even if no session was active."""
        res = browser_tools.browser_close()
        assert isinstance(res, str)


class TestCommandParserIntegration:
    """Tests for CommandParser matching new Phase 4, 5, 6 voice commands."""

    def setup_method(self):
        self.parser = CommandParser()

    def test_screen_parser(self):
        cmd = self.parser.parse("what is on my screen")
        assert cmd is not None
        assert cmd["tool"] == "analyze_screen"

        cmd2 = self.parser.parse("active window")
        assert cmd2 is not None
        assert cmd2["tool"] == "get_active_window"

        cmd3 = self.parser.parse("read this text")
        assert cmd3 is not None
        assert cmd3["tool"] == "get_selected_text"

    def test_file_parser(self):
        cmd = self.parser.parse("search files for invoice")
        assert cmd is not None
        assert cmd["tool"] == "search_files"
        assert cmd["args"]["query"] == "invoice"

        cmd2 = self.parser.parse("undo file")
        assert cmd2 is not None
        assert cmd2["tool"] == "undo_file_action"

    def test_browser_parser(self):
        cmd = self.parser.parse("close browser")
        assert cmd is not None
        assert cmd["tool"] == "browser_close"

        cmd2 = self.parser.parse("browse to https://news.ycombinator.com")
        assert cmd2 is not None
        assert cmd2["tool"] == "browser_open"
        assert "ycombinator" in cmd2["args"]["url"]
