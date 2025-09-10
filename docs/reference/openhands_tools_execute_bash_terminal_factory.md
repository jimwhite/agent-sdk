# openhands.tools.execute_bash.terminal.factory

Factory for creating appropriate terminal sessions based on system capabilities.

## Functions

### create_terminal_session(work_dir: str, username: str | None = None, no_change_timeout_seconds: int | None = None, terminal_type: Optional[Literal['tmux', 'subprocess']] = None) -> openhands.tools.execute_bash.terminal.terminal_session.TerminalSession

Create an appropriate terminal session based on system capabilities.

Args:
    work_dir: Working directory for the session
    username: Optional username for the session
    no_change_timeout_seconds: Timeout for no output change
    terminal_type: Force a specific session type ('tmux', 'subprocess')
                 If None, auto-detect based on system capabilities

Returns:
    TerminalSession instance

Raises:
    RuntimeError: If the requested session type is not available

