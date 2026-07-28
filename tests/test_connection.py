from pathlib import Path

import pytest

from ayon_syntheyes.api import connection


def test_resolve_sypy_beside_executable(tmp_path: Path, monkeypatch):
    package = tmp_path / "SyPy3"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    executable = tmp_path / "SynthEyes64.exe"
    executable.touch()
    monkeypatch.delenv("AYON_SYNTHEYES_SYPY_DIR", raising=False)

    assert connection.resolve_sypy_directory(str(executable)) == str(tmp_path)


def test_resolve_sypy_rejects_missing_package(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("AYON_SYNTHEYES_SYPY_DIR", raising=False)
    with pytest.raises(RuntimeError, match="SyPy3 was not found"):
        connection.resolve_sypy_directory(str(tmp_path / "SynthEyes64.exe"))


def test_pin_is_command_line_safe():
    pin = connection.create_pin()
    assert pin
    assert all(char.isalnum() or char == "_" for char in pin)
