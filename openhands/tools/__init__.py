"""Runtime tools package."""

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("openhands-tools")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for editable/unbuilt environments
