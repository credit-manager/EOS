from __future__ import annotations

from dataclasses import dataclass

from eos_v2.modules.foundation import ModuleDescriptor
from eos_v2.modules.hr import DESCRIPTOR as HR
from eos_v2.modules.inventory import DESCRIPTOR as INVENTORY
from eos_v2.modules.projects import DESCRIPTOR as PROJECTS
from eos_v2.modules.purchasing import DESCRIPTOR as PURCHASING
from eos_v2.modules.sales import DESCRIPTOR as SALES


@dataclass(frozen=True, slots=True)
class ModuleRegistry:
    descriptors: tuple[ModuleDescriptor, ...]

    def __post_init__(self) -> None:
        keys = [item.key for item in self.descriptors]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate module key")

    def get(self, key: str) -> ModuleDescriptor:
        for descriptor in self.descriptors:
            if descriptor.key == key:
                return descriptor
        raise KeyError(f"Unknown module: {key}")


FOUNDATION_MODULES = ModuleRegistry((SALES, PURCHASING, INVENTORY, HR, PROJECTS))
