import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.app as app_module
import backend.downloader as downloader
import backend.file_manager as file_manager
from backend.file_manager import check_existing_download, open_in_file_explorer


class DownloadCompletionRegressionTest(unittest.TestCase):
    def test_run_download_task_resolves_final_file_and_writes_caption(self):
        with tempfile.TemporaryDirectory(dir=r"D:\tmp") as tmpdir:
            tmp_root = Path(tmpdir)
            media_path = tmp_root / "downloads" / "TikTok" / "channel" / "Demo Clip [abc123].mp4"
            media_path.parent.mkdir(parents=True, exist_ok=True)
            media_path.write_bytes(b"fake media")

            old_downloader_base = downloader.BASE_DOWNLOADS_DIR
            old_file_manager_base = file_manager.BASE_DOWNLOADS_DIR
            downloader.BASE_DOWNLOADS_DIR = str(tmp_root / "downloads")
            file_manager.BASE_DOWNLOADS_DIR = str(tmp_root / "downloads")
            try:
                task = downloader.DownloadTask("task-1", "https://example.com/watch?v=abc123", {})
                task.filepath = str(tmp_root / "staging" / "temp.part")

                def fake_extract(url, ydl_opts, cookie_type, cookie_val, download):
                    self.assertTrue(download)
                    return {
                        "id": "abc123",
                        "title": "Demo Clip",
                        "uploader": "channel",
                        "extractor_key": "TikTok",
                    }

                with patch.object(downloader, "_run_yt_dlp_with_cookie_fallback", side_effect=fake_extract):
                    downloader.run_download_task(task)

                self.assertEqual(task.status, "completed")
                self.assertEqual(Path(task.filepath).resolve(), media_path.resolve())
                self.assertEqual(task.filename, media_path.name)
                self.assertTrue(media_path.exists())

                caption_path = media_path.with_name(media_path.stem + ".caption.txt")
                self.assertTrue(caption_path.exists())
                caption_text = caption_path.read_text(encoding="utf-8")
                self.assertTrue(caption_text.startswith("=== CAPTION STUDIO ==="))

                lookup = check_existing_download("abc123")
                self.assertTrue(lookup["exists"])
                self.assertEqual(Path(lookup["absolute_path"]).resolve(), media_path.resolve())
            finally:
                downloader.BASE_DOWNLOADS_DIR = old_downloader_base
                file_manager.BASE_DOWNLOADS_DIR = old_file_manager_base

    def test_open_in_file_explorer_uses_parent_folder_for_file_path(self):
        with tempfile.TemporaryDirectory(dir=r"D:\tmp") as tmpdir:
            tmp_root = Path(tmpdir)
            media_path = tmp_root / "downloads" / "YouTube" / "channel" / "Clip [xyz789].mp4"
            media_path.parent.mkdir(parents=True, exist_ok=True)
            media_path.write_bytes(b"fake media")

            old_file_manager_base = file_manager.BASE_DOWNLOADS_DIR
            file_manager.BASE_DOWNLOADS_DIR = str(tmp_root / "downloads")
            try:
                with patch("backend.file_manager.platform.system", return_value="Windows"), \
                     patch("backend.file_manager.subprocess.Popen") as popen_mock:
                    self.assertTrue(open_in_file_explorer(str(media_path)))
                    popen_mock.assert_called_once()
                    args, _kwargs = popen_mock.call_args
                    self.assertEqual(args[0][0], "explorer")
                    self.assertEqual(Path(args[0][1]).resolve(), media_path.parent.resolve())
            finally:
                file_manager.BASE_DOWNLOADS_DIR = old_file_manager_base



    def test_open_in_file_explorer_handles_long_thai_mp4_path(self):
        thai_path = None
        for candidate in Path(r"D:\\Project\\yt-dlp-project\\yt-dlp-web-downloader\\downloads").rglob("*.mp4"):
            if "[1322644996513521]" in candidate.name:
                thai_path = candidate
                break

        self.assertIsNotNone(thai_path)
        self.assertTrue(any(ord(ch) > 127 for ch in str(thai_path)))

        lookup = check_existing_download("1322644996513521")
        self.assertTrue(lookup["exists"])
        self.assertEqual(Path(lookup["absolute_path"]).resolve(), thai_path.resolve())

        old_file_manager_base = file_manager.BASE_DOWNLOADS_DIR
        file_manager.BASE_DOWNLOADS_DIR = str(Path(r"D:\\Project\\yt-dlp-project\\yt-dlp-web-downloader\\downloads"))
        try:
            with patch("backend.file_manager.platform.system", return_value="Windows"), \
                 patch("backend.file_manager.subprocess.Popen") as popen_mock:
                self.assertTrue(open_in_file_explorer(str(thai_path)))
                popen_mock.assert_called_once()
                args, _kwargs = popen_mock.call_args
                self.assertEqual(args[0][0], "explorer")
                self.assertEqual(Path(args[0][1]).resolve(), thai_path.parent.resolve())
        finally:
            file_manager.BASE_DOWNLOADS_DIR = old_file_manager_base


    def test_run_download_task_generates_whisper_srt_when_enabled(self):
        with tempfile.TemporaryDirectory(dir=r"D:\tmp") as tmpdir:
            tmp_root = Path(tmpdir)
            media_path = tmp_root / "downloads" / "Facebook" / "page" / "Thai Clip [fb1322644996513521].mp4"
            media_path.parent.mkdir(parents=True, exist_ok=True)
            media_path.write_bytes(b"fake media")

            old_downloader_base = downloader.BASE_DOWNLOADS_DIR
            old_file_manager_base = file_manager.BASE_DOWNLOADS_DIR
            downloader.BASE_DOWNLOADS_DIR = str(tmp_root / "downloads")
            file_manager.BASE_DOWNLOADS_DIR = str(tmp_root / "downloads")
            try:
                task = downloader.DownloadTask(
                    "task-whisper",
                    "https://www.facebook.com/watch/?v=1322644996513521&_rdr",
                    {"use_whisper": True, "whisper_lang": "auto"},
                )
                task.filepath = str(tmp_root / "staging" / "temp.part")

                def fake_extract(url, ydl_opts, cookie_type, cookie_val, download):
                    self.assertTrue(download)
                    return {
                        "id": "fb1322644996513521",
                        "title": "Thai Clip",
                        "uploader": "page",
                        "extractor_key": "Facebook",
                    }

                whisper_calls = []

                def fake_whisper(input_path, output_srt_path, language=None):
                    whisper_calls.append((input_path, output_srt_path, language))
                    Path(output_srt_path).write_text(
                        "1\n00:00:00,000 --> 00:00:01,000\n??????\n",
                        encoding="utf-8",
                    )
                    return True

                with patch.object(downloader, "_run_yt_dlp_with_cookie_fallback", side_effect=fake_extract),                      patch.object(downloader, "generate_subtitles_whisper", side_effect=fake_whisper):
                    downloader.run_download_task(task)

                self.assertEqual(task.status, "completed")
                self.assertEqual(Path(task.filepath).resolve(), media_path.resolve())
                self.assertTrue(task.caption_studio.get("whisper_enabled"))
                self.assertEqual(len(whisper_calls), 1)
                self.assertEqual(Path(whisper_calls[0][0]).resolve(), media_path.resolve())
                self.assertEqual(Path(whisper_calls[0][1]).resolve(), media_path.with_suffix(".whisper.srt").resolve())
                self.assertEqual(whisper_calls[0][2], "auto")
                self.assertTrue(media_path.with_suffix(".whisper.srt").exists())
            finally:
                downloader.BASE_DOWNLOADS_DIR = old_downloader_base
                file_manager.BASE_DOWNLOADS_DIR = old_file_manager_base

    def test_run_download_task_retries_browser_cookies_when_none_selected(self):
        attempts = []

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts
                attempts.append(opts)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def extract_info(self, url, download):
                if len(attempts) == 1:
                    raise RuntimeError("Fresh cookies (not necessarily logged in) are needed")
                return {
                    "id": "fb1322644996513521",
                    "title": "Thai Clip",
                    "uploader": "page",
                    "extractor_key": "Facebook",
                }

        with patch.object(downloader.yt_dlp, "YoutubeDL", FakeYDL):
            info = downloader._run_yt_dlp_with_cookie_fallback(
                "https://www.facebook.com/watch/?v=1322644996513521&_rdr",
                {"quiet": True},
                None,
                None,
                download=False,
            )

        self.assertEqual(info["id"], "fb1322644996513521")
        self.assertGreaterEqual(len(attempts), 2)
        self.assertIn("cookiesfrombrowser", attempts[0])
        self.assertEqual(attempts[0]["cookiesfrombrowser"][0], "chrome")

    def test_run_download_task_retries_without_subtitles_after_429(self):
        attempts = []

        with tempfile.TemporaryDirectory(dir=r"D:\tmp") as tmpdir:
            tmp_root = Path(tmpdir)
            media_path = tmp_root / "downloads" / "YouTube" / "channel" / "Demo Clip [abc123].mp4"
            media_path.parent.mkdir(parents=True, exist_ok=True)
            media_path.write_bytes(b"fake media")

            old_downloader_base = downloader.BASE_DOWNLOADS_DIR
            old_file_manager_base = file_manager.BASE_DOWNLOADS_DIR
            downloader.BASE_DOWNLOADS_DIR = str(tmp_root / "downloads")
            file_manager.BASE_DOWNLOADS_DIR = str(tmp_root / "downloads")
            try:
                task = downloader.DownloadTask("task-429", "https://example.com/watch?v=abc123", {"write_subs": True})
                task.filepath = str(tmp_root / "staging" / "temp.part")

                def fake_extract(url, ydl_opts, cookie_type, cookie_val, download):
                    attempts.append(dict(ydl_opts))
                    if len(attempts) == 1:
                        raise RuntimeError("Unable to download video subtitles for 'aa': HTTP Error 429: Too Many Requests")
                    self.assertNotIn("writesubtitles", ydl_opts)
                    self.assertNotIn("writeautomaticsub", ydl_opts)
                    return {
                        "id": "abc123",
                        "title": "Demo Clip",
                        "uploader": "channel",
                        "extractor_key": "YouTube",
                    }

                with patch.object(downloader, "_run_yt_dlp_with_cookie_fallback", side_effect=fake_extract):
                    downloader.run_download_task(task)

                self.assertEqual(task.status, "completed")
                self.assertEqual(len(attempts), 2)
                self.assertIn("writesubtitles", attempts[0])
                self.assertNotIn("writesubtitles", attempts[1])
                self.assertEqual(Path(task.filepath).resolve(), media_path.resolve())
                self.assertTrue(media_path.with_suffix(".caption.txt").exists())
            finally:
                downloader.BASE_DOWNLOADS_DIR = old_downloader_base
                file_manager.BASE_DOWNLOADS_DIR = old_file_manager_base

    def test_run_download_task_selected_browser_falls_back_without_other_browsers(self):
        attempts = []

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts
                attempts.append(opts)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def extract_info(self, url, download):
                if len(attempts) < 3:
                    raise RuntimeError("Could not copy Chrome cookie database. See https://github.com/yt-dlp/yt-dlp/issues/7271 for more info")
                return {
                    "id": "fb1322644996513521",
                    "title": "Thai Clip",
                    "uploader": "page",
                    "extractor_key": "Facebook",
                }

        with patch.object(downloader.yt_dlp, "YoutubeDL", FakeYDL), \
             patch.object(downloader, "get_cookie_attempts", return_value=[
                 {"source_type": "browser", "source_value": "chrome", "options": {"cookiesfrombrowser": ("chrome",)}},
                 {"source_type": "file", "source_value": "uploaded.cookies", "options": {"cookiefile": "uploaded.cookies"}},
                 {"source_type": "none", "source_value": None, "options": {}},
             ]):
            info = downloader._run_yt_dlp_with_cookie_fallback(
                "https://www.facebook.com/watch/?v=1322644996513521&_rdr",
                {"quiet": True},
                "browser",
                "chrome",
                download=False,
            )

        self.assertEqual(info["id"], "fb1322644996513521")
        self.assertEqual(len(attempts), 3)
        self.assertIn("cookiesfrombrowser", attempts[0])
        self.assertIn("cookiefile", attempts[1])
        self.assertEqual(attempts[2], {"quiet": True})
        self.assertNotIn("edge", str(attempts))
        self.assertNotIn("firefox", str(attempts))

    def test_update_ytdlp_endpoint_invokes_pip_upgrade(self):
        client = TestClient(app_module.app)
        completed = subprocess.CompletedProcess(
            args=[sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            returncode=0,
            stdout="updated",
            stderr="",
        )

        with patch.object(app_module.subprocess, "run", return_value=completed) as run_mock:
            response = client.post("/api/update-ytdlp")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertIn("yt_dlp_version", body)
        run_mock.assert_called_once()
        self.assertEqual(run_mock.call_args.args[0][0], sys.executable)
        self.assertIn("yt-dlp", run_mock.call_args.args[0])

if __name__ == "__main__":
    unittest.main(verbosity=2)
