"""Document Intelligence schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentUpload(BaseModel):
    filename: str = Field(..., max_length=500)
    file_size: int = Field(..., ge=0)
    mime_type: str = Field(..., max_length=200)
    document_type: str = Field(default="other", max_length=20)
    category: str = Field(default="other", max_length=50)
    linked_entity_type: str | None = Field(default=None, max_length=100)
    linked_entity_id: str | None = Field(default=None, max_length=36)
    metadata_json: dict | None = None
    tags: list[str] | None = None
    description: str | None = None


class DocumentUpdate(BaseModel):
    filename: str | None = Field(default=None, max_length=500)
    document_type: str | None = Field(default=None, max_length=20)
    category: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=20)
    linked_entity_type: str | None = Field(default=None, max_length=100)
    linked_entity_id: str | None = Field(default=None, max_length=36)
    metadata_json: dict | None = None
    tags: list[str] | None = None
    description: str | None = None


class DocumentResponse(BaseModel):
    id: str
    tenant_id: str
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    document_type: str
    category: str
    status: str
    storage_path: str
    storage_backend: str
    checksum_sha256: str | None = None
    extracted_data: dict | None = None
    extraction_confidence: float | None = None
    extraction_method: str | None = None
    extraction_error: str | None = None
    ocr_text: str | None = None
    ocr_language: str | None = None
    ocr_confidence: float | None = None
    classification: str | None = None
    classification_confidence: float | None = None
    classification_label: str | None = None
    linked_entity_type: str | None = None
    linked_entity_id: str | None = None
    metadata_json: dict | None = None
    tags: list[str] | None = None
    description: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentFieldResponse(BaseModel):
    id: str
    document_id: str
    field_name: str
    field_value: str | None = None
    field_type: str
    confidence: float | None = None
    bbox_x: float | None = None
    bbox_y: float | None = None
    bbox_width: float | None = None
    bbox_height: float | None = None
    page_number: int | None = None
    source: str
    validated: bool
    validated_by: str | None = None
    validated_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentProcessingJobResponse(BaseModel):
    id: str
    document_id: str
    job_type: str
    status: str
    priority: int
    progress: float
    input_data: dict | None = None
    output_data: dict | None = None
    error_message: str | None = None
    error_traceback: str | None = None
    worker_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    document_category: str = Field(..., max_length=50)
    document_type: str = Field(..., max_length=50)
    extraction_schema: dict | None = None
    validation_rules: dict | None = None
    classification_keywords: list[str] | None = None
    ocr_config: dict | None = None
    is_default: bool = False
    is_active: bool = True


class DocumentTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    document_category: str | None = Field(default=None, max_length=50)
    document_type: str | None = Field(default=None, max_length=50)
    extraction_schema: dict | None = None
    validation_rules: dict | None = None
    classification_keywords: list[str] | None = None
    ocr_config: dict | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class DocumentTemplateResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str | None = None
    document_category: str
    document_type: str
    extraction_schema: dict | None = None
    validation_rules: dict | None = None
    classification_keywords: list[str] | None = None
    ocr_config: dict | None = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentClassifyRequest(BaseModel):
    document_id: str
    category: str = Field(..., max_length=50)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class DocumentExtractRequest(BaseModel):
    document_id: str
    template_id: str | None = None
    extraction_config: dict | None = None


class DocumentLinkRequest(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=100)
    entity_id: str = Field(..., min_length=1, max_length=36)


class DocumentSearchRequest(BaseModel):
    query: str | None = None
    category: str | None = None
    document_type: str | None = None
    status: str | None = None
    linked_entity_type: str | None = None
    linked_entity_id: str | None = None
    tags: list[str] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class DocumentSearchResult(BaseModel):
    documents: list[DocumentResponse]
    total: int
    has_more: bool
