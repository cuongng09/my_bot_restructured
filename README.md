# 🤖 Ollama Telegram Bot v6.2

<p align="center">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey" alt="Platform" />
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python version" />
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status" />
  <img src="https://img.shields.io/badge/architecture-modular-orange" alt="Architecture" />
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License" />
</p>

<p align="center">
  <img src="bia_repo.png" alt="Telegram AI Bot Banner" width="100%" />
</p>

> **A free, powerful, self-hosted AI assistant for Telegram:** Powered by Ollama (streaming LLM responses + deep hidden reasoning), a multi-tier intelligent web-search system (SearXNG/DuckDuckGo + core-keyword extraction + real-time context anchoring), 100% local two-way voice (faster-whisper + Piper TTS), vision OCR & image/PDF translation, self-summarizing long-term memory, and a dual interface (Telegram dashboard + a traditional lacquer-styled web app).

---

## 🌟 Key Features

### 1. 🧠 AI Intelligence & Deep Reasoning
- **Real-time streaming responses:** Smooth, token-by-token replies with the ability to cancel an in-progress generation using `/stop`.
- **Hidden chain-of-thought reasoning:** Automatically classifies complex questions (math, coding, multi-dimensional analysis) and forces the model to "think silently" inside a `<suy_nghi>` tag before producing the final answer; the thinking portion is stripped out by `ThinkingStreamFilter`.
- **4 flexible personas:** Instantly switch tone between `ban_than` (Close Friend), `chuyen_gia` (Expert), `hai_huoc` (Humorous), and `co_van` (Strategic Advisor).
- **Profile & long-term memory:** Automatically distills user habits and preferences every 10 conversation turns to personalize responses without bloating the context window (supports per-user reset via `/resetmemory`).

### 2. 🌐 Multi-Tier, Real-Time Smart Web Search (Smart Web RAG)
- **Flexible search sources:** Prioritizes a self-hosted **SearXNG** instance (private, no rate limits) with automatic fallback to the **DuckDuckGo API (DDGS)** and direct HTML scraping.
- **Fast heuristic intent filter:** Instantly recognizes greetings, coding requests, math problems, creative writing, and casual chat to answer directly from the model's own knowledge — skipping unnecessary web searches.
- **Query reformulation:** Automatically converts natural-language questions into clean, search-engine-ready keywords for Google/DuckDuckGo.
- **Adaptive keyword extraction & retry:** When a long or complex technical query returns no results, the system automatically strips modifier words while preserving version numbers (e.g. `3.7`, `3.14`, `5090`) and retries, enabling accurate real-time technical searches (`<core_query> latest update`).
- **Real-time clock anchor (GMT+7):** Supplies the model with the current date/time and cross-references retrieved data against the model's own knowledge for fast-moving domains (AI, software, new technology) — **completely eliminating unhelpful "no data found" replies**.
- **Trusted-source prioritization & security:** Ranks trusted sources first (VnExpress, Tuổi Trẻ, Government News, WHO, Wikipedia, etc.) and includes an **SSRF Guard** to block the bot from accessing malicious internal IP addresses.

### 3. 🎙️ 100% Local Two-Way Voice (No External API Required)
- **Speech-to-text (STT):** Uses `faster-whisper` running directly on the server (CPU/GPU) for highly accurate Vietnamese recognition, with automatic fallback to the Groq Whisper API if configured.
- **Text-to-speech (TTS):** Converts text into natural Vietnamese speech via `Piper TTS` using lightweight ONNX models.
- **3 voice-reply modes (`/ttsmode`):** `off` (text only), `smart` (auto voice for short/medium replies), `always` (always reply with voice).

### 4. 🖼️ Multi-Format Vision OCR & Translation
- **Image & PDF support:** Automatically extracts text from image files (JPG, PNG, WebP) and PDF documents (both scanned and text-layer PDFs).
- **Automatic language detection:** Detects Vietnamese or English and provides accurate two-way translation.

### 5. 🏮 Dual Interface: Telegram Dashboard & Lacquer-Styled Web App
- **Telegram Control Station (`/ui`):** A multi-level inline-keyboard menu split into 3 branches: 💬 Chat · 🧰 Utilities · 🖥️ System. Change the Ollama model, voice, and persona visually with button taps.
- **Web Control Station (`webapp/`):** A browser-based admin dashboard built with FastAPI + Vanilla JS, styled in the language of **traditional Vietnamese lacquer art** (black lacquer, vermilion red, gold inlay). Monitors Ollama status in real time (a blinking status seal), CPU/RAM/disk hardware stats, active users, and a live terminal log.

---

## 🛠️ System Requirements

1. **Python:** 3.10+ (Python 3.11 or 3.12 recommended)
2. **Ollama:** Installed and running locally (`ollama serve`) with at least one model pulled (e.g. `llama3.1`, `qwen2.5:7b`, etc.)
3. **System dependencies (install at the OS level):**
   - **FFmpeg:** Handles audio file processing/conversion (`.ogg`, `.wav`, `.mp3`) — used by the local voice stack (faster-whisper/Piper).
   - **Tesseract OCR:** Extracts text from images (requires the `tesseract-ocr` package plus the `tesseract-ocr-eng` / `tesseract-ocr-vie` language packs).
4. **Piper voice model** *(required only if you want local TTS)*: download the `.onnx` + `.onnx.json` file pair for any Vietnamese voice from the [`rhasspy/piper-voices`](https://huggingface.co/rhasspy/piper-voices) repository (the `vi/vi_VN/` folder), place them in `./voices/`, and reference them via `PIPER_VOICE_PATHS` in `.env`. faster-whisper requires **no manual download** — it downloads its model to the local cache automatically on first run.
5. **Groq API key** *(optional, fallback only)*: since v5.2, voice defaults to running fully local (faster-whisper); Groq Whisper is now only a fallback option if you explicitly switch to it. All features work without a key.

---

## 📦 Installation

### 1. On Linux (Ubuntu / Debian)

1. Copy the source code into your project directory.
2. Update the system and install dependencies:

```bash
sudo apt update
sudo apt install python3-full python3-pip ffmpeg -y
sudo apt install tesseract-ocr tesseract-ocr-eng
sudo apt-get install -y tesseract-ocr tesseract-ocr-vie
```

> 🎙️ After installing `requirements.txt` (next step), download the Vietnamese Piper voice model (one-time setup) from [`rhasspy/piper-voices`](https://huggingface.co/rhasspy/piper-voices) and place it in `./voices/` — see details in [`UPGRADE_GUIDE.md`](./UPGRADE_GUIDE.md#0-cài-thêm-thư-viện).

3. Create and activate a virtual environment, install dependencies, and test:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. Create the `.env` configuration file from the template and fill in the required variables (at minimum `TELEGRAM_TOKEN`):

```bash
cp .env.example .env
nano .env   # fill in TELEGRAM_TOKEN, ALLOWED_USERS, ADMIN_USER_IDS, etc.
```

5. Run the bot to test it (Ctrl+C to stop; see [Running the Bot](#-running-the-bot) for background/auto-start setup):

```bash
python3 my_bot.py
deactivate
```

### 2. On Windows

1. Install the required tools:

```powershell
# 1. Install Python
winget install --id Python.Python.3.11 -e

# 2. Install FFmpeg
winget install --id Gyan.FFmpeg -e

# 3. Install Tesseract OCR
winget install --id UB-Mannheim.TesseractOCR -e
```

2. Create a virtual environment:

```powershell
python -m venv venv
Set-ExecutionPolicy Unrestricted -Scope Process
.\venv\Scripts\Activate.ps1
python.exe -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Create the `.env` configuration file from the template and fill in the required variables (at minimum `TELEGRAM_TOKEN`):

```powershell
Copy-Item .env.example .env
notepad .env   # fill in TELEGRAM_TOKEN, ALLOWED_USERS, ADMIN_USER_IDS, etc.
```

4. Launch the bot:

```powershell
python my_bot.py
```

---

## 🏮 Web Control Station (Dashboard)

This repo ships with a browser-based admin dashboard (`webapp/`), built with FastAPI + Uvicorn.
The required libraries (`fastapi`, `uvicorn`) are **already included in `requirements.txt`** —
no extra installation is needed if you already ran `pip install -r requirements.txt` above.

1. (Optional) configuration in `.env` — sensible defaults are already provided:

```env
WEBAPP_HOST=0.0.0.0     # server listen address (0.0.0.0 = all network interfaces)
WEBAPP_PORT=8080
WEBAPP_TOKEN=           # empty = no authentication; set any string to enable token login
```

2. Run it for testing — **always run from the project root `chatAi_bots/`** (where `config.py` lives), independently of `my_bot.py`:

```bash
# Linux/macOS (with venv activated)
python -m webapp.main
```

```powershell
# Windows (with venv activated)
python -m webapp.main
```

3. Open your browser at `http://localhost:8080` (do **not** use `0.0.0.0:8080`, it will not connect).

The web app is read-only (SQLite in read-only mode) and does not conflict with the bot process, so it
can run alongside `my_bot.py` without issue. See [Running the Bot](#-running-the-bot) below for
running it automatically at system startup.

---

## 🚀 Running the Bot

### 1. Run Directly

```bash
# Activate the venv if not already active
source venv/bin/activate  # Linux/macOS
# Launch the bot
python my_bot.py
```

### 2. Run as a Systemd Service (Linux — Recommended)

Create the service file `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Telegram AI Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/cwng/Documents/GitHub/my_bot_restructured/chatAi_bots
ExecStart=/home/cwng/Documents/GitHub/my_bot_restructured/chatAi_bots/venv/bin/python3 /home/cwng/Documents/GitHub/my_bot_restructured/chatAi_bots/my_bot.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot.service
sudo systemctl start telegram-bot.service
sudo systemctl status telegram-bot.service
sudo systemctl restart telegram-bot.service
```

If you'd also like the Web Control Station to auto-start with the system, create a separate service
file `/etc/systemd/system/telegram-bot-webapp.service` (runs independently, no conflict with the bot):

```ini
[Unit]
Description=Telegram AI Bot - Web Dashboard
After=network.target telegram-bot.service

[Service]
Type=simple
WorkingDirectory=/home/cwng/Documents/GitHub/my_bot_restructured/chatAi_bots
ExecStart=/home/cwng/Documents/GitHub/my_bot_restructured/chatAi_bots/venv/bin/python3 -m webapp.main
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot-webapp.service
sudo systemctl start telegram-bot-webapp.service
sudo systemctl status telegram-bot-webapp.service
```

> Remember to update `WorkingDirectory` and the `venv` path in both `.service` files to match
> the actual project directory on your machine (the paths above are just examples).

### 3. Run as a Windows Service (NSSM — automated script, recommended)

This repo includes a PowerShell script that fully automates installing NSSM for
**both the bot and the web app** — no need to configure NSSM manually through its UI.

1. Open PowerShell as **Administrator** and navigate to the project root (`chatAi_bots/`):

```powershell
cd C:\Users\<your-username>\...\my_bot_restructured\chatAi_bots
```

2. Make sure `venv\` already exists (created during installation) and that `nssm.exe` is available —
   the repo already includes `nssm.exe` in the project root, or you can copy your own copy into
   `.\scripts\nssm.exe`.

3. Run the installation script — add `-WithWebapp` to also install the service for the Web Control Station:

```powershell
.\scripts\install_nssm_service.ps1 -WithWebapp
```

The script will automatically:
- Create the **MyBotTelegram** (`python my_bot.py`) and **MyBotWebapp** (`python -m webapp.main`) services.
- Point them to the correct `venv\Scripts\python.exe` and set the project folder as `AppDirectory`.
- Enable auto-start with Windows (`SERVICE_AUTO_START`) and auto-restart on crash.
- Write rotating logs to `logs\MyBotTelegram.out.log` / `logs\MyBotWebapp.out.log`.
- Automatically start both services immediately after installation.

> ⚠️ Once the service is installed, **do not manually run** `python my_bot.py` again — Telegram
> will report a Conflict error since two processes would be polling the same token. Use the NSSM
> commands to stop the service first if you need to run it manually.

Handy management commands going forward (PowerShell Admin):

```powershell
Get-Service MyBotTelegram, MyBotWebapp        # check status
nssm restart MyBotTelegram                    # restart the bot
nssm restart MyBotWebapp                      # restart the web app
nssm stop MyBotTelegram                       # stop the bot (to run it manually)
Get-Content .\logs\bot.log -Wait -Tail 30      # tail the live log
```

To remove all services when no longer needed:

```powershell
.\scripts\uninstall_nssm_service.ps1
```

---

## 🎮 Commands Reference (`/commands`)

| Command | Access | Description |
|---|---|---|
| `/start` | Everyone | Starts the bot and displays a welcome message |
| `/help` | Everyone | Shows detailed usage instructions |
| `/ui` | Everyone | Opens the multi-level, button-based Telegram Control Station |
| `/weather <city>` | Everyone | Looks up current weather & air quality (PM2.5) |
| `/news [source]` | Everyone | Quick news digest from `vnexpress`, `tuoitre`, `thanhnien`, `dantri`, `bbcvietnamese` |
| `/nickname <name>` | Everyone | Sets a nickname for the bot to address you by |
| `/persona [name]` | Everyone | Switches the bot's personality: `ban_than`, `chuyen_gia`, `hai_huoc`, `co_van` |
| `/autoweb` | Everyone | Toggles **smart auto web search** (auto-classifies questions & extracts keywords) |
| `/voice <name>` | Everyone | Changes the Piper TTS voice |
| `/stt <local\|groq>` | Everyone | Switches the speech-recognition engine between `faster-whisper` and `Groq Whisper` |
| `/ttsmode <off\|smart\|always>` | Everyone | Configures the voice-reply mode |
| `/export` | Everyone | Exports the full conversation history as a `.txt` file |
| `/stop` | Everyone | Cancels an in-progress AI response |
| `/reset` | Everyone | Clears the recent conversation context |
| `/resetmemory` | Everyone | Clears the long-term memory profile (everything the bot has learned about you) |
| `/ping` | Admin | Checks latency and connection status to Ollama |
| `/shutdown` | Admin | Remotely shuts down the server (requires 2-step confirmation) |
| `/reboot` | Admin | Remotely reboots the server (requires 2-step confirmation) |

---

## 🏗️ Project Structure

```text
chatAi_bots/
├── my_bot.py                 # 🚀 Entry point — initializes the Application & wires up handlers
├── config.py                  # ⚙️ Loads environment variables (.env) & system constants
├── bot_logger.py               # 📝 Centralized rotating log management
├── utils.py                     # 🧰 Shared utilities: permissions, rate limiting, locks...
├── llm_engine.py                 # 🧠 LLM handling: streaming, grounded RAG, real-time clock
├── database.py                    # 🗄️ SQLite database management (history, settings, profiles)
├── reasoning.py                     # 💡 Question classification, hidden reasoning, long-term memory summarization
├── local_voice.py                    # 🎙️ Manages the local faster-whisper and Piper TTS engines
│
├── skills/                            # 🔧 Independent business-logic modules (no Telegram dependency)
│   ├── web_search.py                  #    🔍 Multi-tier search, query cleanup, core-keyword extraction
│   ├── ocr.py                         #    🖼️ OCR text extraction and image/PDF translation
│   ├── voice.py                       #    🗣️ Orchestrates STT (Local/Groq) and voice-reply generation
│   ├── weather.py                     #    🌤️ Weather & AQI lookups (Open-Meteo API)
│   ├── news.py                        #    📰 RSS reader for major news outlets
│   ├── pdf_report.py                  #    📄 Generates professional PDF research reports
│   └── dashboard.py                   #    🖥️ Hardware resource monitoring (CPU/RAM/Disk)
│
├── handlers/                          # 📨 Receives & routes Telegram update events
│   ├── text_handler.py                #    Handles text chat, triggers Smart Auto-Web
│   ├── voice_handler.py               #    Handles incoming voice messages
│   ├── media_handler.py               #    Handles images and PDF documents
│   ├── commands.py                    #    Handles all /command inputs
│   └── dashboard_handler.py           #    Handles the inline keyboard interface (/ui)
│
├── webapp/                            # 🏮 Web Control Station (browser dashboard)
│   ├── main.py                        #    FastAPI app — provides a read-only monitoring API
│   └── static/                        #    Lacquer-styled UI (plain HTML, CSS, JS)
│
├── data/                              # Stores bot_data.db (created automatically)
├── voices/                            # Stores Piper voice models (.onnx)
├── logs/                              # Stores rotating log files
├── requirements.txt                   # List of Python dependencies
└── .env.example                       # Environment configuration template
```

---

## 📄 License

This project is distributed under the **MIT License**. You are free to use, modify, and contribute
to the source code for both personal/educational and commercial purposes.