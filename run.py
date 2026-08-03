import sys
import os
import uvicorn

if __name__ == "__main__":
    # Ensure current directory is on sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    print("==================================================")
    print("Starting yt-dlp Web Studio Server...")
    print("Open Web UI at: http://127.0.0.1:8000")
    print("==================================================")

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
