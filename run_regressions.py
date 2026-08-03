import subprocess
import sys


def main() -> int:
    commands = [
        [sys.executable, "-m", "unittest", "test_download_completion_regression"],
        [sys.executable, "test_browser_open_folder.py"],
    ]

    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
