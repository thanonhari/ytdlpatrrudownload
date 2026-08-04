import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright


ROOT = Path(r"D:\Project\yt-dlp-project\yt-dlp-web-downloader")
BASE_URL = "http://127.0.0.1:8000"


async def wait_for_server(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status in {200, 204, 404}:
                    return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.5)
    raise RuntimeError(f"Server did not become ready: {last_error}")


async def main() -> None:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    server = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    try:
        await wait_for_server(BASE_URL)

        ascii_task_path = Path(r"D:\Project\yt-dlp-project\yt-dlp-web-downloader\downloads\Reddit\leotime0821\Who's at the front door! [jfhjilwff2hh1].mp4")
        unicode_task_path = None
        for candidate in Path(ROOT / "downloads").rglob("*"):
            if candidate.is_file() and candidate.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".mp3", ".m4a", ".flac", ".wav", ".aac", ".opus"}:
                if any(ord(ch) > 127 for ch in str(candidate)):
                    unicode_task_path = candidate
                    break
        if unicode_task_path is None:
            raise RuntimeError("No unicode path found in downloads for regression coverage")

        tasks_payload = {
            "tasks": [
                {
                    "task_id": "task-2",
                    "url": "https://example.com/watch?v=unicode123",
                    "title": unicode_task_path.stem,
                    "status": "completed",
                    "stage": "? ????????????????????????????????",
                    "percent": 100,
                    "speed": "8.12 MB/s",
                    "eta": "00:00",
                    "filename": unicode_task_path.name,
                    "filepath": str(unicode_task_path),
                    "error_msg": "",
                    "caption_studio": {
                        "hashtags_text": "#unicode #caption",
                        "caption_short": "Unicode caption",
                    },
                },
                {
                    "task_id": "task-1",
                    "url": "https://example.com/watch?v=jfhjilwff2hh1",
                    "title": "Who's at the front door!",
                    "status": "completed",
                    "stage": "? ????????????????????????????????",
                    "percent": 100,
                    "speed": "9.56 MB/s",
                    "eta": "00:00",
                    "filename": ascii_task_path.name,
                    "filepath": str(ascii_task_path),
                    "error_msg": "",
                    "caption_studio": {
                        "hashtags_text": "#demo #caption",
                        "caption_short": "Demo caption",
                    },
                },
            ]
        }

        routes = []
        captured_open_folder = {}
        captured_update = {"called": False}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1440, "height": 900})

            async def route_json(route, payload):
                await route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

            async def handle(route, request):
                url = request.url
                if url.endswith("/api/status"):
                    await route_json(route, {
                        "yt_dlp_version": "2026.08.01",
                        "gpu": {"gpu_accelerated": False},
                        "whisper": False,
                        "browsers": [],
                        "uploaded_cookies": [],
                        "downloads_dir": str(ROOT / "downloads"),
                    })
                    return
                if url.endswith("/api/presets"):
                    await route_json(route, {"presets": []})
                    return
                if url.endswith("/api/tasks"):
                    await route_json(route, tasks_payload)
                    return
                if url.endswith("/api/files"):
                    await route_json(route, {"files": []})
                    return
                if url.endswith("/api/open-folder"):
                    captured_open_folder["path"] = request.post_data_json["path"]
                    await route_json(route, {"success": True})
                    return
                if url.endswith("/api/update-ytdlp"):
                    captured_update["called"] = True
                    await route_json(route, {"success": True, "yt_dlp_version": "2026.08.01"})
                    return
                await route.continue_()

            await page.route("**/*", handle)
            await page.goto(BASE_URL, wait_until="domcontentloaded")

            await page.locator('.nav-btn[data-tab="tab-queue"]').click()
            await page.wait_for_selector("button.btn-open-card-folder", state="visible")
            folder_buttons = page.locator("button.btn-open-card-folder")
            if await folder_buttons.count() < 2:
                raise AssertionError("Expected at least two completed-task folder buttons")

            status_tags = page.locator(".task-status-tag")
            if await status_tags.count() < 2:
                raise AssertionError("Expected at least two task status tags")
            for index in range(2):
                if "COMPLETED" not in await status_tags.nth(index).inner_text():
                    raise AssertionError("A task row did not render as completed")

            await folder_buttons.nth(0).click()
            for _ in range(20):
                if captured_open_folder.get("path"):
                    break
                await page.wait_for_timeout(100)

            first_expected = str(ascii_task_path)
            first_actual = captured_open_folder.get("path")
            if first_actual != first_expected:
                raise AssertionError(f"open-folder path mismatch: {first_actual!r} != {first_expected!r}")

            captured_open_folder.clear()
            await folder_buttons.nth(1).click()
            for _ in range(20):
                if captured_open_folder.get("path"):
                    break
                await page.wait_for_timeout(100)

            second_expected = str(unicode_task_path)
            second_actual = captured_open_folder.get("path")
            if second_actual != second_expected:
                raise AssertionError(f"unicode open-folder path mismatch: {second_actual!r} != {second_expected!r}")

            if await page.locator("button.btn-copy-task-tags").count() != 2:
                raise AssertionError("Expected hashtags buttons to render from caption studio data")
            if await page.locator("button.btn-copy-task-cap").count() != 2:
                raise AssertionError("Expected caption buttons to render from caption studio data")
            if await page.locator("#btn-update-ytdlp").count() != 1:
                raise AssertionError("Expected yt-dlp update button to render")
            if await page.locator("#opt-whisper-lang").count() != 1:
                raise AssertionError("Expected Whisper language selector to render")
            if not await page.evaluate("Boolean(window.downloadWebSocket)"):
                raise AssertionError("Expected the websocket client instance to stay referenced")

            await page.locator("#btn-update-ytdlp").click()
            for _ in range(20):
                if captured_update.get("called"):
                    break
                await page.wait_for_timeout(100)
            if not captured_update.get("called"):
                raise AssertionError("Expected yt-dlp update endpoint to be called")

            await browser.close()
            print("BROWSER_UI_OK")
            print(f"OPEN_FOLDER_PATH_1={first_actual.encode('unicode_escape').decode()}")
            print(f"OPEN_FOLDER_PATH_2={second_actual.encode('unicode_escape').decode()}")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:
            server.kill()


if __name__ == "__main__":
    asyncio.run(main())
