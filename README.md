# 🤖 Ollama Telegram Bot v7.0

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-lightgrey?style=for-the-badge&logo=linux" alt="Platform" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/Docker-Supported-2496ED?style=for-the-badge&logo=docker" alt="Docker" />
  <img src="https://img.shields.io/badge/Architecture-Modular-orange?style=for-the-badge" alt="Architecture" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/Status-Active%20Production-brightgreen?style=for-the-badge" alt="Status" />
</p>

<p align="center">
  <img src="bia_repo.png" alt="Telegram AI Bot Banner" width="100%" />
</p>

> **Privacy-First, Self-Hosted Local AI Assistant:** Powered by Ollama (LLM Streaming & Hidden Chain-of-Thought Reasoning), Multi-Tier Smart Web Search (SearXNG + DuckDuckGo + Deep Trafilatura RAG), 2-Way Voice Engine via **Voicebox Docker** (Whisper STT + Piper TTS), Dual-Layer Response Delivery with automated **Word (`.docx`) & Excel (`.xlsx`)** report generation, Vision OCR, Long-Term User Memory, and a Web App Management Dashboard.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
  - [🔍 Multi-Tier Smart Web Search](#-multi-tier-smart-web-search)
  - [💬 Dual-Layer Responses & Automated Document Export](#-dual-layer-responses--automated-document-export)
  - [🎙️ Voicebox Studio (Local STT + TTS)](#️-voicebox-studio-local-stt--tts)
  - [🖥️ Glassmorphism Web Dashboard](#️-glassmorphism-web-dashboard)
  - [🧰 Advanced Utilities](#-advanced-utilities)
- [System Architecture](#-system-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
  - [Linux / macOS](#linux--macos)
  - [Windows](#windows)
- [Service Management](#-service-management)
- [Command Reference](#-command-reference)
- [Repository Structure](#-repository-structure)
- [Configuration](#-configuration)
- [License](#-license)

---

## 🌐 Overview

**Ollama Telegram Bot v7.0** is an enterprise-grade, fully autonomous assistant system designed to run 100% locally. By decoupling LLM inference, web searching, speech synthesis, and document formatting into modular layers, it delivers lightning-fast chat interactions on Telegram while maintaining full control over your data.

---

## ✨ Key Features

### 🔍 Multi-Tier Smart Web Search
*Enabled by default for all user prompts with zero manual switching required.*
- **Instant Intent Classifier:** Quickly bypasses search engines for greetings, code snippets, mathematical queries, and creative writing to conserve hardware resources.
- **LLM Query Abstraction:** Extracts essential keywords (2–6 core terms) from complex questions to perform targeted web queries.
- **Multi-Layer Fallback Chain:** Local SearXNG instance → DuckDuckGo API → Deep HTML Scraping (Trafilatura) → Automatic English translation for queries.
- **Source Reputation Ranking:** Prioritizes verified news outlets, official documentations, and trustworthy domain extensions.

### 💬 Dual-Layer Responses & Automated Document Export
- **Streamlined Telegram Output:** Sends a concise **1–3 sentence core answer** in chat while routing comprehensive output into attached files.
- **Automatic Excel (`.xlsx`) Generation:** Formats tabular data, statistics, and comparisons into styled spreadsheets with header branding, zebra striping, and auto-adjusted column widths.
- **Automatic Word (`.docx`) Generation:** Converts analytical reports, travel itineraries, and detailed essays into formatted Word documents with embedded callout boxes and clean Arial typography.
- **Zero Chat Clutter:** Real-time feedback during streaming (`⏳ Processing detailed content into document...`).

### 🎙️ Voicebox Studio (Local STT + TTS)
- **Local Speech-to-Text (STT):** High-precision Whisper models running via Voicebox Docker. No audio leaves your local infrastructure.
- **Dynamic Model Switching:** Toggle Whisper models (`tiny`, `base`, `small`, `medium`, `turbo`) on the fly via `/ui` without service restarts.
- **Offline Text-to-Speech (TTS):** Neural voice synthesis powered by Piper TTS.
- **Custom Audio DSP Effects:** Built-in audio filters including `Robotic`, `Radio`, `Echo Chamber`, and `Deep Voice`.
- **Smart Short Voice Reply:** Reads only the primary takeaway response, reducing voice latency from ~30s down to **2–5 seconds**.

### 🖥️ Glassmorphism Web Dashboard
*Accessible locally at `http://localhost:8080`*
- **Voicebox Studio Monitor:** Real-time Docker state, active Whisper model memory allocation, audio effect profiles, and audio player controls.
- **Report & File Repository:** Browse, preview, and download all generated `.docx` and `.xlsx` files directly from your browser.
- **System Diagnostics:** Live charts for CPU, RAM, Disk usage, system uptime, active Ollama model, and registered Telegram users.
- **Secure Authentication:** Protected by token authentication (`WEBAPP_TOKEN`).

### 🧰 Advanced Utilities
- 🌤️ **Weather & Air Quality:** Instant meteorological data & PM2.5 AQI indices via Open-Meteo API.
- 📰 **RSS News Aggregator:** Automated headlines from leading national and international media outlets.
- 🖼️ **Vision & Document OCR:** Text extraction from images and PDF files (via Tesseract OCR & machine translation).
- 🧠 **Long-Term Memory:** LLM-backed background summarization of user profiles, preferences, and interaction history.
- 💡 **Hidden Chain-of-Thought Reasoning:** Supports wrapped `<think>` / `<suy_nghi>` reasoning blocks for complex reasoning tasks.
- 📤 **Conversation Export:** One-click history export into formatted `.txt` files.

---

## 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER (Telegram App)                            │
└───────────────┬─────────────────────────────────┬───────────────────────┘
                │                                 │
        ┌───────▼────────┐              ┌─────────▼─────────┐
        │  Text / Voice  │              │   Image / PDF     │
        └───────┬────────┘              └─────────┬─────────┘
                │                                 │
        ┌───────▼────────┐              ┌─────────▼─────────┐
        │  text_handler  │              │   media_handler   │
        │ voice_handler  │              │   (OCR + Vision)  │
        └───────┬────────┘              └─────────┬─────────┘
                │                                 │
        ┌───────▼─────────────────────────────────▼─────────┐
        │              llm_engine.py + reasoning.py          │
        │       (Streaming · Hidden Reasoning · Grounded RAG)│
        └───────┬──────────────────────┬────────────────────┘
                │                      │
      ┌─────────▼─────────┐  ┌─────────▼──────────┐
      │   web_search.py   │  │  document_exporter │
      │  (Multi-layer)    │  │   (.docx / .xlsx)  │
      └─────────┬─────────┘  └─────────┬──────────┘
                │                      │
      ┌─────────▼─────────┐  ┌─────────▼──────────┐
      │  SearXNG + DDGS   │  │   data/reports/    │
      │  + Trafilatura    │  │   (Exported Files) │
      └───────────────────┘  └────────────────────┘

      ┌────────────────────────────────────────────┐
      │  Voicebox Docker (Whisper STT + Piper TTS) │
      └────────────────────┬───────────────────────┘
                           │
      ┌────────────────────▼───────────────────────┐
      │  Web Dashboard (FastAPI + Dark Glass UI)   │
      └────────────────────────────────────────────┘