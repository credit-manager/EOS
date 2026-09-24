"""Document Intelligence service."""
import re
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from .models import (
    Document,
    DocumentCategory,
    DocumentField,
    DocumentProcessingJob,
    DocumentStatus,
    DocumentTemplate,
    DocumentType,
)
from .ocr import get_best_available_ocr

logger = logging.getLogger("2to-eos.documents")


class DocumentClassifier:
    """Classify documents based on content and metadata."""

    CATEGORY_KEYWORDS = {
        "invoice": ["invoice", "bill", "payment due", "amount due", "total", "tax", "subtotal"],
        "receipt": ["receipt", "paid", "cash", "change", "transaction", "store"],
        "contract": ["agreement", "contract", "terms", "conditions", "sign", "party"],
        "purchase_order": ["purchase order", "po number", "quantity", "unit price", "delivery"],
        "goods_received": ["goods received", "delivery note", "received by", "quantity received"],
        "bank_statement": ["statement", "balance", "debit", "credit", "account number"],
        "email": ["from:", "to:", "subject:", "dear", "regards", "best regards"],
        "report": ["report", "summary", "analysis", "quarterly", "annual", "findings"],
    }

    def classify(self, text: str, filename: str) -> tuple[str, float, str]:
        """Classify document by content and filename."""
        text_lower = text.lower() if text else ""
        filename_lower = filename.lower()

        scores: dict[str, float] = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                if kw in text_lower:
                    score += 0.15
                if kw in filename_lower:
                    score += 0.1
            scores[category] = min(score, 1.0)

        if not scores or max(scores.values()) == 0:
            return "other", 0.3, "No keywords matched"

        best = max(scores, key=scores.get)
        return best, scores[best], f"Keyword matching: {scores[best]:.2f}"

    def classify_from_metadata(self, metadata: dict) -> tuple[str, float, str]:
        """Classify from extracted metadata fields."""
        if not metadata:
            return "other", 0.0, "No metadata"

        invoice_fields = ["invoice_number", "invoice_date", "total_amount", "tax_amount"]
        contract_fields = ["contract_number", "party_a", "party_b", "effective_date"]
        po_fields = ["po_number", "supplier_name", "delivery_date"]

        invoice_score = sum(1 for f in invoice_fields if f in metadata) / len(invoice_fields)
        contract_score = sum(1 for f in contract_fields if f in contract_fields) / len(contract_fields)
        po_score = sum(1 for f in po_fields if f in metadata) / len(po_fields)

        scores = {"invoice": invoice_score, "contract": contract_score, "purchase_order": po_score}
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best, scores[best], f"Metadata field matching: {scores[best]:.2f}"

        return "other", 0.0, "No metadata matches"


class DocumentExtractor:
    """Extract structured data from documents."""

    FIELD_PATTERNS = {
        "invoice_number": [
            r"invoice\s*(?:#|number|no\.?)\s*:?\s*([A-Z0-9\-]+)",
            r"inv\s*(?:#|number|no\.?)\s*:?\s*([A-Z0-9\-]+)",
        ],
        "po_number": [
            r"purchase\s*order\s*(?:#|number|no\.?)\s*:?\s*([A-Z0-9\-]+)",
            r"p\.?o\.?\s*(?:#|number|no\.?)\s*:?\s*([A-Z0-9\-]+)",
        ],
        "date": [
            r"date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{2,4})",
        ],
        "total_amount": [
            r"total\s*(?:amount)?\s*:?\s*[\$£€]?\s*([\d,]+\.?\d*)",
            r"amount\s*due\s*:?\s*[\$£€]?\s*([\d,]+\.?\d*)",
            r"grand\s*total\s*:?\s*[\$£€]?\s*([\d,]+\.?\d*)",
        ],
        "tax_amount": [
            r"tax\s*(?:amount)?\s*:?\s*[\$£€]?\s*([\d,]+\.?\d*)",
            r"vat\s*:?\s*[\$£€]?\s*([\d,]+\.?\d*)",
        ],
        "supplier_name": [
            r"from\s*:?\s*(.+?)(?:\n|$)",
            r"supplier\s*:?\s*(.+?)(?:\n|$)",
            r"vendor\s*:?\s*(.+?)(?:\n|$)",
        ],
        "customer_name": [
            r"bill\s*to\s*:?\s*(.+?)(?:\n|$)",
            r"customer\s*:?\s*(.+?)(?:\n|$)",
            r"client\s*:?\s*(.+?)(?:\n|$)",
        ],
        "phone": [
            r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}",
        ],
        "email": [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        ],
    }

    def extract_fields(self, text: str) -> list[dict]:
        """Extract fields from OCR text using regex patterns."""
        if not text:
            return []

        fields = []
        for field_name, patterns in self.FIELD_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    value = match.group(1) if match.lastindex else match.group(0)
                    fields.append({
                        "field_name": field_name,
                        "field_value": value.strip(),
                        "field_type": "text",
                        "confidence": 0.7,
                        "source": "regex",
                        "page_number": 1,
                    })
                    break
                else:
                    continue
                break
        return fields

    def extract_amounts(self, text: str) -> list[dict]:
        """Extract monetary amounts from text."""
        if not text:
            return []

        amount_pattern = r"[\$£€]\s*([\d,]+\.?\d*)"
        amounts = []
        for match in re.finditer(amount_pattern, text):
            amounts.append({
                "field_name": "amount",
                "field_value": match.group(0),
                "field_type": "currency",
                "confidence": 0.8,
                "source": "regex",
                "page_number": 1,
            })
        return amounts


class DocumentService:
    """Main document intelligence service."""

    def __init__(self, db: Session):
        self.db = db
        self.classifier = DocumentClassifier()
        self.extractor = DocumentExtractor()

    def create_document(self, tenant_id: str, data: dict) -> Document:
        """Create a new document record."""
        doc = Document(
            tenant_id=tenant_id,
            filename=data["filename"],
            original_filename=data["filename"],
            file_size=data["file_size"],
            mime_type=data["mime_type"],
            document_type=data.get("document_type", DocumentType.other.value),
            category=data.get("category", DocumentCategory.other.value),
            status=DocumentStatus.uploaded.value,
            storage_path=f"/uploads/{tenant_id}/{data['filename']}",
            storage_backend="local",
            metadata_json=data.get("metadata_json"),
            tags=data.get("tags"),
            description=data.get("description"),
            linked_entity_type=data.get("linked_entity_type"),
            linked_entity_id=data.get("linked_entity_id"),
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_document(self, document_id: str, tenant_id: str) -> Document | None:
        """Get document by ID and tenant."""
        return (
            self.db.query(Document)
            .filter(Document.id == document_id, Document.tenant_id == tenant_id)
            .first()
        )

    def list_documents(
        self,
        tenant_id: str,
        category: str | None = None,
        status: str | None = None,
        linked_entity_type: str | None = None,
        linked_entity_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        """List documents with optional filters."""
        q = self.db.query(Document).filter(Document.tenant_id == tenant_id)

        if category:
            q = q.filter(Document.category == category)
        if status:
            q = q.filter(Document.status == status)
        if linked_entity_type:
            q = q.filter(Document.linked_entity_type == linked_entity_type)
        if linked_entity_id:
            q = q.filter(Document.linked_entity_id == linked_entity_id)

        total = q.count()
        docs = q.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
        return docs, total

    def classify_document(self, document_id: str, tenant_id: str, category: str, confidence: float = 0.0) -> Document | None:
        """Classify a document."""
        doc = self.get_document(document_id, tenant_id)
        if not doc:
            return None

        doc.category = category
        doc.classification = category
        doc.classification_confidence = confidence
        doc.classification_label = f"Manual classification: {category}"
        doc.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def extract_document_data(self, document_id: str, tenant_id: str) -> Document | None:
        """Extract data from document OCR text."""
        doc = self.get_document(document_id, tenant_id)
        if not doc:
            return None

        if not doc.ocr_text:
            doc.status = DocumentStatus.failed.value
            doc.extraction_error = "No OCR text available"
            self.db.commit()
            self.db.refresh(doc)
            return doc

        fields = self.extractor.extract_fields(doc.ocr_text)
        amounts = self.extractor.extract_amounts(doc.ocr_text)
        all_fields = fields + amounts

        extracted_data = {}
        for f in all_fields:
            if f["field_name"] not in extracted_data:
                extracted_data[f["field_name"]] = f["field_value"]

        for f in all_fields:
            existing = (
                self.db.query(DocumentField)
                .filter(
                    DocumentField.document_id == document_id,
                    DocumentField.field_name == f["field_name"],
                )
                .first()
            )
            if not existing:
                field = DocumentField(
                    document_id=document_id,
                    tenant_id=tenant_id,
                    field_name=f["field_name"],
                    field_value=f["field_value"],
                    field_type=f["field_type"],
                    confidence=f["confidence"],
                    source=f["source"],
                    page_number=f.get("page_number"),
                )
                self.db.add(field)

        doc.extracted_data = extracted_data
        doc.extraction_confidence = sum(f["confidence"] for f in all_fields) / len(all_fields) if all_fields else 0.0
        doc.extraction_method = "regex"
        doc.status = DocumentStatus.processed.value
        doc.updated_at = datetime.utcnow()

        if not doc.classification:
            cat, conf, reason = self.classifier.classify(doc.ocr_text, doc.filename)
            doc.classification = cat
            doc.classification_confidence = conf
            doc.classification_label = reason

        self.db.commit()
        self.db.refresh(doc)
        return doc

    def process_document_ocr(self, document_id: str, tenant_id: str, ocr_config: dict | None = None) -> Document | None:
        """Process document with OCR and extract structured data."""
        doc = self.get_document(document_id, tenant_id)
        if not doc:
            return None

        # Read file content
        try:
            with open(doc.storage_path, "rb") as f:
                file_content = f.read()
        except Exception as e:
            logger.error("Failed to read document file: %s", e)
            doc.status = DocumentStatus.failed.value
            doc.extraction_error = f"File read error: {e}"
            self.db.commit()
            self.db.refresh(doc)
            return doc

        # Get OCR provider
        ocr = get_best_available_ocr(ocr_config)

        # Extract structured data
        try:
            doc.status = DocumentStatus.processing.value
            self.db.commit()

            result = ocr.extract_structured(file_content, doc.mime_type)
            ocr_text = result.get("text", "")
            tables = result.get("tables", [])
            key_values = result.get("key_values", {})

            if not ocr_text:
                doc.status = DocumentStatus.failed.value
                doc.extraction_error = "No text extracted from document"
                self.db.commit()
                self.db.refresh(doc)
                return doc

            doc.ocr_text = ocr_text
            doc.extracted_tables = tables
            doc.extracted_key_values = key_values

            # Extract fields using regex + key_values
            fields = self.extractor.extract_fields(ocr_text)
            amounts = self.extractor.extract_amounts(ocr_text)

            # Add key_values as fields
            for k, v in key_values.items():
                fields.append({
                    "field_name": k,
                    "field_value": v,
                    "field_type": "text",
                    "confidence": 0.85,
                    "source": "ocr_kv",
                    "page_number": 1,
                })

            all_fields = fields + amounts

            # Save extracted fields
            extracted_data = {}
            for f in all_fields:
                if f["field_name"] not in extracted_data:
                    extracted_data[f["field_name"]] = f["field_value"]

                existing = (
                    self.db.query(DocumentField)
                    .filter(
                        DocumentField.document_id == document_id,
                        DocumentField.field_name == f["field_name"],
                    )
                    .first()
                )
                if not existing:
                    field = DocumentField(
                        document_id=document_id,
                        tenant_id=tenant_id,
                        field_name=f["field_name"],
                        field_value=f["field_value"],
                        field_type=f["field_type"],
                        confidence=f["confidence"],
                        source=f["source"],
                        page_number=f.get("page_number"),
                    )
                    self.db.add(field)

            doc.extracted_data = extracted_data
            doc.extraction_confidence = (
                sum(f["confidence"] for f in all_fields) / len(all_fields) if all_fields else 0.0
            )
            doc.extraction_method = "ocr"

            # Auto-classify
            cat, conf, reason = self.classifier.classify(ocr_text, doc.filename)
            doc.classification = cat
            doc.classification_confidence = conf
            doc.classification_label = reason

            doc.status = DocumentStatus.processed.value
            doc.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(doc)

            logger.info("Document %s processed with OCR: %d fields, confidence %.2f",
                       document_id, len(all_fields), doc.extraction_confidence)
            return doc

        except Exception as e:
            logger.exception("OCR processing failed for document %s", document_id)
            doc.status = DocumentStatus.failed.value
            doc.extraction_error = str(e)
            self.db.commit()
            self.db.refresh(doc)
            return doc

    def link_document(self, document_id: str, tenant_id: str, entity_type: str, entity_id: str) -> Document | None:
        """Link document to an entity."""
        doc = self.get_document(document_id, tenant_id)
        if not doc:
            return None

        doc.linked_entity_type = entity_type
        doc.linked_entity_id = entity_id
        doc.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_document_fields(self, document_id: str, tenant_id: str) -> list[DocumentField]:
        """Get all extracted fields for a document."""
        return (
            self.db.query(DocumentField)
            .filter(
                DocumentField.document_id == document_id,
                DocumentField.tenant_id == tenant_id,
            )
            .order_by(DocumentField.created_at.desc())
            .all()
        )

    def validate_field(self, field_id: str, document_id: str, tenant_id: str, validated_by: str) -> DocumentField | None:
        """Validate an extracted field."""
        field = (
            self.db.query(DocumentField)
            .filter(
                DocumentField.id == field_id,
                DocumentField.document_id == document_id,
                DocumentField.tenant_id == tenant_id,
            )
            .first()
        )
        if not field:
            return None

        field.validated = True
        field.validated_by = validated_by
        field.validated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(field)
        return field

    def create_job(self, document_id: str, tenant_id: str, job_type: str, priority: int = 0) -> DocumentProcessingJob:
        """Create a processing job."""
        job = DocumentProcessingJob(
            document_id=document_id,
            tenant_id=tenant_id,
            job_type=job_type,
            status="pending",
            priority=priority,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_jobs(self, tenant_id: str, status: str | None = None, limit: int = 50) -> list[DocumentProcessingJob]:
        """List processing jobs."""
        q = self.db.query(DocumentProcessingJob).filter(DocumentProcessingJob.tenant_id == tenant_id)
        if status:
            q = q.filter(DocumentProcessingJob.status == status)
        return q.order_by(DocumentProcessingJob.created_at.desc()).limit(limit).all()

    def create_template(self, tenant_id: str, data: dict) -> DocumentTemplate:
        """Create a document template."""
        template = DocumentTemplate(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            document_category=data["document_category"],
            document_type=data["document_type"],
            extraction_schema=data.get("extraction_schema"),
            validation_rules=data.get("validation_rules"),
            classification_keywords=data.get("classification_keywords"),
            ocr_config=data.get("ocr_config"),
            is_default=data.get("is_default", False),
            is_active=data.get("is_active", True),
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_template(self, template_id: str, tenant_id: str) -> DocumentTemplate | None:
        """Get template by ID and tenant."""
        return (
            self.db.query(DocumentTemplate)
            .filter(DocumentTemplate.id == template_id, DocumentTemplate.tenant_id == tenant_id)
            .first()
        )

    def list_templates(self, tenant_id: str, limit: int = 50) -> list[DocumentTemplate]:
        """List document templates."""
        return (
            self.db.query(DocumentTemplate)
            .filter(DocumentTemplate.tenant_id == tenant_id)
            .order_by(DocumentTemplate.name)
            .limit(limit)
            .all()
        )

    def search_documents(
        self,
        tenant_id: str,
        query: str | None = None,
        category: str | None = None,
        document_type: str | None = None,
        status: str | None = None,
        linked_entity_type: str | None = None,
        linked_entity_id: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        """Search documents with multiple criteria."""
        q = self.db.query(Document).filter(Document.tenant_id == tenant_id)

        if query:
            q = q.filter(
                (Document.filename.ilike(f"%{query}%"))
                | (Document.description.ilike(f"%{query}%"))
                | (Document.ocr_text.ilike(f"%{query}%"))
            )
        if category:
            q = q.filter(Document.category == category)
        if document_type:
            q = q.filter(Document.document_type == document_type)
        if status:
            q = q.filter(Document.status == status)
        if linked_entity_type:
            q = q.filter(Document.linked_entity_type == linked_entity_type)
        if linked_entity_id:
            q = q.filter(Document.linked_entity_id == linked_entity_id)

        total = q.count()
        docs = q.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
        return docs, total

    def archive_document(self, document_id: str, tenant_id: str) -> Document | None:
        """Archive a document."""
        doc = self.get_document(document_id, tenant_id)
        if not doc:
            return None

        doc.status = DocumentStatus.archived.value
        doc.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_document_stats(self, tenant_id: str) -> dict:
        """Get document statistics for tenant."""
        total = self.db.query(Document).filter(Document.tenant_id == tenant_id).count()
        processed = (
            self.db.query(Document)
            .filter(Document.tenant_id == tenant_id, Document.status == DocumentStatus.processed.value)
            .count()
        )
        failed = (
            self.db.query(Document)
            .filter(Document.tenant_id == tenant_id, Document.status == DocumentStatus.failed.value)
            .count()
        )
        processing = (
            self.db.query(Document)
            .filter(Document.tenant_id == tenant_id, Document.status == DocumentStatus.processing.value)
            .count()
        )

        categories = {}
        for doc in self.db.query(Document).filter(Document.tenant_id == tenant_id).all():
            cat = doc.category
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total": total,
            "processed": processed,
            "failed": failed,
            "processing": processing,
            "by_category": categories,
        }
