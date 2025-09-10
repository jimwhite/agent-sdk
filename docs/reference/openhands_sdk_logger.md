# openhands.sdk.logger

Minimal logger setup that encourages per-module loggers,
with Rich for humans and JSON for machines.

Usage:
    from openhands.sdk.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Hello from this module!")

## Functions

### disable_logger(name: str, level: int = 50) -> None

Disable or quiet down a specific logger by name.

### get_logger(name: str) -> logging.Logger

Return a logger for the given module name.

### setup_logging(level: int | None = None, log_to_file: bool | None = None, log_dir: str | None = None, fmt: str | None = None, when: str | None = None, backup_count: int | None = None) -> None

Configure the root logger. All child loggers inherit this setup.

