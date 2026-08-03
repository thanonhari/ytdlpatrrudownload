# Progress: yt-dlp Web Studio (Local Web Downloader)

## Goal
Build a modern, feature-rich Local Web Downloader app for YouTube, TikTok, X, FB, IG, Reddit, Twitch, Vimeo, Dailymotion, Bilibili, Douyin, Kuaishou, Weibo, with GPU acceleration detection, Whisper AI auto-captioning, SponsorBlock, custom time sections, cookie manager, real-time WebSocket progress monitoring, duplicate clip detection, direct folder launcher, and Hashtags & Captions Studio for video editing.

---

## Task Checklist & Milestones

- [x] **0. Requirements & Handoff / Ref Alignment**
  - [x] Read `ref.txt` and aligned with Peter Steinberger / OpenAI Build Week Close-The-Loop workflow.
  - [x] Confirmed user preferences (FastAPI + Modern Web UI + Whisper AI + Cookie Manager + WebSockets).

- [x] **1. Backend Core Setup (`backend/`)**
  - [x] `gpu_checker.py`: NVIDIA NVENC / CUDA / Intel QSV / AMD AMF detection tool.
  - [x] `cookie_manager.py`: Browser cookies auto-import & `cookies.txt` parser.
  - [x] `whisper_service.py`: Local `faster-whisper` AI speech-to-text for missing subtitles.
  - [x] `downloader.py`: `yt-dlp` Python API engine with progress hooks, SponsorBlock, `--download-sections`, metadata/thumbnail embedding, format selection.
  - [x] `caption_generator.py`: Smart Thai & English hashtag & social media caption generator for video editors.
  - [x] `file_manager.py`: File explorer API, media player streaming, duplicate clip check (`check_existing_download`), Windows Explorer `/select` launcher (`open_in_file_explorer`).
  - [x] `preset_manager.py`: Quick preset profiles (MP3 320k, 4K Best + Subs, Short Cuts).
  - [x] `app.py`: FastAPI server with REST endpoints, favicon handler (fixes 404), startup event loop capture (fixes ThreadPoolExecutor error), & WebSocket `/ws/download`.

- [x] **2. Frontend Web UI (`frontend/`)**
  - [x] `index.html`: Premium dark-themed UI layout (Dashboard, Download Form, Queue & Progress, File Browser, Settings).
  - [x] `css/style.css`: Glassmorphic styling, animations, responsive design, Toast notifications, Caption Studio styles, Duplicate alert banner.
  - [x] `js/websocket.js`: Real-time WebSocket connection and live progress bar updates.
  - [x] `js/app.js`: Tab switching, REST API fallback for tasks, instant Task Card rendering on download submit, Hashtags & Caption Studio copy actions, path segment URL encoding for media playback (`#` & Unicode character fix), duplicate warning alert, direct DOM element binding for File Manager (`escapeHtml` & native `addEventListener` fix).

- [x] **3. End-to-End Verification & Close-the-Loop Testing**
  - [x] Upgraded Windows File Explorer launcher using `explorer /select, <path>` to open File Explorer directly and highlight the exact file.
  - [x] Resolved File Manager tab rendering issue by replacing unescaped HTML string attribute interpolation with safe DOM element creation (`document.createElement`) and direct `addEventListener` binding.
  - [x] Verified duplicate clip detection: Automatically detected `TikTok/vlftxjxd1u8` download as `exists: True`.
  - [x] Verified direct folder opening (`POST /api/open-folder`) for specific clip folders.
  - [x] Resolved `There is no current event loop in thread 'ThreadPoolExecutor-0_0'` error by capturing `main_loop` during FastAPI startup.
  - [x] Fixed File Manager media preview 404 error on filenames containing `#` and Unicode by encoding each path segment (`encodeURIComponent`).
  - [x] Verified HTTP 206 Range request video streaming for Chinese & hashtagged filenames: `Media HTTP Code: 206 Content Length: 101`.
  - [x] Tested live TikTok download: Successfully downloaded 100% to `downloads/TikTok/vlftxjxd1u8/...` at 7.75 MB/s.
  - [x] Generated rich Thai & English hashtags (`#คลิปฮิต`, `#คลิปเด็ด`, `#คลิปดัง`, `#ฟีด`, `#ขึ้นฟีดเหอะ`, `#สาระน่ารู้`, `#เทรนด์วันนี้`, `#ตัดต่อวิดีโอ`, `#VideoEditing`, `#Shorts`, `#Reels`, `#TikTok`) & Caption presets.
  - [x] Verified REST endpoints `/api/status`, `/api/presets`, `/api/files`, `/api/tasks`, `/favicon.ico`.
  - [x] Tested launcher scripts `run.py` & `run.bat`.

---

## Log of Key Decisions
| Date | Topic | Decision & Rationale |
|---|---|---|
| 2026-08-02 | Tech Stack | Selected Python FastAPI + HTML5/CSS3/Vanilla JS + WebSockets for native `yt-dlp` / `FFmpeg` / `faster-whisper` integration with zero external frontend build complexity. |
| 2026-08-02 | Explorer Launcher | Switched to `subprocess.Popen(['explorer', '/select,', norm_path])` so Windows File Explorer opens non-blockingly and automatically highlights the target file inside its folder. |
| 2026-08-02 | DOM Escaping | Refactored `renderFilesTable` to use native JavaScript `document.createElement` and direct `addEventListener` to eliminate unescaped Windows path backslash (`\`) and quote syntax errors in HTML attributes. |
| 2026-08-02 | GPU Acceleration | Implemented automatic hardware detection for NVIDIA NVENC (`h264_nvenc`), Intel QSV, and AMD AMF to accelerate FFmpeg re-encoding & Whisper AI transcription. |
| 2026-08-02 | Duplicate Check | Integrated `check_existing_download()` by video ID pattern matching to detect previously downloaded clips and prompt users with direct folder buttons. |
| 2026-08-02 | Direct Clip Folder | Added dedicated "📂 เปิดโฟลเดอร์คลิปนี้" button right on the header/title of preview cards, task cards, and file manager items to jump straight into the specific folder. |
| 2026-08-02 | URL Encoding Fix | Applied `encodeURIComponent` on each relative path segment before building video `src` URL to prevent browser hashtag `#` truncation on Chinese & social media filenames. |
| 2026-08-02 | Thread Safety | Captured FastAPI `main_loop` during startup to enable safe cross-thread `asyncio.run_coroutine_threadsafe` calls from ThreadPoolExecutor worker threads. |
| 2026-08-02 | Thai Caption Studio | Built smart Thai & English hashtag generation (`#คลิปฮิต #คลิปเด็ด #ฟีด #ขึ้นฟีดเหอะ #ตัดต่อวิดีโอ`) and caption presets for TikTok / Reels / Shorts video editing. |
| 2026-08-02 | Close-The-Loop Workflow | Aligned with `ref.txt` guidelines: self-test server startup, run API verification, catch errors automatically without asking user to QA. |
