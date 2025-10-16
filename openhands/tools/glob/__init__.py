# Compatibility shim: if this module is imported as top-level 'glob' during
# build isolation (e.g., by setuptools), delegate to the stdlib glob module.
# This avoids name shadowing from the package path 'openhands.tools.glob'.
import sys, sysconfig, importlib.util, os  # noqa: E401
if __name__ == "glob":  # pragma: no cover - build-time path only
    stdlib = sysconfig.get_paths().get("stdlib")
    if stdlib:
        stdlib_glob_path = os.path.join(stdlib, "glob.py")
        spec = importlib.util.spec_from_file_location("glob", stdlib_glob_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules["glob"] = module
            globals().update(module.__dict__)

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
