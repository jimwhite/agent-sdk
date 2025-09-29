import shlex
import subprocess
import sys

from openhands.sdk.logger import get_logger


logger = get_logger(__name__)


def execute_command(
    cmd: list[str] | str,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    print_output: bool = True,
) -> subprocess.CompletedProcess:
    if isinstance(cmd, str):
        cmd_list = shlex.split(cmd)
    else:
        cmd_list = cmd
    logger.info("$ %s", " ".join(shlex.quote(c) for c in cmd_list))

    proc = subprocess.Popen(
        cmd_list,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    if proc is None:
        raise RuntimeError("Failed to start process")

    # Read line by line, echo to parent stdout/stderr
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    if proc.stdout is None or proc.stderr is None:
        raise RuntimeError("Failed to capture stdout/stderr")

    for line in proc.stdout:
        if print_output:
            sys.stdout.write(line)
        stdout_lines.append(line)
    for line in proc.stderr:
        if print_output:
            sys.stderr.write(line)
        stderr_lines.append(line)

    proc.wait()

    return subprocess.CompletedProcess(
        cmd_list,
        proc.returncode,
        "".join(stdout_lines),
        "".join(stderr_lines),
    )
