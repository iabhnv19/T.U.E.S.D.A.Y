<div align="center">

<img width="1792" height="592" alt="df" src="https://github.com/user-attachments/assets/deeed3bd-85ba-4514-84fb-bdc87f4e2309" />

# T.U.E.S.D.A.Y

### Your Windows desktop, on speaking terms.

**Tactical Unified Electronic Systematic Digital Assistant**

A voice-activated AI desktop assistant for Windows, combining natural Hinglish conversations, system automation, persistent memory, browser and file operations, productivity tools, and a minimal Dynamic Island-style interface.

![Platform](https://img.shields.io/badge/platform-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white)
![Language](https://img.shields.io/badge/language-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Interface](https://img.shields.io/badge/interface-PyQt5-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Voice](https://img.shields.io/badge/Voice-Edge--TTS%20Neural-00B4D8?style=for-the-badge)
![AI](https://img.shields.io/badge/AI-Universal%20LLM%20(Cloud%2FOpenAI%2FLocal)-F55036?style=for-the-badge)
![Architecture](https://img.shields.io/badge/architecture-Autonomous%20ReAct-6C5CE7?style=for-the-badge)
![Multi-Agent](https://img.shields.io/badge/agents-Specialist%20Swarm-blueviolet?style=for-the-badge)
![Overlay](https://img.shields.io/badge/overlay-Living%20Cyber%20Scan-0984e3?style=for-the-badge)

</div>

---

## Why this exists

A desktop assistant should do more than answer questions. It should understand a request, interact with the operating system, work with files and applications, remember useful context, anticipate your needs proactively, and get out of the way when it is not needed.

T.U.E.S.D.A.Y is a lightweight, voice-first Windows assistant built around that idea. It combines a fast local command parser for common actions with an **Autonomous ReAct Planner**, a **Specialist Multi-Agent Swarm** (Researcher, Analyst, Writer), a **Proactive Ambient Companion**, and a **Universal LLM AI agent** (supporting Cloud, OpenAI, OpenRouter, DeepSeek, and local Ollama/LM Studio models). Its interface pairs a floating Dynamic Island capsule with a **Living Cyber Screen Scan Overlay**, while its speech layer delivers **Real-Time Streaming Neural Speech** via Microsoft Edge-TTS with Indian English and Hindi support.

The interaction loop is designed to stay simple:

```text
Press Right Shift + Enter
        -> Speak naturally
        -> Mood engine adapts tone & sentiment
        -> Parse a direct command, autonomous plan, or agent query
        -> Execute approved tools with real-time cyber scan feedback
        -> Hear the response stream instantly (~0.3s)
        -> Interrupt speech whenever needed
```

Common commands are handled locally without an LLM round trip. Multi-step workflows trigger the autonomous planner, while complex web analysis delegates to the specialist swarm.

## What it provides

| Capability | Description |
|---|---|
| Voice interaction | Continuous speech input with real-time streaming neural speech (~0.3s start) |
| Local command routing | Regex-based command parser with conversational normalizer & fuzzy matching |
| Universal AI agent | Multi-provider LLM support (Cloud, OpenAI, OpenRouter, DeepSeek, Ollama, LM Studio) |
| Autonomous ReAct Planner | Multi-step goal decomposition, tool execution chaining, thought loop & self-correction |
| Specialist Multi-Agent Swarm | Parallel research fan-out, technical spec comparison, and crisp synthesis |
| Proactive Ambient Companion | Low-overhead (<1% CPU) background health, fatigue, battery, and schedule monitor |
| Mood-Adaptive Engine | Real-time sentiment scoring, time-of-day shifting, and SQLite emotion tracking |
| Living Cyber Scan Overlay | Full-screen content-reactive edge glow, radial energy blooms, and error spotting |
| Windows automation | Application control, window management, volume, media, and desktop actions |
| Screen understanding | Dual-engine Python OCR (winocr + RapidOCR), on-screen text search and clicking |
| File operations | Search, read, create, move, rename, compress, and undo supported file actions |
| Browser automation | Chromium navigation and interaction through Playwright |
| Persistent memory | SQLite-backed facts, conversation turns, reminders, todos, notes, and mood history |
| Semantic retrieval | ChromaDB-based search over past conversations and indexed documents |
| Productivity | Reminders, routines, daily briefings, and optional Google Workspace integration |
| Floating interface | PyQt5 Dynamic Island overlay with animated status and audio visualization |
| Safety controls | Confirmation gates for high-risk actions, audit logs, and an undo journal |

## Features

### Voice assistant and conversation

- Activate the assistant globally with `Right Shift + Enter`.
- Continuous listening supports multi-turn interaction until the configured silence period is reached.
- Speech recognition is configured for Indian English (`en-IN`) and Hindi (`hi-IN`).
- **Real-Time Streaming Neural TTS**: Responses stream sentence-by-sentence via Microsoft Edge-TTS (`en-IN-NeerjaNeural`, `hi-IN-SwaraNeural`), dropping time-to-first-word to ~0.3s.
- Automatic online fallback to `gTTS` and offline fallback to local Windows `pyttsx3`.
- **Strict No-Emoji & Tight Cadence**: Spoken replies filter out all emojis and compress ellipses to eliminate awkward audio pauses.
- Barge-in listening allows speech playback to be interrupted instantly with phrases such as `Tuesday stop`, `Tuesday chup`, `Tuesday ruko`, or `Tuesday sun`.

### Local command parser and AI agent

- A table-driven regex parser handles supported commands without waiting for an LLM.
- **Conversational Speech Normalizer**: Automatically cleans wake words (`Tuesday`), conversational hooks (`bhai`, `yaar`, `suno`, `ek kaam karo`), and politeness tags (`please`, `na`, `kar do`) so commands spoken inside natural dialogue execute locally with zero latency.
- `rapidfuzz` improves application-name matching.
- **Dynamic Tool Injection & Chatbot Mode**: Pure conversational questions (*"tell me a joke"*, *"who was Einstein?"*) bypass tool schemas entirely (`tools=None`), dropping token consumption by 95% and boosting response speed. Tool schemas are dynamically attached only when action/tool intent is detected.
- The AI brain uses function calling to select and execute registered tools when complex automation is required.
- Multi-step tool calls can be chained for requests that require more than one operation.
- The model fallback chain helps handle rate limits by moving to another available model.
- Tool results are converted into a natural-language response rather than exposing raw tool-call data.

### Windows automation and diagnostics

- Launch, close, and focus desktop applications.
- Control system volume, mute state, and media playback.
- Snap, maximize, minimize, and switch windows.
- Create, close, and navigate virtual desktops.
- Open supported Windows Settings pages.
- Capture screenshots and control Windows Game Bar screen recording.
- Inspect CPU, memory, disk, battery, network, and process information.
- Organize desktop files into categories, with a reversible operation recorded in the undo journal.
- Perform supported memory-cleanup operations.

### Screen understanding and UI automation

- Inspect the active window, PID, and process information.
- **Dual-Engine Python OCR**: Local text recognition powered by hardware-accelerated `winocr` (Windows Media OCR) and deep learning `rapidocr-onnxruntime`.
- **Visual On-Screen Text Search & Click**: Find the exact (X, Y) pixel coordinates of any visible button, tab, link, or label and click it directly via PyAutoGUI.
- **Spatial UI Layout Analysis**: Capture the desktop, map on-screen UI text elements with coordinates, and feed the live visual state to the LLM agent to reason and act.
- Read selected text while preserving the existing clipboard contents.
- Enumerate accessible window controls with `pywinauto`.
- Apply safety checks to potentially destructive or sensitive UI actions.

### Files, documents, and knowledge retrieval

- Search configured folders for files.
- Read supported text and code files.
- Extract text from PDF and Word documents.
- Summarize document content through the AI agent.
- Create files and parent directories.
- Move and rename files, with supported operations recorded for undo.
- Compress directories into ZIP archives.
- Open files using their Windows default application.
- Index folders into the document knowledge collection.
- Ask questions against indexed documents using semantic retrieval.

### Browser automation

- Open a Chromium browser session with a persistent profile.
- Navigate to URLs and search the web.
- Click supported links and page elements.
- Fill fields and submit ordinary search forms.
- Extract readable page text.
- Capture browser screenshots.
- Download files to the Downloads folder.
- Close the browser session and release its resources.
- Block supported payment and checkout actions in the browser automation layer.

### Memory and productivity

- Store and retrieve user facts in SQLite.
- Search prior conversation content semantically with ChromaDB.
- Add, list, read, complete, and delete to-do items.
- Create, list, and delete reminders.
- Save and retrieve persistent notes.
- Create and run named routines such as study or focus workflows.
- Generate a daily briefing containing configured weather, reminders, tasks, headlines, and India-related information.
- Optionally read and create Google Calendar events.
- Optionally inspect unread Gmail messages and create email drafts. Sending an email is not part of the draft operation.

### Dynamic Island overlay

- Floating PyQt5 capsule interface for assistant status and response text.
- Smooth position interpolation for movement.
- Multi-layer animated waveform visualization during speech.
- Capsule sizing adapts to short, medium, and long text.
- Text and waveform rendering are clipped to the rounded overlay boundary.

### Autonomous ReAct Planner (`core/planner.py`)

- **Multi-Step Goal Decomposition**: Decomposes complex user requests (*"Find all PDFs in downloads, zip them, and move them to desktop"*) into structured, atomic `PlanStep` sequences.
- **Thought-Action-Observation Loop**: Formulates reasoning thoughts before each tool call, executes the tool, evaluates the observation, and advances the plan.
- **Autonomous Self-Correction**: When a step encounters an error or missing file, the planner prompts the LLM to inspect the error and replan dynamically on the fly without breaking execution.
- **Dynamic Island Live Updates**: Streams step progress (e.g. `[Step 2/3] Compressing files...`) directly to the floating capsule.

### Specialist Multi-Agent Swarm (`core/agents.py`)

- **Researcher Agent**: Fans out parallel real-time web searches across sub-queries using thread pooling (`concurrent.futures`).
- **Analyst Agent**: Scrapes and cross-examines findings, extracts technical specifications, price comparisons, and filters marketing fluff.
- **Writer Agent**: Synthesizes structured markdown intelligence, automatically persists notes to SQLite, and formats a crisp spoken summary for voice output.
- **End-to-End Orchestration**: Triggers automatically on deep research or product comparison queries.

### Proactive Ambient Companion (`core/ambient.py`)

- **Lightweight Background Thread**: Operates at `<1% CPU` overhead using Windows `GetLastInputInfo` idle detection and `psutil`.
- **Ergonomic Fatigue Alerts**: Monitors continuous active screen time and gently suggests short stretch or eye breaks after 90 minutes.
- **Hardware Health Guardian**: Proactively notifies the user of low battery (<20% unplugged) and high sustained RAM usage (>88%).
- **Preemptive Reminder Alerts**: Alerts the user of scheduled tasks 15 minutes before the due time.
- **Contextual Greetings**: Greets the user in the morning with a daily briefing prompt and offers a clean wrap-up in the evening.

### Mood-Adaptive Personality Engine (`core/mood.py`)

- **Real-Time Sentiment Scoring**: Evaluates bilingual English + Hinglish cues for frustration, stress, fatigue, or excitement.
- **Adaptive Persona Shifting**: Automatically tunes tone:
  - *Frustrated*: Calm, patient, reassuring, zero humor, direct problem solving.
  - *Stressed*: Hyper-efficient, concise, skips small talk.
  - *Tired*: Low cognitive load, soothing, offers task deferral.
  - *Excited*: Upbeat, celebratory, high-energy.
- **Time-of-Day Cadence**: Shifts tone from energizing optimism in the morning to calm, quiet brevity late at night.
- **SQLite Mood Tracking**: Records emotional history to monitor burnout and stress trends over time.

### Living Cyber Screen Scan Overlay (`modules/overlay.py`)

- **Full-Screen Living Vignette**: Breathing glowing edge borders (top, bottom, left, right) rendered via `QLinearGradient` during OCR and screen analysis.
- **Content-Reactive Color Sampling**: Sub-millisecond dominant screen accent sampling that dynamically lerps border colors to match the active content.
- **Orbiting Radial Energy Blooms**: Radial gradient blooms highlight spatial UI text centroids and active focus areas.
- **Error Hotspot Spotter**: Shifts the perimeter glow to coral red (`#F43F5E`) when on-screen error logs, exceptions, or failures are detected.
- **Silky Pacing**: Smooth exponential easing with a 2.2-second minimum hold timer ensures the scan animation breathes naturally without flickering away prematurely.

## Quick start

### Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- A working microphone and audio output device
- Internet connection for AI conversations and online services
- An AI API key for conversation and tool-calling features (Cloud, OpenAI, OpenRouter, DeepSeek, or local Ollama)

Some capabilities depend on Windows APIs, installed applications, optional services, and their corresponding configuration.

### Clone the repository

```bash
git clone https://github.com/iabhnv19/T.U.E.S.D.A.Y.git
cd T.U.E.S.D.A.Y
```

Replace the repository URL above if the project is hosted under a different GitHub repository name.

### Install dependencies

```bash
python -m pip install -r requirements.txt
```

### Configure environment variables

Create your local `.env` file from the example:

```bash
copy .env.example .env
```

Open `.env` and add your LLM API credentials:

```env
LLM_PROVIDER=cloud
LLM_API_KEY=your_api_key_here
LLM_MODEL=openai/gpt-oss-120b
```

Do not commit `.env` or publish API keys. The `.env.example` file is intended to contain placeholders only.

### Run T.U.E.S.D.A.Y

```bash
python main.py
```

Press **`Right Shift + Enter`** to activate listening.

## Configuration

The following settings are documented by the project:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `cloud` | Active AI provider (`cloud`, `openai`, `openrouter`, `deepseek`, `ollama`, `lmstudio`) |
| `LLM_API_KEY` | Not set | Universal API key for the selected AI provider |
| `LLM_MODEL` | Provider default | Default model (e.g. `openai/gpt-oss-120b`, `gpt-4o-mini`, `llama3.2`) |
| `LLM_BASE_URL` | Provider default | Custom OpenAI-compatible endpoint URL (optional) |
| `TTS_ENGINE` | `edge-tts` | Primary voice engine (`edge-tts`, `gtts`, `pyttsx3`, `auto`) |
| `EDGE_VOICE_EN` | `en-IN-NeerjaNeural` | Microsoft Neural voice for English / Hinglish speech |
| `EDGE_VOICE_HI` | `hi-IN-SwaraNeural` | Microsoft Neural voice for Hindi speech |
| `ASSISTANT_NAME` | `T.U.E.S.D.A.Y` | Assistant display name |
| `HOTKEY_MODIFIER` | `right shift` | Modifier used by the global activation shortcut |
| `HOTKEY_KEY` | `enter` | Key used with the modifier to activate listening |
| `VOICE_LANGUAGE` | `en-IN` | Speech recognition language tag |
| `WEATHER_CITY` | `Amritsar` | Default city for weather requests |

Additional optional integrations, including Google Workspace, are controlled through project configuration. Check `core/config.py` and `.env.example` for the current supported environment settings.

## Common voice commands

The assistant supports a broad command set. These examples cover frequently used actions; the complete capability and tool mapping is documented in [`TUESDAY_INDEX.md`](./TUESDAY_INDEX.md).

| Category | Example command | Action |
|---|---|---|
| Clipboard | "Make this professional" | Rewrites clipboard text into polished English |
| Clipboard | "Summarize clipboard" | Summarizes copied text |
| Clipboard | "Translate to Hindi" | Translates clipboard content |
| Diagnostics | "System diagnostics" | Reports system health and resource usage |
| Diagnostics | "Clean RAM" | Runs the supported memory-cleanup operation |
| Network | "What's my IP" / "Check ping" | Reports network information and latency |
| Desktop | "Clean my desktop" | Organizes loose desktop files |
| Screen | "What's on my screen" / "Analyze screen" | Triggers cyber scan overlay, maps screen layout via OCR, and reasons |
| Screen | "Find text Submit on screen" | Locates visual element coordinates via local OCR |
| Screen | "Click text Save on screen" | Clicks element center using OCR-guided coordinates |
| Screen | "Read screen text" | Extracts on-screen text with layout preservation |
| Screen | "Take a screenshot" | Captures the desktop |
| Screen | "Start screen recording" | Starts Windows Game Bar recording |
| Windows | "Snap left" / "Snap right" | Snaps the active window |
| Windows | "New desktop" | Creates a virtual desktop |
| Apps | "Open Chrome" | Launches an application |
| Media | "Pause" / "Next track" | Controls media playback |
| Search | "Google search Python tutorial" | Opens a Google search |
| Research | "Compare M3 vs Snapdragon X Elite battery" | Specialist Multi-Agent Swarm fans out parallel research |
| Planner | "Find PDFs in Downloads and zip to Desktop" | Decomposes goal into multi-step ReAct execution plan |
| Ambient | "How long have I been working" | Proactive ambient check for continuous work time & fatigue |
| Files | "Search files for invoice" | Searches configured folders |
| Files | "Read PDF [path]" | Extracts PDF text |
| Browser | "Open browser to [URL]" | Opens a page in the automation browser |
| Memory | "Remember that ..." | Stores a user fact |
| Productivity | "Remind me to ... in 10 minutes" | Creates a reminder |
| Productivity | "Add todo ..." | Adds a task |
| Productivity | "Daily briefing" | Generates the configured daily briefing |

## Architecture

T.U.E.S.D.A.Y uses a hybrid intelligence architecture. Fast commands execute locally with zero latency, complex goals trigger the Autonomous ReAct Planner or Specialist Swarm, and general reasoning is routed through the Universal LLM Agent with live visual scan feedback.

```mermaid
flowchart TD

subgraph group_interaction["Voice and Interface"]
  node_app["Assistant Runtime<br/>[main.py]"]
  node_voice["Speech I/O<br/>[voice.py]"]
  node_overlay["Floating Overlays<br/>[overlay.py]"]
end

subgraph group_reasoning["Reasoning and Agents"]
  node_parser["Command Parser<br/>[command_parser.py]"]
  node_brain["AI Brain<br/>[brain.py]"]
  node_planner["ReAct Planner<br/>[planner.py]"]
  node_agents["Specialist Swarm<br/>[agents.py]"]
  node_llm["Universal LLM<br/>[llm.py]"]
  node_mood["Mood Engine<br/>[mood.py]"]
end

subgraph group_actions["Tools and Automation"]
  node_tool_dispatch["Tool Registry and Safety<br/>[tools.py]"]
  node_registered["Desktop Action Tools"]
  node_pc["Windows Control<br/>[pc_control.py]"]
  node_utilities["System Utilities<br/>[utilities.py]"]
  node_screen["Screen Understanding<br/>[screen_tools.py]"]
  node_browser["Browser Operations<br/>[browser_tools.py]"]
  node_files["File Operations<br/>[file_tools.py]"]
  node_web["Web Search<br/>[web_search.py]"]
end

subgraph group_context["Memory and Productivity"]
  node_productivity["Productivity Tools"]
  node_memory[("Persistent Memory<br/>[memory.py]")]
end

subgraph group_proactive["Proactive Support"]
  node_scheduler["Reminder Scheduler<br/>[scheduler.py]"]
  node_ambient["Ambient Companion<br/>[ambient.py]"]
end

node_user(("Desktop User"))
node_external_services{{"AI and Web Services"}}

node_user -->|"activates"| node_app
node_app -->|"captures speech"| node_voice
node_voice -->|"transcribes"| node_app
node_app -->|"routes requests"| node_brain
node_app -->|"routes commands"| node_parser
node_parser -->|"executes direct tools"| node_tool_dispatch
node_brain -->|"delegates goals"| node_planner
node_brain -->|"delegates research"| node_agents
node_brain -->|"requests completions"| node_llm
node_planner -->|"generates plans"| node_llm
node_brain -->|"adapts tone"| node_mood
node_brain -->|"reads and records"| node_memory
node_agents -->|"researches with"| node_web
node_brain -->|"invokes tools"| node_tool_dispatch
node_planner -->|"executes steps"| node_tool_dispatch
node_tool_dispatch -->|"loads tool set"| node_registered
node_registered -->|"delegates control"| node_pc
node_registered -->|"uses utilities"| node_utilities
node_registered -->|"uses search"| node_web
node_registered -->|"uses stored context"| node_memory
node_brain -->|"uses screen tools"| node_screen
node_brain -->|"uses browser tools"| node_browser
node_brain -->|"uses file tools"| node_files
node_productivity -->|"stores reminders and notes"| node_memory
node_app -->|"starts scheduler"| node_scheduler
node_scheduler -->|"reads reminders"| node_memory
node_app -->|"starts monitor"| node_ambient
node_ambient -->|"uses memory"| node_memory
node_app -->|"updates interface"| node_overlay
node_brain -->|"streams response"| node_voice
node_llm -->|"calls providers"| node_external_services
node_web -->|"queries online sources"| node_external_services
node_productivity -.->|"optionally accesses Workspace"| node_external_services
node_voice -.->|"optionally uses speech services"| node_external_services

click node_app "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/main.py"
click node_voice "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/core/voice.py"
click node_overlay "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/modules/overlay.py"
click node_parser "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/modules/command_parser.py"
click node_brain "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/core/brain.py"
click node_planner "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/core/planner.py"
click node_agents "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/core/agents.py"
click node_llm "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/core/llm.py"
click node_mood "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/core/mood.py"
click node_tool_dispatch "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/core/tools.py"
click node_registered "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/modules/registered_tools.py"
click node_pc "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/modules/pc_control.py"
click node_utilities "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/modules/utilities.py"
click node_screen "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/modules/screen_tools.py"
click node_browser "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/modules/browser_tools.py"
click node_files "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/modules/file_tools.py"
click node_web "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/modules/web_search.py"
click node_productivity "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/modules/productivity_tools.py"
click node_memory "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/core/memory.py"
click node_scheduler "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/core/scheduler.py"
click node_ambient "https://github.com/iabhnv19/t.u.e.s.d.a.y/blob/main/core/ambient.py"

classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a
classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
class node_app,node_voice,node_overlay,node_user toneBlue
class node_parser,node_brain,node_planner,node_agents,node_llm,node_mood toneAmber
class node_tool_dispatch,node_registered,node_pc,node_utilities,node_screen,node_browser,node_files,node_web toneMint
class node_productivity,node_memory toneRose
class node_scheduler,node_ambient,node_external_services toneIndigo
```

### Main responsibilities

| Component | Responsibility |
|---|---|
| `main.py` | Application entry point, Qt application lifecycle, global hotkey, listening and barge-in coordination |
| `core/config.py` | Environment loading, central configuration, and assistant system prompt |
| `core/brain.py` | AI agent loop, multi-model fallback, tool orchestration, and memory integration |
| `core/planner.py` | Autonomous ReAct Planner for multi-step goal decomposition, tool chaining, and self-correction |
| `core/agents.py` | Specialist Multi-Agent Swarm (Researcher, Analyst, Writer) for deep research and synthesis |
| `core/ambient.py` | Proactive Ambient Intelligence companion monitoring ergonomics, battery, RAM, and habits (<1% CPU) |
| `core/mood.py` | Mood-Adaptive Personality Engine tracking sentiment, stress, and time-of-day conversational tone |
| `core/llm.py` | Universal LLM Client supporting Cloud, OpenAI, OpenRouter, DeepSeek, Ollama, and LM Studio |
| `core/memory.py` | SQLite persistence (facts, turns, reminders, todos, notes, moods) and ChromaDB semantic memory |
| `core/scheduler.py` | Background reminder scheduler |
| `core/tools.py` | Decorator-based tool registry, schemas, safety gate, confirmation manager, and undo journal |
| `core/voice.py` | Speech recognition, language handling, real-time streaming Edge-TTS, and audio playback |
| `modules/command_parser.py` | Local regex command routing, conversational normalizer, and fuzzy application matching |
| `modules/registered_tools.py` | 45+ registered native tools for Windows, utilities, web search, and diagnostics |
| `modules/screen_tools.py` | Screen inspection, dual-engine OCR (winocr + RapidOCR), UI click actions, and screen accent sampling |
| `modules/file_tools.py` | File operations, document extraction, indexing, and retrieval |
| `modules/browser_tools.py` | Playwright browser automation |
| `modules/productivity_tools.py` | Reminders, tasks, notes, routines, briefing, and optional Google integration |
| `modules/pc_control.py` | Windows application, window, media, volume, and system controls |
| `modules/web_search.py` | Keyless weather, news, and Wikipedia lookup helpers |
| `modules/utilities.py` | Standalone utility functions |
| `modules/overlay.py` | Dual overlay UI: OLED Dynamic Island capsule + Living Cyber ScreenScanOverlay with content-reactive edge glow |

## Safety, confirmations, and audit logs

Desktop automation can change files and system state, so tool execution is not treated as an unrestricted command pipe.

- Tools have risk classifications.
- High-risk operations require explicit user confirmation before execution.
- Confirmation can be accepted or denied in the following interaction.
- Executed tool calls are recorded in `logs/actions.jsonl`.
- Reversible file and desktop operations are tracked in `logs/undo_journal.json`.
- Supported undo commands can restore recorded file moves, renames, and desktop organization operations.
- Browser automation includes safeguards for payment and checkout actions.

These controls reduce accidental execution, but they do not replace reviewing a command before approving it.

## Memory and local data

T.U.E.S.D.A.Y stores its runtime data locally in the project directories:

| Location | Purpose |
|---|---|
| `memory/tuesday.db` | SQLite database for facts, conversation turns, reminders, todos, and notes |
| `memory/chroma_db/` | Persistent ChromaDB vector store |
| `memory/routines.json` | User-defined automation routines |
| `memory/conversation_history.json` | Legacy conversation history, migrated to SQLite |
| `memory/user_profile.json` | Legacy user facts, migrated to SQLite |
| `logs/actions.jsonl` | Tool execution audit history |
| `logs/undo_journal.json` | Reversible operation history |

The project index documents a ChromaDB embedding configuration using `all-MiniLM-L6-v2`. Runtime databases, logs, user profiles, credentials, and other generated data should remain local and should not be committed to the repository.

## Project structure

```text
T.U.E.S.D.A.Y/
├── .env                         # Local credentials and runtime settings; do not commit
├── .env.example                 # Safe environment variable template
├── .gitignore
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest configuration
├── README.md
├── TUESDAY_INDEX.md             # Detailed architecture and capability reference
├── main.py                      # Application entry point and orchestrator
│
├── core/
│   ├── config.py                # Configuration and assistant system prompt
│   ├── brain.py                 # AI agent and tool-calling loop
│   ├── planner.py               # Autonomous ReAct Planner (multi-step decomposition & self-correction)
│   ├── agents.py                # Specialist Multi-Agent Swarm (Researcher, Analyst, Writer)
│   ├── ambient.py               # Proactive Ambient Companion (background health, habits & fatigue)
│   ├── mood.py                  # Mood-Adaptive Personality Engine (real-time sentiment & time-of-day tone)
│   ├── llm.py                   # Universal LLM Client (Cloud, OpenAI, OpenRouter, DeepSeek, Ollama)
│   ├── memory.py                # SQLite (facts, turns, reminders, todos, notes, moods) & ChromaDB
│   ├── scheduler.py             # Background reminder scheduler
│   ├── tools.py                 # Tool registry and safety mechanisms
│   └── voice.py                 # Speech recognition and real-time streaming Edge-TTS
│
├── modules/
│   ├── registered_tools.py      # Core registered tools
│   ├── screen_tools.py          # Screen analysis, OCR, UI automation, and screen accent sampling
│   ├── file_tools.py            # File handling, documents, and RAG
│   ├── browser_tools.py          # Playwright browser automation
│   ├── productivity_tools.py    # Productivity and Google integrations
│   ├── pc_control.py             # Windows automation
│   ├── command_parser.py        # Local command parser & conversational speech normalizer
│   ├── web_search.py             # Weather, news, and knowledge lookup
│   ├── utilities.py              # Utility helpers
│   └── overlay.py                # Dynamic Island capsule & Living Cyber ScreenScanOverlay
│
├── logs/                         # Runtime audit and undo logs
├── memory/                       # Local databases and persistent assistant data
└── tests/
    ├── test_phase1.py            # Core tools, schemas, agent, safety, parser
    ├── test_phase3.py            # Memory and semantic search
    ├── test_phase456.py          # Screen, file, RAG, and browser tests
    ├── test_phase7.py            # Productivity and Google integration tests
    ├── test_smart_router.py      # Intent router and normalizer tests
    ├── test_universal_llm.py     # Multi-provider LLM client tests
    ├── test_mood.py              # Mood engine and sentiment tests
    ├── test_planner.py           # ReAct planner multi-step chaining tests
    └── test_ambient_and_swarm.py # Ambient companion & multi-agent swarm tests
```

## Development and testing

Run the full test suite (76 tests across 9 test suites) from the repository root:

```bash
python -m pytest tests/ -v
```

Start the assistant:

```bash
python main.py
```

The architecture index also documents direct tool-execution examples for development:

```bash
python -c "from core.tools import execute_tool; print(execute_tool('get_active_window', {}))"
python -c "from core.tools import execute_tool; print(execute_tool('search_files', {'query': 'invoice'}))"
python -c "from core.tools import execute_tool; print(execute_tool('browser_close', {}))"
```

Run targeted tests for specific intelligence subsystems:

```bash
python -m pytest tests/test_planner.py -v
python -m pytest tests/test_ambient_and_swarm.py -v
python -m pytest tests/test_mood.py -v
python -m pytest tests/test_smart_router.py -v
```

Some tests exercise Windows-specific functionality or optional integrations. Their results may depend on the host environment and installed services.

## Tech stack

| Technology | Purpose |
|---|---|
| Python | Application logic and orchestration |
| PyQt5 | Floating desktop overlay |
| Cloud / Local LLM | AI inference and function calling |
| SpeechRecognition | Microphone input and speech-to-text |
| gTTS | Online text-to-speech |
| pygame | Audio playback |
| pyttsx3 | Offline text-to-speech fallback |
| SQLite | Structured persistent storage |
| ChromaDB | Semantic memory and document retrieval |
| Playwright | Browser automation |
| pywinauto | Windows UI automation |
| psutil | System and process telemetry |
| PyAutoGUI / pywin32 | Desktop and Windows automation |
| rapidfuzz | Fuzzy command and application matching |
| pytest | Automated testing |

## Troubleshooting

<details>
<summary><strong>AI API requests fail or return rate-limit errors</strong></summary>

Check that `LLM_API_KEY` is present in `.env` and that the key is valid. The agent has a model fallback mechanism for rate limits, but all available models can still be unavailable or restricted by account limits.

</details>

<details>
<summary><strong>The global hotkey does not activate the assistant</strong></summary>

Confirm that the application is running and that the configured modifier and key match `HOTKEY_MODIFIER` and `HOTKEY_KEY`. Check whether another application or utility is intercepting the shortcut.

</details>

<details>
<summary><strong>Speech recognition cannot hear me</strong></summary>

Check the Windows microphone input device, microphone permissions, and input volume. Speech recognition may also require a working network connection depending on the configured recognizer.

</details>

<details>
<summary><strong>There is no spoken response</strong></summary>

Check the selected Windows output device and system volume. Verify that the audio dependencies installed successfully. The project documents gTTS playback and a `pyttsx3` offline fallback.

</details>

<details>
<summary><strong>Browser automation cannot start</strong></summary>

Check the Playwright installation and browser availability. Install the required Playwright browser runtime if it is not present in the environment:

```bash
python -m playwright install chromium
```

</details>

<details>
<summary><strong>Google Calendar or Gmail features are unavailable</strong></summary>

These integrations are optional and require their corresponding configuration and Google OAuth setup. They are not required for the core local assistant workflow.

</details>

## Known limitations

- T.U.E.S.D.A.Y is designed for Windows and relies on Windows-specific APIs and automation libraries.
- AI conversations and several online services require internet access.
- Cloud AI availability, provider model limits, and API behavior can change independently of the project.
- Screen analysis, OCR, and UI automation depend on the active application and accessible controls.
- Browser automation behavior can vary across websites and their layouts.
- Google Workspace functionality requires optional OAuth configuration.
- Hardware telemetry and system-control behavior may vary by Windows version and permissions.

## Contributing

Contributions, bug reports, and feature requests are welcome. Please keep changes focused, avoid committing credentials or generated runtime data, and include tests for changes to core behavior.

## Developer

<div align="center">

<a href="https://github.com/iabhnv19">
  <img src="https://github.com/iabhnv19.png" width="80" height="80" alt="GitHub profile picture" />
  <br />
  Abhinav
  <br />
  @iabhnv19
</a>

<br />

**Built with Python to make desktop automation feel like a conversation.**

</div>
