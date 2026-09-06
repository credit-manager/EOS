from __future__ import annotations

from typing import Final

from eos_v2.modules.industry import IndustryPackBuilder
from eos_v2.modules.industry.construction_real_estate import ConstructionRealEstatePack


CATALOG: Final[dict[str, IndustryPackBuilder]] = {
    "construction-real-estate": ConstructionRealEstatePack(),
}


def get_pack(key: str) -> IndustryPackBuilder:
    try:
        return CATALOG[key]
    except KeyError as exc:
        raise KeyError(f"Unknown industry pack: {key}") from exc
