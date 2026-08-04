"""Create a processed plate render product."""

from ayon_core.lib import BoolDef, EnumDef

from ayon_syntheyes.api.creator import SynthEyesCreator


IMAGE_EXTENSIONS = [
    "jpg",
    "jpeg",
    "png",
    "tif",
    "tiff",
    "tga",
    "sgi",
    "exr",
]


class CreateRender(SynthEyesCreator):
    """Create an Image Preprocessor Save Sequence product."""

    identifier = "io.ayon.creators.syntheyes.render"
    label = "Processed Plate Render"
    product_base_type = "render"
    product_type = "render"
    icon = "image"
    enabled = True
    default_variants = ["Undistorted"]
    reset_filtering_color = True
    file_extension = "jpg"

    def _render_attr_defs(self):
        return [
            BoolDef(
                "reset_filtering_color",
                label="Temporarily reset Filtering and Color",
                tooltip=(
                    "Render with default Image Preprocessor Filtering and "
                    "Color controls, then restore their previous values."
                ),
                default=self.reset_filtering_color,
            ),
            EnumDef(
                "file_extension",
                IMAGE_EXTENSIONS,
                label="File extension",
                default=self.file_extension,
            ),
        ]

    def get_pre_create_attr_defs(self):
        """Expose project defaults as artist-overridable options."""
        return self._render_attr_defs()

    def get_attr_defs_for_instance(self, instance):
        """Keep render overrides editable after creation."""
        return self._render_attr_defs()

    def create(self, product_name, instance_data, pre_create_data):
        """Persist the selected render options on the created instance."""
        instance_data = dict(instance_data)
        instance_data["creator_attributes"] = {
            "reset_filtering_color": pre_create_data.get(
                "reset_filtering_color", self.reset_filtering_color
            ),
            "file_extension": pre_create_data.get(
                "file_extension", self.file_extension
            ),
        }
        return super().create(
            product_name,
            instance_data,
            pre_create_data,
        )
