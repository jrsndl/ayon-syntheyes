"""Dependency-free helpers for SynthEyes review publishing."""

from __future__ import annotations

import re
from pathlib import Path

IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "tif",
    "tiff",
    "tga",
    "sgi",
    "exr",
}
REVIEW_EXTENSION = "mov"


def validate_review_output_extension(extension: str) -> str:
    """Accept any filename-safe output extension for native SynthEyes."""
    value = extension.lower().lstrip(".")
    if not re.fullmatch(r"[a-z0-9]+", value):
        raise ValueError(
            "SynthEyes review extension must contain only letters and digits."
        )
    return value


def native_review_sequence_filename(
    product_name: str,
    frame: int,
    extension: str,
) -> str:
    """Build a native SynthEyes numbered review filename."""
    ext = validate_review_output_extension(extension)
    return f"{product_name}.{int(frame):04d}.{ext}"


def validate_review_extension(extension: str) -> str:
    """Accept only the SynthEyes ProRes MOV review container."""
    value = extension.lower().lstrip(".")
    if value != REVIEW_EXTENSION:
        raise ValueError("SynthEyes reviews must use the '.mov' container.")
    return value


def review_movie_filename(product_name: str, extension: str = "mov") -> str:
    """Build the filename for a single-file review representation."""
    return f"{product_name}.{validate_review_extension(extension)}"


def collect_review_movie(directory: Path, filename: str) -> Path | None:
    """Return the exact rendered review movie when it exists."""
    path = directory / filename
    if path.is_file() and path.suffix.lower() == f".{REVIEW_EXTENSION}":
        return path
    return None


def validate_image_extension(extension: str) -> str:
    """Return a normalized supported image extension."""
    value = extension.lower().lstrip(".")
    if value not in IMAGE_EXTENSIONS:
        raise ValueError(
            f"Review extension '.{value}' is not a supported image format. "
            "Movie and other container formats are not allowed."
        )
    return value


def review_filename(
    product_name: str,
    frame_start: int,
    extension: str,
) -> str:
    """Build the first filename of a numbered review sequence."""
    ext = validate_image_extension(extension)
    return f"{product_name}.{int(frame_start):04d}.{ext}"


def collect_review_files(directory: Path, extension: str) -> list[Path]:
    """Return image-sequence files from a review staging directory."""
    ext = validate_review_output_extension(extension)
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == f".{ext}"
    )
