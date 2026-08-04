"""Regression tests for AYON's client-addon discovery scan."""

import ayon_syntheyes


def test_lazy_addon_class_is_visible_to_dir_discovery():
    """AYON scans ``dir(module)`` before resolving addon classes."""
    assert "SynthEyesAddon" in dir(ayon_syntheyes)
