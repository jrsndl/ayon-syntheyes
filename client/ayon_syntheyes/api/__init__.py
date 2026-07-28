"""Public SynthEyes host API."""

__all__ = ["Container", "SynthEyesHost"]


def __getattr__(name: str):
    """Delay AYON/pyblish imports until the host is actually requested."""
    if name == "SynthEyesHost":
        from .host import SynthEyesHost

        return SynthEyesHost
    if name == "Container":
        from .pipeline import Container

        return Container
    raise AttributeError(name)
