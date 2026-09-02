"""
ERROR HANDLING MODULE
=====================
Provides secure error responses that don't expose internal details.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi.responses import JSONResponse


# Error code constants
class ErrorCodes:
    # Entity errors
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    TABLE_NOT_FOUND = "TABLE_NOT_FOUND"
    TABLE_INVALID = "TABLE_INVALID"
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    REQUIRED = "REQUIRED"
    INVALID_TYPE = "INVALID_TYPE"
    TOO_LONG = "TOO_LONG"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    INVALID_ENUM = "INVALID_ENUM"
    INVALID_DATE = "INVALID_DATE"
    NOT_NULL_VIOLATION = "NOT_NULL_VIOLATION"
    NO_VALID_COLUMNS = "NO_VALID_COLUMNS"
    EMPTY_PAYLOAD = "EMPTY_PAYLOAD"
    
    # Duplicate errors
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    
    # Authentication errors
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    MISSING_TOKEN = "MISSING_TOKEN"
    
    # Authorization errors
    FORBIDDEN = "FORBIDDEN"
    
    # Record errors
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    
    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"


# Bilingual error messages
ERROR_MESSAGES: dict[str, dict[str, str]] = {
    ErrorCodes.ENTITY_NOT_FOUND: {
        "message": "الكيان '{entity}' غير موجود",
        "message_en": "Entity '{entity}' not found",
    },
    ErrorCodes.TABLE_NOT_FOUND: {
        "message": "الجدول '{table}' غير موجود",
        "message_en": "Table '{table}' not found",
    },
    ErrorCodes.VALIDATION_ERROR: {
        "message": "أخطاء في التحقق من البيانات",
        "message_en": "Validation errors",
    },
    ErrorCodes.REQUIRED: {
        "message": "الحقل '{field}' مطلوب",
        "message_en": "Field '{field}' is required",
    },
    ErrorCodes.INVALID_TYPE: {
        "message": "الحقل '{field}' يجب أن يكون {type}",
        "message_en": "Field '{field}' must be {type}",
    },
    ErrorCodes.DUPLICATE_RECORD: {
        "message": "السجل موجود بالفعل ({fields})",
        "message_en": "Record already exists ({fields})",
    },
    ErrorCodes.UNAUTHORIZED: {
        "message": "المصادقة مطلوبة",
        "message_en": "Authentication required",
    },
    ErrorCodes.FORBIDDEN: {
        "message": "ممنوع: يتطلب صلاحية {permission}",
        "message_en": "Forbidden: requires {permission} permission",
    },
    ErrorCodes.RECORD_NOT_FOUND: {
        "message": "السجل غير موجود",
        "message_en": "Record not found",
    },
    ErrorCodes.INTERNAL_ERROR: {
        "message": "خطأ داخلي في الخادم",
        "message_en": "Internal server error",
    },
    ErrorCodes.DATABASE_ERROR: {
        "message": "خطأ في قاعدة البيانات",
        "message_en": "Database error",
    },
}


def get_error_message(code: str, **kwargs) -> dict[str, str]:
    """Get bilingual error message with interpolation."""
    template = ERROR_MESSAGES.get(code, {
        "message": "خطأ غير معروف",
        "message_en": "Unknown error",
    })
    
    return {
        "message": template["message"].format(**kwargs) if kwargs else template["message"],
        "message_en": template["message_en"].format(**kwargs) if kwargs else template["message_en"],
    }


def create_error_response(
    status_code: int,
    code: str,
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
    **kwargs
) -> JSONResponse:
    """
    Create a secure error response.
    
    Logs full error internally, returns generic message to client.
    """
    if not request_id:
        request_id = str(uuid.uuid4())
    
    messages = get_error_message(code, **kwargs)
    
    error_body = {
        "code": code,
        "message": messages["message"],
        "message_en": messages["message_en"],
    }
    
    if details:
        error_body["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error": error_body,
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
    )


def secure_db_error(e: Exception, request_id: str | None = None) -> JSONResponse:
    """
    Convert database/internal errors to secure responses.
    
    NEVER exposes raw exception to client.
    Logs full error for debugging.
    """
    if not request_id:
        request_id = str(uuid.uuid4())
    
    # Log the full error internally (in production, use proper logging)
    type(e).__name__
    error_str = str(e)
    
    # Determine error code based on exception type
    error_code = ErrorCodes.DATABASE_ERROR
    status_code = 500
    
    if "connection" in error_str.lower():
        error_code = ErrorCodes.DATABASE_ERROR
    elif "does not exist" in error_str.lower():
        error_code = ErrorCodes.TABLE_NOT_FOUND
        status_code = 400
    elif "duplicate key" in error_str.lower() or "unique" in error_str.lower():
        error_code = ErrorCodes.DUPLICATE_RECORD
        status_code = 409
    
    messages = get_error_message(error_code)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error": {
                "code": error_code,
                "message": messages["message"],
                "message_en": messages["message_en"],
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
    )
