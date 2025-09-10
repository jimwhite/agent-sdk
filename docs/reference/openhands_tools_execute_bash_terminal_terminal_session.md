# openhands.tools.execute_bash.terminal.terminal_session

Unified terminal session using TerminalInterface backends.

## Classes

### TerminalCommandStatus

Status of a terminal command execution.

### TerminalSession

Unified bash session that works with any TerminalInterface backend.

This class contains all the session controller logic (timeouts, command parsing,
output processing) while delegating terminal operations to the TerminalInterface.

#### Functions

##### close(self) -> None

Clean up the terminal backend.

##### execute(self, action: openhands.tools.execute_bash.definition.ExecuteBashAction) -> openhands.tools.execute_bash.definition.ExecuteBashObservation

Execute a command using the terminal backend.

##### initialize(self) -> None

Initialize the terminal backend.

##### interrupt(self) -> bool

Interrupt the currently running command (equivalent to Ctrl+C).

##### is_running(self) -> bool

Check if a command is currently running.

