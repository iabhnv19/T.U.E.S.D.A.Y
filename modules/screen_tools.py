"""modules/screen_tools.py
Phase 4: Screen understanding, OCR, and Windows UI automation tools for T.U.E.S.D.A.Y.
"""

import base64
import io
import os
import time
from typing import Optional, Dict, Any, List

import psutil
import pyautogui
import pyperclip
from PIL import Image

from core.config import Config
from core.tools import tool

# Optional Win32 & UI Automation imports
try:
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import pywinauto
    from pywinauto import Desktop
    HAS_PYWINAUTO = True
except ImportError:
    HAS_PYWINAUTO = False

try:
    from rapidocr_onnxruntime import RapidOCR
    _ocr_engine = RapidOCR()
    HAS_OCR = True
except Exception:
    _ocr_engine = None
    HAS_OCR = False


# ── Active Window & Selection ──────────────────────────────────────────────

@tool(
    name="get_active_window",
    description="Get the title and process name of the currently active/focused window.",
    params_schema={},
    risk="low",
)
def get_active_window() -> str:
    """Return active window title and process name."""
    if not HAS_WIN32:
        return "Win32 extensions not available to inspect active window."

    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "Koi active window detect nahi hui bhai, ho sakta hai desktop focused ho."

        title = win32gui.GetWindowText(hwnd) or "Untitled Window"
        thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc_name = "Unknown"
        if pid > 0:
            try:
                proc_name = psutil.Process(pid).name()
            except Exception:
                pass

        return f"Active window: '{title}' (Process: {proc_name}, PID: {pid})."
    except Exception as e:
        return f"Active window inspect karne mein error aaya: {e}"


@tool(
    name="get_selected_text",
    description="Get the text currently selected/highlighted by the user on screen using clipboard preservation.",
    params_schema={},
    risk="low",
)
def get_selected_text() -> str:
    """Read selected text without destroying user's existing clipboard contents."""
    old_clipboard = ""
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        pass

    try:
        # Clear clipboard temporarily
        pyperclip.copy("")
        time.sleep(0.05)

        # Send Ctrl+C
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.15)

        selected = pyperclip.paste()

        # Restore original clipboard
        if old_clipboard:
            pyperclip.copy(old_clipboard)

        if not selected or not selected.strip():
            return "Koi text selected nahi mila. Pehle mouse se text highlight kar lo."

        # Limit return text length
        snippet = selected.strip()
        if len(snippet) > 1000:
            snippet = snippet[:1000] + "... [truncated]"
        return f"Selected text: '{snippet}'"
    except Exception as e:
        if old_clipboard:
            try:
                pyperclip.copy(old_clipboard)
            except Exception:
                pass
        return f"Selected text copy nahi ho paya: {e}"


# ── Screen Capture & OCR ───────────────────────────────────────────────────

@tool(
    name="read_screen_text",
    description="Extract and read visible text from the screen (or a specific region) using local OCR.",
    params_schema={
        "region": {
            "type": "string",
            "description": "Optional bounding box 'x,y,width,height' or leave empty for full screen.",
        }
    },
    risk="low",
)
def read_screen_text(region: Optional[str] = None) -> str:
    """Perform OCR on screen capture."""
    global _ocr_engine, HAS_OCR
    if not HAS_OCR or _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
            HAS_OCR = True
        except Exception:
            return "OCR module (rapidocr_onnxruntime) install nahi hai bhai. Screen text read karne ke liye ise install karein."

    try:
        bbox = None
        if region:
            parts = [int(p.strip()) for p in region.split(",") if p.strip().isdigit()]
            if len(parts) == 4:
                bbox = tuple(parts)

        screenshot = pyautogui.screenshot(region=bbox)
        # Convert PIL Image to bytes or numpy array
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format="PNG")
        img_bytes = img_byte_arr.getvalue()

        result, _ = _ocr_engine(img_bytes)
        if not result:
            return "Screen par koi readable text detect nahi hua."

        lines = [item[1] for item in result if item and len(item) > 1 and item[1]]
        full_text = "\n".join(lines)
        if len(full_text) > 1500:
            full_text = full_text[:1500] + "\n... [truncated]"

        return f"Screen text extracted:\n{full_text}"
    except Exception as e:
        return f"OCR processing mein error aaya: {e}"


@tool(
    name="analyze_screen",
    description="Capture and visually analyze the screen or active window. Uses Groq vision model if available or OCR fallback.",
    params_schema={
        "prompt": {
            "type": "string",
            "description": "Question or instruction about what to look for on screen.",
        },
        "region": {
            "type": "string",
            "description": "Optional 'x,y,width,height' coordinates or empty for full screen.",
        },
    },
    risk="low",
)
def analyze_screen(prompt: str = "Describe what is on screen and any open windows or errors", region: Optional[str] = None) -> str:
    """Analyze screen via Groq Vision API or local inspection."""
    try:
        bbox = None
        if region:
            parts = [int(p.strip()) for p in region.split(",") if p.strip().isdigit()]
            if len(parts) == 4:
                bbox = tuple(parts)

        img = pyautogui.screenshot(region=bbox)

        # Downscale to max 1024x1024 to save tokens and bandwidth
        max_dim = 1024
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=75)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        vision_model = os.getenv("LLM_VISION_MODEL", os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview"))
        api_key = Config.LLM_API_KEY
        is_local = Config.LLM_PROVIDER in ("ollama", "lmstudio")

        if not api_key and not is_local:
            return "AI API key missing hai bhai, visual analysis nahi kar sakti."

        try:
            from core.llm import UniversalLLMClient
            client = UniversalLLMClient(
                provider=Config.LLM_PROVIDER,
                api_key=Config.LLM_API_KEY,
                base_url=Config.LLM_BASE_URL,
                default_model=vision_model,
            )
            response = client.chat.completions.create(
                model=vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"You are T.U.E.S.D.A.Y voice assistant. Analyze this Windows screen capture concisely in witty Hinglish. Question: {prompt}"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                        ],
                    }
                ],
                max_tokens=250,
                temperature=0.3,
            )
            analysis = response.choices[0].message.content.strip()
            return analysis
        except Exception as vision_err:
            # Fallback to local OCR + Active window info
            win_info = get_active_window()
            ocr_info = read_screen_text(region=region)
            return (
                f"Vision model call fail hua ({vision_err}). "
                f"Local inspection: {win_info}\nDetected text: {ocr_info[:400]}"
            )
    except Exception as e:
        return f"Screen analyze nahi ho paya: {e}"


# ── UI Automation (pywinauto) ─────────────────────────────────────────────

@tool(
    name="list_window_controls",
    description="List accessible buttons, text inputs, and controls inside the active window or target app.",
    params_schema={
        "window_title": {
            "type": "string",
            "description": "Optional title of window to inspect. If empty, active foreground window is used.",
        }
    },
    risk="low",
)
def list_window_controls(window_title: Optional[str] = None) -> str:
    """Inspect UI controls of the focused window."""
    if not HAS_PYWINAUTO:
        return "pywinauto library install nahi hai bhai."

    try:
        desktop = Desktop(backend="uia")
        if window_title:
            win = desktop.window(title_re=f".*{window_title}.*")
        else:
            hwnd = win32gui.GetForegroundWindow() if HAS_WIN32 else None
            if not hwnd:
                return "Koi foreground window nahi mili control list karne ke liye."
            win = desktop.window(handle=hwnd)

        controls = win.descendants()
        if not controls:
            return "Is window mein koi accessible UI controls nahi mile."

        items: List[str] = []
        for ctrl in controls[:30]:  # Cap at 30 controls
            try:
                name = ctrl.window_text().strip()
                c_type = ctrl.friendly_class_name()
                if name and len(name) < 50:
                    items.append(f"[{c_type}] '{name}'")
            except Exception:
                continue

        if not items:
            return "Window ke controls standard UIA format mein exposed nahi hain."

        return f"Found {len(items)} controls:\n" + "\n".join(items[:20])
    except Exception as e:
        return f"Controls inspect karne mein error aaya: {e}"


@tool(
    name="click_button",
    description="Click a UI button or element by visible text in the active window or specified window.",
    params_schema={
        "button_name": {
            "type": "string",
            "description": "The text or label of the button to click.",
        },
        "window_title": {
            "type": "string",
            "description": "Optional window title. If omitted, uses active window.",
        },
    },
    risk="medium",
)
def click_button(button_name: str, window_title: Optional[str] = None) -> str:
    """Click a button by label."""
    if not HAS_PYWINAUTO:
        return "pywinauto install nahi hai, button click nahi kar sakti."

    danger_words = ["delete", "remove", "pay", "buy", "uninstall", "format", "send email", "place order"]
    if any(w in button_name.lower() for w in danger_words):
        # We enforce high caution
        pass

    try:
        desktop = Desktop(backend="uia")
        if window_title:
            win = desktop.window(title_re=f".*{window_title}.*")
        else:
            hwnd = win32gui.GetForegroundWindow() if HAS_WIN32 else None
            if not hwnd:
                return "Active window nahi mili."
            win = desktop.window(handle=hwnd)

        btn = win.child_window(title_re=f"(?i).*{button_name}.*", control_type="Button")
        if not btn.exists(timeout=2):
            # Try any control matching text
            btn = win.child_window(title_re=f"(?i).*{button_name}.*")

        if btn.exists(timeout=2):
            btn.click_input()
            return f"Button '{button_name}' click kar diya bhai."
        else:
            return f"'{button_name}' button window mein nahi mila."
    except Exception as e:
        return f"Button click karne mein dikkat aayi: {e}"


@tool(
    name="type_into_field",
    description="Type text into a designated input field or the current active focus.",
    params_schema={
        "text": {
            "type": "string",
            "description": "Text to type.",
        },
        "field_name": {
            "type": "string",
            "description": "Optional name/label of the input field.",
        },
    },
    risk="low",
)
def type_into_field(text: str, field_name: Optional[str] = None) -> str:
    """Type text into field or cursor position."""
    try:
        if field_name and HAS_PYWINAUTO:
            desktop = Desktop(backend="uia")
            hwnd = win32gui.GetForegroundWindow() if HAS_WIN32 else None
            if hwnd:
                win = desktop.window(handle=hwnd)
                edit = win.child_window(title_re=f"(?i).*{field_name}.*", control_type="Edit")
                if edit.exists(timeout=1):
                    edit.set_focus()
                    edit.type_keys(text, with_spaces=True)
                    return f"'{field_name}' field mein '{text}' type kar diya."

        # Fallback to direct keyboard typing
        pyautogui.write(text, interval=0.02)
        return f"Text '{text}' type kar diya."
    except Exception as e:
        return f"Type karne mein error aaya: {e}"
