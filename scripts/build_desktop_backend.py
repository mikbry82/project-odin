import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
ENTRYPOINT = BACKEND / "app" / "desktop.py"


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "project-odin-backend",
        "--paths",
        str(BACKEND),
        "--collect-submodules",
        "app",
        "--collect-all",
        "aiosqlite",
        "--collect-all",
        "asyncpg",
        "--collect-all",
        "uvicorn",
        str(ENTRYPOINT),
    ]
    return subprocess.call(command, cwd=BACKEND)


if __name__ == "__main__":
    raise SystemExit(main())
