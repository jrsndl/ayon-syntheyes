"""AYON integration for Boris FX SynthEyes."""

import os

from .version import __version__

SYNTH_EYES_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


def get_launch_script_path() -> str:
    return os.path.join(SYNTH_EYES_HOST_DIR, "api", "launch_script.py")


__all__ = [
    "SYNTH_EYES_HOST_DIR",
    "SynthEyesAddon",
    "__version__",
    "get_launch_script_path",
]


def __getattr__(name: str):
    """Import the addon class lazily for dependency-light tooling."""
    if name == "SynthEyesAddon":
        from .addon import SynthEyesAddon

        return SynthEyesAddon
    raise AttributeError(name)
