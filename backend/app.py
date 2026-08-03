import os
import asyncio
import logging
import subprocess
import sys
import uuid
import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel

from backend.gpu_checker import get_system_gpu_status
from backend.cookie_manager import get_available_browsers, list_uploaded_cookie_files, save_uploaded_cookie_file
from backend.whisper_service import is_whisper_available
from backend.preset_manager import get_all_presets, get_preset_by_id
from backend.file_manager import scan_downloads_folder, open_in_file_explorer, delete_downloaded_file, BASE_DOWNLOADS_DIR
from backend.downloader import DownloadTask, run_download_task, get_video_info

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("app")

app = FastAPI(title="yt-dlp Web Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=4)

# Global task storage & active websockets & main event loop reference
tasks_store: Dict[str, DownloadTask] = {}
active_websockets: List[WebSocket] = []
main_loop: Optional[asyncio.AbstractEventLoop] = None
TASK_RETENTION_SECONDS = 60 * 60
TASK_MAX_ITEMS = 100

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    logger.info("FastAPI startup event: Main event loop captured.")

async def broadcast_progress(task_dict: dict):
    """Send progress update to all connected WebSocket clients."""
    if not active_websockets:
        return
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_json({"type": "progress_update", "data": task_dict})
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)

def sync_progress_callback(task_dict: dict):
    """Thread-safe callback invoked by yt-dlp hook inside ThreadPoolExecutor."""
    global main_loop
    if main_loop and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_progress(task_dict), main_loop)

def prune_tasks_store(max_age_seconds: int = TASK_RETENTION_SECONDS, max_items: int = TASK_MAX_ITEMS):
    """Keep recent tasks and prune terminal tasks that are no longer useful."""
    now = time.time()
    removable_ids = [
        task_id
        for task_id, task in tasks_store.items()
        if task.status in {"completed", "error"}
        and getattr(task, "finished_at", None)
        and now - task.finished_at >= max_age_seconds
    ]
    for task_id in removable_ids:
        tasks_store.pop(task_id, None)

    if len(tasks_store) <= max_items:
        return

    terminal_tasks = [
        (task_id, getattr(task, "finished_at", getattr(task, "created_at", 0.0)))
        for task_id, task in tasks_store.items()
        if task.status in {"completed", "error"}
    ]
    terminal_tasks.sort(key=lambda item: item[1] or 0.0)

    overflow = len(tasks_store) - max_items
    for task_id, _ in terminal_tasks[:overflow]:
        tasks_store.pop(task_id, None)


def clear_finished_tasks() -> int:
    """Remove completed/error tasks from the store and return the removed count."""
    removable_ids = [task_id for task_id, task in tasks_store.items() if task.status in {"completed", "error"}]
    for task_id in removable_ids:
        tasks_store.pop(task_id, None)
    return len(removable_ids)

# Request Models
class DownloadRequest(BaseModel):
    url: str
    preset_id: Optional[str] = None
    resolution: Optional[str] = "best"
    format: Optional[str] = None
    extract_audio: bool = False
    audio_format: Optional[str] = "mp3"
    audio_quality: Optional[str] = "320"
    write_subs: bool = True
    embed_subs: bool = True
    sub_langs: List[str] = ["th", "en"]
    embed_metadata: bool = True
    embed_thumbnail: bool = True
    sponsorblock: bool = True
    time_section: Optional[str] = None
    cookie_type: Optional[str] = None  # 'browser' or 'file'
    cookie_val: Optional[str] = None
    use_whisper: bool = False
    whisper_lang: Optional[str] = "auto"

class OpenFolderRequest(BaseModel):
    path: Optional[str] = None

import re
def extract_clean_url(text: str) -> str:
    """Extracts the first http/https URL from raw share text."""
    match = re.search(r'(https?://[^\s]+)', text.strip())
    return match.group(1) if match else text.strip()

# Favicon handler to fix 404
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

# REST Endpoints
@app.get("/api/status")
def get_system_status():
    import yt_dlp
    return {
        "yt_dlp_version": yt_dlp.version.__version__,
        "gpu": get_system_gpu_status(),
        "whisper": is_whisper_available(),
        "browsers": get_available_browsers(),
        "uploaded_cookies": list_uploaded_cookie_files(),
        "downloads_dir": BASE_DOWNLOADS_DIR
    }


@app.post("/api/update-ytdlp")
def update_ytdlp():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            check=True,
        )
        import yt_dlp
        return {
            "success": True,
            "yt_dlp_version": yt_dlp.version.__version__,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=exc.stderr or exc.stdout or str(exc))


@app.post("/api/upload-cookies")
async def upload_cookies(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing cookies file")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    saved_name = save_uploaded_cookie_file(file.filename, content)
    return {
        "success": True,
        "filename": saved_name,
        "uploaded_cookies": list_uploaded_cookie_files(),
    }

@app.get("/api/info")
def extract_metadata(url: str, cookie_type: Optional[str] = None, cookie_val: Optional[str] = None):
    try:
        clean_url = extract_clean_url(url)
        info = get_video_info(clean_url, cookie_type, cookie_val)
        return {"success": True, "info": info}
    except Exception as e:
        logger.error(f"Failed to fetch info for {url}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/presets")
def list_presets():
    return {"presets": get_all_presets()}

@app.get("/api/files")
def list_files(subfolder: str = ""):
    return {"files": scan_downloads_folder(subfolder)}

@app.post("/api/open-folder")
def open_folder(req: OpenFolderRequest):
    success = open_in_file_explorer(req.path)
    return {"success": success}

@app.delete("/api/files")
def delete_file(path: str):
    try:
        success = delete_downloaded_file(path)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download")
def queue_download(req: DownloadRequest):
    task_id = str(uuid.uuid4())[:8]
    
    clean_url = extract_clean_url(req.url)
    prune_tasks_store()
    opts = req.model_dump()
    if req.preset_id:
        preset = get_preset_by_id(req.preset_id)
        if preset:
            opts.update(preset)

    task = DownloadTask(
        task_id=task_id,
        url=clean_url,
        options=opts,
        progress_callback=sync_progress_callback
    )
    tasks_store[task_id] = task

    # Submit task to ThreadPool
    executor.submit(run_download_task, task)
    return {"success": True, "task_id": task_id, "task": task.to_dict()}

@app.get("/api/tasks")
def list_tasks():
    prune_tasks_store()
    return {"tasks": [t.to_dict() for t in tasks_store.values()]}

@app.post("/api/tasks/clear-completed")
def clear_completed_tasks():
    removed_count = clear_finished_tasks()
    return {"success": True, "removed_count": removed_count, "tasks": [t.to_dict() for t in tasks_store.values()]}

# WebSockets
@app.websocket("/ws/download")
async def websocket_download_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    prune_tasks_store()
    try:
        # Send initial list of all tasks
        await websocket.send_json({
            "type": "init_tasks",
            "data": [t.to_dict() for t in tasks_store.values()]
        })
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

# Mount Downloads Folder for streaming video/audio
app.mount("/downloads-media", StaticFiles(directory=BASE_DOWNLOADS_DIR), name="downloads-media")

# Mount Frontend Static Files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
