"""Document Intelligence models."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from ..db import Base


class DocumentStatus(enum.StrEnum):
    uploaded = "uploaded"
    processing = "processing"
    processed = "processed"
    failed = "failed"
    archived = "archived"


class DocumentType(enum.StrEnum):
    pdf = "pdf"
    image = "image"
    excel = "excel"
    word = "word"
    email = "email"
    other = "other"


class DocumentCategory(enum.StrEnum):
    invoice = "invoice"
    receipt = "receipt"
    contract = "contract"
    purchase_order = "purchase_order"
    goods_received = "goods_received"
    bank_statement = "bank_statement"
    email = "email"
    report = "report"
    other = "other"


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(200), nullable=False)
    document_type = Column(String(20), nullable=False, default=DocumentType.other.value)
    category = Column(String(50), nullable=False, default=DocumentCategory.other.value)
    status = Column(String(20), nullable=False, default=DocumentStatus.uploaded.value)

    storage_path = Column(String(1000), nullable=False)
    storage_backend = Column(String(50), nullable=False, default="local")
    checksum_sha256 = Column(String(64), nullable=True)

    extracted_data = Column(JSON, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    extraction_method = Column(String(50), nullable=True)
    extraction_error = Column(Text, nullable=True)

    ocr_text = Column(Text, nullable=True)
    ocr_language = Column(String(10), nullable=True)
    ocr_confidence = Column(Float, nullable=True)

    extracted_tables = Column(JSON, nullable=True)
    extracted_key_values = Column(JSON, nullable=True)

    classification = Column(String(50), nullable=True)
    classification_confidence = Column(Float, nullable=True)
    classification_label = Column(String(200), nullable=True)

    linked_entity_type = Column(String(100), nullable=True)
    linked_entity_id = Column(String(36), nullable=True)

    metadata_json = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)

    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class DocumentField(Base):
    __tablename__ = "document_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)

    field_name = Column(String(200), nullable=False)
    field_value = Column(Text, nullable=True)
    field_type = Column(String(50), nullable=False, default="text")
    confidence = Column(Float, nullable=True)
    bbox_x = Column(Float, nullable=True)
    bbox_y = Column(Float, nullable=True)
    bbox_width = Column(Float, nullable=True)
    bbox_height = Column(Float, nullable=True)
    page_number = Column(Integer, nullable=True, default=1)
    source = Column(String(50), nullable=False, default="ocr")
    validated = Column(Boolean, nullable=False, default=False)
    validated_by = Column(String(36), nullable=True)
    validated_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DocumentProcessingJob(Base):
    __tablename__ = "document_processing_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)

    job_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=0)
    progress = Column(Float, nullable=False, default=0.0)

    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    worker_id = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    document_category = Column(String(50), nullable=False)
    document_type = Column(String(50), nullable=False)

    extraction_schema = Column(JSON, nullable=True)
    validation_rules = Column(JSON, nullable=True)
    classification_keywords = Column(JSON, nullable=True)
    ocr_config = Column(JSON, nullable=True)

    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
