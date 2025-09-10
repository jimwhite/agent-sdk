# openhands.tools.str_replace_editor.utils.shell

## Functions

### check_tool_installed(tool_name: str) -> bool

Check if a tool is installed.

### run_shell_cmd(cmd: str, timeout: float | None = 120.0, truncate_after: int | None = 16000, truncate_notice: str = '<response clipped><NOTE>Due to the max output limit, only part of the full response has been shown to you.</NOTE>') -> tuple[int, str, str]

Run a shell command synchronously with a timeout.

Args:
    cmd: The shell command to run.
    timeout: The maximum time to wait for the command to complete.
    truncate_after: The maximum number of characters to return for stdout
        and stderr.

Returns:
    A tuple containing the return code, stdout, and stderr.

