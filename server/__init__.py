"""SynthEyes server addon."""

from ayon_server.addons import BaseServerAddon

from .settings import DEFAULT_SYNTHEYES_SETTINGS, SynthEyesSettings


class SynthEyesAddon(BaseServerAddon):
    """Server-side SynthEyes addon definition."""

    name = "syntheyes"
    title = "SynthEyes"
    settings_model = SynthEyesSettings

    async def get_default_settings(self) -> SynthEyesSettings:
        return self.get_settings_model()(**DEFAULT_SYNTHEYES_SETTINGS)
