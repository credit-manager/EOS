"""
EOS System — AI OCR Document Processing
All endpoints: RBAC enforced, tenant_id filtered, audit logged.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
import re

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import log_audit, get_user_permissions
from app.models.ai import AIPrediction

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────

class OCRRequest(BaseModel):
    document_type: str  # invoice, receipt, prescription, id_card
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    language: str = "ar"

class OCRResponse(BaseModel):
    extracted_data: dict
    confidence: float
    document_type: str
    suggestions: list
    processing_time_ms: float


# ─── MOCK OCR ENGINE ──────────────────────────────────────
# In production, this calls Google Vision / Azure Form Recognizer / AWS Textract.
# For now, we simulate structured extraction from document type.

def _extract_invoice_data(doc_type: str, lang: str) -> dict:
    """Simulate OCR extraction for invoices."""
    return {
        "document_type": "invoice",
        "supplier_name": "Sample Supplier Co.",
        "supplier_name_ar": "شركة مورد نموذجية",
        "invoice_number": f"INV-{uuid.uuid4().hex[:8].upper()}",
        "invoice_date": datetime.utcnow().date().isoformat(),
        "due_date": (datetime.utcnow().replace(day=28)).date().isoformat(),
        "subtotal": 15000.00,
        "vat_amount": 2100.00,
        "total": 17100.00,
        "currency": "EGP",
        "items": [
            {"description": "Product A", "quantity": 10, "unit_price": 1000.0, "total": 10000.0},
            {"description": "Product B", "quantity": 5, "unit_price": 1000.0, "total": 5000.0},
        ],
        "tax_rate": 0.14,
        "payment_terms": "Net 30",
        "notes": "",
    }

def _extract_receipt_data(doc_type: str, lang: str) -> dict:
    return {
        "document_type": "receipt",
        "store_name": "Sample Store",
        "receipt_number": f"RCP-{uuid.uuid4().hex[:8].upper()}",
        "date": datetime.utcnow().date().isoformat(),
        "items": [
            {"name": "Item 1", "price": 250.0},
            {"name": "Item 2", "price": 175.0},
        ],
        "subtotal": 425.0,
        "vat": 59.5,
        "total": 484.5,
        "payment_method": "cash",
    }

def _extract_prescription_data(doc_type: str, lang: str) -> dict:
    return {
        "document_type": "prescription",
        "doctor_name": "Dr. Ahmed Mohamed",
        "doctor_name_ar": "د. أحمد محمد",
        "patient_name": "Patient Name",
        "patient_name_ar": "اسم المريض",
        "prescription_date": datetime.utcnow().date().isoformat(),
        "medications": [
            {"name": "Amoxicillin 500mg", "dosage": "1 capsule 3 times daily", "duration": "7 days"},
            {"name": "Ibuprofen 400mg", "dosage": "1 tablet as needed", "duration": "5 days"},
        ],
        "notes": "Take with food",
    }

def _extract_id_card_data(doc_type: str, lang: str) -> dict:
    return {
        "document_type": "national_id",
        "national_id": "29001011234567",
        "full_name": "Ahmed Mohamed Ali",
        "full_name_ar": "أحمد محمد علي",
        "date_of_birth": "2000-01-01",
        "gender": "male",
        "address": "Cairo, Egypt",
        "address_ar": "القاهرة، مصر",
        "expiry_date": "2030-01-01",
    }


EXTRACTORS = {
    "invoice": _extract_invoice_data,
    "receipt": _extract_receipt_data,
    "prescription": _extract_prescription_data,
    "id_card": _extract_id_card_data,
}


def _generate_suggestions(data: dict, doc_type: str) -> list:
    """Generate actionable suggestions based on extracted data."""
    suggestions = []

    if doc_type == "invoice":
        if data.get("vat_amount", 0) > 0:
            suggestions.append({
                "action": "create_journal_entry",
                "description": "Create purchase journal entry for this invoice",
                "module": "accounting",
            })
        if data.get("total", 0) > 0:
            suggestions.append({
                "action": "create_supplier_invoice",
                "description": f"Create supplier invoice for EGP {data['total']:,.2f}",
                "module": "accounting",
            })
        suggestions.append({
            "action": "create_payment",
            "description": "Schedule payment according to payment terms",
            "module": "accounting",
        })

    elif doc_type == "prescription":
        suggestions.append({
            "action": "dispense_medications",
            "description": f"Dispense {len(data.get('medications', []))} medications",
            "module": "pharmacy",
        })
        suggestions.append({
            "action": "check_stock",
            "description": "Verify stock availability for prescribed medications",
            "module": "inventory",
        })

    elif doc_type == "receipt":
        suggestions.append({
            "action": "record_expense",
            "description": f"Record expense of EGP {data.get('total', 0):,.2f}",
            "module": "accounting",
        })

    return suggestions


# ─── OCR ENDPOINTS ────────────────────────────────────────

@router.post("/ocr/extract", response_model=OCRResponse)
async def ocr_extract(
    request: Request,
    body: OCRRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires AI access")

    tenant_id = current_user["tenant_id"]
    start = datetime.utcnow()

    if body.document_type not in EXTRACTORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document type: {body.document_type}. Supported: {list(EXTRACTORS.keys())}",
        )

    if not body.image_url and not body.image_base64:
        raise HTTPException(status_code=400, detail="Either image_url or image_base64 is required")

    # Run extraction
    extractor = EXTRACTORS[body.document_type]
    extracted_data = extractor(body.document_type, body.language)

    suggestions = _generate_suggestions(extracted_data, body.document_type)

    processing_time = (datetime.utcnow() - start).total_seconds() * 1000

    # Log prediction
    db.add(AIPrediction(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        model_name="eos-ocr-v1", service="ocr",
        input_data={"document_type": body.document_type, "language": body.language},
        output_data={"extracted_fields": list(extracted_data.keys())},
        confidence=0.92, latency_ms=processing_time,
        user_id=current_user["id"], module="ai",
    ))
    await db.flush()

    await log_audit(
        db, tenant_id=tenant_id, user=current_user,
        action="query", module="ai",
        entity_type="OCR", entity_id=body.document_type,
        entity_name=f"Extracted {body.document_type} in {processing_time:.0f}ms",
        request=request,
    )

    return OCRResponse(
        extracted_data=extracted_data,
        confidence=0.92,
        document_type=body.document_type,
        suggestions=suggestions,
        processing_time_ms=processing_time,
    )


@router.get("/ocr/supported-types")
async def supported_document_types(
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires AI access")

    return {
        "supported_types": [
            {"type": "invoice", "name": "Purchase/Sales Invoice", "name_ar": "فاتورة شراء/بيع"},
            {"type": "receipt", "name": "Payment Receipt", "name_ar": "إيصال دفع"},
            {"type": "prescription", "name": "Medical Prescription", "name_ar": "وصفة طبية"},
            {"type": "id_card", "name": "National ID Card", "name_ar": "بطاقة الرقم القومي"},
        ],
        "supported_languages": ["ar", "en"],
    }
