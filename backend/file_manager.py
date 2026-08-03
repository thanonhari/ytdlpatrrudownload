import os
import platform
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("file_manager")

BASE_DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads")
os.makedirs(BASE_DOWNLOADS_DIR, exist_ok=True)

def open_in_file_explorer(target_path: str = None) -> bool:
    """Opens target folder or selects file in host OS file explorer (Windows / Mac / Linux)."""
    if not target_path or not os.path.exists(target_path):
        target_path = BASE_DOWNLOADS_DIR

    norm_path = os.path.normpath(target_path)

    try:
        if platform.system() == "Windows":
            folder_path = os.path.dirname(norm_path) if os.path.isfile(norm_path) else norm_path
            # Use explorer explicitly to force a window to open
            subprocess.Popen(['explorer', folder_path])
            return True
        elif platform.system() == "Darwin":
            if os.path.isfile(norm_path):
                subprocess.Popen(["open", "-R", norm_path])
            else:
                subprocess.Popen(["open", norm_path])
            return True
        else:
            folder_path = os.path.dirname(norm_path) if os.path.isfile(norm_path) else norm_path
            subprocess.Popen(["xdg-open", folder_path])
            return True
    except Exception as e:
        logger.error(f"Failed to open explorer path '{norm_path}': {e}")
        return False

def scan_downloads_folder(subfolder: str = "") -> List[Dict]:
    """Recursively scans downloads folder and returns detailed file list."""
    target_dir = os.path.join(BASE_DOWNLOADS_DIR, subfolder) if subfolder else BASE_DOWNLOADS_DIR
    if not os.path.exists(target_dir):
        return []

    file_list = []
    for root, dirs, files in os.walk(target_dir):
        for f in files:
            # Skip hidden files
            if f.startswith("."):
                continue
            
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, BASE_DOWNLOADS_DIR)
            stat = os.stat(full_path)
            
            ext = os.path.splitext(f)[1].lower()
            file_type = "video" if ext in [".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv"] else (
                "audio" if ext in [".mp3", ".m4a", ".wav", ".flac", ".aac", ".opus"] else (
                    "subtitle" if ext in [".srt", ".vtt", ".ass"] else "other"
                )
            )

            file_list.append({
                "name": f,
                "relative_path": rel_path.replace("\\", "/"),
                "absolute_path": full_path,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "type": file_type,
                "created_at": int(stat.st_ctime)
            })

    # Sort newest first
    file_list.sort(key=lambda x: x["created_at"], reverse=True)
    return file_list

def check_existing_download(video_id: str) -> Dict[str, Any]:
    """Checks if a video has already been downloaded by matching ID or title in downloads folder."""
    if not video_id:
        return {"exists": False}

    media_exts = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".mp3", ".m4a", ".flac", ".wav", ".aac", ".opus"}

    for root, dirs, files in os.walk(BASE_DOWNLOADS_DIR):
        for f in files:
            if f"[{video_id}]" in f:
                ext = os.path.splitext(f)[1].lower()
                if ext in media_exts:
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, BASE_DOWNLOADS_DIR).replace("\\", "/")
                    return {
                        "exists": True,
                        "filename": f,
                        "absolute_path": full_path,
                        "relative_path": rel_path,
                        "folder_path": root
                    }

    return {"exists": False}

def delete_downloaded_file(relative_path: str) -> bool:
    """Deletes a file given its relative path in downloads dir."""
    base_dir = Path(BASE_DOWNLOADS_DIR).resolve()
    target = (base_dir / relative_path).resolve()

    # Security check: prevent directory traversal and prefix collisions
    try:
        target.relative_to(base_dir)
    except ValueError:
        raise ValueError("Invalid file path outside downloads directory")

    if target.exists():
        target.unlink()
        return True
    return False
