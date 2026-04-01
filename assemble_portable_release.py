from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RELEASE_ROOT = PROJECT_ROOT / "portable_release" / "demoV1-portable"
LAUNCHER_DIST = PROJECT_ROOT / "dist_portable_launcher" / "demoV1-launcher"
RUNTIME_SOURCE = Path(sys.executable).resolve().parent

COPY_DIRS = [
    "config",
    "data",
    "domain",
    "engines",
    "example",
    "llm",
    "services",
    "stage_pages",
    "ui",
]
COPY_FILES = [
    "app.py",
    "README.md",
    ".env.example",
    "requirements.txt",
]


def build_launcher() -> None:
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--distpath", "dist_portable_launcher", "--workpath", "build_portable_launcher", "-y", "demoV1.spec"],
        cwd=PROJECT_ROOT,
        check=True,
    )


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main() -> None:
    build_launcher()
    if RELEASE_ROOT.exists():
        shutil.rmtree(RELEASE_ROOT)
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)

    shutil.copy2(LAUNCHER_DIST / "demoV1-launcher.exe", RELEASE_ROOT / "demoV1-launcher.exe")

    runtime_target = RELEASE_ROOT / "runtime"
    copy_tree(RUNTIME_SOURCE, runtime_target)

    for name in COPY_DIRS:
        copy_tree(PROJECT_ROOT / name, RELEASE_ROOT / name)
    for name in COPY_FILES:
        shutil.copy2(PROJECT_ROOT / name, RELEASE_ROOT / name)

    print(f"portable release created: {RELEASE_ROOT}")


if __name__ == "__main__":
    main()
