from decimal import Decimal
from uuid import uuid4
import pytest
from eos_v2.modules.industry.construction_flow import ConstructionFlow, ContractMode, FlowStatus


def test_sale_flow_reaches_close_and_calculates_margin():
    flow = ConstructionFlow(uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), ContractMode.SALE, Decimal("100"), Decimal("250"), Decimal("500"))
    flow = flow.start_development().mark_unit_ready().contract().deliver().close()
    assert flow.status is FlowStatus.CLOSED
    assert flow.total_cost == Decimal("350")
    assert flow.projected_margin == Decimal("150")


def test_invalid_transition_is_rejected():
    flow = ConstructionFlow(uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), ContractMode.RENT, Decimal("1"), Decimal("2"), Decimal("10"))
    with pytest.raises(ValueError):
        flow.contract()
