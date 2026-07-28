"""Small, testable adapter around the vendor-supplied SyPy3 package."""

from __future__ import annotations

import importlib
import os
import secrets
import socket
import sys
import time
from pathlib import Path
from typing import Any


def reserve_listener_port() -> int:
    """Ask Windows for an unused local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def create_pin() -> str:
    """Create a command-line-safe SyPy listener PIN."""
    return secrets.token_urlsafe(18).replace("-", "_")


def resolve_sypy_directory(executable: str) -> str:
    """Resolve the SyPy3 package beside a SynthEyes executable."""
    override = os.getenv("AYON_SYNTHEYES_SYPY_DIR")
    if override:
        candidate = Path(override)
    else:
        candidate = Path(executable).resolve().parent / "SyPy3"
    if not (candidate / "__init__.py").is_file():
        raise RuntimeError(
            f"SyPy3 was not found at '{candidate}'. Set the addon setting "
            "'SyPy3 directory override' when using a custom installation."
        )
    return str(candidate.parent)


def import_sypy(executable: str) -> Any:
    """Import SyPy3 without copying it into AYON's Python installation."""
    package_parent = resolve_sypy_directory(executable)
    if package_parent not in sys.path:
        sys.path.insert(0, package_parent)
    return importlib.import_module("SyPy3")


def connect(sypy: Any, port: int, pin: str, timeout: float) -> Any:
    """Connect to a listener, retrying while SynthEyes initializes."""
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        level = sypy.SyLevel()
        try:
            if level.OpenExisting(port, pin):
                return level
        except OSError as exc:
            last_error = exc
        time.sleep(0.2)
    message = f"Could not connect to SynthEyes on local port {port}."
    if last_error:
        message = f"{message} Last error: {last_error}"
    raise RuntimeError(message)
