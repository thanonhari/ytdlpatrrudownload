import os
import shutil
import logging

logger = logging.getLogger("whisper_service")

def is_whisper_available():
    """Checks if faster-whisper or whisper package is installed or accessible via CLI."""
    try:
        import faster_whisper
        return {"available": True, "engine": "faster-whisper (Python)"}
    except ImportError:
        pass

    try:
        import whisper
        return {"available": True, "engine": "openai-whisper (Python)"}
    except ImportError:
        pass

    whisper_cli = shutil.which("whisper")
    if whisper_cli:
        return {"available": True, "engine": "whisper (CLI)"}

    return {"available": False, "engine": None, "reason": "No whisper library installed"}

def format_timestamp(seconds: float) -> str:
    """Converts seconds to SRT timestamp format 00:00:00,000"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def generate_subtitles_whisper(audio_or_video_path: str, output_srt_path: str, language: str = None) -> bool:
    """
    Transcribes audio/video file using faster-whisper or fallback, saving to SRT.
    """
    if not os.path.exists(audio_or_video_path):
        logger.error(f"File not found for Whisper: {audio_or_video_path}")
        return False

    status = is_whisper_available()
    if not status["available"]:
        logger.warning("Whisper not available in Python environment. Skipping AI auto-subtitles.")
        return False

    try:
        if "faster-whisper" in status["engine"]:
            from faster_whisper import WhisperModel
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            
            logger.info(f"Loading faster-whisper model (small) on {device} ({compute_type})...")
            model = WhisperModel("small", device=device, compute_type=compute_type)
            
            segments, info = model.transcribe(
                audio_or_video_path,
                language=language if language and language != "auto" else None,
                beam_size=5
            )
            
            logger.info(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")
            
            with open(output_srt_path, "w", encoding="utf-8") as f:
                for idx, segment in enumerate(segments, start=1):
                    start_str = format_timestamp(segment.start)
                    end_str = format_timestamp(segment.end)
                    text = segment.text.strip()
                    f.write(f"{idx}\n{start_str} --> {end_str}\n{text}\n\n")
            
            logger.info(f"Successfully generated SRT at: {output_srt_path}")
            return True

        elif "openai-whisper" in status["engine"]:
            import whisper
            model = whisper.load_model("small")
            result = model.transcribe(audio_or_video_path, language=language if language != "auto" else None)
            
            with open(output_srt_path, "w", encoding="utf-8") as f:
                for idx, segment in enumerate(result.get("segments", []), start=1):
                    start_str = format_timestamp(segment["start"])
                    end_str = format_timestamp(segment["end"])
                    text = segment["text"].strip()
                    f.write(f"{idx}\n{start_str} --> {end_str}\n{text}\n\n")
            return True

    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}", exc_info=True)
        return False

    return False
