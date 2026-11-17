# T.U.E.S.D.A.Y — Master Architectural & Capability Index 🧠⚡

> **Developer & AI Model Context Card**  
> *Read this single document to understand 100% of the T.U.E.S.D.A.Y system architecture, commands, data structures, and implementation details without needing to inspect individual source files.*

---

## 1. Project High-Level Overview
- **Name**: T.U.E.S.D.A.Y (Tactical Unified Electronic Systematic Digital Assistant)
- **Role**: Lightweight, proactive, Windows desktop voice assistant inspired by Friday/JARVIS.
- **Persona**: Female voice, sharp, witty, warm, conversational Hinglish (Hindi + English) speaker.
- **User Gender**: Male (`karoge`, `tum sunao`, `bhai`, `dost`).
- **Core Loop**: Global Hotkey (`Right Shift + Enter`) → Continuous Active Listening until 5s silence → Local Regex Command Parser (Zero API Latency) → Fallback to Groq LLM with tool-calling agent loop → Natural Female Voice (gTTS) with real-time Barge-In speech cancellation → Floating OLED Dynamic Island Overlay UI.

---

## 2. Directory & Source File Mapping

```
E:\T.U.E.S.D.A.Y\
├── .env                     # User API credentials & runtime options (Never commit)
├── .env.example             # Safe template with environment variable placeholders
├── .gitignore               # Excludes secrets, cache, logs, db, and screenshots
├── requirements.txt         # Pinned production Python dependencies
├── pytest.ini               # Pytest path and runner configuration
├── README.md                # Public GitHub project guide & quick-start instructions
├── TUESDAY_INDEX.md         # THIS FILE: Master single-source architectural context
├── main.py                  # Orchestrator & entry point: Qt App, Hotkey, Barge-in loop
│
├── core/
│   ├── config.py            # Central settings, environment loader, and core SYSTEM_PROMPT
│   ├── brain.py             # Agentic AI Brain: multi-hop tool loop, fallback chain, memory integration
│   ├── memory.py            # MemoryStore: SQLite facts/turns/reminders/todos/notes + ChromaDB
│   ├── scheduler.py         # BackgroundScheduler thread checking due reminders & triggering alerts
│   ├── tools.py             # Decorator-based @tool registry, OpenAI schemas, safety gate & undo journal
│   └── voice.py             # Bilingual SpeechRecognition (en-IN/hi-IN) & gTTS audio playback
│
├── modules/
│   ├── registered_tools.py  # 40+ native tools wrapping PC, web search, utilities, and diagnostics
│   ├── screen_tools.py      # Phase 4: Screen analysis, active window, OCR, and pywinauto UI automation
│   ├── file_tools.py        # Phase 5: Fast file search, PDF/DOCX readers, RAG indexing & file manipulation
│   ├── browser_tools.py     # Phase 6: Playwright browser navigation, interaction, and search
│   ├── productivity_tools.py# Phase 7: Reminders, todos, notes, routines, daily briefing, Google OAuth
│   ├── pc_control.py        # Windows automation: apps, tabs, volume, media, snapping, telemetry
│   ├── command_parser.py    # Data-driven zero-latency parser: regex table + rapidfuzz matching
│   ├── web_search.py        # Keyless tri-engine: wttr.in (weather), Google News RSS, Wikipedia
│   ├── utilities.py         # Standalone helpers: timers, math, datetime, web shortcuts
│   └── overlay.py           # PyQt5 Dynamic Island UI with LERP glide & Siri fluid ribbon wave
│
├── logs/                    # Audit & safety logs
│   ├── actions.jsonl        # Complete execution history: timestamp, tool, args, risk, confirmed, result
│   └── undo_journal.json    # Reversible actions journal (desktop moves, file moves, renames)
│
├── memory/                  # Local runtime persistence
│   ├── tuesday.db           # SQLite database: user_facts, conversation_turns, reminders, todos, notes
│   ├── chroma_db/           # ChromaDB persistent vector database (all-MiniLM-L6-v2 embeddings)
│   ├── routines.json        # Custom named automation sequences (study mode, good night, etc.)
│   ├── conversation_history.json  # Legacy dialogue history (auto-migrated to SQLite)
│   └── user_profile.json          # Legacy user facts (auto-migrated to SQLite)
│
└── tests/
    ├── test_phase1.py       # Unit tests: tools, schemas, agent loop, safety gate, fuzzy parser
    ├── test_phase3.py       # Memory tests: SQLite CRUD, ChromaDB semantic search, privacy guard
    ├── test_phase456.py     # Screen/OCR, File/Undo/RAG, and Playwright browser integration tests
    └── test_phase7.py       # Productivity, Reminders, Todos, Notes, Routines, Briefing, Google tests
```

---

## 3. End-to-End Execution Flow

```
[User presses Right Shift + Enter]
                  │
                  ▼
         Dynamic Island activates: "Listening..."
                  │
                  ▼
         [Microphone Input: SpeechRecognition (en-IN / hi-IN)]
                  │
                  ▼
        ┌────────────────────────────────────────────────────────┐
        │ modules/command_parser.py (try_parse)                  │
        │ - Table-driven regex + rapidfuzz fuzzy app matching    │
        │ - Direct routing for screen, file, browser, PC actions │
        │ - Checks ConfirmationManager for high-risk approvals   │
        └────────────────────────────────────────────────────────┘
                 │                                │
            [YES: Local]                      [NO: AI Brain]
                 │                                │
                 ▼                                ▼
       Execute registered @tool        core/brain.py (AIBrain.think)
       (direct Python execution)                  │
                 │                      Needs live facts/weather/news?
                 │                                │
                 │                      [Fetch via web_search.py]
                 │                                │
                 │                      Groq Function Calling Agent Loop
                 │                      (Auto-model fallback if 429)
                 │                                │
                 │                      Executes tool calls (up to 6 hops)
                 │                      Feeds results back via role: tool
                 │                      Logs to logs/actions.jsonl
                 │                                │
                 │                      Synthesizes natural Hinglish reply
                 │                      (Zero raw JSON leaks)
                 │                                │
                 └────────────────┬───────────────┘
                                  │
                                  ▼
           Speak response aloud (gTTS via PyGame at 27.5 kHz)
                                  +
           Update Dynamic Island visualizer & text
                                  │
       ┌──────────────────────────┴──────────────────────────┐
       │ Simultaneous Background Interruption Listener       │
       │ User says: "Tuesday stop" / "Tuesday chup" / ...    │
       │ -> Instantly kills audio playback & accepts query   │
       └─────────────────────────────────────────────────────┘
```

---

## 4. Voice Commands & Capabilities Matrix

### A. System Diagnostics & Telemetry (JARVIS Radar)
| Voice Trigger | Tool Called | Description |
|---|---|---|
| *"System diagnostics"*, *"PC report"* | `get_diagnostics` | Reports CPU %, RAM (used/total GB), C: disk free GB, battery status, and top memory-hogging processes. |
| *"Clean RAM"*, *"Optimize memory"* | `clean_ram` | Trims working sets via Windows API, triggers Python GC, truthfully reports freed objects. |
| *"What is my IP"*, *"Check ping"* | `get_network_radar` | Returns local subnet IP, public IP, and ping latency in ms. |
| *"Clean my desktop"*, *"Organize desktop"* | `organize_desktop` | Categorizes loose desktop files into folders. Supports undo. Gated by confirmation. |
| *"Undo desktop"*, *"Undo organize"*, *"Undo that"* | `undo_desktop_organize` | Restores organized files back to original desktop locations from undo journal. |

### B. Smart Clipboard AI Copilot
| Voice Trigger | Method Called | Description |
|---|---|---|
| *"Make this professional"*, *"Fix grammar"* | `CommandParser` + `AIBrain` | Reads clipboard draft, rewrites into formal business English, loads result back to clipboard. |
| *"Summarize clipboard"*, *"Iska summary"* | `CommandParser` + `AIBrain` | Summarizes copied text/article in 1–2 punchy Hinglish sentences, copies and speaks summary. |
| *"Translate to Hindi"*, *"Translate to English"* | `CommandParser` + `AIBrain` | Translates clipboard content into natural Hindi/English and loads onto clipboard. |

### C. Audio, Volume & Media Controls
| Voice Trigger | Method Called | Description |
|---|---|---|
| *"Set volume to 40%"*, *"Volume 80%"* | `set_volume(percent=N)` | Sets master Windows volume to exact percentage (0–100%). |
| *"Volume up"*, *"Awaaz badhao"* | `volume_up()` | Steps volume up by 5-10%. |
| *"Volume down"*, *"Awaaz kam karo"* | `volume_down()` | Steps volume down by 5-10%. |
| *"Mute"*, *"Unmute"*, *"Awaaz band"* | `volume_mute()` | Toggles audio mute. |
| *"Play"*, *"Pause"*, *"Gaana roko"* | `media_play_pause()` | Toggles global system media playback. |
| *"Next track"*, *"Skip"*, *"Agla gaana"* | `media_next()` | Next media item. |
| *"Previous track"*, *"Pichla gaana"* | `media_previous()` | Previous media item. |

### D. Windows Snapping, Navigation & Virtual Desktops
| Voice Trigger | Method Called | Description |
|---|---|---|
| *"Snap left"*, *"Left mein lagao"* | `snap_left()` | `Win + Left` |
| *"Snap right"*, *"Right mein lagao"* | `snap_right()` | `Win + Right` |
| *"Maximize"*, *"Badi karo"* | `maximize_window()` | `Win + Up` |
| *"Minimize"*, *"Choti karo"* | `minimize_window()` | `Win + Down` |
| *"Show desktop"*, *"Minimize all"* | `minimize_all()` | `Win + D` |
| *"Task view"* | `toggle_task_view()` | `Win + Tab` |
| *"New desktop"* | `new_virtual_desktop()` | `Win + Ctrl + D` |
| *"Close desktop"* | `close_virtual_desktop()` | `Win + Ctrl + F4` |
| *"Next desktop"* / *"Prev desktop"* | `next/prev_virtual_desktop()` | `Win + Ctrl + Left/Right` |
| *"Switch to <app>"*, *"Focus <app>"* | `focus_window(app)` | Brings target app window to the front via WScript `AppActivate`. |
| *"Open <page> settings"* | `open_settings(page)` | Launches Windows URI schemes (`bluetooth`, `network-wifi`, `sound`, etc.). |

### E. Screen Recording & Screenshots
| Voice Trigger | Method Called | Description |
|---|---|---|
| *"Start screen recording"*, *"Screen record karo"* | `start_screen_recording()` | Native Windows Game Bar (`Win + Alt + R`). Saves to `Videos\Captures`. |
| *"Stop recording"*, *"Recording band karo"* | `stop_screen_recording()` | Stops recording (`Win + Alt + R`). |
| *"Take a screenshot"*, *"Ek screenshot lo"* | `take_screenshot()` | Captures desktop to `screenshot.png`. |

### F. Web Search & Keyless Knowledge Engine
| Voice Trigger | Method Called | Description |
|---|---|---|
| *"Weather in <city>"*, *"Forecast"* | `get_weather(city)` | Real-time weather, temperature, humidity, and 3-day forecast via `wttr.in`. |
| *"News"*, *"Latest tech news"* | `get_news(query)` | Live RSS headlines from Google News with topic routing. |
| *"YouTube search <x>"* | `search_youtube(query)` | Regex parser launches YouTube to query. |
| *"Google search <x>"* | `search_google(query)` | Opens Google search in default browser. |

### G. Long-Term Personal Memory (Phase 3: SQLite + ChromaDB)
| Voice Trigger | Tool Called | Description |
|---|---|---|
| *"Remember that <fact>"*, *"Yaad rakhna ki <x>"* | `remember_fact` | Saves persistent structured fact into SQLite `memory/tuesday.db`. |
| *"What do you know about me"*, *"Who am I"* | `recall_facts` | Summarizes user facts (name, occupation, location, preferences) injected into system prompt. |
| *"Forget that <fact>"*, *"Bhool jao"* | `forget_fact` | Deletes matching user fact from memory database. |
| *"Search past conversations for <x>"* | `search_memory` | Performs semantic cosine similarity vector search over past dialogue in ChromaDB. |

### H. Screen Understanding & UI Automation (Phase 4)
| Voice Trigger | Tool Called | Description |
|---|---|---|
| *"What's on my screen"*, *"Analyze screen"* | `analyze_screen` | Captures screen, downscales to 1024px, and analyzes visual state via Groq Vision API or local OCR. |
| *"Active window"*, *"Focused window"* | `get_active_window` | Retrieves foreground window title, process name, and PID via Win32. |
| *"Read this text"*, *"Selected text"* | `get_selected_text` | Preserves clipboard, sends `Ctrl+C`, reads selected text, and restores user's original clipboard. |
| *"Read screen"*, *"Screen text"* | `read_screen_text` | Performs local dual-engine OCR using `winocr` (Windows Media OCR) and `rapidocr_onnxruntime`. |
| *"Find text <x>"*, *"Screen pe dhoondo"* | `find_text_on_screen` | Searches for visual text on screen via OCR and returns exact pixel (X, Y) coordinates and bounding box. |
| *"Click text <x>"*, *"Screen pe click karo"* | `click_text_on_screen` | Visually locates text on screen via OCR and clicks its exact center coordinates with PyAutoGUI. |
| *"List controls"*, *"Window controls"* | `list_window_controls` | Enumerates accessible buttons, text fields, and UI elements via `pywinauto`. |
| *"Click <button>"*, *"Button dabao <x>"* | `click_button` | Finds and clicks button by visible label. High-risk safety check on payment/destructive buttons. |
| *"Type <text> into <field>"* | `type_into_field` | Sets focus and types text into specified input field. |

### I. Files, Documents & RAG Knowledge (Phase 5)
| Voice Trigger | Tool Called | Description |
|---|---|---|
| *"Search files for <query>"*, *"Find file <x>"* | `search_files` | Fast file scan across Desktop, Documents, Downloads, or custom `SEARCH_DIRS`. Everything CLI (`es.exe`) support. |
| *"Read file <path>"*, *"File padho <x>"* | `read_file_content` | Reads text, code, PDF, or Word document up to 4000 characters. |
| *"Read PDF <path>"* | `read_pdf` | Extracts clean text page-by-page using PyPDF2 / pypdf. |
| *"Read docx <path>"* | `read_docx` | Extracts paragraphs and tables from Word documents via `python-docx`. |
| *"Summarize file <path>"* | `summarize_file` | Extracts document text and uses Groq to produce a 3-5 bullet point Hinglish executive summary. |
| *"Create file <path> with <content>"* | `create_file` | Creates text file and parent folders automatically. |
| *"Move file <src> to <dest>"* | `move_file` | Moves file or directory and logs operation to undo journal. |
| *"Rename file <path> to <new_name>"* | `rename_file` | Renames file and logs operation to undo journal. |
| *"Undo file"* / *"Undo file move"* | `undo_file_action` | Reverts last file move, rename, or desktop organization from `logs/undo_journal.json`. |
| *"Zip folder <path>"* | `zip_folder` | Compresses directory into `.zip` archive using stdlib `zipfile`. |
| *"Open file <path>"* | `open_file` | Opens any document with Windows default handler (`os.startfile`). |
| *"Index folder <path>"* | `index_folder` | Chunks and embeds folder documents into ChromaDB `document_knowledge` collection for semantic retrieval. |
| *"Ask docs <query>"*, *"Search documents"* | `ask_documents` | Queries ChromaDB document knowledge base for semantic excerpts answering user's question. |

### J. Browser Automation via Playwright (Phase 6)
| Voice Trigger | Tool Called | Description |
|---|---|---|
| *"Open browser to <url>"*, *"Browse to <x>"* | `browser_open` | Launches Chromium with persistent profile, navigates to URL, returns page title. |
| *"Browser search <query>"* | `browser_search` | Navigates to Google/Bing in interactive browser window and displays search results. |
| *"Click on <link/selector>"* | `browser_click` | Clicks element by text or CSS selector. Blocks payment/checkout buttons automatically. |
| *"Type <text> into <selector>"* | `browser_type` | Fills input field and optionally presses Enter. |
| *"Extract page text"* | `browser_extract_text` | Extracts clean text content from active browser page. |
| *"Take browser screenshot"* | `browser_screenshot` | Saves screenshot of active browser window. |
| *"Download from <url>"* | `browser_download` | Downloads file into user's Downloads folder. |
| *"Close browser"*, *"Browser band karo"* | `browser_close` | Closes Chromium session and releases Playwright resources. |

### K. Productivity, Reminders, Notes, Routines & Google Workspace (Phase 7)
| Voice Trigger | Tool Called | Description |
|---|---|---|
| *"Remind me to <task> in <N> minutes"* | `add_reminder` | Persistent reminder stored in SQLite. Handled by `BackgroundScheduler` even during idle. |
| *"Remind me to <task> at <time>"* | `add_reminder` | Exact time or recurring ('daily', 'weekly') persistent reminder. |
| *"List reminders"*, *"Reminders dikhao"* | `list_reminders` | Fetches active scheduled reminders with due timestamps. |
| *"Delete reminder <id>"* | `delete_reminder` | Removes reminder by ID number. |
| *"Add todo <task>"*, *"Add task <x>"* | `add_todo` | Adds task to SQLite to-do list. |
| *"List todos"*, *"My tasks"*, *"To do list"* | `list_todos` | Shows pending/completed tasks with checkmarks. |
| *"Complete todo <task>"*, *"Task ho gaya"* | `complete_todo` | Marks task as completed by ID or keyword. |
| *"Delete todo <task>"* | `delete_todo` | Removes task from to-do list. |
| *"Add note <title> <content>"* | `add_note` | Saves persistent note with title and text in SQLite. |
| *"List notes"*, *"Notes dikhao"* | `list_notes` | Lists saved notes with keyword search support. |
| *"Read note <title/id>"* | `read_note` | Reads full note body. |
| *"Daily briefing"*, *"Good morning"*, *"Briefing"* | `get_daily_briefing` | Multi-section briefing: Weather, Reminders, To-dos, Headlines, and India block (Cricket & local news). |
| *"Study mode"*, *"Focus mode"*, *"Good night"* | `run_routine` | Runs automated multi-step sequences from `memory/routines.json`. |
| *"List routines"* | `list_routines` | Lists custom automation routines. |
| *"Create routine <name> <actions>"* | `create_routine` | Creates custom automation sequence. |
| *"Today's schedule"*, *"My schedule"* | `get_schedule` | Reads Google Calendar events (behind `ENABLE_GOOGLE=true`). |
| *"Create calendar event <title> <time>"* | `create_calendar_event` | Schedules event on Google Calendar. |
| *"Unread emails"*, *"Check mail"* | `list_unread_emails` | Reads unread Gmail message subjects and senders. |
| *"Draft email reply <id> <text>"* | `draft_email_reply` | Creates draft in Gmail (draft only, sending requires confirmation). |

---

## 5. Tool-Calling Architecture & Safety Protocol

T.U.E.S.D.A.Y utilizes an OpenAI/Groq function-calling tool registry (`core/tools.py`). Actions are declared using the `@tool` decorator:

```python
@tool(
    name="open_app",
    description="Launch an application by name (e.g. chrome, notepad).",
    params_schema={
        "type": "object",
        "properties": {"app_name": {"type": "string"}},
        "required": ["app_name"]
    },
    risk="low"
)
def open_app(app_name: str) -> str:
    ...
```

### Safety Gate & Confirmation Manager
- Tools classified with `risk="high"` (`shutdown_pc`, `restart_pc`, `lock_pc`, `empty_recycle_bin`, `organize_desktop`, dangerous button clicks, payment submissions) require explicit confirmation.
- If called without prior confirmation, `execute_tool` holds execution and responds with a prompt (e.g. *"Bhai, kya sach mein PC shutdown kar doon?"*).
- When the user confirms in the next turn (*"haan"*, *"yes"*, *"kar do"*), the action is executed. If denied (*"nahi"*, *"cancel"*), the action is aborted.

### Audit Logging & Undo Journal
- **Action Audit Log (`logs/actions.jsonl`)**: Appends timestamp, tool name, arguments, risk rating, confirmation status, and human-readable result for every tool execution.
- **Undo Journal (`logs/undo_journal.json`)**: Tracks reversible operations (`move_file`, `rename_file`, `organize_desktop`) so the user can say *"undo that"* to restore original locations.

---

## 6. Groq Model Fallback Chain & Rate Limit Guard

The assistant queries Groq's API on startup to discover all available chat models and sorts them into a priority fallback chain:
1. `qwen/qwen3.8-27b` (Primary default)
2. `openai/gpt-oss-120b` (First fallback)
3. `openai/gpt-oss-20b` (Second fallback)

### Key Guardrails:
- `max_tokens = 500`: Strictly enforces concise responses and prevents exceeding free-tier tokens-per-minute (TPM) limits.
- `RateLimitError` & `429` Handling: Automatically advances `current_model_index` and retries on the next model seamlessly.
- **Clean Dialogue Storage**: Raw web search dumps are injected only into the single turn's prompt payload and are **never saved into persistent history**. This keeps request tokens tiny (~150 tokens) and generation latencies at **~0.21s**.

---

## 7. Overlay UI Specifications (`DynamicIsland`)

- **Design**: Pure OLED black capsule (`#08090E`, opacity 250) with 1px glassmorphic specular top highlight.
- **Physics**: Silk-smooth exponential asymptotic LERP (`lerp_factor = 0.16`). Moves 16% of the remaining distance per frame. Zero harmonic oscillation, zero bounce, zero jiggle.
- **Clipping**: `QPainter.setClipPath(path)` strictly enforces that text and waves never bleed outside the rounded capsule borders.
- **Waveform**: Multi-layered fluid sine wave ribbon centered on the left:
  - Layer 1: Electric Cyan (`#00E6FF`, opacity 190)
  - Layer 2: Siri Royal Violet (`#8C5AFF`, opacity 175)
  - Layer 3: Hot Magenta (`#F03CC8`, opacity 150)
  - Spine: Glowing white core line (`#FFFFFF`, opacity 230)
- **Geometry Sizing**:
  - Short (<= 20 chars): `280px × 48px`
  - Medium (<= 50 chars): `400px × 52px`
  - Long (> 50 chars): `520px × 60px`

---

## 8. Speech & Audio Engine Details

- **TTS Engine**: `gTTS` with automatic language routing:
  - English/Hinglish: `lang="en"`, `tld="co.in"`
  - Pure Hindi: `lang="hi"`
  - Playback via `pygame.mixer` at **27,500 Hz frequency** (~1.15x natural speech pacing).
  - Offline Fallback: `pyttsx3` with local Windows female voice (Zira/Hazel).
- **Speech Interruption (Barge-In)**:
  - Background listener thread runs during speech playback with energy threshold 450.
  - Targeted triggers: `"tuesday stop"`, `"tuesday chup"`, `"tuesday ruko"`, `"tuesday sun"`. Ambient room noise will not cut off speech.

---

## 9. Developer Quick Reference & Testing

```bash
# Run complete test suite (Phase 1 + 3 + 4 + 5 + 6: 30 tests)
python -m pytest tests/ -v

# Start assistant
python main.py

# Toggle listening
[Right Shift + Enter]

# Test tool execution from CLI
python -c "from core.tools import execute_tool; print(execute_tool('get_active_window', {}))"
python -c "from core.tools import execute_tool; print(execute_tool('search_files', {'query': 'invoice'}))"
python -c "from core.tools import execute_tool; print(execute_tool('browser_close', {}))"
```
