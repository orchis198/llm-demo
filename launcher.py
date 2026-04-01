from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import webbrowser

EXTERNAL_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
APP_FILE = EXTERNAL_ROOT / "app.py"
RUNTIME_DIR = EXTERNAL_ROOT / "runtime"
LOG_FILE = EXTERNAL_ROOT / "launcher.log"
RUNTIME_LOG_FILE = EXTERNAL_ROOT / "streamlit_runtime.log"


def write_log(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def choose_mode() -> str | None:
    root = tk.Tk()
    root.title("demoV1 启动模式")
    root.geometry("360x180")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    selected: dict[str, str | None] = {"mode": None}

    def select_demo() -> None:
        selected["mode"] = "demo"
        root.destroy()

    def select_full() -> None:
        selected["mode"] = "full"
        root.destroy()

    def on_close() -> None:
        selected["mode"] = None
        root.destroy()

    tk.Label(root, text="请选择启动模式", font=("Microsoft YaHei", 14, "bold")).pack(pady=18)
    tk.Button(root, text="演示模式（无需 API）", width=24, command=select_demo).pack(pady=6)
    tk.Button(root, text="完整模式（需先配置 API）", width=24, command=select_full).pack(pady=6)
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
    return selected["mode"]


def choose_free_port(start_port: int = 8501, end_port: int = 8999) -> int:
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("未找到可用端口")


def wait_for_server(host: str, port: int, timeout: int = 25) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(1)
    return False


def get_runtime_python() -> Path:
    if getattr(sys, "frozen", False):
        for candidate in [RUNTIME_DIR / "pythonw.exe", RUNTIME_DIR / "python.exe"]:
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"未找到便携运行时，请检查目录：{RUNTIME_DIR}")
    return Path(sys.executable)


def launch_streamlit(mode: str) -> None:
    port = choose_free_port()
    url = f"http://localhost:{port}"
    python_exe = get_runtime_python()
    env = os.environ.copy()
    env["DEMO_RUN_MODE"] = mode
    command = [
        str(python_exe),
        "-m",
        "streamlit",
        "run",
        str(APP_FILE),
        "--server.headless",
        "true",
        f"--server.port={port}",
    ]

    write_log(f"launch mode={mode} port={port} cmd={command}")
    RUNTIME_LOG_FILE.write_text("", encoding="utf-8")
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if getattr(sys, "frozen", False) else 0
    with RUNTIME_LOG_FILE.open("a", encoding="utf-8") as runtime_log:
        process = subprocess.Popen(
            command,
            cwd=str(EXTERNAL_ROOT),
            env=env,
            stdout=runtime_log,
            stderr=runtime_log,
            creationflags=creationflags,
        )

    if wait_for_server("127.0.0.1", port):
        write_log(f"server started successfully on port={port}")
        webbrowser.open(url)
        return

    if process.poll() is not None:
        write_log(f"child exited early code={process.returncode}")
    else:
        write_log("server did not become ready within timeout")
    messagebox.showerror("demoV1 启动失败", f"本地服务未成功启动，请查看日志：\n{LOG_FILE}\n{RUNTIME_LOG_FILE}")


def main() -> None:
    mode = choose_mode()
    if mode is None:
        write_log("launch cancelled by user")
        return
    try:
        launch_streamlit(mode)
    except Exception as exc:
        write_log(f"launcher crash: {exc!r}")
        messagebox.showerror("demoV1 启动失败", f"启动器异常：{exc}\n请查看日志：\n{LOG_FILE}")


if __name__ == "__main__":
    main()
