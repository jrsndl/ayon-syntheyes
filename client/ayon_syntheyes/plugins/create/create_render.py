"""Create a processed plate render product."""

from ayon_syntheyes.api.creator import SynthEyesCreator


class CreateRender(SynthEyesCreator):
    """Create an Image Preprocessor Save Sequence product."""

    identifier = "io.ayon.creators.syntheyes.render"
    label = "Processed Plate Render"
    product_base_type = "render"
    product_type = "render"
    icon = "image"
    enabled = True
    default_variants = ["Undistorted"]
