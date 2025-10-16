# Avoid shadowing stdlib `glob` during build by providing stdlib proxies
try:
    from importlib import import_module as _import_module

    _stdlib_glob = _import_module("glob")
    glob = _stdlib_glob.glob
    iglob = _stdlib_glob.iglob
except Exception:  # pragma: no cover - best-effort for build environments
    pass

# Avoid importing heavy dependencies at module import time (helps build isolation)
__all__ = [
    "GlobTool",
    "GlobAction",
    "GlobObservation",
    "GlobExecutor",
]


def __getattr__(name):  # PEP 562 lazy import
    if name in {"GlobTool", "GlobAction", "GlobObservation"}:
        from .definition import GlobAction, GlobObservation, GlobTool

        return {"GlobTool": GlobTool, "GlobAction": GlobAction, "GlobObservation": GlobObservation}[name]
    if name == "GlobExecutor":
        from .impl import GlobExecutor

        return GlobExecutor
    raise AttributeError(name)
