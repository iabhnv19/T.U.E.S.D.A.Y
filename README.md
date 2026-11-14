# T.U.E.S.D.A.Y 🎙️⚡

> **Tactical Unified Electronic Systematic Digital Assistant**  
> A fast, voice-activated AI desktop companion for Windows with native Hinglish fluency, Siri-style Dynamic Island overlay, and hardware automation.

[![System Architecture](https://img.shields.io/badge/Architecture-TUESDAY__INDEX.md-blue?style=flat-square)](./TUESDAY_INDEX.md)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](#)

> [!TIP]
> **For AI Agents & Developers**: To save context window tokens, read [`TUESDAY_INDEX.md`](./TUESDAY_INDEX.md) — it contains the full architectural reference, voice command matrix, data flows, and JSON schemas in a single file!

---

## ✨ Features

- **🎙️ Hands-Free Voice Control**: Press `Right Shift + Enter` to activate continuous listening mode. Stays awake through multi-turn conversations until silence is detected.
- **🛑 Real-Time Speech Interruption (Barge-In)**: Cut in anytime while she's speaking by saying *"Tuesday stop"*, *"Tuesday sun"*, or starting a new query with *"Tuesday..."*.
- **🏝️ Dynamic Island Overlay**: Clean, minimal capsule pill that glides into place with smooth exponential interpolation and multi-layered fluid ribbon waveforms.
- **📋 Smart Clipboard AI Copilot**:
  - *"Make this professional"* — Rewrites rough drafts or emails into polished business English.
  - *"Summarize clipboard"* — Summarizes copied articles or notes in 1–2 punchy sentences.
  - *"Translate to Hindi / English"* — Translates clipboard text and loads the result ready to paste.
- **🛡️ Hardware Telemetry & Diagnostics**:
  - *"System diagnostics"* — Reports CPU load, RAM usage, free C: disk space, battery status, and the top 2 memory-consuming processes.
  - *"Clean RAM"* — Trims working sets and frees memory.
- **🌐 Network Radar**:
  - *"What is my IP"* / *"Check ping"* — Reports local IP, public IP, and live ping latency in milliseconds.
- **🗂️ One-Click Desktop Organizer**:
  - *"Clean my desktop"* — Scans your Windows Desktop and sorts loose files into `Images`, `Documents`, `Installers`, and `Media` folders.
- **🎥 Windows Screen Recording**:
  - *"Start screen recording"* / *"Stop recording"* — Controls native Windows Game Bar (`Win + Alt + R`) with recordings saved directly to `Videos\Captures`.
- **🪟 Power Window Snapping & Virtual Desktops**:
  - *"Snap left"*, *"Snap right"*, *"Maximize"*, *"Task view"*, *"New desktop"*.
- **⚡ Free-Tier Failover Engine**: Powered by Groq with automatic failover across active chat models so you never get stuck on rate limits.

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/your-username/T.U.E.S.D.A.Y.git
cd T.U.E.S.D.A.Y
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup configuration
Copy the example environment file:
```bash
cp .env.example .env
```
Open `.env` and add your free Groq API key (get one at [console.groq.com](https://console.groq.com)):
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 4. Run the assistant
```bash
python main.py
```

Press **`Right Shift + Enter`** to wake Tuesday.

---

## 🗣️ Common Voice Commands

| Category | Spoken Command | Action |
|---|---|---|
| **Clipboard** | *"Make this professional"* | Rewrites draft on clipboard into formal English |
| **Clipboard** | *"Summarize this"* | Summarizes copied text in 1–2 sentences |
| **Clipboard** | *"Translate to Hindi / English"* | Translates clipboard text |
| **Diagnostics** | *"System diagnostics"* | Reports CPU, RAM, disk, and top memory-hogging apps |
| **Diagnostics** | *"Clean RAM"* | Optimizes memory usage |
| **Network** | *"What's my IP"* / *"Check ping"* | Live IP and ping latency |
| **Desktop** | *"Clean my desktop"* | Organizes loose desktop files into folders |
| **Screen** | *"Start screen recording"* | Starts recording (`Win + Alt + R`) |
| **Screen** | *"Stop recording"* | Stops and saves recording |
| **Screen** | *"Take a screenshot"* | Saves screenshot to project directory |
| **Windows** | *"Snap left"* / *"Snap right"* | Snaps window to screen halves |
| **Windows** | *"New tab"* / *"Close tab"* | Browser tab controls |
| **Apps** | *"Open Chrome"* / *"Close Notepad"* | Launches or terminates apps |
| **Media** | *"Play"* / *"Pause"* / *"Next track"* | Media playback |
| **Search** | *"YouTube per search kar Python tutorial"* | Opens YouTube directly to query |
| **Search** | *"Google search Machine Learning"* | Opens Google search |

---

## ⚙️ Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *None* | Required for AI conversation (Free on Groq) |
| `ASSISTANT_NAME` | `T.U.E.S.D.A.Y` | Assistant display name |
| `HOTKEY_MODIFIER` | `right shift` | Wake hotkey modifier |
| `HOTKEY_KEY` | `enter` | Wake hotkey trigger key |
| `VOICE_LANGUAGE` | `en-IN` | Speech recognition language tag |
| `WEATHER_CITY` | `Amritsar` | Default city for weather queries |

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **PyQt5** — Floating Dynamic Island overlay UI
- **Groq API** — Ultra-fast LLM inference
- **SpeechRecognition & gTTS** — Bilingual Hinglish STT/TTS
- **PyAutoGUI & pywin32** — Windows PC automation and window management
- **psutil** — Hardware diagnostics and process telemetry

