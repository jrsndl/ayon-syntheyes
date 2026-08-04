"""Keep SynthEyes review creator instances after publishing."""

from __future__ import annotations

from typing import ClassVar

import pyblish.api

from ayon_syntheyes.api import SynthEyesHost


class IntegratePersistReview(pyblish.api.InstancePlugin):
    """Reassert the stored creator instance at the end of publishing."""

    order = pyblish.api.IntegratorOrder + 0.49
    hosts: ClassVar[list[str]] = ["syntheyes"]
    families: ClassVar[list[str]] = ["review"]
    label = "Persist SynthEyes Review Instance"

    def process(self, instance: pyblish.api.Instance) -> None:
        host = SynthEyesHost.get_host()
        instance_id = instance.data.get("instance_id")
        if host is None or not instance_id:
            return
        if not host.keep_publish_instance(str(instance_id)):
            self.log.warning(
                "Review creator instance '%s' was not found in Scene "
                "Information.",
                instance_id,
            )
