"""Creator base implementation for SynthEyes."""

from __future__ import annotations

from ayon_core.pipeline import CreatedInstance, Creator


class SynthEyesCreator(Creator):
    """Persist creator instances in the SynthEyes scene description."""

    skip_discovery = True
    settings_category = "syntheyes"

    def create(
        self,
        product_name: str,
        instance_data: dict,
        pre_create_data: dict,
    ) -> CreatedInstance:
        instance = CreatedInstance(
            product_base_type=self.product_base_type,
            product_type=self.product_type,
            product_name=product_name,
            data=instance_data,
            creator=self,
        )
        self._add_instance_to_context(instance)
        self.host.add_publish_instance(instance.data_to_store())
        return instance

    def collect_instances(self) -> None:
        for instance_data in self.host.get_publish_instances():
            if instance_data.get("creator_identifier") != self.identifier:
                continue
            self._add_instance_to_context(
                CreatedInstance.from_existing(instance_data, self)
            )

    def update_instances(self, update_list: list[tuple]) -> None:
        stored = self.host.get_publish_instances()
        by_id = {
            item.get("instance_id"): item
            for item in stored
            if item.get("instance_id")
        }
        for instance, changes in update_list:
            value = changes.new_value
            current = by_id.get(instance.id)
            if current is None:
                stored.append(value)
                continue
            for key in set(current) - set(value):
                current.pop(key)
            current.update(value)
        self.host.write_create_instances(stored)

    def remove_instances(self, instances: list[CreatedInstance]) -> None:
        for instance in instances:
            self._remove_instance_from_context(instance)
            self.host.remove_create_instance(instance.id)
