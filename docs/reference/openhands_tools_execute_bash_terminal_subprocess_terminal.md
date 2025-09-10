# openhands.tools.execute_bash.terminal.subprocess_terminal

PTY-based terminal backend implementation (replaces pipe-based subprocess).

## Classes

### SubprocessTerminal

PTY-backed terminal backend.

Creates an interactive bash in a pseudoterminal (PTY) so programs behave as if
attached to a real terminal. Initialization uses a sentinel-based handshake
and prompt detection instead of blind sleeps.

#### Functions

##### clear_screen(self) -> None

Drop buffered output up to the most recent PS1 block; do not emit ^L.

##### close(self) -> None

Clean up the PTY terminal.

##### initialize(self) -> None

Initialize the PTY terminal session.

##### interrupt(self) -> bool

Send SIGINT to the PTY process group (fallback to signal-based interrupt).

##### is_powershell(self) -> bool

Check if this is a PowerShell terminal.

Returns:
    True if this is a PowerShell terminal, False otherwise

##### is_running(self) -> bool

Heuristic: command running if not at PS1 prompt and process alive.

##### read_screen(self) -> str

Read the current terminal screen content.

The content we return should NOT contains carriage returns (CR, ).

##### send_keys(self, text: str, enter: bool = True) -> None

Send keystrokes to the PTY.

Supports:
  - Plain text
  - Ctrl sequences: 'C-a'..'C-z' (Ctrl+C sends ^C byte)
  - Special names: 'ENTER','TAB','BS','ESC','UP','DOWN','LEFT','RIGHT',
                   'HOME','END','PGUP','PGDN','C-L','C-D'

