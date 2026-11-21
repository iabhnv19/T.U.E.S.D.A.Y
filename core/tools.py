import functools
import inspect
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.config import Config

LOGS_DIR = Config.PROJECT_ROOT / "logs"
ACTIONS_LOG_FILE = LOGS_DIR / "actions.jsonl"
UNDO_JOURNAL_FILE = LOGS_DIR / "undo_journal.json"


def _ensure_logs_dir():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


class Tool:
    """Represents an executable assistant capability with schema and safety metadata."""

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        params_schema: Optional[Dict[str, Any]] = None,
        risk: str = "low",
        confirmation_prompt: Optional[str] = None,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.risk = risk.lower()
        self.confirmation_prompt = confirmation_prompt
        self.params_schema = params_schema or self._generate_default_schema(func)

    @staticmethod
    def _generate_default_schema(func: Callable) -> Dict[str, Any]:
        """Auto-generate JSON schema from function parameters and annotations."""
        sig = inspect.signature(func)
        properties = {}
        required = []

        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls", "args", "kwargs"):
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                param_type = type_map.get(param.annotation, "string")

            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter '{param_name}'",
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI / Groq function-calling tool schema."""
        schema = self.params_schema
        # Auto-wrap flat property dicts into valid JSON Schema objects.
        # Many tools define params_schema as {"title": {...}, "content": {...}}
        # instead of {"type": "object", "properties": {...}, "required": [...]}.
        if schema and schema.get("type") != "object":
            # Heuristic: if every value is a dict with a "type" key, it's a
            # flat properties map that needs wrapping.
            if all(isinstance(v, dict) and "type" in v for v in schema.values()):
                schema = {
                    "type": "object",
                    "properties": schema,
                    "required": [
                        k for k, v in schema.items()
                        # Mark a property as required only when the matching
                        # function parameter has no default value.
                        if not self._param_has_default(k)
                    ],
                }
        elif not schema:
            schema = {"type": "object", "properties": {}}
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }

    def _param_has_default(self, param_name: str) -> bool:
        """Check whether *param_name* has a default value in the wrapped function."""
        import inspect
        try:
            sig = inspect.signature(self.func)
            p = sig.parameters.get(param_name)
            if p is None:
                return False
            return p.default is not inspect.Parameter.empty
        except (ValueError, TypeError):
            return False

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


# Global Tool Registry
TOOL_REGISTRY: Dict[str, Tool] = {}


def register_tool(tool_obj: Tool) -> Tool:
    """Register a tool instance in the global registry."""
    TOOL_REGISTRY[tool_obj.name] = tool_obj
    return tool_obj


def tool(
    name: str,
    description: str,
    params_schema: Optional[Dict[str, Any]] = None,
    risk: str = "low",
    confirmation_prompt: Optional[str] = None,
):
    """Decorator to register a function as an AI agent tool."""
    def decorator(fn: Callable):
        t = Tool(
            name=name,
            description=description,
            func=fn,
            params_schema=params_schema,
            risk=risk,
            confirmation_prompt=confirmation_prompt,
        )
        register_tool(t)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        wrapper.tool_instance = t
        return wrapper

    return decorator


def get_tool(name: str) -> Optional[Tool]:
    """Retrieve a tool by name."""
    return TOOL_REGISTRY.get(name)


def list_tools() -> List[Tool]:
    """Return all registered tools."""
    return list(TOOL_REGISTRY.values())


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Return all tool schemas formatted for Groq / OpenAI function calling."""
    return [t.to_openai_schema() for t in TOOL_REGISTRY.values()]


# ── Action Logging & Audit Trail ──────────────────────────────────────────

def log_action(tool_name: str, args: Dict[str, Any], risk: str, confirmed: bool, result: str):
    """Append tool execution record to logs/actions.jsonl."""
    _ensure_logs_dir()
    record = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "args": args,
        "risk": risk,
        "confirmed": confirmed,
        "result": str(result)[:300],
    }
    try:
        with open(ACTIONS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except IOError:
        pass


# ── Undo Journal for Reversible Actions ───────────────────────────────────

def record_undo_action(tool_name: str, undo_payload: Dict[str, Any]):
    """Record reversible action to logs/undo_journal.json."""
    _ensure_logs_dir()
    entries = []
    if UNDO_JOURNAL_FILE.exists():
        try:
            with open(UNDO_JOURNAL_FILE, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except Exception:
            entries = []

    entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "data": undo_payload,
    }
    entries.append(entry)

    # Keep last 50 entries
    if len(entries) > 50:
        entries = entries[-50:]

    try:
        with open(UNDO_JOURNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    except IOError:
        pass


def pop_last_undo_action() -> Optional[Dict[str, Any]]:
    """Retrieve and remove the most recent undo entry."""
    if not UNDO_JOURNAL_FILE.exists():
        return None

    try:
        with open(UNDO_JOURNAL_FILE, "r", encoding="utf-8") as f:
            entries = json.load(f)
        if not entries:
            return None
        last_entry = entries.pop()
        with open(UNDO_JOURNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        return last_entry
    except Exception:
        return None


# ── Confirmation Safety Gate ──────────────────────────────────────────────

class ConfirmationManager:
    """Manages high-risk action confirmation state across dialogue turns."""

    _pending: Optional[Dict[str, Any]] = None

    @classmethod
    def set_pending(cls, tool_name: str, args: Dict[str, Any], prompt: str):
        cls._pending = {
            "tool": tool_name,
            "args": args,
            "prompt": prompt,
            "timestamp": time.time(),
        }

    @classmethod
    def get_pending(cls) -> Optional[Dict[str, Any]]:
        # Expire pending action after 60 seconds
        if cls._pending and (time.time() - cls._pending["timestamp"] > 60):
            cls._pending = None
        return cls._pending

    @classmethod
    def clear(cls):
        cls._pending = None

    @classmethod
    def check_user_intent(cls, text: str) -> Optional[str]:
        """Classify user response as 'confirm', 'deny', or None."""
        clean = text.lower().strip()
        affirmatives = [
            "yes", "yeah", "yep", "sure", "haan", "ha", "kar do", "kardo",
            "proceed", "confirm", "theek hai", "chalega", "do it", "bilkul"
        ]
        negatives = [
            "no", "nope", "nahi", "nahin", "mat karo", "cancel",
            "abort", "ruko", "stop", "rehndo", "rehne do", "nevermind"
        ]

        # Exact match or starts-with check
        tokens = set(clean.split())
        if any(a in clean for a in affirmatives) or bool(tokens & set(affirmatives)):
            return "confirm"
        if any(n in clean for n in negatives) or bool(tokens & set(negatives)):
            return "deny"
        return None


# ── Execution Engine ──────────────────────────────────────────────────────

def execute_tool(
    name: str,
    args: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    bypass_confirmation: bool = False,
) -> str:
    """
    Safely execute a registered tool by name with exception isolation and audit logging.
    Returns a concise human-readable message for the assistant/user.
    """
    args = args or {}
    context = context or {}

    tool_obj = get_tool(name)
    if not tool_obj:
        err = f"Tool '{name}' not found in registry."
        log_action(name, args, "low", False, err)
        return err

    # High-risk confirmation check
    is_confirmed = bypass_confirmation or context.get("confirmed", False)
    if tool_obj.risk == "high" and not is_confirmed:
        prompt = (
            tool_obj.confirmation_prompt
            or f"Bhai, kya sach mein {tool_obj.name.replace('_', ' ')} kar doon?"
        )
        ConfirmationManager.set_pending(name, args, prompt)
        log_action(name, args, tool_obj.risk, False, "Awaiting user confirmation")
        return f"CONFIRMATION_REQUIRED: {prompt}"

    try:
        result = tool_obj(**args)
        result_str = str(result)
        log_action(name, args, tool_obj.risk, True, result_str)
        return result_str
    except Exception as e:
        err_msg = f"Error executing {name}: {str(e)}"
        log_action(name, args, tool_obj.risk, is_confirmed, err_msg)
        return err_msg


# ── Dynamic Tool Discovery ────────────────────────────────────────────────

def discover_and_register_tools():
    """Import built-in tools module and any custom tool plugins in tools/ or modules/."""
    # Load built-in standard tools
    try:
        import modules.registered_tools  # noqa: F401
    except ImportError:
        pass

    # Load optional tool modules (fail gracefully if deps missing)
    for mod_name in ["modules.screen_tools", "modules.file_tools", "modules.browser_tools", "modules.productivity_tools"]:
        try:
            __import__(mod_name)
        except ImportError:
            pass
        except Exception as e:
            print(f"[Tools] Optional module {mod_name} skipped: {e}")

    # Discover any plugins placed in tools/ folder
    tools_dir = Config.PROJECT_ROOT / "tools"
    if tools_dir.exists() and tools_dir.is_dir():
        import importlib.util
        for py_file in tools_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            module_name = f"tools.{py_file.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, str(py_file))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
            except Exception as e:
                print(f"[Tools] Could not load tool module {py_file.name}: {e}")


# ── Auto-discover on module load (guarded to run only once) ───────────────
_tools_discovered = False
try:
    if not _tools_discovered:
        discover_and_register_tools()
        _tools_discovered = True
except Exception:
    pass
