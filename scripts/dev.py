import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    password = values.get("POSTGRES_PASSWORD")
    if not password:
        raise SystemExit("Set POSTGRES_PASSWORD in .env before starting development.")
    api_env = os.environ.copy()
    api_env.update(
        {
            key: value
            for key, value in values.items()
            if (
                key.startswith("KIMMY_")
                or key in {"OPENAI_API_KEY", "OPENROUTER_API_KEY"}
            )
            and value is not None
        }
    )
    api_env["KIMMY_DATABASE_URL"] = values.get("KIMMY_DATABASE_URL") or (
        f"postgresql+psycopg://kimmy:{quote(password, safe='')}@127.0.0.1:54329/kimmy"
    )
    web_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("KIMMY_")
        and key not in {"OPENAI_API_KEY", "OPENROUTER_API_KEY", "POSTGRES_PASSWORD"}
    }
    commands = {
        "migrate": (
            [
                "uv",
                "run",
                "--project",
                "apps/api",
                "python",
                "-m",
                "kimmy.cli",
                "migrate",
            ],
            api_env,
        ),
        "seed": (
            ["uv", "run", "--project", "apps/api", "python", "-m", "kimmy.cli", "seed"],
            api_env,
        ),
        "fleet-report": (
            [
                "uv",
                "run",
                "--project",
                "apps/api",
                "python",
                "-m",
                "kimmy.cli",
                "fleet-report",
                *sys.argv[2:],
            ],
            api_env,
        ),
        "api": (
            [
                "uv",
                "run",
                "--project",
                "apps/api",
                "uvicorn",
                "kimmy.main:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                "9000",
            ],
            api_env,
        ),
        "worker": (
            ["uv", "run", "--project", "apps/api", "python", "-m", "kimmy.jobs"],
            api_env,
        ),
        "web": (
            ["pnpm", "--dir", "apps/web", "dev", "--port", "5173", "--strictPort"],
            web_env,
        ),
    }
    selected = [sys.argv[1]] if len(sys.argv) > 1 else ["api", "worker", "web"]
    children: list[subprocess.Popen[bytes]] = []
    stopping = False

    def stop(signum: int, frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        for name in selected:
            command, environment = commands[name]
            children.append(
                subprocess.Popen(
                    command, cwd=ROOT, env=environment, start_new_session=True
                )
            )
        while not stopping:
            for child in children:
                result = child.poll()
                if result is not None:
                    return result
            time.sleep(0.1)
        return 0
    finally:
        for child in children:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 5
        for child in children:
            try:
                child.wait(timeout=max(0.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
