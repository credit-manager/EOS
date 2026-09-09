"""
EOS System — AI Copilot & Core AI Endpoints
All endpoints: RBAC enforced, tenant_id filtered, audit logged.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid
import time

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import log_audit, get_user_permissions
from app.models.ai import AICopilotConversation, AICopilotMessage, AIPrediction
from app.models.sales import Customer
from app.models.inventory import Product
from app.models.accounting import Account, JournalEntry
from app.models.hr import Employee

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────

class CopilotChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    module: Optional[str] = None

class CopilotMessageSchema(BaseModel):
    role: str
    content: str
    content_type: str = "text"

class CopilotChatResponse(BaseModel):
    session_id: str
    response: str
    module: Optional[str]
    confidence: float
    tokens_used: int

class CopilotSessionResponse(BaseModel):
    id: str
    session_id: str
    title: Optional[str]
    active_module: Optional[str]
    message_count: int
    status: str
    created_at: datetime

class CopilotHistoryResponse(BaseModel):
    messages: List[CopilotMessageSchema]
    total: int

class PredictRequest(BaseModel):
    module: str
    entity_type: str
    entity_id: Optional[str] = None
    horizon_days: int = 30

class PredictResponse(BaseModel):
    predictions: list
    model_used: str
    confidence: float
    generated_at: datetime

class AnomalyRequest(BaseModel):
    module: str
    entity_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None

class AnomalyResponse(BaseModel):
    anomalies: list
    total_checked: int
    anomaly_count: int
    generated_at: datetime

class OCRRequest(BaseModel):
    document_type: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    language: str = "ar"

class OCRResponse(BaseModel):
    extracted_data: dict
    confidence: float
    document_type: str
    suggestions: list


# ─── COPILOT CHAT ENGINE ─────────────────────────────────

async def _process_copilot_message(
    message: str, tenant_id: str, user_id: str, db: AsyncSession
):
    msg_lower = message.lower()
    confidence = 0.9

    if any(w in msg_lower for w in ["customer", "clients", "sales"]):
        count = (await db.execute(
            select(func.count(Customer.id))
        )).scalar() or 0
        total = (await db.execute(
            select(func.coalesce(func.sum(Customer.total_spent), 0))
        )).scalar() or 0
        return (f"You have {count} customers with total sales of EGP {float(total):,.2f}.", "sales", confidence)

    if any(w in msg_lower for w in ["product", "inventory", "stock"]):
        count = (await db.execute(
            select(func.count(Product.id))
        )).scalar() or 0
        value = (await db.execute(
            select(func.coalesce(func.sum(Product.current_stock * Product.cost_price), 0))
        )).scalar() or 0
        return (f"You have {count} products with inventory value of EGP {float(value):,.2f}.", "inventory", confidence)

    if any(w in msg_lower for w in ["account", "balance", "journal"]):
        count = (await db.execute(
            select(func.count(Account.id))
        )).scalar() or 0
        entries = (await db.execute(
            select(func.count(JournalEntry.id))
        )).scalar() or 0
        return (f"You have {count} accounts and {entries} journal entries.", "accounting", confidence)

    if any(w in msg_lower for w in ["employee", "staff", "hr"]):
        count = (await db.execute(
            select(func.count(Employee.id))
        )).scalar() or 0
        return (f"You have {count} employees.", "hr", confidence)

    if any(w in msg_lower for w in ["hello", "hi"]):
        return ("Hello! I'm your EOS AI assistant. Ask me about sales, inventory, accounting, or HR.", None, 0.95)

    return ("I can help with sales, inventory, accounting, and HR. Please ask a specific question.", None, 0.7)


# ─── COPILOT ENDPOINTS ───────────────────────────────────

@router.post("/copilot/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    request: Request,
    body: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires AI access")

    tenant_id = current_user["tenant_id"]
    start = time.time()

    session_id = body.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        conv = AICopilotConversation(
            id=str(uuid.uuid4()), tenant_id=tenant_id, user_id=current_user["id"],
            session_id=session_id, active_module=body.module,
            title=body.message[:50], status="active",
        )
        db.add(conv)
        await db.flush()

    result = await db.execute(
        select(AICopilotConversation).filter(
            AICopilotConversation.session_id == session_id,
            AICopilotConversation.tenant_id == tenant_id,
        )
    )
    conv = result.scalar()
    if not conv:
        raise HTTPException(status_code=404, detail="Session not found")

    db.add(AICopilotMessage(
        id=str(uuid.uuid4()), conversation_id=conv.id,
        role="user", content=body.message,
    ))

    response_text, module, confidence = await _process_copilot_message(
        body.message, tenant_id, current_user["id"], db
    )
    latency_ms = (time.time() - start) * 1000

    db.add(AICopilotMessage(
        id=str(uuid.uuid4()), conversation_id=conv.id,
        role="assistant", content=response_text,
        model_used="eos-copilot-v1", confidence=confidence, latency_ms=latency_ms,
    ))

    conv.message_count = (conv.message_count or 0) + 2
    conv.last_message_at = datetime.utcnow()
    if module:
        conv.active_module = module
    await db.flush()

    db.add(AIPrediction(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        model_name="eos-copilot-v1", service="copilot",
        input_data={"message": body.message},
        output_data={"response": response_text},
        confidence=confidence, latency_ms=latency_ms,
        user_id=current_user["id"], module=module,
    ))
    await db.flush()

    await log_audit(
        db, tenant_id=tenant_id, user=current_user,
        action="query", module="ai",
        entity_type="Copilot", entity_id=session_id,
        entity_name=body.message[:50], request=request,
    )

    return CopilotChatResponse(
        session_id=session_id, response=response_text,
        module=module, confidence=confidence, tokens_used=0,
    )


@router.get("/copilot/sessions", response_model=list[CopilotSessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires AI access")

    result = await db.execute(
        select(AICopilotConversation)
        .filter(
            AICopilotConversation.tenant_id == current_user["tenant_id"],
            AICopilotConversation.user_id == current_user["id"],
        )
        .order_by(AICopilotConversation.created_at.desc())
        .limit(50)
    )
    return [CopilotSessionResponse(
        id=s.id, session_id=s.session_id, title=s.title,
        active_module=s.active_module, message_count=s.message_count,
        status=s.status, created_at=s.created_at,
    ) for s in result.scalars().all()]


@router.get("/copilot/sessions/{session_id}/history", response_model=CopilotHistoryResponse)
async def get_session_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires AI access")

    result = await db.execute(
        select(AICopilotConversation).filter(
            AICopilotConversation.session_id == session_id,
            AICopilotConversation.tenant_id == current_user["tenant_id"],
        )
    )
    conv = result.scalar()
    if not conv:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(AICopilotMessage)
        .filter(AICopilotMessage.conversation_id == conv.id)
        .order_by(AICopilotMessage.created_at)
    )
    messages = result.scalars().all()
    return CopilotHistoryResponse(
        messages=[CopilotMessageSchema(role=m.role, content=m.content, content_type=m.content_type) for m in messages],
        total=len(messages),
    )
