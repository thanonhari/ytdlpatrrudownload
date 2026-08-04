import os
import logging
import time
import yt_dlp
from typing import Dict, Any, Callable, Optional
from backend.cookie_manager import get_cookie_attempts, build_cookie_fresh_cookie_hint
from backend.whisper_service import generate_subtitles_whisper
from backend.caption_generator import create_caption_presets
from backend.file_manager import check_existing_download

logger = logging.getLogger("downloader")

BASE_DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads")
os.makedirs(BASE_DOWNLOADS_DIR, exist_ok=True)


def _format_cookie_error(exc: Exception, cookie_source_type: Optional[str] = None) -> str:
    message = str(exc)
    if "Fresh cookies" in message:
        return f"{message}\n\n{build_cookie_fresh_cookie_hint(cookie_source_type)}"
    return message



def _is_retryable_subtitle_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "unable to download video subtitles" in message or ("429" in message and "subtitle" in message)

def _run_yt_dlp_with_cookie_fallback(
    url: str,
    ydl_opts: Dict[str, Any],
    cookie_type: Optional[str],
    cookie_val: Optional[str],
    download: bool,
):
    attempts = get_cookie_attempts(cookie_type, cookie_val)
    if not attempts:
        attempts = [None]

    last_exc = None
    for index, attempt in enumerate(attempts):
        attempt_opts = dict(ydl_opts)
        if attempt:
            attempt_opts.update(attempt["options"])

        try:
            with yt_dlp.YoutubeDL(attempt_opts) as ydl:
                return ydl.extract_info(url, download=download)
        except Exception as exc:
            last_exc = exc
            if index + 1 < len(attempts):
                logger.warning(
                    "Cookie attempt failed with %s cookies, retrying fallback %s: %s",
                    attempt.get("source_type") if attempt else "unknown",
                    attempts[index + 1].get("source_type") if attempts[index + 1] else "default",
                    exc,
                )
                continue
            raise RuntimeError(_format_cookie_error(exc, cookie_type)) from exc

    if last_exc is not None:
        raise RuntimeError(_format_cookie_error(last_exc, cookie_type)) from last_exc
    raise RuntimeError("yt-dlp failed without a clear error")


class DownloadTask:
    def __init__(self, task_id: str, url: str, options: Dict[str, Any], progress_callback: Optional[Callable] = None):
        self.task_id = task_id
        self.url = url
        self.options = options
        self.progress_callback = progress_callback
        self.status = "queued"  # queued, fetching_info, downloading, processing, transcribing_whisper, completed, error
        self.stage = "⏳ อยู่ในคิวดาวน์โหลด (Queued)"
        self.percent = 0.0
        self.speed = "0 B/s"
        self.eta = "N/A"
        self.filename = ""
        self.filepath = ""
        self.error_msg = ""
        self.title = ""
        self.caption_studio = {}
        self.created_at = time.time()
        self.finished_at = None

    def _ytdl_progress_hook(self, d: Dict[str, Any]):
        if d['status'] == 'downloading':
            self.status = "downloading"
            self.stage = "📥 กำลังดาวน์โหลดสตรีมภาพและเสียง..."
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded_bytes = d.get('downloaded_bytes') or 0
            
            if total_bytes > 0:
                self.percent = round((downloaded_bytes / total_bytes) * 100, 1)
            else:
                self.percent = 0.0

            speed_raw = d.get('speed')
            if speed_raw:
                if speed_raw > 1024 * 1024:
                    self.speed = f"{speed_raw / (1024 * 1024):.2f} MB/s"
                elif speed_raw > 1024:
                    self.speed = f"{speed_raw / 1024:.2f} KB/s"
                else:
                    self.speed = f"{speed_raw:.0f} B/s"
            
            eta_raw = d.get('eta')
            if eta_raw is not None:
                mins, secs = divmod(int(eta_raw), 60)
                self.eta = f"{mins:02d}:{secs:02d}"

            filename = d.get('filename', '')
            if filename:
                self.filename = os.path.basename(filename)
                self.filepath = filename

            if self.progress_callback:
                self.progress_callback(self.to_dict())

        elif d['status'] == 'finished':
            self.status = "processing"
            self.stage = "⚙️ กำลังประมวลผลวิดีโอ/ฝังซับ/ปก (FFmpeg GPU Transcoding)..."
            self.percent = 98.0
            self.filename = os.path.basename(d.get('filename', ''))
            self.filepath = d.get('filename', '')
            if self.progress_callback:
                self.progress_callback(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "url": self.url,
            "title": self.title,
            "status": self.status,
            "stage": self.stage,
            "percent": self.percent,
            "speed": self.speed,
            "eta": self.eta,
            "filename": self.filename,
            "filepath": self.filepath,
            "error_msg": self.error_msg,
            "caption_studio": self.caption_studio
        }

def get_video_info(url: str, cookie_type: Optional[str] = None, cookie_val: Optional[str] = None) -> Dict[str, Any]:
    """Extracts metadata without downloading."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    info = _run_yt_dlp_with_cookie_fallback(url, ydl_opts, cookie_type, cookie_val, download=False)

    if not info:
        raise ValueError("Could not extract video metadata")

    # Parse resolution formats
    formats = []
    if 'formats' in info:
        for f in info['formats']:
            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')
            height = f.get('height')
            ext = f.get('ext')
            format_id = f.get('format_id')
            fps = f.get('fps')
            
            # Filter clean video formats
            if vcodec != 'none' and height:
                formats.append({
                    "format_id": format_id,
                    "height": height,
                    "resolution": f"{height}p" + (f" {fps}fps" if fps and fps > 30 else ""),
                    "ext": ext,
                    "vcodec": vcodec,
                    "acodec": acodec,
                    "filesize_approx_mb": round((f.get('filesize') or f.get('filesize_approx') or 0) / (1024*1024), 1)
                })

    # Sort formats by resolution descending
    formats.sort(key=lambda x: x["height"], reverse=True)

    video_id = info.get("id")
    duplicate_info = check_existing_download(video_id)
    caption_studio = create_caption_presets(info)

    return {
        "id": video_id,
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "duration_string": f"{int(info.get('duration', 0)//60)}:{int(info.get('duration', 0)%60):02d}" if info.get("duration") else "Live",
        "uploader": info.get("uploader") or info.get("extractor_key"),
        "extractor": info.get("extractor_key"),
        "view_count": info.get("view_count"),
        "subtitles": list(info.get("subtitles", {}).keys()),
        "automatic_captions": list(info.get("automatic_captions", {}).keys()),
        "formats": formats[:10],
        "caption_studio": caption_studio,
        "duplicate_info": duplicate_info
    }

def run_download_task(task: DownloadTask):
    """Executes yt-dlp download in synchronous thread."""
    opts = task.options
    
    # Base output template: downloads/Extractor/Uploader/Title [ID].ext
    output_folder = opts.get("output_folder") or BASE_DOWNLOADS_DIR
    out_tmpl = os.path.join(output_folder, "%(extractor)s", "%(uploader,channel)s", "%(title)s [%(id)s].%(ext)s")

    ydl_opts = {
        'outtmpl': out_tmpl,
        'progress_hooks': [task._ytdl_progress_hook],
        'quiet': False,
        'no_warnings': False,
        'restrictfilenames': False,
    }

    cookie_type = opts.get("cookie_type")
    cookie_val = opts.get("cookie_val")

    # Format selection (Video / Audio)
    if opts.get("extract_audio"):
        ydl_opts['format'] = 'bestaudio/best'
        audio_fmt = opts.get("audio_format", "mp3")
        postprocs = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_fmt,
            'preferredquality': opts.get("audio_quality", "320").replace("K", ""),
        }]
        ydl_opts['postprocessors'] = postprocs
    else:
        chosen_format = opts.get("format")
        if chosen_format:
            ydl_opts['format'] = chosen_format
        else:
            res = opts.get("resolution", "best")
            if res != "best" and res.isdigit():
                ydl_opts['format'] = f"bestvideo[height<={res}]+bestaudio/best[height<={res}]/best"
            else:
                ydl_opts['format'] = "bestvideo+bestaudio/best"

    # Subtitles options
    if opts.get("write_subs"):
        ydl_opts['writesubtitles'] = True
        ydl_opts['writeautomaticsub'] = True
        ydl_opts['subtitleslangs'] = opts.get("sub_langs", ["th", "en", "all"])
        ydl_opts['subtitlesformat'] = opts.get("sub_format", "srt/vtt/best")

    # Embed options
    postprocessors = ydl_opts.get('postprocessors', [])
    
    if opts.get("embed_subs") and not opts.get("extract_audio"):
        postprocessors.append({
            'key': 'FFmpegEmbedSubtitle',
            'already_have_subtitle': False
        })

    if opts.get("embed_metadata"):
        postprocessors.append({'key': 'FFmpegMetadata'})

    if opts.get("embed_thumbnail"):
        ydl_opts['writethumbnail'] = True
        postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
        postprocessors.append({'key': 'EmbedThumbnail'})

    ydl_opts['postprocessors'] = postprocessors

    # Time section trimming (--download-sections "*01:30-04:00")
    if opts.get("time_section"):
        time_sec = opts.get("time_section").strip()
        if time_sec:
            def time_range_func(info_dict, ydl):
                parts = time_sec.split("-")
                if len(parts) == 2:
                    def parse_sec(s):
                        p = s.strip().split(":")
                        if len(p) == 3: return int(p[0])*3600 + int(p[1])*60 + float(p[2])
                        elif len(p) == 2: return int(p[0])*60 + float(p[1])
                        else: return float(p[0])
                    start = parse_sec(parts[0])
                    end = parse_sec(parts[1])
                    return [{'start_time': start, 'end_time': end}]
                return []
            ydl_opts['download_ranges'] = time_range_func

    # SponsorBlock
    if opts.get("sponsorblock"):
        ydl_opts['sponsorblock_remove'] = ['sponsor', 'intro', 'outro', 'selfpromo', 'preview']

    try:
        task.status = "fetching_info"
        task.stage = "🔍 กำลังแกะข้อมูล Metadata และสตรีม..."
        if task.progress_callback:
            task.progress_callback(task.to_dict())

        try:
            info = _run_yt_dlp_with_cookie_fallback(task.url, ydl_opts, cookie_type, cookie_val, download=True)
        except Exception as exc:
            if opts.get("write_subs") and _is_retryable_subtitle_error(exc):
                logger.warning("Subtitle download failed with %s; retrying once without subtitle capture: %s", type(exc).__name__, exc)
                fallback_opts = dict(ydl_opts)
                fallback_opts.pop("writesubtitles", None)
                fallback_opts.pop("writeautomaticsub", None)
                fallback_opts.pop("subtitleslangs", None)
                fallback_opts.pop("subtitlesformat", None)
                info = _run_yt_dlp_with_cookie_fallback(task.url, fallback_opts, cookie_type, cookie_val, download=True)
            else:
                raise
        task.title = info.get("title", "Downloaded Video")

        # Resolve the final media file path after yt-dlp and post-processing finish.
        final_path = task.filepath
        video_id = info.get("id")
        if video_id:
            duplicate_info = check_existing_download(video_id)
            final_path = duplicate_info.get("absolute_path") or final_path

        if final_path:
            final_path = os.path.normpath(final_path)
            task.filepath = final_path
            task.filename = os.path.basename(final_path)

        task.caption_studio = create_caption_presets(info, task.filepath)

        # Optional Whisper transcription for spoken clips.
        if opts.get("use_whisper") and task.filepath and os.path.exists(task.filepath):
            whisper_lang = opts.get("whisper_lang") or "auto"
            task.status = "transcribing_whisper"
            task.stage = "?? ????????????????? AI Whisper ???? SRT..."
            if task.progress_callback:
                task.progress_callback(task.to_dict())

            whisper_srt_path = os.path.splitext(task.filepath)[0] + ".whisper.srt"
            try:
                whisper_ok = generate_subtitles_whisper(task.filepath, whisper_srt_path, whisper_lang)
                task.caption_studio["whisper_enabled"] = bool(whisper_ok)
                if whisper_ok:
                    task.caption_studio["whisper_srt_path"] = whisper_srt_path
            except Exception as ex:
                logger.warning(f"Whisper subtitle generation failed: {ex}")
                task.caption_studio["whisper_enabled"] = False

        # Save caption to text file alongside the media
        if task.filepath and os.path.exists(task.filepath):
            base_name = os.path.splitext(task.filepath)[0]
            cap_file_path = base_name + ".caption.txt"
            try:
                with open(cap_file_path, "w", encoding="utf-8") as f:
                    f.write("=== CAPTION STUDIO ===\n\n")
                    f.write("--- ?????????? (Full) ---\n")
                    f.write(task.caption_studio.get("caption_full", "") + "\n\n")
                    f.write("--- ?????????????? (Editor Note) ---\n")
                    f.write(task.caption_studio.get("caption_editor", "") + "\n\n")
                    f.write("=== ????????????? (RAW METADATA) ===\n")
                    f.write(task.caption_studio.get("metadata_archive", "") + "\n")
            except Exception as ex:
                logger.warning(f"Could not write caption file: {ex}")
        task.status = "completed"
        task.stage = "✅ ดาวน์โหลดและประมวลผลเสร็จสมบูรณ์"
        task.percent = 100.0
        if task.progress_callback:
            task.progress_callback(task.to_dict())

    except Exception as e:
        logger.error(f"Download task {task.task_id} failed: {e}", exc_info=True)
        task.status = "error"
        task.stage = f"❌ เกิดข้อผิดพลาด: {str(e)}"
        task.error_msg = str(e)
        if task.progress_callback:
            task.progress_callback(task.to_dict())
