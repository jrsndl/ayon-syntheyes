"""Helpers for profile-driven SynthEyes exports."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
WORKFILE_VERSION_PATTERN = re.compile(
    r"(?:^|[._-])v(?P<version>\d+)(?=$|[._-])",
    re.IGNORECASE,
)


def validate_preset_name(name: str) -> str:
    """Validate and return a filename-safe export preset name."""
    if not SAFE_NAME_PATTERN.fullmatch(name):
        raise ValueError(
            f"Invalid export preset name '{name}'. Only a-z, A-Z, 0-9, "
            "and underscore are allowed."
        )
    return name


def workfile_version(workfile_path: str) -> int:
    """Extract the last v### token from a SynthEyes workfile name."""
    matches = list(
        WORKFILE_VERSION_PATTERN.finditer(Path(workfile_path).stem)
    )
    if not matches:
        raise ValueError(
            "The SynthEyes workfile name does not contain a version token "
            "such as '_v001'."
        )
    return int(matches[-1].group("version"))


def export_directory(
    workfile_path: str,
    task_name: str,
    version: int,
    preset_name: str,
) -> Path:
    """Return <work dir>/<task>/v###/<preset>."""
    validate_preset_name(preset_name)
    return (
        Path(workfile_path).resolve().parent
        / task_name
        / f"v{version:03d}"
        / preset_name
    )


def expand_anatomy_path(
    template: str,
    anatomy: Any,
    project_entity: dict,
    folder_entity: dict,
    task_entity: dict,
) -> str:
    """Expand supported AYON anatomy/context tokens in a preset path."""
    data = {
        "root": anatomy.roots,
        "project": project_entity,
        "folder": folder_entity,
        "task": task_entity,
    }
    try:
        return str(template).format(**data)
    except (KeyError, IndexError, AttributeError) as exc:
        raise ValueError(
            f"Could not expand SynthEyes preset path '{template}': {exc}"
        ) from exc


def matching_files(
    directory: Path,
    extension: str,
    file_name_includes: str = "",
) -> list[Path]:
    """Find recursively matching files with case-insensitive filters."""
    normalized_extension = extension.lower().lstrip(".")
    substring = file_name_includes.lower()
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if (
            path.is_file()
            and path.suffix.lower().lstrip(".") == normalized_extension
            and substring in path.name.lower()
        )
    )


def product_name(
    preset_name: str,
    expected_product: dict,
    used_names: set[str],
) -> str:
    """Create a unique, filename-safe AYON product name."""
    discriminator = (
        expected_product.get("file_name_includes")
        or expected_product["extension"]
    )
    discriminator = re.sub(r"[^A-Za-z0-9_]+", "_", discriminator).strip("_")
    base = f"{preset_name}_{discriminator}" if discriminator else preset_name
    candidate = base
    suffix = 2
    while candidate.lower() in used_names:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used_names.add(candidate.lower())
    return candidate


def index_presets(export_presets: list[dict]) -> dict[str, dict]:
    """Validate uniqueness and return presets indexed by name."""
    output = {}
    for preset in export_presets:
        name = validate_preset_name(preset["name"])
        lowered = name.lower()
        if lowered in output:
            raise ValueError(f"Duplicate export preset name '{name}'.")
        output[lowered] = preset
    return output
