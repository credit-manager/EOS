import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("2to-eos.response_validation")


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list
    data: Any | None = None


class ResponseValidator:
    def __init__(self):
        self._validators: dict[str, type[BaseModel]] = {}
    
    def register(self, name: str, model: type[BaseModel]) -> None:
        self._validators[name] = model
    
    def validate(self, name: str, data: dict) -> ValidationResult:
        model = self._validators.get(name)
        if not model:
            logger.warning("Validator '%s' not registered", name)
            return ValidationResult(is_valid=True, errors=[], data=data)
        
        try:
            validated_data = model(**data)
            return ValidationResult(
                is_valid=True,
                errors=[],
                data=validated_data.model_dump(),
            )
        except ValidationError as exc:
            errors = []
            for error in exc.errors():
                loc = " -> ".join(str(loc) for loc in error.get("loc", []))
                msg = error.get("msg", "Validation error")
                errors.append({"field": loc, "message": msg})
            
            return ValidationResult(
                is_valid=False,
                errors=errors,
                data=None,
            )
    
    def validate_list(self, name: str, data: list[dict]) -> ValidationResult:
        model = self._validators.get(name)
        if not model:
            logger.warning("Validator '%s' not registered", name)
            return ValidationResult(is_valid=True, errors=[], data=data)
        
        validated_items = []
        all_errors = []
        
        for i, item in enumerate(data):
            try:
                validated_item = model(**item)
                validated_items.append(validated_item.model_dump())
            except ValidationError as exc:
                for error in exc.errors():
                    loc = f"[{i}] -> " + " -> ".join(str(loc) for loc in error.get("loc", []))
                    msg = error.get("msg", "Validation error")
                    all_errors.append({"field": loc, "message": msg})
        
        if all_errors:
            return ValidationResult(
                is_valid=False,
                errors=all_errors,
                data=None,
            )
        
        return ValidationResult(
            is_valid=True,
            errors=[],
            data=validated_items,
        )


validator = ResponseValidator()


def validate_response(model: type[BaseModel]):
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if isinstance(result, dict):
                try:
                    validated = model(**result)
                    return validated.model_dump()
                except ValidationError as exc:
                    logger.error("Response validation failed: %s", exc)
                    raise
            elif isinstance(result, list):
                validated_items = []
                for item in result:
                    if isinstance(item, dict):
                        try:
                            validated = model(**item)
                            validated_items.append(validated.model_dump())
                        except ValidationError as exc:
                            logger.error("Response validation failed: %s", exc)
                            raise
                    else:
                        validated_items.append(item)
                return validated_items
            
            return result
        
        return wrapper
    
    return decorator


def validate_request(model: type[BaseModel]):
    def decorator(func):
        def wrapper(*args, **kwargs):
            request_data = kwargs.get("request_data") or (args[0] if args else None)
            
            if isinstance(request_data, dict):
                try:
                    validated = model(**request_data)
                    kwargs["request_data"] = validated.model_dump()
                except ValidationError as exc:
                    logger.error("Request validation failed: %s", exc)
                    raise
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator
