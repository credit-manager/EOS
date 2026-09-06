from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from eos_v2.modules.industry import IndustryPack
from eos_v2.modules.industry.construction_real_estate import build_pack as build_construction_real_estate


@dataclass(frozen=True, slots=True)
class RegisteredIndustryPack:
    key: str
    version: str
    display_name: str
    builder: Callable[[UUID], IndustryPack]


CATALOG: tuple[RegisteredIndustryPack, ...] = (
    RegisteredIndustryPack(
        key="construction-real-estate",
        version="1.0.0",
        display_name="Construction & Real Estate",
        builder=build_construction_real_estate,
    ),
)


def get_pack(key: str) -> RegisteredIndustryPack:
    for pack in CATALOG:
        if pack.key == key:
            return pack
    raise KeyError(key)
