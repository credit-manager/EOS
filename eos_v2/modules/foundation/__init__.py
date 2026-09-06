"""Shared contracts for first-party foundation modules."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    key: str
    version: str
    display_name: str

    def __post_init__(self) -> None:
        if not self.key or not self.key.replace("_", "").isalnum():
            raise ValueError("Invalid module key")
        if not self.version or not self.display_name:
            raise ValueError("Module version and display name are required")
