# openhands.tools.execute_bash.utils.command

Utilities for parsing and processing bash commands.

## Functions

### escape_bash_special_chars(command: str) -> str

Escapes characters that have different interpretations in bash vs python.
Specifically handles escape sequences like \;, \|, \&, etc.

### split_bash_commands(commands: str) -> list[str]

Split bash commands into individual command strings.

