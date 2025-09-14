from __future__ import annotations
import sys
import threading
from collections import deque
from typing import Callable

import docker
from docker.models.containers import Container
from openhands.sdk.logger import DEBUG

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
    max_lines: int
    char_limit: int
    log_lines: list[str]
    all_lines: str

    def __init__(self, max_lines: int = 10, char_limit: int = 80) -> None:
        self.max_lines = max_lines
        self.char_limit = char_limit
        self.log_lines = [''] * self.max_lines
        self.all_lines = ''

    def is_enabled(self) -> bool:
        return DEBUG and sys.stdout.isatty()

    def start(self, message: str = '') -> None:
        if message:
            print(message)
        self._write('\n' * self.max_lines)
        self._flush()

    def add_line(self, line: str) -> None:
        self.log_lines.pop(0)
        self.log_lines.append(line[: self.char_limit])
        self.print_lines()
        self.all_lines += line + '\n'

    def write_immediately(self, line: str) -> None:
        self._write(line)
        self._flush()

    def print_lines(self) -> None:
        """Display the last n log_lines in the console (not for file logging).

        This will create the effect of a rolling display in the console.
        """
        self.move_back()
        for line in self.log_lines:
            self.replace_current_line(line)

    def move_back(self, amount: int = -1) -> None:
        r"""'\033[F' moves the cursor up one line."""
        if amount == -1:
            amount = self.max_lines
        self._write('\033[F' * (self.max_lines))
        self._flush()

    def replace_current_line(self, line: str = '') -> None:
        r"""'\033[2K\r' clears the line and moves the cursor to the beginning of the line."""
        self._write('\033[2K' + line + '\n')
        self._flush()

    def _write(self, line: str) -> None:
        if not self.is_enabled():
            return
        sys.stdout.write(line)

    def _flush(self) -> None:
        if not self.is_enabled():
            return
        sys.stdout.flush()
        