PRESETS = {
    "video_best_subs": {
        "id": "video_best_subs",
        "name": "🎬 Best Video + Subs + Metadata (Recommended)",
        "description": "Download highest resolution video (4K/1080p) with subtitles and full metadata.",
        "format": "bestvideo+bestaudio/best",
        "extract_audio": False,
        "write_subs": True,
        "sub_langs": ["th", "en", "all"],
        "embed_subs": True,
        "embed_metadata": True,
        "embed_thumbnail": True,
        "sponsorblock": True
    },
    "audio_mp3_320": {
        "id": "audio_mp3_320",
        "name": "🎵 MP3 Audio 320kbps",
        "description": "Extract audio only and convert to high quality MP3 320kbps.",
        "format": "bestaudio/best",
        "extract_audio": True,
        "audio_format": "mp3",
        "audio_quality": "320K",
        "embed_metadata": True,
        "embed_thumbnail": True
    },
    "audio_flac_lossless": {
        "id": "audio_flac_lossless",
        "name": "🎧 FLAC Audio Lossless",
        "description": "Extract raw audio and convert to lossless FLAC format.",
        "format": "bestaudio/best",
        "extract_audio": True,
        "audio_format": "flac",
        "embed_metadata": True,
        "embed_thumbnail": True
    },
    "video_1080p_mp4": {
        "id": "video_1080p_mp4",
        "name": "📱 1080p MP4 Video",
        "description": "Fast download 1080p MP4 compatible with all devices.",
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "extract_audio": False,
        "write_subs": True,
        "embed_metadata": True,
        "embed_thumbnail": True
    },
    "shorts_reels_fast": {
        "id": "shorts_reels_fast",
        "name": "⚡ TikTok / Reels / Shorts Fast Cut",
        "description": "Quick download for short vertical videos with metadata.",
        "format": "best",
        "extract_audio": False,
        "embed_metadata": True,
        "embed_thumbnail": True
    }
}

def get_all_presets():
    return list(PRESETS.values())

def get_preset_by_id(preset_id: str):
    return PRESETS.get(preset_id)
