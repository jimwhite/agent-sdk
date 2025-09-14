from __future__ import annotations

import threading
from collections import deque
from typing import Callable

import docker
from docker.models.containers import Container


class LogStreamer:
    """Streams Docker container logs to a provided logger function.

    Usage:
        streamer = LogStreamer(container, logFn)
        ... later ...
        streamer.close()
    """

    def __init__(
        self,
        container: Container,
        logFn: Callable[[str, str], None],
    ) -> None:
        self._container = container
        self.log = logFn
        self.stdout_thread: threading.Thread | None = None
        self.log_generator = None
        self._stop_event = threading.Event()

        try:
            self.log_generator = container.logs(stream=True, follow=True)
            self.stdout_thread = threading.Thread(target=self._stream_logs, daemon=True)
            self.stdout_thread.start()
        except Exception as e:  # pragma: no cover - defensive
            self.log("error", f"Failed to initialize log streaming: {e}")

    def _stream_logs(self) -> None:
        if not self.log_generator:  # pragma: no cover - defensive
            self.log("error", "Log generator not initialized")
            return

        try:
            for log_line in self.log_generator:
                if self._stop_event.is_set():
                    break
                if not log_line:
                    continue
                try:
                    decoded_line = log_line.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    decoded_line = str(log_line).rstrip()
                self.log("debug", f"[container:{self._container.name}] {decoded_line}")
        except Exception as e:  # pragma: no cover - best-effort streaming
            self.log("error", f"Error streaming docker logs to stdout: {e}")

    def close(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self.stdout_thread and self.stdout_thread.is_alive():
            self.stdout_thread.join(timeout)
        try:
            if self.log_generator is not None:
                self.log_generator.close()
        except Exception:
            pass

    def __del__(self) -> None:  # pragma: no cover - destructor best-effort
        try:
            self.close(timeout=2.0)
        except Exception:
            pass


class RollingLogger:
    """Very small rolling logger buffer for build progress."""

    def __init__(self, max_lines: int = 50) -> None:
        self.max_lines = max_lines
        self.lines: deque[str] = deque(maxlen=max_lines)

    def is_enabled(self) -> bool:
        return True

    def add_line(self, line: str) -> None:
        self.lines.append(line)

    def write_immediately(self, line: str) -> None:
        self.lines.append(line)

    # No-op placeholders for advanced terminal behavior
    def start(self, title: str) -> None:  # pragma: no cover
        self.add_line(title)

    def move_back(self, n: int) -> None:  # pragma: no cover
        pass

    def replace_current_line(self) -> None:  # pragma: no cover
        pass

    @property
    def all_lines(self) -> str:
        return "\n".join(self.lines)
