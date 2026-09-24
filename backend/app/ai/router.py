import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..db import get_db
from ..tenant import require_admin, require_tenant
from .models import AIAgent, AIAgentExecution, AILLMConfig, AITool
from .schemas import (
    AgentDefinition,
    AgentExecutionRequest,
    AgentExecutionResponse,
    AgentResponse,
    AgentSummary,
    LLMConfigDefinition,
    LLMConfigResponse,
    ToolDefinition,
    ToolResponse,
    ToolSummary,
)
from .service import AIService, tool_registry
from .governance.service import AIGovernanceService
from .governance.policies import PolicyViolationError

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


def _parse_json(json_str: str | None, default=None):
    """Parse JSON safely"""
    if not json_str:
        return default
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def _agent_response(row: AIAgent) -> AgentResponse:
    """Convert agent model to response"""
    return AgentResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        code=row.code,
        name=row.name,
        description=row.description,
        agent_type=row.agent_type,
        enabled=row.enabled,
        config=_parse_json(row.config_json, {}),
        tools=_parse_json(row.tools_json, []),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _tool_response(row: AITool) -> ToolResponse:
    """Convert tool model to response"""
    return ToolResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        code=row.code,
        name=row.name,
        description=row.description,
        tool_type=row.tool_type,
        enabled=row.enabled,
        config=_parse_json(row.config_json, {}),
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# AI Workforce - Agent endpoints
# ---------------------------------------------------------------------------

@router.get("/agents", response_model=list[AgentSummary])
def list_agents(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[AgentSummary]:
    """List all AI agents"""
    rows = db.scalars(
        select(AIAgent).where(AIAgent.tenant_id == tenant_id)
    ).all()

    return [
        AgentSummary(
            id=row.id,
            code=row.code,
            name=row.name,
            agent_type=row.agent_type,
            enabled=row.enabled,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/agents", response_model=AgentResponse, status_code=201)
def create_agent(
    payload: AgentDefinition,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AgentResponse:
    """Create a new AI agent"""
    # Check if code exists
    existing = db.scalar(
        select(AIAgent).where(
            AIAgent.tenant_id == tenant_id,
            AIAgent.code == payload.code,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="agent code already exists")

    row = AIAgent(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        agent_type=payload.agent_type,
        enabled=payload.enabled,
        config_json=payload.config.model_dump_json(),
        tools_json=json.dumps(payload.tools) if payload.tools else None,
    )
    db.add(row)

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="ai.agent.created",
        resource_type="ai_agent",
        resource_id=row.id,
        metadata={"code": payload.code, "name": payload.name},
        request_id=request.state.request_id,
    )

    db.commit()
    db.refresh(row)
    return _agent_response(row)


@router.get("/agents/{agent_code}", response_model=AgentResponse)
def get_agent(
    agent_code: str,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> AgentResponse:
    """Get an AI agent by code"""
    row = db.scalar(
        select(AIAgent).where(
            AIAgent.tenant_id == tenant_id,
            AIAgent.code == agent_code,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return _agent_response(row)


@router.post("/agents/execute", response_model=AgentExecutionResponse)
def execute_agent(
    payload: AgentExecutionRequest,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> AgentExecutionResponse:
    """Execute an AI agent with governance checks."""
    import time
    start = time.monotonic()

    # Resolve agent type for governance check
    from .models import AIAgent
    agent_row = db.scalar(
        select(AIAgent).where(
            AIAgent.tenant_id == tenant_id,
            AIAgent.code == payload.agent_code,
        )
    )
    agent_type = agent_row.agent_type if agent_row else "general"

    # --- Governance pre-execution check ---
    governance = AIGovernanceService(db, tenant_id)
    try:
        gov_result = governance.pre_execution_check(
            agent_code=payload.agent_code,
            agent_type=agent_type,
            action=payload.action or "run_agent",
            input_data=payload.input_data,
        )
    except PolicyViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if gov_result.requires_approval:
        return AgentExecutionResponse(
            id=UUID(),
            agent_code=payload.agent_code,
            status="escalated",
            output=None,
            error=gov_result.escalation_reason,
            execution_time_ms=0,
            created_at=None,
        )

    # --- Execute agent ---
    service = AIService(db, tenant_id)
    try:
        result = service.execute_agent(
            agent_code=payload.agent_code,
            input_data=payload.input_data,
            context=payload.context,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    elapsed_ms = int((time.monotonic() - start) * 1000)

    # --- Governance post-execution log ---
    governance.post_execution_log(
        agent_code=payload.agent_code,
        agent_type=agent_type,
        action=payload.action or "run_agent",
        result=result,
        execution_time_ms=elapsed_ms,
    )

    return AgentExecutionResponse(
        id=UUID(result["id"]) if result.get("id") else UUID(),
        agent_code=result["agent_code"],
        status=result["status"],
        output=result.get("output"),
        error=result.get("error"),
        execution_time_ms=result.get("execution_time_ms"),
        created_at=None,
    )


@router.get("/agents/{agent_code}/executions", response_model=list[AgentExecutionResponse])
def list_agent_executions(
    agent_code: str,
    request: Request,
    limit: int = 50,
    offset: int = 0,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[AgentExecutionResponse]:
    """List agent execution history"""
    # Verify agent exists
    agent = db.scalar(
        select(AIAgent).where(
            AIAgent.tenant_id == tenant_id,
            AIAgent.code == agent_code,
        )
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")

    rows = db.scalars(
        select(AIAgentExecution)
        .where(
            AIAgentExecution.tenant_id == tenant_id,
            AIAgentExecution.agent_code == agent_code,
        )
        .order_by(AIAgentExecution.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return [
        AgentExecutionResponse(
            id=row.id,
            agent_code=row.agent_code,
            status=row.status,
            output=_parse_json(row.output_json),
            error=row.error_message,
            execution_time_ms=row.execution_time_ms,
            created_at=row.created_at,
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# AI Workforce - Tool endpoints
# ---------------------------------------------------------------------------

@router.get("/tools", response_model=list[ToolSummary])
def list_tools(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[ToolSummary]:
    """List all AI tools"""
    rows = db.scalars(
        select(AITool).where(AITool.tenant_id == tenant_id)
    ).all()

    return [
        ToolSummary(
            id=row.id,
            code=row.code,
            name=row.name,
            tool_type=row.tool_type,
            enabled=row.enabled,
        )
        for row in rows
    ]


@router.post("/tools", response_model=ToolResponse, status_code=201)
def create_tool(
    payload: ToolDefinition,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ToolResponse:
    """Create a new AI tool"""
    # Check if code exists
    existing = db.scalar(
        select(AITool).where(
            AITool.tenant_id == tenant_id,
            AITool.code == payload.code,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="tool code already exists")

    row = AITool(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        tool_type=payload.tool_type,
        enabled=payload.enabled,
        config_json=payload.config.model_dump_json(),
    )
    db.add(row)

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="ai.tool.created",
        resource_type="ai_tool",
        resource_id=row.id,
        metadata={"code": payload.code, "name": payload.name},
        request_id=request.state.request_id,
    )

    db.commit()
    db.refresh(row)
    return _tool_response(row)


# ---------------------------------------------------------------------------
# AI Workforce - LLM Config endpoints
# ---------------------------------------------------------------------------

@router.get("/llm-configs", response_model=list[LLMConfigResponse])
def list_llm_configs(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[LLMConfigResponse]:
    """List LLM configurations"""
    rows = db.scalars(
        select(AILLMConfig).where(AILLMConfig.tenant_id == tenant_id)
    ).all()

    return [
        LLMConfigResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            provider=row.provider,
            model=row.model,
            base_url=row.base_url,
            is_default=row.is_default,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/llm-configs", response_model=LLMConfigResponse, status_code=201)
def create_llm_config(
    payload: LLMConfigDefinition,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> LLMConfigResponse:
    """Create a new LLM configuration"""
    row = AILLMConfig(
        tenant_id=tenant_id,
        provider=payload.provider,
        model=payload.model,
        api_key_encrypted=payload.api_key,  # Would encrypt in production
        base_url=payload.base_url,
        config_json=json.dumps(payload.config) if payload.config else None,
        is_default=payload.is_default,
    )
    db.add(row)

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="ai.llm_config.created",
        resource_type="ai_llm_config",
        resource_id=row.id,
        metadata={"provider": payload.provider, "model": payload.model},
        request_id=request.state.request_id,
    )

    db.commit()
    db.refresh(row)

    return LLMConfigResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        provider=row.provider,
        model=row.model,
        base_url=row.base_url,
        is_default=row.is_default,
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# AI Workforce - Registered tools endpoint
# ---------------------------------------------------------------------------

@router.get("/registered-tools")
def list_registered_tools(
    request: Request,
) -> dict:
    """List all registered tool handlers with their permissions."""
    tools = []
    for code in tool_registry.list_tools():
        handler = tool_registry.get_handler(code)
        tools.append({
            "code": code,
            "name": handler.__doc__ or code if handler else code,
            "module": handler.__module__ if handler else "",
        })
    return {"tools": tools}


# ---------------------------------------------------------------------------
# Ask EOS - Natural Language Query Engine (Tool-powered)
# ---------------------------------------------------------------------------

class AskEOSRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    context: dict | None = None


class AskEOSResponse(BaseModel):
    answer: str
    intent: str
    sources: list[dict]
    suggestions: list[str]
    confidence: float


def _classify_intent(query: str) -> tuple[str, list[str]]:
    """Classify user intent and route to appropriate tool."""
    q = query.lower()

    # Financial intents - enhanced
    if any(w in q for w in ['trial balance', 'balances', 'ledger']):
        return 'finance', ['get_financial_summary']
    if any(w in q for w in ['profit and loss', 'p&l', 'income statement', 'net income', 'revenue', 'expenses']):
        return 'profit_loss', ['get_financial_summary']
    if any(w in q for w in ['balance sheet', 'assets', 'liabilities', 'equity']):
        return 'balance_sheet', ['get_financial_summary']
    if any(w in q for w in ['ar aging', 'accounts receivable', 'receivable', 'outstanding invoices', 'overdue invoices', 'overdue bills']):
        return 'ar_aging', ['get_financial_summary']
    if any(w in q for w in ['ap aging', 'accounts payable', 'payable', 'unpaid bills']):
        return 'ap_aging', ['get_financial_summary']
    if any(w in q for w in ['cash flow', 'cash position', 'bank balance']):
        return 'cash_flow', ['get_financial_summary']
    if any(w in q for w in ['budget', 'utilization', 'spending']):
        return 'budget', ['get_project_health']
    if any(w in q for w in ['payment', 'payments made', 'payments received']):
        return 'payments', ['get_financial_summary']
    if any(w in q for w in ['invoice', 'invoices']):
        return 'invoices', ['get_financial_summary']
    if any(w in q for w in ['bill', 'bills']):
        return 'bills', ['get_financial_summary']

    # Procurement intents
    if any(w in q for w in ['supplier', 'vendor', 'purchase order', 'procurement']):
        return 'procurement', ['get_procurement_analysis']
    if any(w in q for w in ['pending order', 'open order', 'draft order']):
        return 'pending_orders', ['get_procurement_analysis']

    # Project intents
    if any(w in q for w in ['project', 'risk', 'over budget', 'behind']):
        return 'project_risk', ['get_project_health']
    if any(w in q for w in ['project health', 'project status', 'portfolio']):
        return 'project_overview', ['get_project_health']

    # Workflow intents
    if any(w in q for w in ['approve', 'pending', 'waiting', 'approval']):
        return 'approvals', ['get_workflow_status']

    # Event intents
    if any(w in q for w in ['recent', 'events', 'activity', 'log']):
        return 'events', ['get_recent_events']

    # Search intents
    if any(w in q for w in ['show', 'list', 'find', 'get', 'search']):
        entity = None
        for e in ['project', 'contract', 'invoice', 'order', 'supplier', 'customer', 'employee']:
            if e in q:
                entity = e
                break
        return 'search', ['search_records']

    # Aggregate
    if any(w in q for w in ['count', 'how many', 'total', 'sum']):
        return 'aggregate', ['aggregate_records']

    # Executive summary
    if any(w in q for w in ['summary', 'overview', 'status', 'health', 'dashboard']):
        return 'executive_summary', ['get_financial_summary', 'get_project_health', 'get_procurement_analysis', 'get_workflow_status']

    return 'general', []


@router.post("/ask", response_model=AskEOSResponse)
def ask_eos(
    payload: AskEOSRequest,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> AskEOSResponse:
    """Ask EOS a natural language question about your business data."""
    intent, tool_codes = _classify_intent(payload.query)

    agent_context = {"db": db, "tenant_id": str(tenant_id)}

    answer = ""
    sources: list[dict] = []
    confidence = 0.5

    if intent == 'finance' and 'get_financial_summary' in tool_codes:
        result = tool_registry.execute('get_financial_summary', {}, agent_context)
        accounts = result.get('accounts', [])
        answer = (
            f"Financial Summary:\n"
            f"  Accounts: {result['total_accounts']}\n"
            f"  Total Debits: {result['total_debit']:,}\n"
            f"  Total Credits: {result['total_credit']:,}\n"
            f"  Balanced: {'Yes' if result['is_balanced'] else 'No'}\n"
            f"  Posted Entries: {result['posted_entries']}"
        )
        sources = [{'type': 'financial', 'data': result}]
        confidence = 0.9

    elif intent == 'profit_loss':
        from ..financial.service import get_profit_and_loss
        pnl = get_profit_and_loss(db, tenant_id)
        answer = (
            f"Profit & Loss Statement:\n"
            f"\n  Revenue: {pnl['currency']} {pnl['revenue']['total']:,.2f}"
        )
        for line in pnl['revenue']['lines']:
            answer += f"\n    - {line['name']}: {line['balance']:,.2f}"
        answer += f"\n\n  Expenses: {pnl['currency']} {pnl['expense']['total']:,.2f}"
        for line in pnl['expense']['lines']:
            answer += f"\n    - {line['name']}: {line['balance']:,.2f}"
        answer += f"\n\n  Net Income: {pnl['currency']} {pnl['net_income']:,.2f}"
        if pnl['net_income'] < 0:
            answer += " (LOSS)"
        sources = [{'type': 'profit_loss', 'data': pnl}]
        confidence = 0.95

    elif intent == 'balance_sheet':
        from ..financial.service import get_balance_sheet
        bs = get_balance_sheet(db, tenant_id)
        answer = (
            f"Balance Sheet:\n"
            f"\n  Assets: {bs['currency']} {bs['assets']['total']:,.2f}"
        )
        for line in bs['assets']['lines']:
            answer += f"\n    - {line['name']}: {line['balance']:,.2f}"
        answer += f"\n\n  Liabilities: {bs['currency']} {bs['liabilities']['total']:,.2f}"
        for line in bs['liabilities']['lines']:
            answer += f"\n    - {line['name']}: {line['balance']:,.2f}"
        answer += f"\n\n  Equity: {bs['currency']} {bs['equity']['total']:,.2f}"
        answer += f"\n\n  Balanced: {'Yes' if bs['is_balanced'] else 'NO - needs attention'}"
        sources = [{'type': 'balance_sheet', 'data': bs}]
        confidence = 0.95

    elif intent == 'ar_aging':
        from ..financial.service import get_ar_aging
        from ..financial.models import Invoice
        aging = get_ar_aging(db, tenant_id)
        overdue = db.scalars(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(['sent', 'overdue']),
                Invoice.balance_due > 0,
            )
        ).all()
        answer = f"Accounts Receivable Aging:\n"
        for bucket, amount in aging['buckets'].items():
            label = bucket.replace('_', '-').replace('one-thirty', '1-30').replace('thirty-one-sixty', '31-60').replace('sixty-one-ninety', '61-90').replace('over-ninety', '90+')
            answer += f"\n  {label}: {amount:,.2f}"
        answer += f"\n\n  Total Outstanding: {aging['total_outstanding']:,.2f}"
        if overdue:
            answer += f"\n\n  Overdue Invoices ({len(overdue)}):"
            for inv in overdue[:5]:
                answer += f"\n    - {inv.invoice_number}: {inv.balance_due:,.2f} (due {inv.due_date})"
        sources = [{'type': 'ar_aging', 'data': aging}]
        confidence = 0.95

    elif intent == 'ap_aging':
        from ..financial.service import get_ap_aging
        from ..financial.models import Bill
        aging = get_ap_aging(db, tenant_id)
        overdue = db.scalars(
            select(Bill).where(
                Bill.tenant_id == tenant_id,
                Bill.status.in_(['received', 'overdue']),
                Bill.balance_due > 0,
            )
        ).all()
        answer = f"Accounts Payable Aging:\n"
        for bucket, amount in aging['buckets'].items():
            label = bucket.replace('_', '-').replace('one-thirty', '1-30').replace('thirty-one-sixty', '31-60').replace('sixty-one-ninety', '61-90').replace('over-ninety', '90+')
            answer += f"\n  {label}: {amount:,.2f}"
        answer += f"\n\n  Total Outstanding: {aging['total_outstanding']:,.2f}"
        if overdue:
            answer += f"\n\n  Overdue Bills ({len(overdue)}):"
            for bill in overdue[:5]:
                answer += f"\n    - {bill.bill_number}: {bill.balance_due:,.2f} (due {bill.due_date})"
        sources = [{'type': 'ap_aging', 'data': aging}]
        confidence = 0.95

    elif intent == 'invoices':
        from ..financial.models import Invoice, Customer
        invoices = db.scalars(
            select(Invoice).where(Invoice.tenant_id == tenant_id).order_by(Invoice.issue_date.desc())
        ).all()
        total_outstanding = sum(i.balance_due for i in invoices)
        overdue = [i for i in invoices if i.status in ('sent', 'overdue') and i.balance_due > 0]
        answer = f"Invoices Summary:\n"
        answer += f"\n  Total Invoices: {len(invoices)}"
        answer += f"\n  Total Outstanding: {total_outstanding:,.2f}"
        answer += f"\n  Overdue: {len(overdue)}"
        if invoices:
            answer += "\n\n  Recent Invoices:"
            for inv in invoices[:5]:
                customer = db.get(Customer, inv.customer_id)
                cname = customer.name if customer else 'Unknown'
                answer += f"\n    - {inv.invoice_number}: {inv.total_amount:,.2f} ({cname}) [{inv.status}]"
        sources = [{'type': 'invoices', 'data': {'count': len(invoices), 'outstanding': total_outstanding}}]
        confidence = 0.9

    elif intent == 'bills':
        from ..financial.models import Bill, Supplier
        bills = db.scalars(
            select(Bill).where(Bill.tenant_id == tenant_id).order_by(Bill.issue_date.desc())
        ).all()
        total_outstanding = sum(b.balance_due for b in bills)
        overdue = [b for b in bills if b.status in ('received', 'overdue') and b.balance_due > 0]
        answer = f"Bills Summary:\n"
        answer += f"\n  Total Bills: {len(bills)}"
        answer += f"\n  Total Outstanding: {total_outstanding:,.2f}"
        answer += f"\n  Overdue: {len(overdue)}"
        if bills:
            answer += "\n\n  Recent Bills:"
            for bill in bills[:5]:
                supplier = db.get(Supplier, bill.supplier_id)
                sname = supplier.name if supplier else 'Unknown'
                answer += f"\n    - {bill.bill_number}: {bill.total_amount:,.2f} ({sname}) [{bill.status}]"
        sources = [{'type': 'bills', 'data': {'count': len(bills), 'outstanding': total_outstanding}}]
        confidence = 0.9

    elif intent == 'payments':
        from ..financial.models import Payment
        payments = db.scalars(
            select(Payment).where(Payment.tenant_id == tenant_id).order_by(Payment.payment_date.desc())
        ).all()
        total_paid = sum(p.amount for p in payments if p.status == 'completed')
        answer = f"Payments Summary:\n"
        answer += f"\n  Total Payments: {len(payments)}"
        answer += f"\n  Total Paid: {total_paid:,.2f}"
        if payments:
            answer += "\n\n  Recent Payments:"
            for p in payments[:5]:
                answer += f"\n    - {p.payment_number}: {p.amount:,.2f} ({p.payment_type}) [{p.status}]"
        sources = [{'type': 'payments', 'data': {'count': len(payments), 'total': total_paid}}]
        confidence = 0.9

    elif intent == 'budget' and 'get_project_health' in tool_codes:
        result = tool_registry.execute('get_project_health', {}, agent_context)
        at_risk = result.get('at_risk', [])
        answer = (
            f"Budget Analysis:\n"
            f"  Projects: {result['total_projects']}\n"
            f"  At Risk: {len(at_risk)}"
        )
        if at_risk:
            answer += "\n\nAt Risk Projects:"
            for p in at_risk:
                answer += f"\n  - {p['name']}: {p['utilization_pct']}% [{p['risk_level']}]"
        sources = [{'type': 'budget', 'data': result}]
        confidence = 0.85

    elif intent == 'procurement' and 'get_procurement_analysis' in tool_codes:
        result = tool_registry.execute('get_procurement_analysis', {}, agent_context)
        answer = (
            f"Procurement Overview:\n"
            f"  Total: {result['total_procurements']}\n"
            f"  Pending: {result['pending_count']}\n"
            f"  Total Value: {result['total_value']:,}\n"
            f"  Suppliers: {len(result['suppliers'])}"
        )
        sources = [{'type': 'procurement', 'data': result}]
        confidence = 0.85

    elif intent in ('project_risk', 'project_overview') and 'get_project_health' in tool_codes:
        result = tool_registry.execute('get_project_health', {}, agent_context)
        at_risk = result.get('at_risk', [])
        answer = f"Project Health: {result['total_projects']} projects, {len(at_risk)} at risk."
        if at_risk:
            answer += "\n\nAt Risk:"
            for p in at_risk:
                answer += f"\n  - {p['name']}: {p['utilization_pct']}% [{p['risk_level']}]"
        sources = [{'type': 'projects', 'data': result}]
        confidence = 0.85

    elif intent == 'approvals' and 'get_workflow_status' in tool_codes:
        result = tool_registry.execute('get_workflow_status', {}, agent_context)
        approvals = result.get('approvals', [])
        answer = f"Pending Approvals: {result['pending_approvals']}"
        if approvals:
            answer += "\n\nRecent:"
            for a in approvals[:5]:
                answer += f"\n  - {a['action']} (assigned: {a['assigned_to']})"
        sources = [{'type': 'approvals', 'data': result}]
        confidence = 0.85

    elif intent == 'executive_summary':
        fin = tool_registry.execute('get_financial_summary', {}, agent_context)
        proj = tool_registry.execute('get_project_health', {}, agent_context)
        proc = tool_registry.execute('get_procurement_analysis', {}, agent_context)
        wf = tool_registry.execute('get_workflow_status', {}, agent_context)
        answer = (
            f"Business Health Dashboard:\n"
            f"\n  Financial: {fin['total_accounts']} accounts, Dr {fin['total_debit']:,} | Cr {fin['total_credit']:,}"
            f"\n  Projects: {proj['total_projects']} total, {len(proj.get('at_risk', []))} at risk"
            f"\n  Procurement: {proc['total_procurements']} orders, {proc['pending_count']} pending"
            f"\n  Approvals: {wf['pending_approvals']} pending"
        )
        sources = [
            {'type': 'financial', 'data': fin},
            {'type': 'projects', 'data': proj},
            {'type': 'procurement', 'data': proc},
            {'type': 'workflow', 'data': wf},
        ]
        confidence = 0.9

    elif intent == 'search' and 'search_records' in tool_codes:
        entity = None
        for e in ['project', 'contract', 'invoice', 'order', 'supplier', 'customer', 'employee']:
            if e in payload.query.lower():
                entity = e
                break
        result = tool_registry.execute('search_records', {'entity_code': entity}, agent_context)
        count = result.get('count', 0)
        items = result.get('results', [])
        answer = f"Found {count} {entity or 'record'}(s)." if count else f"No {entity or 'records'} found."
        if items:
            answer += "\n" + "\n".join(f"  - {i['title']} ({i['entity_code']})" for i in items[:10])
        sources = [{'type': 'search', 'data': result}]
        confidence = 0.8 if count else 0.3

    elif intent == 'aggregate' and 'aggregate_records' in tool_codes:
        result = tool_registry.execute('aggregate_records', {}, agent_context)
        agg = result.get('aggregation', {})
        lines = [f"  {k}: {v}" for k, v in sorted(agg.items(), key=lambda x: -x[1])]
        answer = f"Record Counts ({result['total']} total):\n" + "\n".join(lines)
        sources = [{'type': 'aggregate', 'data': result}]
        confidence = 0.9

    else:
        result = tool_registry.execute('aggregate_records', {}, agent_context)
        agg = result.get('aggregation', {})
        answer = (
            f"I can help you with:\n"
            f"  - Financial queries (trial balance, accounts, cash flow)\n"
            f"  - Project health and budget analysis\n"
            f"  - Procurement and supplier data\n"
            f"  - Workflow approvals\n"
            f"  - Record search and aggregation\n\n"
            f"Your business has {result['total']} records across {len(agg)} entity types."
        )
        sources = [{'type': 'help', 'data': agg}]
        confidence = 0.5

    suggestions = []
    if intent != 'executive_summary':
        suggestions.append("Give me a business health summary")
    if intent != 'finance':
        suggestions.append("Show me the trial balance")
    if intent != 'project_risk':
        suggestions.append("Which projects are at risk?")
    if intent != 'procurement':
        suggestions.append("Show pending procurements")
    suggestions.append("What needs my attention?")

    return AskEOSResponse(
        answer=answer,
        intent=intent,
        sources=sources,
        suggestions=suggestions,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# LLM-powered Copilot Chat
# ---------------------------------------------------------------------------

from .llm.clients import get_llm_client


class CopilotChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    agent_type: str = "executive"


class CopilotChatResponse(BaseModel):
    reply: str
    agent: str
    agent_name: str = "Executive Agent"
    model_used: str = "rule-based"
    intent: str = "query"
    entities: list[str] = Field(default_factory=list)
    actions_taken: list[dict] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    compliant: bool = True


@router.post("/copilot/chat", response_model=CopilotChatResponse)
def copilot_chat(
    payload: CopilotChatRequest,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Ask EOS — intelligent copilot with intent understanding, data retrieval, and analysis."""
    from .copilot.engine import AskEOSEngine

    engine = AskEOSEngine(db=db, tenant_id=tenant_id)

    result = engine.process(
        message=payload.message,
        context={"agent_type": payload.agent_type},
        history=payload.history,
    )

    from .llm.clients import get_llm_client
    llm = get_llm_client("openai", {})

    return CopilotChatResponse(
        reply=result["response"],
        agent=result["agent"],
        agent_name=result["agent_name"],
        model_used="llm" if llm.is_available() else "rule-based",
        intent=result["intent"],
        entities=result["entities"],
        actions_taken=result["actions_taken"],
        suggestions=result["suggestions"],
        sources=result["sources"],
        insights=result["insights"],
        risks=result["risks"],
        compliant=result["compliant"],
    )
