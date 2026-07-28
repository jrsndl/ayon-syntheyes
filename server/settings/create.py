"""Creator settings for SynthEyes publish products."""

from typing import Literal

from ayon_server.settings import BaseSettingsModel, SettingsField


class CreateReviewModel(BaseSettingsModel):
    """Perspective Preview Movie settings for review products."""

    enabled: bool = SettingsField(True, title="Enabled")
    default_variants: list[str] = SettingsField(
        default_factory=lambda: ["Main"],
        title="Default variants",
    )
    file_extension: Literal[
        "jpg", "jpeg", "png", "tif", "tiff", "tga", "sgi", "exr"
    ] = SettingsField(
        "jpg",
        title="File extension",
        description="Image sequences only; container formats are not allowed.",
    )
    show_all_viewport_items: bool = SettingsField(
        False,
        title="Show all viewport items",
    )
    show_grid: bool = SettingsField(False, title="Show grid")
    square_pixel_output: bool = SettingsField(
        True,
        title="Square-pixel output",
    )
    anti_aliasing_motion_blur: Literal[
        "None",
        "Low",
        "Medium",
        "High",
        "Moblur Low",
        "Moblur Medium",
        "Moblur High",
    ] = SettingsField(
        "Medium",
        title="Anti-aliasing and motion blur",
    )
    shutter_angle: float = SettingsField(
        180.0,
        title="Shutter angle",
        ge=0.0,
        le=360.0,
    )
    phase: float = SettingsField(
        -90.0,
        title="Phase",
        ge=-360.0,
        le=360.0,
    )
    frame_time_burnin: bool = SettingsField(
        True,
        title="Frame#/Time burn-in",
    )
    tags: list[str] = SettingsField(
        default_factory=lambda: ["review"],
        title="Representation tags",
        description=(
            "Tags passed to AYON review and burn-in processing. Include "
            "'review' to process the source with Extract Review."
        ),
    )


class CreateRenderModel(BaseSettingsModel):
    """Processed plate settings for Image Preprocessor Save Sequence."""

    enabled: bool = SettingsField(True, title="Enabled")
    default_variants: list[str] = SettingsField(
        default_factory=lambda: ["Undistorted"],
        title="Default variants",
    )
    reset_filtering_color: bool = SettingsField(
        True,
        title="Temporarily reset Filtering and Color",
        description=(
            "Render with default Filtering and Color controls, then restore "
            "the complete original Image Preprocessor state."
        ),
    )
    file_extension: Literal[
        "jpg", "jpeg", "png", "tif", "tiff", "tga", "sgi", "exr"
    ] = SettingsField(
        "jpg",
        title="File extension",
        description="Image sequences only; container formats are not allowed.",
    )
    rgb_included: bool = SettingsField(True, title="RGB included")
    alpha_included: bool = SettingsField(False, title="Alpha included")
    meshes_included: bool = SettingsField(False, title="Meshes included")
    frame_time_burnin: bool = SettingsField(
        False,
        title="Frame#/Time burn-in",
    )
    tags: list[str] = SettingsField(
        default_factory=lambda: ["review"],
        title="Representation tags",
        description=(
            "Tags passed to AYON review and burn-in processing. Include "
            "'review' to process the render with Extract Review."
        ),
    )


class CreatorSettings(BaseSettingsModel):
    """All SynthEyes creator-plugin settings."""

    CreateReview: CreateReviewModel = SettingsField(
        default_factory=CreateReviewModel,
        title="Create Review",
    )
    CreateRender: CreateRenderModel = SettingsField(
        default_factory=CreateRenderModel,
        title="Create Processed Plate Render",
    )


DEFAULT_CREATE_SETTINGS = {
    "CreateReview": {
        "enabled": True,
        "default_variants": ["Main"],
        "file_extension": "jpg",
        "show_all_viewport_items": False,
        "show_grid": False,
        "square_pixel_output": True,
        "anti_aliasing_motion_blur": "Medium",
        "shutter_angle": 180.0,
        "phase": -90.0,
        "frame_time_burnin": True,
        "tags": ["review"],
    },
    "CreateRender": {
        "enabled": True,
        "default_variants": ["Undistorted"],
        "reset_filtering_color": True,
        "file_extension": "jpg",
        "rgb_included": True,
        "alpha_included": False,
        "meshes_included": False,
        "frame_time_burnin": False,
        "tags": ["review"],
    },
}
