import logging
import re
import subprocess
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_tunnel_proc: subprocess.Popen | None = None
TUNNEL_URL: str | None = None


def _save_url_to_env(url: str) -> None:
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    lines: list[str] = []
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("WEBAPP_URL="):
            lines.append(f"WEBAPP_URL={url}")
        else:
            lines.append(line)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def start_tunnel(port: int, timeout: int = 90) -> str | None:
    """Запускает localhost.run туннель и возвращает HTTPS URL."""
    global _tunnel_proc, TUNNEL_URL

    logger.info("Запуск HTTPS туннеля на порт %s...", port)
    _tunnel_proc = subprocess.Popen(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ServerAliveInterval=30",
            "-R",
            f"80:127.0.0.1:{port}",
            "nokey@localhost.run",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    deadline = time.time() + timeout
    while time.time() < deadline and _tunnel_proc.stdout:
        line = _tunnel_proc.stdout.readline()
        if not line:
            if _tunnel_proc.poll() is not None:
                break
            time.sleep(0.3)
            continue
        logger.info("tunnel: %s", line.strip())
        match = re.search(r"https://[a-z0-9]+\.lhr\.life", line)
        if match:
            TUNNEL_URL = match.group(0)
            _save_url_to_env(TUNNEL_URL)
            logger.info("Туннель готов: %s", TUNNEL_URL)
            break

    if not TUNNEL_URL:
        logger.error("Не удалось получить URL туннеля")
        return None

    def _watch() -> None:
        if _tunnel_proc:
            _tunnel_proc.wait()
            logger.warning("Туннель остановился! Перезапусти start.bat")

    threading.Thread(target=_watch, daemon=True).start()
    return TUNNEL_URL
