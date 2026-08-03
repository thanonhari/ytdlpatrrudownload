import os
import logging

logger = logging.getLogger("cookie_manager")

COOKIES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies")
os.makedirs(COOKIES_DIR, exist_ok=True)

SUPPORTED_BROWSERS = ["chrome", "edge", "firefox", "brave", "opera", "vivaldi"]


def get_available_browsers():
    """Return browsers that the UI can offer."""
    return [{"name": browser_name, "label": browser_name.capitalize()} for browser_name in SUPPORTED_BROWSERS]


def list_uploaded_cookie_files():
    """List saved cookies files in the cookies directory."""
    files = []
    if os.path.exists(COOKIES_DIR):
        for filename in os.listdir(COOKIES_DIR):
            if filename.endswith(".txt") or filename.endswith(".cookies"):
                files.append(filename)
    return files


def save_uploaded_cookie_file(filename: str, content: bytes) -> str:
    """Persist an uploaded cookies file inside the cookies directory."""
    safe_name = os.path.basename(filename or "cookies.txt")
    base_name, ext = os.path.splitext(safe_name)
    if ext.lower() not in {".txt", ".cookies"}:
        ext = ".txt"

    candidate = f"{base_name}{ext}"
    target_path = os.path.join(COOKIES_DIR, candidate)
    counter = 1
    while os.path.exists(target_path):
        candidate = f"{base_name}_{counter}{ext}"
        target_path = os.path.join(COOKIES_DIR, candidate)
        counter += 1

    with open(target_path, "wb") as handle:
        handle.write(content)

    return candidate


def get_yt_dlp_cookie_opts(cookie_source_type: str, cookie_value: str) -> dict:
    """Return yt-dlp cookie options for a browser or a saved cookie file."""
    if cookie_source_type == "browser" and cookie_value:
        return {"cookiesfrombrowser": (cookie_value,)}
    if cookie_source_type == "file" and cookie_value:
        file_path = os.path.join(COOKIES_DIR, cookie_value)
        if os.path.exists(file_path):
            return {"cookiefile": file_path}
        if os.path.exists(cookie_value):
            return {"cookiefile": cookie_value}
    return {}


def get_cookie_attempts(cookie_source_type: str, cookie_value: str):
    """Return cookie option candidates in priority order."""
    attempts = []
    seen_options = set()

    def add_attempt(source_type: str, source_value: str):
        opts = get_yt_dlp_cookie_opts(source_type, source_value)
        if not opts:
            return
        options_key = tuple(sorted(opts.items()))
        if options_key in seen_options:
            return
        seen_options.add(options_key)
        attempts.append({
            "source_type": source_type,
            "source_value": source_value,
            "options": opts,
        })

    add_attempt(cookie_source_type, cookie_value)

    if cookie_source_type == "browser" and cookie_value:
        for uploaded_file in list_uploaded_cookie_files():
            add_attempt("file", uploaded_file)
    elif cookie_source_type == "file" and cookie_value:
        for browser_name in SUPPORTED_BROWSERS:
            add_attempt("browser", browser_name)
        for uploaded_file in list_uploaded_cookie_files():
            if uploaded_file != cookie_value:
                add_attempt("file", uploaded_file)
    else:
        for browser_name in SUPPORTED_BROWSERS:
            add_attempt("browser", browser_name)
        for uploaded_file in list_uploaded_cookie_files():
            add_attempt("file", uploaded_file)

    attempts.append({
        "source_type": "none",
        "source_value": None,
        "options": {},
    })

    return attempts


def build_cookie_fresh_cookie_hint(cookie_source_type: str = None) -> str:
    """User-facing guidance when yt-dlp reports a fresh-cookies requirement."""
    lines = [
        "Fresh cookies are required:",
        "1. Open the site in your browser and log in if needed.",
        "2. Export cookies as cookies.txt in Netscape/Mozilla format.",
        "3. Upload the file in Settings > Cookies.",
        "4. Try the download again.",
    ]
    if cookie_source_type == "browser":
        lines.append("If browser cookies fail, export cookies.txt and upload that file instead.")
    return "\n".join(lines)
