# T.U.E.S.D.A.Y — Master Architectural & Capability Index 🧠⚡

> **Developer & AI Model Context Card**  
> *Read this single document to understand 100% of the T.U.E.S.D.A.Y system architecture, commands, data structures, and implementation details without needing to inspect individual source files.*

---

## 1. Project High-Level Overview
- **Name**: T.U.E.S.D.A.Y (Tactical Unified Electronic Systematic Digital Assistant)
- **Role**: Lightweight, proactive, Windows desktop voice assistant inspired by Friday/JARVIS.
- **Persona**: Female voice, sharp, witty, warm, conversational Hinglish (Hindi + English) speaker. Strict no-emoji rule and tight natural punctuation cadence.
- **User Gender**: Male, addressed respectfully as 'Sir' or 'Boss' (`karoge`, `aap sunao`, `Sir`, `Boss`). Strict ban on 'bhai'.
- **Core Loop**: Global Hotkey (`Right Shift + Enter`) → Continuous Active Listening until 5s silence → Local Regex Command Parser (Zero API Latency) → Autonomous ReAct Planner / Universal LLM Brain with tool-calling agent loop (Groq, OpenAI, OpenRouter, DeepSeek, Ollama, LM Studio) → Specialist Multi-Agent Swarm (Research, Analysis, Writing) → Mood-Adaptive Personality Engine (real-time sentiment & time-of-day shifting) → Real-Time Streaming Neural Voice (Edge-TTS `en-IN-NeerjaNeural` / `hi-IN-SwaraNeural`) with instant mid-generation playback (~0.3s start) and real-time Barge-In cancellation → Floating OLED Dynamic Island Overlay UI & Living Cyber ScreenScanOverlay.
- **Background Intelligence**: Proactive Ambient Companion (<1% CPU idle/habit/health monitor) + Background Reminder Scheduler.

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
│   ├── brain.py             # Agentic AI Brain: multi-hop tool loop, fallback chain, SentenceChunker, memory integration
│   ├── planner.py           # Autonomous ReAct Planner: multi-step goal decomposition, tool chaining & self-correction
│   ├── agents.py            # Specialist Multi-Agent Swarm: ResearcherAgent, AnalystAgent, WriterAgent
│   ├── ambient.py           # Proactive Ambient Companion: background idle, health, fatigue & habit monitor
│   ├── mood.py              # Mood-Adaptive Personality Engine: real-time sentiment scoring & time-of-day shifts
│   ├── llm.py               # Universal LLM Client: Groq, OpenAI, OpenRouter, DeepSeek, Ollama, LM Studio + token streaming
│   ├── memory.py            # MemoryStore: SQLite facts/turns/reminders/todos/notes/moods + ChromaDB
│   ├── scheduler.py         # BackgroundScheduler thread checking due reminders & triggering alerts
│   ├── tools.py             # Decorator-based @tool registry, schema auto-normalizer, safety gate & undo journal
│   └── voice.py             # Bilingual STT & Real-Time Streaming Neural TTS (Edge-TTS, gTTS, pyttsx3)
│
├── modules/
│   ├── registered_tools.py  # 45+ native tools wrapping PC, web search, utilities, and diagnostics
│   ├── screen_tools.py      # Screen analysis, active window, dual-engine OCR (winocr + RapidOCR), UI click actions & accent sampling
│   ├── file_tools.py        # Fast file search, PDF/DOCX readers, RAG indexing & file manipulation
│   ├── browser_tools.py     # Playwright browser navigation, interaction, and search
│   ├── productivity_tools.py# Reminders, todos, notes, routines, daily briefing, Google OAuth
│   ├── pc_control.py        # Windows automation: apps, tabs, volume, media, snapping, telemetry
│   ├── command_parser.py    # Zero-latency parser: conversational normalizer, regex table + rapidfuzz matching, action intent detection
│   ├── web_search.py        # Keyless tri-engine: wttr.in (weather), Google News RSS, Wikipedia
│   ├── utilities.py         # Standalone helpers: timers, math, datetime, web shortcuts
│   └── overlay.py           # Dual Overlay UI: OLED Dynamic Island capsule + Living Cyber ScreenScanOverlay
│
├── logs/                    # Audit & safety logs
│   ├── actions.jsonl        # Complete execution history: timestamp, tool, args, risk, confirmed, result
│   └── undo_journal.json    # Reversible actions journal (desktop moves, file moves, renames)
│
├── memory/                  # Local runtime persistence
│   ├── tuesday.db           # SQLite database: user_facts, conversation_turns, reminders, todos, notes, user_moods
│   ├── chroma_db/           # ChromaDB persistent vector database (all-MiniLM-L6-v2 embeddings)
│   ├── routines.json        # Custom named automation sequences (study mode, good night, etc.)
│   ├── conversation_history.json  # Legacy dialogue history (auto-migrated to SQLite)
│   └── user_profile.json          # Legacy user facts (auto-migrated to SQLite)
│
└── tests/
    ├── test_phase1.py            # Unit tests: tools, schemas, agent loop, safety gate, fuzzy parser
    ├── test_phase3.py            # Memory tests: SQLite CRUD, ChromaDB semantic search, privacy guard
    ├── test_phase456.py          # Screen/OCR, File/Undo/RAG, and Playwright browser integration tests
    ├── test_phase7.py            # Productivity, Reminders, Todos, Notes, Routines, Briefing, Google tests
    ├── test_smart_router.py      # Intent router & conversational speech normalizer tests
    ├── test_universal_llm.py     # Multi-provider LLM client & fallback chain tests
    ├── test_mood.py              # Mood-Adaptive Personality Engine & sentiment tests
    ├── test_planner.py           # Autonomous ReAct Planner multi-step chaining tests
    └── test_ambient_and_swarm.py # Ambient Companion & Specialist Multi-Agent Swarm tests

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
        │ - Normalizes conversational speech (strips 'tuesday',  │
        │   'ek kaam karo', 'please', 'na', etc.)                │
        │ - Table-driven regex + rapidfuzz fuzzy app matching    │
        │ - Direct routing for screen, file, browser, PC actions │
        │ - Checks ConfirmationManager for high-risk approvals   │
        └────────────────────────────────────────────────────────┘
                 │                                │
            [YES: Local]                      [NO: AI Intelligence]
                 │                                │
                 ▼                                ▼
       Execute registered @tool        core/mood.py (MoodEngine)
       (direct Python execution)       - Detects user sentiment & emotion
                 │                     - Injects time-of-day tone adaptively
                 │                                │
                 │                     Multi-Step Goal or Deep Query?
                 │                     ├── Multi-Step Goal -> core/planner.py (ReActPlanner)
                 │                     │                      Decomposes goal into steps,
                 │                     │                      executes tool chain with self-correction
                 │                     ├── Deep Web Research -> core/agents.py (AgentSwarm)
                 │                     │                      Researcher + Analyst + Writer
                 │                     │                      parallel fan-out & synthesis
                 │                     └── Standard Interaction -> core/brain.py (AIBrain)
                 │                                │
                 │                     Action/Tool intent detected?
                 │                      ├── NO  -> Pure Chat Mode (tools=None)
                 │                      │          ~150 tokens, instant ~200ms reply
                 │                      └── YES -> Attach Tool Schemas
                 │                                 Multi-hop Groq/OpenAI agent loop
                 │                                │
                 │                     Screen Analysis / OCR triggered?
                 │                      └── YES -> modules/overlay.py (ScreenScanOverlay)
                 │                                 Full-screen living cyber edge glow +
                 │                                 content-reactive accent color lerping
                 │                                │
                 │                     Streaming TTS sentence queue
                 │                     (Edge-TTS neural voices)
                 │                                │
                 └────────────────┬───────────────┘
                                  │
                                  ▼
           Speak response aloud (Edge-TTS en-IN-Neerja / hi-IN-Swara)
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
| *"What's on my screen"*, *"Analyze screen"* | `analyze_screen` | Captures screen, runs local dual-engine Python OCR to map all text & coordinates + active window info, and prompts LLM to reason and recommend actions. |
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

### L. Autonomous ReAct Planner (`core/planner.py`)
| Capability / Trigger | Component | Description |
|---|---|---|
| Multi-step complex goals (e.g., *"Find all PDFs in downloads, zip them, and move to desktop"*) | `ReActPlanner.create_plan` | Automatically detects multi-step goals, decomposes them into structured `PlanStep` sequences, and produces a thought chain. |
| Autonomous Execution Loop | `ReActPlanner.execute_plan` | Executes tool calls sequentially, logs execution observations, and detects step success or failure. |
| Self-Correction & Replanning | `ReActPlanner._replan_from_failure` | When a step fails, prompts LLM with error state to dynamically generate alternative steps without crashing the session. |
| Dynamic Island Live Status | `status_callback` | Updates overlay with active step progress (e.g. `[Step 2/3] Moving zip...`). |

### M. Specialist Multi-Agent Swarm (`core/agents.py`)
| Specialist Agent | Class Name | Function |
|---|---|---|
| **Researcher Agent** | `ResearcherAgent` | Fans out parallel real-time web searches across sub-topics via `concurrent.futures`. |
| **Analyst Agent** | `AnalystAgent` | Cross-checks findings, extracts technical specs & pricing matrices, and strips commercial marketing fluff. |
| **Writer Agent** | `WriterAgent` | Formats structured multi-source intelligence, optionally saves a note to SQLite, and synthesizes a punchy spoken summary. |
| **Swarm Orchestrator** | `AgentSwarm.run` | Coordinates Researcher, Analyst, and Writer pipeline end-to-end for deep questions (*"Compare M3 vs Snapdragon X Elite laptop battery and price"*). |

### N. Proactive Ambient Companion (`core/ambient.py`)
| Ambient Monitor | Frequency / Trigger | Action |
|---|---|---|
| **Ergonomic Fatigue Guard** | Continuous work > 90 mins | Suggests a 5-minute stretch or eye break through speech & Dynamic Island. |
| **Low Battery Alert** | Battery < 20% & unplugged | Proactively alerts user to plug in laptop before shutdown. |
| **High Memory Warning** | RAM usage > 88% sustained | Suggests or offers automated memory optimization (`clean_ram`). |
| **Upcoming Reminder Alert** | Reminders due in < 15 mins | Proactively mentions pending task before the deadline arrives. |
| **Contextual Habit Detection** | Work session start / Evening wrap | Welcomes user in morning with daily briefing prompt; offers evening wrap-up. |

### O. Mood-Adaptive Personality Engine (`core/mood.py`)
| Emotion / Tone | Trigger Lexicon / Conditions | Adaptive Persona Shift |
|---|---|---|
| **Frustrated** (`score: -0.8`) | *"bekar"*, *"kharab"*, *"useless"*, *"hang"*, *"bug"*, *"dimag kharab"* | Deeply empathetic, patient, calm, reassuring. Zero jokes, immediate assistance. |
| **Stressed** (`score: -0.6`) | *"tension"*, *"urgent"*, *"deadline"*, *"pressure"*, *"panic"*, *"load"* | Crisp, hyper-efficient, action-oriented. Skips small-talk and solves blockers. |
| **Tired / Fatigued** (`score: -0.4`) | *"thak gaya"*, *"exhausted"*, *"tired"*, *"sleepy"*, *"neend"* | Soft, soothing, low cognitive load. Offers to defer non-critical tasks. |
| **Happy / Excited** (`score: +0.7`) | *"great"*, *"awesome"*, *"shabash"*, *"mast"*, *"party"*, *"kamaal"* | High energy, sharp, upbeat, celebrates accomplishments. |
| **Time-of-Day Shifting** | Morning (5–12) / Afternoon / Night (22–5) | Injects energizing optimism in morning; calm, low-energy brevity late at night. |
| **Mood Persistence** | SQLite table `user_moods` | Tracks emotional valence over time to notice chronic stress or burnout. |

### P. Living Cyber Screen Scan Overlay (`modules/overlay.py` + `screen_tools.py`)
| Visual Element | Implementation | Behavior |
|---|---|---|
| **Edge Glow Vignette** | 4-Edge `QLinearGradient` (Top, Bottom, Left, Right) | Silky breathing cyber glow framing the screen during OCR and screen analysis. |
| **Radial Energy Blooms** | `QRadialGradient` hotspots | Content-reactive illumination tracking active UI focus points and OCR text centroids. |
| **Perimeter Dot-Matrix Grid** | Cyber aesthetic dot pattern | Retro-futuristic texture bordering the desktop perimeter. |
| **Dynamic Color Sampling** | `screen_tools._sample_screen_accent` | Sub-millisecond dominant screen accent color sampling (lerps between current and target colors). |
| **Error Hotspot Alert** | Red alert RGB (`#F43F5E`) | Automatically turns edge glow red if keywords like `error`, `exception`, or `failed` are spotted on screen. |
| **Silky Pacing & Hold Timer** | Exponential LERP + 2.2s hold | Prevents sub-second OCR from flickering away; holds glow smoothly then fades out gracefully. |

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
- If called without prior confirmation, `execute_tool` holds execution and responds with a prompt (e.g. *"Sir, kya sach mein PC shutdown kar doon?"*).
- When the user confirms in the next turn (*"haan"*, *"yes"*, *"kar do"*), the action is executed. If denied (*"nahi"*, *"cancel"*), the action is aborted.

### Audit Logging & Undo Journal
- **Action Audit Log (`logs/actions.jsonl`)**: Appends timestamp, tool name, arguments, risk rating, confirmation status, and human-readable result for every tool execution.
- **Undo Journal (`logs/undo_journal.json`)**: Tracks reversible operations (`move_file`, `rename_file`, `organize_desktop`) so the user can say *"undo that"* to restore original locations.

---

## 6. Universal LLM Providers & Fallback Chain

The assistant connects to any AI provider via `core/llm.py` (`UniversalLLMClient`):
- **Groq** (Primary ultra-fast default: `openai/gpt-oss-120b`, fallback to `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`)
- **OpenAI** (`gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo`)
- **OpenRouter** (Claude, Gemini, Llama, DeepSeek via unified gateway)
- **DeepSeek** (`deepseek-chat`, `deepseek-reasoner`)
- **Ollama / LM Studio** (Local offline models: `llama3.2`, `qwen2.5`, `mistral`)

### Key Guardrails:
- `max_tokens = 500`: Strictly enforces concise responses and prevents exceeding free-tier limits.
- `RateLimitError` & `429` Handling: Automatically advances `current_model_index` and retries on the next fallback model.
- **Strict No-Emoji Rule**: All LLM replies strictly filter out emojis, symbols, and pictographs.
- **Tight Punctuation Cadence**: Ellipses (`...`) are compressed to eliminate unnatural pauses during audio synthesis.
- **Clean Dialogue Storage**: Raw web search dumps are injected only into the single turn's prompt payload and are **never saved into persistent history**. This keeps request tokens tiny (~150 tokens) and generation latencies at **~0.21s**.

---

## 7. Dual Overlay UI Specifications (`modules/overlay.py`)

### A. Dynamic Island (`DynamicIsland`)
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

### B. Living Cyber Screen Scan Overlay (`ScreenScanOverlay`)
- **Framing**: Full-screen transparent overlay (`FramelessWindowHint | WindowStaysOnTopHint | WindowTransparentForInput`).
- **Edge Vignette**: 4-edge directional gradient blooms (`QLinearGradient`) at top, bottom, left, and right (70px depth) that breathe smoothly while OCR or screen analysis is running.
- **Content-Reactive Accent**: Dynamic color lerp (`_curr_rgb` to `_target_rgb`) sampled from the active screen's dominant color palette via `_sample_screen_accent`.
- **Dynamic Hotspot Blooms**: Orbiting radial gradient blooms (`QRadialGradient`) that illuminate the screen's active visual focus or detected OCR text centroids.
- **Error Spotter Mode**: Automatically shifts border vignette to coral red (`#F43F5E`) when keywords like `error`, `exception`, `failed`, or `traceback` are detected on screen.
- **Smooth Pacing**: Asymptotic ease-in bloom (`_opacity_factor += (1.0 - _opacity_factor) * 0.055`), minimum 2.2-second hold timer (`_min_hold_ms = 2200`) to prevent sub-second flashes, and graceful exponential dissolve (`_opacity_factor *= 0.92`).
- **Thread-Safe Signals**: Controlled via `start_screen_scan(label, accent_rgb)`, `update_screen_scan(...)`, and `stop_screen_scan()`.

---

## 8. Speech & Audio Engine Details

- **TTS Engine**: Real-Time Streaming Neural Speech via `edge-tts`:
  - English/Hinglish: `en-IN-NeerjaNeural` (natural, expressive, crisp Indian female voice)
  - Pure Hindi: `hi-IN-SwaraNeural`
  - Pacing: Accelerated with `rate="+12%"` for tight, snappy dialogue without punctuation gaps.
  - Playback via `pygame.mixer` at **27,500 Hz frequency**.
  - Online Fallback: `gTTS` (`en-IN` / `hi`).
  - Offline Fallback: `pyttsx3` with local Windows female voice (Zira/Hazel).
- **Real-Time Streaming TTS (Mid-Generation Speech)**:
  - `SentenceChunker` chunks LLM tokens on natural sentence boundaries (`. `, `! `, `? `, `\n`).
  - As soon as the first sentence is formed (~200ms), it is enqueued into `speak_stream_chunk()`.
  - While Sentence 1 is playing out loud, Sentence 2 is pre-synthesized in the background for gapless speech.
  - Perceived time-to-first-word drops from ~3.0s down to **~0.3s**!
- **Speech Interruption (Barge-In)**:
  - Background listener thread runs during speech playback with energy threshold 450.
  - Targeted triggers: `"tuesday stop"`, `"tuesday chup"`, `"tuesday ruko"`, `"tuesday sun"`. Ambient room noise will not cut off speech.
  - On interruption, `voice.stop_speaking()` halts audio immediately and clears the speech queue.

---

## 9. Developer Quick Reference & Testing

```bash
# Run complete test suite (76 tests across 9 test suites)
python -m pytest tests/ -v

# Run individual targeted test suites
python -m pytest tests/test_planner.py -v
python -m pytest tests/test_ambient_and_swarm.py -v
python -m pytest tests/test_mood.py -v
python -m pytest tests/test_smart_router.py -v
python -m pytest tests/test_phase456.py -v

# Start assistant
python main.py

# Toggle listening
[Right Shift + Enter]

# Test tool execution from CLI
python -c "from core.tools import execute_tool; print(execute_tool('get_active_window', {}))"
python -c "from core.tools import execute_tool; print(execute_tool('search_files', {'query': 'invoice'}))"
python -c "from core.tools import execute_tool; print(execute_tool('browser_close', {}))"
```
