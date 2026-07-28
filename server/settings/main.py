"""Settings for the SynthEyes addon."""

from typing import Literal

from ayon_server.settings import BaseSettingsModel, SettingsField

from .create import CreatorSettings, DEFAULT_CREATE_SETTINGS
from .publish import DEFAULT_PUBLISH_SETTINGS, PublishSettings


class LevelAdjustmentSettings(BaseSettingsModel):
    """Image Preprocessor level adjustment values."""

    low: float = SettingsField(
        0.0,
        title="Low",
        ge=0.0,
        le=1.0,
    )
    mid: float = SettingsField(
        0.5,
        title="Mid",
        ge=0.0,
        le=1.0,
    )
    high: float = SettingsField(
        1.0,
        title="High",
        ge=0.0,
        le=1.0,
    )


class ClipLoaderSettings(BaseSettingsModel):
    """Defaults applied when an AYON clip becomes a SynthEyes shot."""

    match_frame_numbers: bool = SettingsField(
        True,
        title="Match frame numbers",
    )
    process_depth: Literal["8 bit", "16 bit", "Half", "Float"] = (
        SettingsField("Half", title="Process depth")
    )
    output_depth: Literal[
        "Follow process depth", "8 bit", "16 bit", "Half", "Float"
    ] = SettingsField("Half", title="Process / Output depth")
    lut_3d: Literal[
        "None",
        "ACES to LogC 800EI",
        "ACES to R.2020",
        "ACES to R.709",
        "ARRI LogC 800EI to ACES",
        "ARRI LogC to R.2020",
        "ARRI LogC to R.709",
        "Cineon LUT",
        "R.2020 to R.709",
        "R.2020 to R.709A",
        "R.2020HLG to R.709",
        "R.2020HLG to R.709A",
        "R.2020PQ to R.709",
        "R.2020PQ to R.709A",
    ] = SettingsField("None", title="3-D LUT")
    level_adjustment: LevelAdjustmentSettings = SettingsField(
        default_factory=LevelAdjustmentSettings,
        title="Level adjustment",
    )


class SynthEyesSettings(BaseSettingsModel):
    """Project settings used by the client bridge."""

    connect_timeout: float = SettingsField(
        15.0,
        title="Connection timeout",
        description="Seconds to wait for the SynthEyes SyPy listener.",
        ge=1.0,
        le=120.0,
    )
    sy_py_directory: str = SettingsField(
        "",
        title="SyPy3 directory override",
        description=(
            "Optional path to the SynthEyes SyPy3 package. When empty, it is "
            "resolved next to the configured SynthEyes executable."
        ),
    )
    load_clip: ClipLoaderSettings = SettingsField(
        default_factory=ClipLoaderSettings,
        title="Clip loader",
    )
    create: CreatorSettings = SettingsField(
        default_factory=CreatorSettings,
        title="Creator plugins",
    )
    publish: PublishSettings = SettingsField(
        default_factory=PublishSettings,
        title="Publish",
    )


DEFAULT_SYNTHEYES_SETTINGS = {
    "connect_timeout": 15.0,
    "sy_py_directory": "",
    "load_clip": {
        "match_frame_numbers": True,
        "process_depth": "Half",
        "output_depth": "Half",
        "lut_3d": "None",
        "level_adjustment": {
            "low": 0.0,
            "mid": 0.5,
            "high": 1.0,
        },
    },
    "create": DEFAULT_CREATE_SETTINGS,
    "publish": DEFAULT_PUBLISH_SETTINGS,
}
