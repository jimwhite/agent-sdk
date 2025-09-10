# openhands.tools.execute_bash.terminal.interface

Abstract interface for terminal backends.

## Classes

### TerminalInterface

Abstract interface for terminal backends.

This interface abstracts the low-level terminal operations, allowing
different backends (tmux, subprocess, PowerShell) to be used with
the same high-level session controller logic.

#### Functions

##### clear_screen(self) -> None

Clear the terminal screen and history.

##### close(self) -> None

Clean up the terminal backend.

This should properly terminate the terminal session and
clean up any resources.

##### initialize(self) -> None

Initialize the terminal backend.

This should set up the terminal session, configure the shell,
and prepare it for command execution.

##### interrupt(self) -> bool

Send interrupt signal (Ctrl+C) to the terminal.

Returns:
    True if interrupt was sent successfully, False otherwise

##### is_powershell(self) -> bool

Check if this is a PowerShell terminal.

Returns:
    True if this is a PowerShell terminal, False otherwise

##### is_running(self) -> bool

Check if a command is currently running in the terminal.

Returns:
    True if a command is running, False otherwise

##### read_screen(self) -> str

Read the current terminal screen content.

Returns:
    Current visible content of the terminal screen

##### send_keys(self, text: str, enter: bool = True) -> None

Send text/keys to the terminal.

Args:
    text: Text or key sequence to send
    enter: Whether to send Enter key after the text

### TerminalSessionBase

Abstract base class for terminal sessions.

This class defines the common interface for all terminal session implementations,
including tmux-based, subprocess-based, and PowerShell-based sessions.

#### Functions

##### close(self) -> None

Clean up the terminal session.

##### execute(self, action: openhands.tools.execute_bash.definition.ExecuteBashAction) -> openhands.tools.execute_bash.definition.ExecuteBashObservation

Execute a command in the terminal session.

Args:
    action: The bash action to execute

Returns:
    ExecuteBashObservation with the command result

##### initialize(self) -> None

Initialize the terminal session.

##### interrupt(self) -> bool

Interrupt the currently running command (equivalent to Ctrl+C).

Returns:
    True if interrupt was successful, False otherwise

##### is_running(self) -> bool

Check if a command is currently running.

Returns:
    True if a command is running, False otherwise

