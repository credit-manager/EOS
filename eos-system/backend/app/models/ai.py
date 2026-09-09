"""
EOS System — AI Models (Model Registry, Predictions, Training Data, Performance, Usage, Copilot)
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class AIModel(Base):
    """AI Model Registry — tracks all registered models."""

    __tablename__ = "ai_models"

    id = Column(String(36), primary_key=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(20), nullable=False)
    model_type = Column(String(50), nullable=False)  # classification, forecast, anomaly, ocr, copilot
    domain = Column(String(50), nullable=False)  # accounting, inventory, sales, hr, crm
    status = Column(String(20), default="development", index=True)  # development, staging, production, archived
    metrics = Column(JSON, default={})
    hyperparameters = Column(JSON, default={})
    training_data_size = Column(Integer)
    inference_latency_ms = Column(Float)
    description = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_type": self.model_type,
            "domain": self.domain,
            "status": self.status,
            "metrics": self.metrics,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AIPrediction(Base):
    """AI Prediction Log — every prediction is recorded for audit."""

    __tablename__ = "ai_predictions"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    model_id = Column(String(36), ForeignKey("ai_models.id"))
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(20))
    service = Column(String(50), nullable=False, index=True)  # copilot, classify, predict, detect, ocr
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=False)
    confidence = Column(Float)
    latency_ms = Column(Float)
    user_id = Column(String(36), ForeignKey("users.id"))
    module = Column(String(50))  # accounting, inventory, sales, hr
    entity_type = Column(String(50))
    entity_id = Column(String(36))
    tokens_used = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0)
    user_feedback = Column(String(20))  # correct, incorrect, partial
    feedback_notes = Column(Text)
    corrected_output = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "model_name": self.model_name,
            "service": self.service,
            "module": self.module,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AICopilotConversation(Base):
    """Copilot Conversation — tracks chat sessions."""

    __tablename__ = "ai_copilot_conversations"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(100), unique=True, nullable=False)
    title = Column(String(255))
    active_module = Column(String(50))
    context_data = Column(JSON, default={})
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0)
    status = Column(String(20), default="active", index=True)  # active, closed, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "title": self.title,
            "active_module": self.active_module,
            "message_count": self.message_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AICopilotMessage(Base):
    """Copilot Message — individual messages in a conversation."""

    __tablename__ = "ai_copilot_messages"

    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("ai_copilot_conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    content_type = Column(String(20), default="text")  # text, markdown, json
    tool_calls = Column(JSON)
    model_used = Column(String(100))
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    latency_ms = Column(Float)
    confidence = Column(Float)
    user_feedback = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "content_type": self.content_type,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AITenantUsage(Base):
    """Tenant AI Usage — tracks usage per tenant per day."""

    __tablename__ = "ai_tenant_usage"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    usage_date = Column(Date, nullable=False)
    total_requests = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0)
    copilot_requests = Column(Integer, default=0)
    classify_requests = Column(Integer, default=0)
    predict_requests = Column(Integer, default=0)
    detect_requests = Column(Integer, default=0)
    ocr_documents = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "usage_date": self.usage_date.isoformat() if self.usage_date else None,
            "total_requests": self.total_requests,
            "total_cost_usd": self.total_cost_usd,
        }


class AITrainingData(Base):
    """AI Training Data — stores validated training examples per tenant."""

    __tablename__ = "ai_training_data"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    input_text = Column(Text, nullable=False)
    expected_output = Column(JSON, nullable=False)
    source = Column(String(50))  # user_feedback, system_generated, manual
    source_entity_type = Column(String(50))
    source_entity_id = Column(String(36))
    quality_score = Column(Float)  # 0-1
    validated = Column(Boolean, default=False)
    validated_by = Column(String(36), ForeignKey("users.id"))
    validated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "model_name": self.model_name,
            "input_text": self.input_text[:100],
            "source": self.source,
            "validated": self.validated,
            "quality_score": self.quality_score,
        }
