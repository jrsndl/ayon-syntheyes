"""Create a SynthEyes perspective review product."""

from ayon_syntheyes.api.creator import SynthEyesCreator


class CreateReview(SynthEyesCreator):
    """Create a review from the Perspective viewport."""

    identifier = "io.ayon.creators.syntheyes.review"
    label = "Review"
    product_base_type = "review"
    product_type = "review"
    icon = "video-camera"
    enabled = True
    default_variants = ["Main"]

    def create(self, product_name, instance_data, pre_create_data):
        """Create and persist the review instance in the SynthEyes scene."""
        return super().create(
            product_name,
            instance_data,
            pre_create_data,
        )
