# Avoid shadowing stdlib `glob` during build by providing stdlib proxies
try:
    from importlib import import_module as _import_module

    _stdlib_glob = _import_module("glob")
    glob = _stdlib_glob.glob
    iglob = _stdlib_glob.iglob
except Exception:  # pragma: no cover - best-effort for build environments
    pass

# Core tool interface (use relative imports to work both as top-level and package)
from .definition import (
    GlobAction,
    GlobObservation,
    GlobTool,
)
from .impl import GlobExecutor


__all__ = [
    "GlobTool",
    "GlobAction",
    "GlobObservation",
    "GlobExecutor",
]
