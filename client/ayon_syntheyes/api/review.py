"""Dependency-free helpers for SynthEyes review publishing."""

from __future__ import annotations

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
    ext = validate_image_extension(extension)
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == f".{ext}"
    )
