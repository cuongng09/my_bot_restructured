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

> **A free, powerful, self-hosted AI assistant for Telegram:** Powered by Ollama (streaming LLM + hidden reasoning), a multi-tier intelligent web-search system, 100% local two-way voice, vision OCR & translation, self-summarizing long-term memory, and a dual interface (Telegram dashboard + traditional lacquer-styled web app).

---

## 🌟 Key Features

*   **🧠 AI Intelligence & Deep Reasoning:** Streaming responses, hidden chain-of-thought (CoT) reasoning, 4 flexible personas, and long-term memory that automatically distills user habits.
*   **🌐 Multi-Tier Smart Web RAG:** Prioritizes self-hosted SearXNG, falls back to DuckDuckGo, reformulates queries, and anchors real-time clock data to eliminate "no data found" replies.
*   **🎙️ 100% Local Two-Way Voice:** High-accuracy Vietnamese STT via `faster-whisper` and natural TTS via `Piper` (no external APIs required).
*   **🖼️ Multi-Format Vision OCR:** Automatically extracts and translates text from images (JPG, PNG, WebP) and PDF documents.
*   **🏮 Dual Interface:** Control everything via a multi-level Telegram inline keyboard (`/ui`) or a browser-based admin dashboard styled in traditional Vietnamese lacquer art.

---

## 📚 Documentation Hub

To keep this README concise, detailed guides have been moved to the `docs/` directory. Click below to explore:

| Tài liệu | Mô tả chi tiết |
| :--- | :--- |
| **[🏗️ Kiến trúc hệ thống](./docs/architecture.md)** | Sơ đồ luồng dữ liệu (Mermaid), cấu trúc thư mục `src/`, và cơ chế Plug & Play của Skills. |
| **[⚙️ Hướng dẫn Cấu hình](./docs/configuration.md)** | Giải thích chi tiết các biến môi trường (`.env`), phân quyền, Ollama, Voice Pipeline, và Web App. |
| **[🚀 Hướng dẫn Triển khai](./docs/deployment.md)** | Cài đặt Local, Docker Compose, chạy dưới dạng Systemd (Linux), và Windows Service (NSSM). |

---

## ⚡ Quick Start

### 1. System Requirements
*   **Python:** 3.10+ (Recommended: 3.11 or 3.12)
*   **Ollama:** Installed and running locally (`ollama serve`)
*   **System Dependencies:** `ffmpeg` (audio processing) and `tesseract-ocr` (image text extraction).

### 2. Installation (Linux / macOS)
```bash
# 1. Clone the repository
git clone https://github.com/cuongng09/my_bot_restructured.git
cd my_bot_restructured
cd scripts
./install.sh 

```

> 💡 Windows Users: Please refer to the Deployment Guide for PowerShell installation commands and NSSM service setup.

📂 Project Structure
my_bot_restructured/
├── src/                  # Main source code (src layout)
│   ├── core/             # LLM engine, database, reasoning, voice
│   ├── handlers/         # Telegram update handlers
│   ├── skills/           # Plug & Play skill modules (weather, news, OCR...)
│   └── webapp/           # FastAPI Web Control Station
├── tests/                # Automated pytest suite
├── docs/                 # Detailed documentation (Architecture, Config, Deployment)
├── scripts/              # Install/uninstall scripts (Systemd, NSSM)
├── pyproject.toml        # PEP 621 build config
└── docker-compose.yml    # Multi-service Docker orchestration

> 📄 License This project is distributed under the MIT License. You are free to use, modify, and contribute to the source code for both personal/educational and commercial purposes.