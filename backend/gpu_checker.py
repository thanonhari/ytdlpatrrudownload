import subprocess
import shutil
import logging
import json
import os

logger = logging.getLogger("gpu_checker")

def check_nvidia_smi():
    """Check if nvidia-smi is available and return GPU name and VRAM."""
    nvidia_smi_path = shutil.which("nvidia-smi")
    if not nvidia_smi_path:
        return {"available": False, "reason": "nvidia-smi not found in PATH"}

    try:
        cmd = [
            nvidia_smi_path,
            "--query-gpu=name,memory.total,memory.free,driver_version",
            "--format=csv,noheader,nounits"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            gpus = []
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpus.append({
                        "name": parts[0],
                        "memory_total_mb": int(parts[1]),
                        "memory_free_mb": int(parts[2]),
                        "driver_version": parts[3]
                    })
            return {"available": True, "gpus": gpus}
    except Exception as e:
        logger.warning(f"Error querying nvidia-smi: {e}")
    
    return {"available": False, "reason": "Execution failed"}

def check_ffmpeg_encoders():
    """Check FFmpeg available hardware encoders."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return {"ffmpeg_installed": False, "nvenc": False, "qsv": False, "amf": False}

    encoders = {"ffmpeg_installed": True, "nvenc": False, "qsv": False, "amf": False, "supported_encoders": []}
    try:
        result = subprocess.run([ffmpeg_path, "-encoders"], capture_output=True, text=True, timeout=5)
        output = result.stdout
        if "h264_nvenc" in output or "hevc_nvenc" in output:
            encoders["nvenc"] = True
            encoders["supported_encoders"].append("nvenc (NVIDIA)")
        if "h264_qsv" in output or "hevc_qsv" in output:
            encoders["qsv"] = True
            encoders["supported_encoders"].append("qsv (Intel QuickSync)")
        if "h264_amf" in output or "hevc_amf" in output:
            encoders["amf"] = True
            encoders["supported_encoders"].append("amf (AMD)")
    except Exception as e:
        logger.warning(f"Error checking ffmpeg encoders: {e}")
    
    return encoders

def get_system_gpu_status():
    """Combined GPU and Hardware Acceleration Status report."""
    nvidia_info = check_nvidia_smi()
    ffmpeg_info = check_ffmpeg_encoders()
    
    gpu_acceleration_active = nvidia_info.get("available", False) or ffmpeg_info.get("nvenc", False) or ffmpeg_info.get("qsv", False)
    
    return {
        "gpu_accelerated": gpu_acceleration_active,
        "nvidia": nvidia_info,
        "ffmpeg": ffmpeg_info,
        "recommended_video_codec": "h264_nvenc" if ffmpeg_info.get("nvenc") else ("h264_qsv" if ffmpeg_info.get("qsv") else "libx264"),
        "whisper_device": "cuda" if nvidia_info.get("available") else "cpu"
    }

if __name__ == "__main__":
    print(json.dumps(get_system_gpu_status(), indent=2))
