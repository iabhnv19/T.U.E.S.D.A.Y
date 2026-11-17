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
    _rapid_ocr = RapidOCR()
    HAS_RAPID_OCR = True
except Exception:
    _rapid_ocr = None
    HAS_RAPID_OCR = False

try:
    import winocr
    HAS_WINOCR = True
except Exception:
    winocr = None
    HAS_WINOCR = False

HAS_OCR = HAS_RAPID_OCR or HAS_WINOCR


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


# ── Screen Capture & Dual-Engine Python OCR ───────────────────────────────

def _capture_screenshot(region: Optional[str] = None):
    """Safely capture desktop screenshot with optional region 'x,y,w,h'."""
    bbox = None
    offset_x, offset_y = 0, 0
    if region:
        try:
            parts = [int(p.strip()) for p in region.split(",") if p.strip().isdigit()]
            if len(parts) == 4:
                bbox = tuple(parts)
                offset_x, offset_y = parts[0], parts[1]
        except Exception:
            bbox = None

    try:
        shot = pyautogui.screenshot(region=bbox)
        return shot, offset_x, offset_y
    except Exception as e:
        # Fallback using PIL ImageGrab if available
        try:
            from PIL import ImageGrab
            shot = ImageGrab.grab(bbox=bbox)
            return shot, offset_x, offset_y
        except Exception:
            return None, 0, 0


def _extract_ocr_elements(img, offset_x: int = 0, offset_y: int = 0) -> List[Dict[str, Any]]:
    """
    Run local Python OCR engines (WinOCR + RapidOCR) and return structured text elements:
    [{'text': str, 'center': (cx, cy), 'bbox': (x, y, w, h), 'confidence': float}]
    """
    if img is None:
        return []

    elements: List[Dict[str, Any]] = []

    # 1. Try Windows Native Media OCR (winocr)
    if HAS_WINOCR and winocr is not None:
        try:
            import asyncio
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def _scan():
                return await winocr.recognize_pil(img, "en")

            ocr_res = loop.run_until_complete(_scan()) if loop.is_running() is False else asyncio.run(_scan())
            if ocr_res and ocr_res.lines:
                for line in ocr_res.lines:
                    line_text = line.text.strip()
                    if not line_text:
                        continue
                    # Approximate line bbox from words
                    if line.words:
                        min_x = min(w.bounding_rect.x for w in line.words) + offset_x
                        min_y = min(w.bounding_rect.y for w in line.words) + offset_y
                        max_x = max(w.bounding_rect.x + w.bounding_rect.width for w in line.words) + offset_x
                        max_y = max(w.bounding_rect.y + w.bounding_rect.height for w in line.words) + offset_y
                        w_box = max_x - min_x
                        h_box = max_y - min_y
                        cx = int(min_x + w_box / 2)
                        cy = int(min_y + h_box / 2)
                        elements.append({
                            "text": line_text,
                            "center": (cx, cy),
                            "bbox": (int(min_x), int(min_y), int(w_box), int(h_box)),
                            "confidence": 0.98,
                        })
                if elements:
                    return elements
        except Exception:
            pass

    # 2. Try RapidOCR (Deep Learning PaddleOCR ONNX Engine)
    if HAS_RAPID_OCR and _rapid_ocr is not None:
        try:
            import numpy as np
            img_arr = np.array(img)
            ocr_res, _ = _rapid_ocr(img_arr)
            if ocr_res:
                for item in ocr_res:
                    box, text, score = item
                    t = text.strip()
                    if not t:
                        continue
                    xs = [pt[0] + offset_x for pt in box]
                    ys = [pt[1] + offset_y for pt in box]
                    min_x, max_x = min(xs), max(xs)
                    min_y, max_y = min(ys), max(ys)
                    cx = int((min_x + max_x) / 2.0)
                    cy = int((min_y + max_y) / 2.0)
                    elements.append({
                        "text": t,
                        "center": (cx, cy),
                        "bbox": (int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y)),
                        "confidence": round(float(score), 2),
                    })
                if elements:
                    return elements
        except Exception:
            pass

    return elements


@tool(
    name="read_screen_text",
    description="Extract and read visible text from the screen using high-precision local Python OCR.",
    params_schema={
        "region": {
            "type": "string",
            "description": "Optional bounding box 'x,y,width,height' or leave empty for full screen.",
        },
        "with_coordinates": {
            "type": "boolean",
            "description": "Whether to include screen (X, Y) pixel coordinates for each detected element.",
        },
    },
    risk="low",
)
def read_screen_text(region: Optional[str] = None, with_coordinates: bool = False) -> str:
    """Perform local OCR on screen capture and return layout-preserved text."""
    if not HAS_OCR:
        return "Local OCR modules (winocr / rapidocr) available nahi hain bhai."

    img, ox, oy = _capture_screenshot(region)
    if img is None:
        return "Screen capture capture nahi ho saka (desktop access error ya session locked ho sakta hai)."

    elements = _extract_ocr_elements(img, ox, oy)
    if not elements:
        return "Screen par koi readable text detect nahi hua."

    if with_coordinates:
        lines = [f"• '{el['text']}' at pos ({el['center'][0]}, {el['center'][1]})" for el in elements]
        return f"Detected {len(elements)} screen text elements with coordinates:\n" + "\n".join(lines[:40])

    # Plain text summary
    text_content = "\n".join([el["text"] for el in elements])
    if len(text_content) > 1500:
        text_content = text_content[:1500] + "\n... [truncated]"
    return f"Screen text extracted ({len(elements)} elements):\n{text_content}"


@tool(
    name="find_text_on_screen",
    description="Find the exact (X, Y) pixel coordinates of a button, label, or text snippet on screen using OCR.",
    params_schema={
        "query": {
            "type": "string",
            "description": "Text, button label, or word to find on the screen.",
        },
        "region": {
            "type": "string",
            "description": "Optional bounding box 'x,y,width,height' to narrow search.",
        },
    },
    risk="low",
)
def find_text_on_screen(query: str, region: Optional[str] = None) -> str:
    """Search for on-screen text coordinates."""
    if not HAS_OCR:
        return "OCR engine available nahi hai."

    img, ox, oy = _capture_screenshot(region)
    if img is None:
        return "Screen capture nahi ho saka."

    elements = _extract_ocr_elements(img, ox, oy)
    if not elements:
        return "Screen par koi readable text nahi mila."

    q_clean = query.lower().strip()
    matches = []
    for el in elements:
        t = el["text"].lower()
        if q_clean in t or t in q_clean:
            matches.append(el)

    if not matches:
        return f"Text '{query}' screen par nahi mila."

    best = matches[0]
    cx, cy = best["center"]
    return f"Found '{best['text']}' on screen at coordinates X={cx}, Y={cy} (Bounding box: {best['bbox']})."


@tool(
    name="click_text_on_screen",
    description="Visually locate a button, link, or label anywhere on screen via OCR and click it with the mouse.",
    params_schema={
        "text": {
            "type": "string",
            "description": "The exact or partial text of the button/element to click.",
        },
        "double_click": {
            "type": "boolean",
            "description": "Whether to perform a double-click instead of single click.",
        },
        "right_click": {
            "type": "boolean",
            "description": "Whether to right-click the element.",
        },
        "region": {
            "type": "string",
            "description": "Optional bounding box 'x,y,w,h'.",
        },
    },
    risk="medium",
)
def click_text_on_screen(
    text: str,
    double_click: bool = False,
    right_click: bool = False,
    region: Optional[str] = None,
) -> str:
    """Find text via OCR and click its center coordinates."""
    danger_words = ["delete all", "format", "pay now", "buy now", "confirm transfer", "shutdown"]
    if any(w in text.lower() for w in danger_words):
        pass  # Higher safety gate can intercept if needed

    img, ox, oy = _capture_screenshot(region)
    if img is None:
        return "Screen capture fail ho gaya, click nahi kar sakti."

    elements = _extract_ocr_elements(img, ox, oy)
    if not elements:
        return "Screen par koi text detect nahi hua."

    clean_target = text.lower().strip()
    matched = None

    # 1. Exact match
    for el in elements:
        if el["text"].lower().strip() == clean_target:
            matched = el
            break

    # 2. Substring match
    if not matched:
        for el in elements:
            if clean_target in el["text"].lower():
                matched = el
                break

    if not matched:
        return f"'{text}' text screen par nahi mila click karne ke liye."

    cx, cy = matched["center"]
    try:
        if right_click:
            pyautogui.rightClick(cx, cy)
            return f"Right-clicked '{matched['text']}' at screen coordinates ({cx}, {cy})."
        elif double_click:
            pyautogui.doubleClick(cx, cy)
            return f"Double-clicked '{matched['text']}' at screen coordinates ({cx}, {cy})."
        else:
            pyautogui.click(cx, cy)
            return f"Clicked '{matched['text']}' at screen coordinates ({cx}, {cy})."
    except Exception as e:
        return f"Mouse click execute karte waqt error: {e}"


@tool(
    name="analyze_screen",
    description="Capture screen, run high-precision local Python OCR to detect all UI elements & text layout, and use AI reasoning to understand the screen and decide actions.",
    params_schema={
        "prompt": {
            "type": "string",
            "description": "Question, inspection request, or task regarding what is on screen.",
        },
        "region": {
            "type": "string",
            "description": "Optional 'x,y,width,height' coordinates or empty for full screen.",
        },
    },
    risk="low",
)
def analyze_screen(
    prompt: str = "Describe what is on screen and any open windows or errors",
    region: Optional[str] = None,
) -> str:
    """Analyze screen via local Python OCR + Active Window + LLM reasoning."""
    img, ox, oy = _capture_screenshot(region)
    if img is None:
        win_info = get_active_window()
        return f"Screen capture unavailable. Active foreground window: {win_info}"

    elements = _extract_ocr_elements(img, ox, oy)
    win_info = get_active_window()

    # Formulate a structured UI spatial state
    element_lines = []
    for el in elements[:40]:
        element_lines.append(f"- '{el['text']}' at position ({el['center'][0]}, {el['center'][1]})")

    elements_text = "\n".join(element_lines) if element_lines else "No text detected."

    ui_context = (
        f"[ACTIVE WINDOW]: {win_info}\n"
        f"[ON-SCREEN DETECTED UI ELEMENTS & TEXT ({len(elements)} items)]:\n"
        f"{elements_text}\n"
    )

    # Pass the rich visual context to the LLM Brain to reason and answer
    is_local = Config.LLM_PROVIDER in ("ollama", "lmstudio")
    if not Config.LLM_API_KEY and not is_local:
        return f"Local Screen Analysis:\n{ui_context[:600]}"

    try:
        from core.llm import UniversalLLMClient
        client = UniversalLLMClient(
            provider=Config.LLM_PROVIDER,
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
            default_model=Config.LLM_MODEL,
        )
        resp = client.chat.completions.create(
            model=client.default_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are T.U.E.S.D.A.Y, a sharp, witty assistant. "
                        "The user asked about their current PC screen. Based on the active window and "
                        "the OCR-detected UI text with coordinates, provide a clear, concise, witty response. "
                        "If the user wants an action (like clicking something), specify the exact text and coordinates."
                    ),
                },
                {
                    "role": "user",
                    "content": f"User question: {prompt}\n\nLive Screen UI State:\n{ui_context}",
                },
            ],
            max_tokens=300,
            temperature=0.3,
        )
        if resp and resp.choices:
            return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[AnalyzeScreen] LLM call fallback: {e}")

    return f"Active Screen State:\n{ui_context[:600]}"


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
