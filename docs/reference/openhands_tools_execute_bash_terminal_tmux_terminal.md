# openhands.tools.execute_bash.terminal.tmux_terminal

Tmux-based terminal backend implementation.

## Classes

### TmuxTerminal

Tmux-based terminal backend.

This backend uses tmux to provide a persistent terminal session
with full screen capture and history management capabilities.

#### Functions

##### clear_screen(self) -> None

Clear the tmux pane screen and history.

##### close(self) -> None

Clean up the tmux session.

##### initialize(self) -> None

Initialize the tmux terminal session.

##### interrupt(self) -> bool

Send interrupt signal (Ctrl+C) to the tmux pane.

Returns:
    True if interrupt was sent successfully, False otherwise

##### is_powershell(self) -> bool

Check if this is a PowerShell terminal.

Returns:
    True if this is a PowerShell terminal, False otherwise

##### is_running(self) -> bool

Check if a command is currently running.

For tmux, we determine this by checking if the terminal
is ready for new commands (ends with prompt).

##### read_screen(self) -> str

Read the current tmux pane content.

Returns:
    Current visible content of the tmux pane

##### send_keys(self, text: str, enter: bool = True) -> None

Send text/keys to the tmux pane.

Args:
    text: Text or key sequence to send
    enter: Whether to send Enter key after the text

