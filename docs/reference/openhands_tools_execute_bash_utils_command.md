# openhands.tools.execute_bash.utils.command

## Functions

### escape_bash_special_chars(command: str) -> str

Escapes characters that have different interpretations in bash vs python.
Specifically handles escape sequences like \;, \|, \&, etc.

### split_bash_commands(commands: str) -> list[str]

