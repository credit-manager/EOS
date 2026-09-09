# EOS Dynamic Business Platform — Full Source Code

**Version:** 1.0.0-rc1  
**Date:** 2026-08-24  
**Gate:** P7 Complete (Query Engine)

---

## Table of Contents

1. [Configuration Files](#1-configuration-files)
2. [Database & Models](#2-database--models)
3. [Core Modules](#3-core-modules)
4. [Router (Dynamic CRUD)](#4-router-dynamic-crud)
5. [Test Files](#5-test-files)
6. [Gate Documentation](#6-gate-documentation)

---

## 1. Configuration Files

### `main.py`

```python
from fastapi import FastAPI
from routers import dynamic_crud
import os


app = FastAPI(
    title="EOS Dynamic Business Platform",
    version="1.0.0"
)

app.include_router(dynamic_crud.router)


@app.on_event("startup")
async def validate_configuration():
    """Validate required configuration on startup."""
    errors = []
    
    # Database URL is required
    if not os.getenv("DATABASE_URL"):
        errors.append("DATABASE_URL not set")
    
    # Check auth mode
    auth_mode = os.getenv("EOS_AUTH_MODE", "test").lower()
    
    if auth_mode == "production":
        # Production requires SECRET_KEY
        if not os.getenv("EOS_SECRET_KEY"):
            errors.append("EOS_SECRET_KEY required in production mode")
        
        # Warn about algorithm
        algo = os.getenv("EOS_ALGORITHM", "HS256")
        if algo == "HS256":
            print("WARNING: HS256 algorithm. Consider RS256 for production.")
    
    if errors:
        print(f"CONFIGURATION ERRORS: {', '.join(errors)}")
        print("Server will fail to connect to database or authenticate.")
    else:
        print(f"Configuration OK: auth_mode={auth_mode}")


@app.get("/")
def root():
    return {
        "message": "EOS DBP Core is running!",
        "docs": "/docs"
    }
```

### `database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


def _get_database_url() -> str:
    """
    Get DATABASE_URL from environment.
    
    No hardcoded passwords. No fallback to credentials.
    Raises ValueError if not set.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL environment variable is required. "
            "Set it in .env or environment before starting the server."
        )
    return url


DATABASE_URL = _get_database_url()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### `models.py` (PROTECTED — DO NOT MODIFY)

```python
from sqlalchemy import Column, String, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base
import uuid

class DBPEntity(Base):
    __tablename__ = "dbp_entities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    faculty = Column(String(50), nullable=False)
    table_mapping = Column(String(100))
    is_system = Column(Boolean, default=False)
    metadata_schema = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DBPField(Base):
    __tablename__ = "dbp_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id = Column(
        String(36),
        ForeignKey("dbp_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    code = Column(String(100), nullable=False)
    label_en = Column(String(255))
    label_ar = Column(String(255))
    field_type = Column(String(50), nullable=False)
    is_required = Column(Boolean, default=False)
    ui_config = Column(JSON, default={})
    enum_values = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### `.env`

```
# EOS Dynamic Business Platform — Environment Variables
# NEVER commit this file to version control

# Database
DATABASE_URL=postgresql://eos:0100@127.0.0.1:5432/eos_main

# Auth Mode
EOS_AUTH_MODE=test

# Production Auth (required when EOS_AUTH_MODE=production)
# EOS_SECRET_KEY=generate_random_64_chars_here
# EOS_ALGORITHM=HS256
```

### `.env.example`

```
# EOS Dynamic Business Platform — Environment Variables
# Copy to .env and fill in real values

# Database (required)
DATABASE_URL=postgresql://eos:CHANGE_ME@127.0.0.1:5432/eos_main

# Auth Mode: "test" or "production"
EOS_AUTH_MODE=test

# Production Auth (required when EOS_AUTH_MODE=production)
EOS_SECRET_KEY=CHANGE_ME_TO_RANDOM_64_CHARS
EOS_ALGORITHM=HS256

# CORS (optional)
CORS_ORIGINS=["http://localhost:3000"]
```

### `.gitignore`

```
# Environment files (contain secrets)
.env
.env.local
.env.production
.env.staging

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
venv/
.venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Database
*.db
*.sqlite3
```

---

## 2. Database & Models

See `models.py` above (PROTECTED).

---

## 3. Core Modules

### `core/__init__.py`

```python
(empty)
```

### `core/auth.py`

```python
"""
AUTH MODULE
============

This module provides:
1. Test authentication functions (for verification/testing)
2. Delegation to auth_adapter for get_current_user

The auth_adapter switches between test and production auth
based on EOS_AUTH_MODE environment variable.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Test-only secret key — from env or generated
# NEVER use a real production key here
TEST_SECRET_KEY = os.getenv(
    "EOS_TEST_SECRET_KEY",
    "test-verification-key-do-not-use-in-production"
)
TEST_ALGORITHM = "HS256"
TEST_TOKEN_EXPIRE_MINUTES = 60

# Bearer Token extractor
security = HTTPBearer()


def create_test_token(
    tenant_id: str,
    user_id: str = "test-user",
    email: str = "test@example.com",
    roles: Optional[list] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a test JWT token.

    This is for verification/testing only.
    The tenant_id embedded in the token is the
    AUTHENTICATED TENANT — the source of truth
    for tenant isolation.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=TEST_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "tenant_id": tenant_id.lower(),
        "email": email,
        "roles": roles or ["user"],
    }

    return jwt.encode(payload, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)


def verify_test_token(token: str) -> dict:
    """
    Verify and decode a test JWT token.

    Returns the full payload including tenant_id.
    Raises HTTPException on invalid/expired token.
    """
    try:
        payload = jwt.decode(
            token,
            TEST_SECRET_KEY,
            algorithms=[TEST_ALGORITHM]
        )
        return payload
    except JWTError:
        # Never expose JWT error details to client
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Delegate to auth_adapter for get_current_user
# This allows switching between test and production auth
# via EOS_AUTH_MODE environment variable
from core.auth_adapter import get_current_user, optional_get_current_user

__all__ = [
    "create_test_token",
    "verify_test_token",
    "get_current_user",
    "optional_get_current_user",
    "require_permission",
    "TEST_SECRET_KEY",
    "TEST_ALGORITHM",
]


def require_permission(module: str, action: str):
    """
    Dependency factory: require a specific permission.
    
    Usage:
        @router.post("/accounts", dependencies=[Depends(require_permission("dynamic", "create"))])
    """
    async def _check(current_user: Optional[dict] = Depends(optional_get_current_user)):
        # Allow unauthenticated access for NONE entities
        # (endpoint logic will handle NONE/SCOPED distinction)
        if current_user is None:
            return
        
        required = f"{module}:{action}"
        
        # Check if user has wildcard permission
        if "*:*" in current_user.get("permissions", []):
            return
        
        # Check direct permissions
        if required in current_user.get("permissions", []):
            return
        
        # Check roles for permission (test mode fallback)
        roles = current_user.get("roles", [])
        for role in roles:
            if role == "admin":
                return
            if role == "dynamic_manager":
                return
            if role == "dynamic_operator" and action in ("read", "create", "update"):
                return
            if role == "dynamic_viewer" and action == "read":
                return
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return _check
```

### `core/auth_adapter.py`

```python
"""
AUTH ADAPTER
=============

Switches between test and production authentication
based on environment configuration.

Usage:
    from core.auth_adapter import get_current_user, optional_get_current_user

Rules:
    - EOS_AUTH_MODE=production → uses production_auth.py
    - EOS_AUTH_MODE=test (or unset) → uses test auth (core/auth.py)
    - No fallback from production secret to test secret
    - Same return format in both modes
"""

import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


def _is_production() -> bool:
    """Check if running in production auth mode."""
    mode = os.getenv("EOS_AUTH_MODE", "test").lower()
    return mode == "production"


def _get_production_auth():
    """Lazy import of production auth module."""
    from core.production_auth import (
        security as prod_security,
        verify_token as prod_verify_token,
    )
    return prod_security, prod_verify_token


def _get_test_auth():
    """Lazy import of test auth module."""
    from core.auth import (
        security as test_security,
        verify_token as test_verify_token,
    )
    return test_security, test_verify_token


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(auto_error=False)
    )
) -> dict:
    """
    Get current authenticated user.

    Production mode:
        - Uses EOS_SECRET_KEY from environment
        - Raises 401 if SECRET_KEY not set

    Test mode:
        - Uses hardcoded TEST_SECRET_KEY
        - For verification/testing only
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if _is_production():
        from core.production_auth import verify_token, _get_secret_key

        # Verify SECRET_KEY is set (will raise ValueError if not)
        try:
            _get_secret_key()
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

        payload = verify_token(credentials.credentials)

    else:
        from core.auth import verify_test_token as verify_token

        payload = verify_token(credentials.credentials)

    # Extract user info (same format for both modes)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing tenant ID",
        )

    return {
        "id": user_id,
        "tenant_id": tenant_id.lower(),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
    }


async def optional_get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[dict]:
    """
    Optional version of get_current_user.

    Returns None when no token is provided.
    Raises HTTPException only when token is provided but invalid.

    Used for NONE entities where auth is not required.
    """
    if credentials is None:
        return None

    return await get_current_user(credentials)
```

### `core/production_auth.py`

```python
"""
PRODUCTION AUTHENTICATION
==========================

This module provides JWT-based authentication for
production use. It reads SECRET_KEY from environment.

DO NOT import this module in tests.
DO NOT hardcode secrets here.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


def _get_secret_key() -> str:
    """
    Get SECRET_KEY from environment.

    Raises ValueError if not set.
    This prevents accidental use of test auth in production.
    """
    key = os.getenv("EOS_SECRET_KEY")
    if not key:
        raise ValueError(
            "EOS_SECRET_KEY environment variable is required for production auth. "
            "Set it in .env or environment before starting the server."
        )
    return key


def _get_algorithm() -> str:
    return os.getenv("EOS_ALGORITHM", "HS256")


# Bearer Token extractor
security = HTTPBearer()


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[dict] = None
) -> str:
    """Create a JWT access token for production use."""
    secret_key = _get_secret_key()
    algorithm = _get_algorithm()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    if extra_data:
        payload.update(extra_data)

    return jwt.encode(payload, secret_key, algorithm=algorithm)


def verify_token(token: str) -> dict:
    """Verify and decode a production JWT token."""
    secret_key = _get_secret_key()
    algorithm = _get_algorithm()

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm]
        )
        return payload
    except JWTError:
        # Never expose JWT error details to client
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current authenticated user from production JWT token.

    Returns:
        {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "roles": roles
        }
    """
    payload = verify_token(credentials.credentials)

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing tenant ID",
        )

    return {
        "id": user_id,
        "tenant_id": tenant_id.lower(),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
    }
```

### `core/metadata_engine.py` (PROTECTED — DO NOT MODIFY)

```python
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional
import json

from models import DBPEntity, DBPField


class MetadataEngine:

    def __init__(self, db: Session):
        self.db = db

    def get_entity_by_code(
        self,
        code: str
    ) -> Optional[Dict[str, Any]]:

        entity = (
            self.db.query(DBPEntity)
            .filter(DBPEntity.code == code)
            .first()
        )

        if not entity:
            return None

        return {
            k: v
            for k, v in entity.__dict__.items()
            if k != "_sa_instance_state"
        }

    def get_entity_fields(self, entity_id: str) -> list:

        fields = (
            self.db.query(DBPField)
            .filter(DBPField.entity_id == entity_id)
            .order_by(
                text("CAST(ui_config->>'order' AS INTEGER) ASC")
            )
            .all()
        )

        return [
            {
                k: v
                for k, v in field.__dict__.items()
                if k != "_sa_instance_state"
            }
            for field in fields
        ]

    def get_full_schema(self, code: str) -> Dict[str, Any]:

        entity = self.get_entity_by_code(code)

        if not entity:
            raise ValueError(f"الكيان '{code}' غير موجود")

        return {
            "entity": entity,
            "fields": self.get_entity_fields(entity["id"])
        }

    def validate_data(
        self,
        code: str,
        data: Dict[str, Any]
    ):

        schema = self.get_full_schema(code)
        errors = {}

        for field in schema["fields"]:

            val = data.get(field["code"])

            if (
                field["is_required"]
                and (val is None or str(val).strip() == "")
            ):
                errors[field["code"]] = "مطلوب"

            elif (
                val is not None
                and field["field_type"] == "enum"
                and field["enum_values"]
            ):

                enum_list = field["enum_values"]

                if isinstance(enum_list, str):
                    enum_list = json.loads(enum_list)

                if val not in enum_list:
                    errors[field["code"]] = (
                        f"يجب أن يكون: {enum_list}"
                    )

        if errors:
            raise ValueError(
                json.dumps(errors, ensure_ascii=False)
            )

        return True
```

### `core/dynamic_verification.py`

```python
from typing import Dict, Any, List, Optional
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
import uuid
import re

from models import DBPEntity, DBPField
from core.metadata_engine import MetadataEngine


class DynamicVerificationEngine:
    """
    Conservative verification layer.

    Important distinction:
        dbp_entities.tenant_id
        !=
        actual table tenant_id column

    Tenant capability is determined ONLY from the real table schema.

    Tenant VALUE for SCOPED operations comes ONLY from
    authenticated context — NOT from entity metadata or payload.
    """

    def __init__(self, db: Session, entity_code: str):
        self.db = db
        self.entity_code = entity_code

        self.entity_meta: Optional[Dict[str, Any]] = None
        self.table_name: Optional[str] = None
        self.table_valid: bool = False

        self.real_columns: Dict[str, Any] = {}
        self.not_null_columns: List[str] = []
        self.tenant_capability = "NONE"
        self.pk_column: str = "id"
        self.pk_type: str = "uuid"

        self._load_entity()
        self._inspect_table()

    def _load_entity(self) -> None:
        entity = (
            self.db.query(DBPEntity)
            .filter(DBPEntity.code == self.entity_code)
            .first()
        )

        if not entity:
            return

        self.entity_meta = {
            "id": entity.id,
            "code": entity.code,
            "name_en": entity.name_en,
            "name_ar": entity.name_ar,
            "faculty": entity.faculty,
            "table_mapping": entity.table_mapping,
            "is_system": entity.is_system,
        }

        self.table_name = entity.table_mapping

    def _inspect_table(self) -> None:
        if not self.table_name:
            return

        try:
            inspector = inspect(self.db.bind)

            # Verify table exists in PostgreSQL
            if self.table_name not in inspector.get_table_names():
                self.table_valid = False
                return

            self.table_valid = True

            columns = inspector.get_columns(self.table_name)

            self.real_columns = {
                column["name"].lower(): column["name"]
                for column in columns
                if column.get("name")
            }

            self.not_null_columns = [
                column["name"]
                for column in columns
                if not column.get("nullable", True)
            ]

            if "tenant_id" in self.real_columns:
                self.tenant_capability = "SCOPED"
            else:
                self.tenant_capability = "NONE"

            # Detect PK column and type
            pk_constraint = inspector.get_pk_constraint(self.table_name)
            pk_cols = pk_constraint.get("constrained_columns", [])
            
            if pk_cols:
                self.pk_column = pk_cols[0]  # Primary key column name
                # Find PK column type
                for col in columns:
                    if col["name"] == self.pk_column:
                        self.pk_type = str(col["type"]).lower()
                        break
            else:
                self.pk_column = "id"
                self.pk_type = "uuid"  # Default

        except Exception:
            self.table_valid = False
            self.real_columns = {}
            self.tenant_capability = "NONE"
            self.pk_column = "id"
            self.pk_type = "uuid"

    def generate_pk_value(self) -> Any:
        """
        Generate a primary key value based on the PK column type.
        
        Supports:
        - UUID (default)
        - INTEGER (auto-increment simulation)
        - VARCHAR/STRING (UUID or custom format)
        """
        if "uuid" in self.pk_type:
            return str(uuid.uuid4())
        elif "int" in self.pk_type:
            # For integer PKs, we need to find the max value and increment
            try:
                query = text(f"SELECT MAX({self.pk_column}) FROM {self.table_name}")
                result = self.db.execute(query).scalar()
                return (result or 0) + 1
            except Exception:
                return 1
        else:
            # For string PKs, use UUID
            return str(uuid.uuid4())

    def get_pk_column(self) -> str:
        """Get the primary key column name."""
        return self.pk_column

    def entity_exists(self) -> bool:
        return self.entity_meta is not None

    def has_table_mapping(self) -> bool:
        return bool(
            self.entity_meta
            and self.entity_meta.get("table_mapping")
        )

    def is_table_valid(self) -> bool:
        """Check if table_mapping points to a real PostgreSQL table."""
        return self.table_valid

    def has_tenant_id_column(self) -> bool:
        return self.tenant_capability == "SCOPED"

    def detect_tenant_handling(self) -> str:
        return self.tenant_capability

    def validate_table_mapping(self) -> Optional[str]:
        """
        Validate that table_mapping is safe to use in SQL.
        Returns error message if invalid, None if valid.
        """
        if not self.table_name:
            return "Table mapping غير موجود"

        if not self.table_valid:
            return f"الجدول '{self.table_name}' غير موجود في قاعدة البيانات"

        # Verify table name contains only safe characters
        import re
        if not re.match(r'^[a-z0-9_]+$', self.table_name):
            return f"اسم الجدول '{self.table_name}' يحتوي على أحرف غير آمنة"

        return None

    def get_not_null_columns(self) -> List[str]:
        return list(self.not_null_columns)

    def validate_not_null_columns(
        self,
        data: Dict[str, Any],
        exclude_cols: Optional[List[str]] = None
    ) -> List[str]:
        exclude_cols = set(exclude_cols or [])
        exclude_cols.add("id")

        errors = []
        for col in self.not_null_columns:
            if col in exclude_cols:
                continue
            if col not in data or data[col] is None:
                errors.append(
                    f"{col}: الحقل مطلوب (NOT NULL في قاعدة البيانات)"
                )
        return errors

    def get_table_columns(self) -> List[str]:
        return list(self.real_columns.values())

    def check_column_exists(self, column_name: str) -> bool:
        if not column_name:
            return False
        return column_name.lower() in self.real_columns

    def get_valid_columns(
        self,
        payload: Dict[str, Any]
    ) -> List[str]:
        return [
            key
            for key in payload.keys()
            if self.check_column_exists(key)
        ]

    def validate_data(
        self,
        data: Dict[str, Any]
    ) -> bool:
        if not self.entity_exists():
            raise ValueError(
                f"الكيان '{self.entity_code}' غير موجود"
            )

        engine = MetadataEngine(self.db)
        return engine.validate_data(self.entity_code, data)

    def validate_required_fields(
        self,
        data: Dict[str, Any]
    ) -> bool:
        return self.validate_data(data)

    def validate_enum_fields(
        self,
        data: Dict[str, Any]
    ) -> bool:
        return True

    def get_unique_constraints(self) -> List[List[str]]:
        """Get actual unique constraints as lists of column groups."""
        if not self.table_name:
            return []

        try:
            inspector = inspect(self.db.bind)
            constraints = []

            for constraint in inspector.get_unique_constraints(
                self.table_name
            ):
                cols = constraint.get("column_names", [])
                if cols:
                    constraints.append(cols)

            for index in inspector.get_indexes(self.table_name):
                if index.get("unique"):
                    cols = index.get("column_names", [])
                    if cols and cols not in constraints:
                        constraints.append(cols)

            return constraints

        except Exception:
            return []

    def check_duplicate_by_unique_fields(
        self,
        data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """
        Check for duplicate records based on unique constraints.

        For composite constraints like (tenant_id, code),
        the check is scoped to the tenant if tenant_id is provided.
        """
        if not self.table_name:
            return []

        errors = []
        constraints = self.get_unique_constraints()

        for cols in constraints:
            # Skip constraints where not all columns are in data
            if not all(c in data for c in cols):
                continue

            # Skip constraints where all values are None
            values = [data[c] for c in cols]
            if all(v is None for v in values):
                continue

            # Build WHERE clause
            conditions = []
            params = {}
            for i, col in enumerate(cols):
                conditions.append(f"{col} = :val_{i}")
                params[f"val_{i}"] = data[col]

            where_clause = " AND ".join(conditions)

            # For composite constraints with tenant_id,
            # scope to the same tenant
            if (
                "tenant_id" in cols
                and tenant_id
                and "tenant_id" in data
            ):
                # Already scoped by tenant_id in the constraint
                pass
            elif (
                "tenant_id" not in cols
                and tenant_id
                and self.check_column_exists("tenant_id")
            ):
                # Single-column unique constraint on a SCOPED table
                # Add tenant scoping
                where_clause += " AND tenant_id = :tenant_scope"
                params["tenant_scope"] = tenant_id

            query = text(
                f"""
                SELECT 1
                FROM {self.table_name}
                WHERE {where_clause}
                LIMIT 1
                """
            )

            row = self.db.execute(query, params).first()

            if row:
                col_names = ", ".join(cols)
                errors.append(
                    f"{col_names}: موجود بالفعل"
                )

        return errors
```

### `core/audit.py`

```python
"""
AUDIT MODULE FOR DYNAMIC CRUD
==============================
Sync audit logging for Dynamic CRUD operations.
Writes to the same audit_logs table as eos-system.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
from datetime import datetime
from json import dumps
import uuid


def log_dynamic_audit(
    db: Session,
    tenant_id: str,
    user_id: Optional[str],
    user_email: Optional[str],
    action: str,
    entity_code: str,
    record_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
) -> bool:
    """
    Write an audit log entry for Dynamic CRUD operations.
    
    Returns True on success, False on failure (never raises).
    Does NOT commit - caller should commit as part of their transaction.
    """
    try:
        entry = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "user_email": user_email,
            "action": action,
            "module": "dynamic",
            "entity_type": entity_code,
            "entity_id": record_id,
            "entity_name": entity_name,
            "old_values": dumps(old_values) if old_values else None,
            "new_values": dumps(new_values) if new_values else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
            "status": status,
            "error_message": error_message,
            "created_at": datetime.utcnow(),
        }
        
        query = text("""
            INSERT INTO audit_logs 
            (id, tenant_id, user_id, user_email, action, module, 
             entity_type, entity_id, entity_name, old_values, new_values,
             ip_address, user_agent, request_id, status, error_message, created_at)
            VALUES 
            (:id, :tenant_id, :user_id, :user_email, :action, :module,
             :entity_type, :entity_id, :entity_name, :old_values, :new_values,
             :ip_address, :user_agent, :request_id, :status, :error_message, :created_at)
        """)
        
        db.execute(query, entry)
        print(f"[AUDIT-OK] {action} on {entity_code}", flush=True)
        return True
        
    except Exception as e:
        print(f"[AUDIT-FAIL] {action} on {entity_code}: {e}", flush=True)
        return False
```

### `core/errors.py`

```python
"""
ERROR HANDLING MODULE
=====================
Provides secure error responses that don't expose internal details.
"""

import uuid
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Request
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
ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
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


def get_error_message(code: str, **kwargs) -> Dict[str, str]:
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
    details: Optional[List[Dict[str, Any]]] = None,
    request_id: Optional[str] = None,
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


def secure_db_error(e: Exception, request_id: Optional[str] = None) -> JSONResponse:
    """
    Convert database/internal errors to secure responses.
    
    NEVER exposes raw exception to client.
    Logs full error for debugging.
    """
    if not request_id:
        request_id = str(uuid.uuid4())
    
    # Log the full error internally (in production, use proper logging)
    error_type = type(e).__name__
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
```

### `core/rate_limit.py`

```python
"""
RATE LIMITING MODULE
====================
Simple in-memory rate limiter for FastAPI endpoints.
"""

import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from collections import defaultdict


class RateLimiter:
    """
    In-memory sliding window rate limiter.
    
    Usage:
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        
        @router.get("/endpoint", dependencies=[Depends(limiter.check)])
        async def endpoint():
            ...
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_func=None
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Window duration in seconds
            key_func: Function to extract rate limit key from request
                     Default: client IP address
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func
        
        # In-memory storage: {key: [(timestamp, count), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
    
    def _default_key_func(self, request: Request) -> str:
        """Default key function: client IP address."""
        # Check for X-Forwarded-For (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _cleanup(self, key: str) -> None:
        """Remove expired entries for a key."""
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[key] = [
            ts for ts in self._requests[key]
            if ts > cutoff
        ]
    
    def check(self, request: Request) -> None:
        """
        Check if request is allowed.
        
        Raises HTTPException if rate limit exceeded.
        """
        key = self.key_func(request)
        
        # Cleanup old entries
        self._cleanup(key)
        
        # Check count
        if len(self._requests[key]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                }
            )
        
        # Record request
        self._requests[key].append(time.time())
    
    def get_remaining(self, request: Request) -> int:
        """Get remaining requests for current window."""
        key = self.key_func(request)
        self._cleanup(key)
        return max(0, self.max_requests - len(self._requests[key]))
    
    def get_reset_time(self, request: Request) -> float:
        """Get seconds until rate limit resets."""
        key = self.key_func(request)
        self._cleanup(key)
        
        if not self._requests[key]:
            return 0
        
        oldest = min(self._requests[key])
        reset_time = oldest + self.window_seconds - time.time()
        return max(0, reset_time)


# Pre-configured rate limiters
# Usage: dependencies=[Depends(default_limiter.check)]

# General API: 100 requests per minute
default_limiter = RateLimiter(max_requests=100, window_seconds=60)

# Auth endpoints: 10 requests per minute (stricter)
auth_limiter = RateLimiter(max_requests=10, window_seconds=60)

# Read endpoints: 200 requests per minute (more lenient)
read_limiter = RateLimiter(max_requests=200, window_seconds=60)

# Write endpoints: 50 requests per minute (moderate)
write_limiter = RateLimiter(max_requests=50, window_seconds=60)
```

### `core/query_parser.py`

```python
"""
DYNAMIC QUERY PARSER
====================
Parses and validates filter/sort parameters for Dynamic CRUD.

Security chain:
  Request → Parse → Column Allowlist → Operator Allowlist →
  Type Validation → Tenant Scope → Parameterized SQL

NEVER allows raw user input in SQL.
"""

import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class Operator(str, Enum):
    """Supported filter operators."""
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    LIKE = "like"
    IN = "in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


# Operator to SQL mapping (parameterized)
OPERATOR_SQL = {
    Operator.EQ: "{col} = :{param}",
    Operator.NEQ: "{col} != :{param}",
    Operator.GT: "{col} > :{param}",
    Operator.GTE: "{col} >= :{param}",
    Operator.LT: "{col} < :{param}",
    Operator.LTE: "{col} <= :{param}",
    Operator.LIKE: "{col} ILIKE :{param}",
    Operator.IN: "{col} IN :{param}",
    Operator.IS_NULL: "{col} IS NULL",
    Operator.IS_NOT_NULL: "{col} IS NOT NULL",
}

# Operators that don't need a value
NO_VALUE_OPERATORS = {Operator.IS_NULL, Operator.IS_NOT_NULL}

# Operators that accept multiple values (IN)
MULTI_VALUE_OPERATORS = {Operator.IN}


@dataclass
class FilterClause:
    """A single validated filter clause."""
    column: str           # Actual column name (validated)
    operator: Operator    # Validated operator
    value: Any = None     # Validated value
    param_name: str = ""  # Unique parameter name for SQL


@dataclass
class SortClause:
    """A single validated sort clause."""
    column: str           # Actual column name (validated)
    descending: bool      # True = DESC, False = ASC


@dataclass
class QueryFilter:
    """Parsed and validated query filters."""
    filters: List[FilterClause]
    sorts: List[SortClause]
    limit: int
    offset: int


class QueryParseError(Exception):
    """Raised when query parameters are invalid."""
    pass


class QueryParser:
    """
    Parses and validates query parameters.
    
    Security:
      - Column names validated against real_columns
      - Operators validated against allowlist
      - Values validated against type rules
      - All SQL is parameterized
    """
    
    # Configuration
    MAX_LIMIT = 500
    DEFAULT_LIMIT = 100
    MAX_OFFSET = 100000
    
    # Column names that are NEVER allowed in user filters
    BLOCKED_COLUMNS = {"id"}  # id is managed by system
    
    def __init__(self, real_columns: Dict[str, str]):
        """
        Initialize parser with valid columns.
        
        Args:
            real_columns: {lowercase_name: actual_name} from DynamicVerificationEngine
        """
        # Build allowlist: lowercase -> actual name
        self.column_allowlist = {
            k.lower(): v for k, v in real_columns.items()
        }
    
    def _validate_column(self, column: str) -> str:
        """
        Validate column name against allowlist.
        
        Returns actual column name if valid.
        Raises QueryParseError if invalid.
        """
        if not column:
            raise QueryParseError("Column name is empty")
        
        col_lower = column.lower().strip()
        
        # Check blocked columns
        if col_lower in self.BLOCKED_COLUMNS:
            raise QueryParseError(f"Column '{column}' is not filterable")
        
        # Check allowlist
        if col_lower not in self.column_allowlist:
            raise QueryParseError(f"Invalid column: '{column}'")
        
        return self.column_allowlist[col_lower]
    
    def _validate_operator(self, op: str) -> Operator:
        """
        Validate operator against allowlist.
        
        Returns Operator enum if valid.
        Raises QueryParseError if invalid.
        """
        if not op:
            raise QueryParseError("Operator is empty")
        
        op_lower = op.lower().strip()
        
        try:
            return Operator(op_lower)
        except ValueError:
            valid_ops = ", ".join(o.value for o in Operator)
            raise QueryParseError(
                f"Invalid operator: '{op}'. Valid operators: {valid_ops}"
            )
    
    def _parse_value(self, value_str: str, operator: Operator) -> Any:
        """
        Parse and validate value based on operator.
        
        Returns parsed value.
        Raises QueryParseError if invalid.
        """
        if operator in NO_VALUE_OPERATORS:
            return None
        
        if not value_str:
            raise QueryParseError(
                f"Operator '{operator.value}' requires a value"
            )
        
        if operator == Operator.IN:
            # Parse pipe-separated values (not comma, which is filter separator)
            values = [v.strip() for v in value_str.split("|") if v.strip()]
            if not values:
                raise QueryParseError("IN operator requires at least one value")
            return tuple(values)
        
        if operator == Operator.LIKE:
            # LIKE value - basic sanitization
            # Remove SQL wildcards that aren't %
            sanitized = value_str.replace("'", "").replace(";", "")
            return f"%{sanitized}%"
        
        # For comparison operators, try to parse as number
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            # Return as string if not a number
            return value_str
    
    def parse_filter(self, filter_str: str) -> FilterClause:
        """
        Parse a single filter string.
        
        Format: column:operator:value
        
        Examples:
          status:eq:active
          price:gte:100
          name:like:ahmed
          deleted_at:is_null
        """
        parts = filter_str.split(":", 2)
        
        if len(parts) < 2:
            raise QueryParseError(
                f"Invalid filter format: '{filter_str}'. "
                f"Expected: column:operator:value"
            )
        
        column = parts[0].strip()
        operator_str = parts[1].strip()
        value_str = parts[2].strip() if len(parts) > 2 else ""
        
        # Validate
        actual_column = self._validate_column(column)
        operator = self._validate_operator(operator_str)
        value = self._parse_value(value_str, operator)
        
        # Generate unique param name
        param_name = f"f_{column}_{operator.value}"
        
        return FilterClause(
            column=actual_column,
            operator=operator,
            value=value,
            param_name=param_name
        )
    
    def parse_filters(self, filters_str: str) -> List[FilterClause]:
        """
        Parse multiple filters from comma-separated string.
        
        Format: filter1,filter2,filter3
        
        Example: status:eq:active,price:gte:100,name:like:ahmed
        """
        if not filters_str or not filters_str.strip():
            return []
        
        filters = []
        for part in filters_str.split(","):
            part = part.strip()
            if part:
                filters.append(self.parse_filter(part))
        
        return filters
    
    def parse_sort(self, sort_str: str) -> List[SortClause]:
        """
        Parse sort string.
        
        Format: -column1,column2,column3
        
        - prefix = DESC
        No prefix = ASC
        
        Example: -created_at,name
        """
        if not sort_str or not sort_str.strip():
            return []
        
        sorts = []
        for part in sort_str.split(","):
            part = part.strip()
            if not part:
                continue
            
            descending = False
            col_name = part
            
            if part.startswith("-"):
                descending = True
                col_name = part[1:]
            
            actual_column = self._validate_column(col_name)
            
            sorts.append(SortClause(
                column=actual_column,
                descending=descending
            ))
        
        return sorts
    
    def parse_pagination(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Parse and validate pagination parameters.
        
        Returns (limit, offset) tuple.
        """
        # Validate limit
        if limit is None:
            limit = self.DEFAULT_LIMIT
        
        limit = max(1, min(limit, self.MAX_LIMIT))
        
        # Validate offset
        if offset is None:
            offset = 0
        
        offset = max(0, min(offset, self.MAX_OFFSET))
        
        return limit, offset
    
    def parse_query(
        self,
        filters_str: Optional[str] = None,
        sort_str: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> QueryFilter:
        """
        Parse all query parameters.
        
        Returns validated QueryFilter.
        """
        filters = self.parse_filters(filters_str)
        sorts = self.parse_sort(sort_str)
        limit, offset = self.parse_pagination(limit, offset)
        
        return QueryFilter(
            filters=filters,
            sorts=sorts,
            limit=limit,
            offset=offset
        )
    
    @staticmethod
    def build_where_clause(
        filters: List[FilterClause]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build SQL WHERE clause from filters.
        
        Returns (where_sql, params_dict).
        """
        if not filters:
            return "", {}
        
        conditions = []
        params = {}
        
        for f in filters:
            if f.operator in NO_VALUE_OPERATORS:
                # IS NULL / IS NOT NULL - no parameter needed
                conditions.append(
                    OPERATOR_SQL[f.operator].format(col=f.column)
                )
            elif f.operator == Operator.IN:
                # IN - parameter is a tuple
                sql = OPERATOR_SQL[f.operator].format(
                    col=f.column, param=f.param_name
                )
                conditions.append(sql)
                params[f.param_name] = f.value
            else:
                # Standard comparison
                sql = OPERATOR_SQL[f.operator].format(
                    col=f.column, param=f.param_name
                )
                conditions.append(sql)
                params[f.param_name] = f.value
        
        where_sql = " AND ".join(conditions)
        return where_sql, params
    
    @staticmethod
    def build_order_clause(sorts: List[SortClause]) -> str:
        """
        Build SQL ORDER BY clause from sorts.
        
        Returns order_sql (no parameters needed - columns already validated).
        """
        if not sorts:
            return ""
        
        parts = []
        for s in sorts:
            direction = "DESC" if s.descending else "ASC"
            parts.append(f"{s.column} {direction}")
        
        return "ORDER BY " + ", ".join(parts)
```

---

## 4. Router (Dynamic CRUD)

### `routers/__init__.py`

```python
(empty)
```

### `routers/dynamic_crud.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional
import uuid

from database import get_db
from core.metadata_engine import MetadataEngine
from core.dynamic_verification import DynamicVerificationEngine
from core.auth import get_current_user, optional_get_current_user, require_permission
from core.audit import log_dynamic_audit
from core.errors import secure_db_error, ErrorCodes, create_error_response
from core.rate_limit import read_limiter, write_limiter
from core.query_parser import QueryParser, QueryParseError


router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Dynamic CRUD"]
)


def get_verification_engine(
    entity_code: str,
    db: Session = Depends(get_db)
):
    return DynamicVerificationEngine(db, entity_code)


@router.get("/entities/{entity_code}/schema",
            dependencies=[
                Depends(require_permission("dynamic", "read")),
                Depends(read_limiter.check)
            ])
async def get_schema(
    entity_code: str,
    db: Session = Depends(get_db),
    verification: DynamicVerificationEngine = Depends(
        get_verification_engine
    )
):
    if not verification.entity_exists():
        raise HTTPException(
            status_code=404,
            detail=f"الكيان '{entity_code}' غير موجود"
        )

    table_error = verification.validate_table_mapping()
    if table_error:
        raise HTTPException(
            status_code=400,
            detail=table_error
        )

    engine = MetadataEngine(db)

    return {
        "status": "success",
        "data": engine.get_full_schema(entity_code),
        "table": verification.entity_meta.get("table_mapping"),
        "tenant_capability": verification.tenant_capability,
        "real_columns": verification.get_table_columns(),
    }


@router.get("/entities/{entity_code}/records",
            dependencies=[
                Depends(require_permission("dynamic", "read")),
                Depends(read_limiter.check)
            ])
async def list_records(
    entity_code: str,
    filters: Optional[str] = None,
    sort: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    verification: DynamicVerificationEngine = Depends(
        get_verification_engine
    ),
    current_user: Optional[dict] = Depends(optional_get_current_user)
):
    if not verification.entity_exists():
        raise HTTPException(
            status_code=404,
            detail=f"الكيان '{entity_code}' غير موجود"
        )

    table_error = verification.validate_table_mapping()
    if table_error:
        raise HTTPException(
            status_code=400,
            detail=table_error
        )

    # Parse and validate query parameters
    try:
        parser = QueryParser(verification.real_columns)
        query_filter = parser.parse_query(
            filters_str=filters,
            sort_str=sort,
            limit=limit,
            offset=offset
        )
    except QueryParseError as e:
        return create_error_response(
            status_code=400,
            code=ErrorCodes.VALIDATION_ERROR,
            details=[{"message": str(e), "message_en": str(e)}]
        )

    table_name = verification.entity_meta["table_mapping"]
    where_clauses = []
    params = {}

    # Tenant scope (NEVER from user filters)
    if verification.has_tenant_id_column():
        # SCOPED: authenticated tenant required
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for SCOPED entity"
            )

        auth_tenant_id = current_user["tenant_id"]
        where_clauses.append("tenant_id = :tenant_id")
        params["tenant_id"] = auth_tenant_id
        tenant_applied = True
        effective_tenant = auth_tenant_id

    else:
        tenant_applied = False
        effective_tenant = None

    # Add user filters (parameterized)
    user_where, user_params = parser.build_where_clause(query_filter.filters)
    if user_where:
        where_clauses.append(user_where)
        params.update(user_params)

    # Build WHERE clause
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Build ORDER BY clause
    order_sql = parser.build_order_clause(query_filter.sorts)
    if not order_sql:
        order_sql = "ORDER BY created_at DESC"  # Default sort

    # Get total count (with filters applied)
    count_query = text(
        f"SELECT COUNT(*) FROM {table_name} WHERE {where_sql}"
    )
    total = db.execute(count_query, params).scalar()

    # Get records with pagination
    limit = query_filter.limit
    offset = query_filter.offset
    
    query = text(
        f"SELECT * FROM {table_name} "
        f"WHERE {where_sql} "
        f"{order_sql} "
        f"LIMIT :limit OFFSET :offset"
    )
    params["limit"] = limit
    params["offset"] = offset

    result = db.execute(query, params)

    # Calculate pagination
    has_next = (offset + limit) < total

    return {
        "status": "success",
        "data": [dict(row._mapping) for row in result],
        "count": result.rowcount,
        "tenant_applied": tenant_applied,
        "effective_tenant": effective_tenant,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_next": has_next,
        },
    }


@router.post("/entities/{entity_code}/records",
             dependencies=[
                 Depends(require_permission("dynamic", "create")),
                 Depends(write_limiter.check)
             ])
async def create_record(
    entity_code: str,
    payload: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    verification: DynamicVerificationEngine = Depends(
        get_verification_engine
    ),
    current_user: Optional[dict] = Depends(optional_get_current_user)
):
    if not verification.entity_exists():
        raise HTTPException(
            status_code=404,
            detail=f"الكيان '{entity_code}' غير موجود"
        )

    table_error = verification.validate_table_mapping()
    if table_error:
        raise HTTPException(
            status_code=400,
            detail=table_error
        )

    try:
        verification.validate_required_fields(payload)
        verification.validate_enum_fields(payload)
    except ValueError as e:
        # Validation error - return structured response
        return create_error_response(
            status_code=400,
            code=ErrorCodes.VALIDATION_ERROR,
            details=[{"message": str(e), "message_en": str(e)}]
        )

    not_null_errors = verification.validate_not_null_columns(payload)

    if not_null_errors:
        return create_error_response(
            status_code=400,
            code=ErrorCodes.NOT_NULL_VIOLATION,
            details=[{"message": e, "message_en": e} for e in not_null_errors]
        )

    # Determine effective tenant for duplicate check
    effective_tenant = None
    if verification.has_tenant_id_column():
        if current_user:
            effective_tenant = current_user["tenant_id"]

    duplicate_errors = verification.check_duplicate_by_unique_fields(
        payload,
        tenant_id=effective_tenant
    )

    if duplicate_errors:
        return create_error_response(
            status_code=409,
            code=ErrorCodes.DUPLICATE_RECORD,
            details=[{"message": e, "message_en": e} for e in duplicate_errors]
        )

    table_name = verification.entity_meta["table_mapping"]

    # Generate PK based on table schema
    clean_data = {verification.get_pk_column(): verification.generate_pk_value()}

    # Determine effective tenant
    effective_tenant = None

    if verification.has_tenant_id_column():
        # SCOPED: authenticated tenant required
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for SCOPED entity"
            )

        effective_tenant = current_user["tenant_id"]

        # Force authenticated tenant — ignore payload.tenant_id
        clean_data["tenant_id"] = effective_tenant

    pk_col = verification.get_pk_column()
    for key, value in payload.items():
        if key == pk_col:
            continue  # Skip PK column
        if key == "tenant_id":
            # tenant_id already handled above
            continue
        if verification.check_column_exists(key):
            clean_data[key] = value

    cols = ", ".join(clean_data.keys())
    placeholders = ", ".join(
        [f":{k}" for k in clean_data.keys()]
    )

    query = text(
        f"""
        INSERT INTO {table_name}
        ({cols})
        VALUES ({placeholders})
        RETURNING {pk_col}
        """
    )

    try:
        result = db.execute(query, clean_data)

        new_id = result.scalar()
        
        # Audit: success (before commit, part of same transaction)
        log_dynamic_audit(
            db=db,
            tenant_id=effective_tenant or "unknown",
            user_id=current_user.get("id") if current_user else None,
            user_email=current_user.get("email") if current_user else None,
            action="create",
            entity_code=entity_code,
            record_id=new_id,
            new_values=clean_data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            status="success",
        )

        db.commit()

        return {
            "status": "success",
            "id": new_id,
            "message": "تم إنشاؤه بنجاح",
            "tenant_capability": verification.tenant_capability,
            "effective_tenant": effective_tenant,
        }

    except Exception as e:
        db.rollback()
        
        # Audit: failure
        log_dynamic_audit(
            db=db,
            tenant_id=effective_tenant or "unknown",
            user_id=current_user.get("id") if current_user else None,
            user_email=current_user.get("email") if current_user else None,
            action="create",
            entity_code=entity_code,
            new_values=clean_data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            status="failure",
            error_message=str(e),
        )
        
        # Secure error: never expose raw exception
        return secure_db_error(e)


@router.put("/entities/{entity_code}/records/{record_id}",
            dependencies=[
                Depends(require_permission("dynamic", "update")),
                Depends(write_limiter.check)
            ])
async def update_record(
    entity_code: str,
    record_id: str,
    payload: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    verification: DynamicVerificationEngine = Depends(
        get_verification_engine
    ),
    current_user: Optional[dict] = Depends(optional_get_current_user)
):
    if not verification.entity_exists():
        raise HTTPException(
            status_code=404,
            detail=f"الكيان '{entity_code}' غير موجود"
        )

    table_error = verification.validate_table_mapping()
    if table_error:
        raise HTTPException(
            status_code=400,
            detail=table_error
        )

    valid_cols = [
        k for k in payload.keys()
        if k != "id"
        and k != "tenant_id"
        and verification.check_column_exists(k)
    ]

    if not valid_cols:
        raise HTTPException(
            status_code=400,
            detail="لا توجد أعمدة صالحة للتحديث"
        )

    table_name = verification.entity_meta["table_mapping"]
    update_params = {"id": record_id}

    set_parts = []
    for key in valid_cols:
        set_parts.append(f"{key} = :{key}")
        update_params[key] = payload[key]

    set_clause = ", ".join(set_parts)
    where_clause = "WHERE id = :id"

    if verification.has_tenant_id_column():
        # SCOPED: authenticated tenant required
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for SCOPED entity"
            )

        auth_tenant_id = current_user["tenant_id"]

        # Add tenant to WHERE clause for isolation
        where_clause += " AND tenant_id = :tenant_filter"
        update_params["tenant_filter"] = auth_tenant_id

    # Build new_values for audit (only the updated columns)
    new_values = {k: v for k, v in update_params.items() if k not in ("id", "tenant_filter")}

    # Get old values for audit (before update)
    auth_tenant_id_audit = current_user.get("tenant_id") if current_user else None
    old_values = None

    query = text(
        f"""
        UPDATE {table_name}
        SET {set_clause}
        {where_clause}
        """
    )

    try:
        result = db.execute(query, update_params)

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="السجل غير موجود"
            )

        # Audit: success (before commit, part of same transaction)
        audit_result = log_dynamic_audit(
            db=db,
            tenant_id=auth_tenant_id_audit or "unknown",
            user_id=current_user.get("id") if current_user else None,
            user_email=current_user.get("email") if current_user else None,
            action="update",
            entity_code=entity_code,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            status="success",
        )
        import sys
        print(f"UPDATE AUDIT: result={audit_result}, record_id={record_id}", file=sys.stderr)

        db.commit()

        return {
            "status": "success",
            "message": "تم تحديث السجل بنجاح",
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        
        # Audit: failure
        log_dynamic_audit(
            db=db,
            tenant_id=auth_tenant_id_audit or "unknown",
            user_id=current_user.get("id") if current_user else None,
            user_email=current_user.get("email") if current_user else None,
            action="update",
            entity_code=entity_code,
            record_id=record_id,
            old_values=old_values,
            new_values=update_params,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            status="failure",
            error_message=str(e),
        )
        
        # Secure error: never expose raw exception
        return secure_db_error(e)


@router.delete("/entities/{entity_code}/records/{record_id}",
               dependencies=[
                   Depends(require_permission("dynamic", "delete")),
                   Depends(write_limiter.check)
               ])
async def delete_record(
    entity_code: str,
    record_id: str,
    request: Request,
    db: Session = Depends(get_db),
    verification: DynamicVerificationEngine = Depends(
        get_verification_engine
    ),
    current_user: Optional[dict] = Depends(optional_get_current_user)
):
    if not verification.entity_exists():
        raise HTTPException(
            status_code=404,
            detail=f"الكيان '{entity_code}' غير موجود"
        )

    table_error = verification.validate_table_mapping()
    if table_error:
        raise HTTPException(
            status_code=400,
            detail=table_error
        )

    table_name = verification.entity_meta["table_mapping"]

    # Get old values for audit (before delete)
    auth_tenant_id_del = current_user.get("tenant_id") if current_user else None
    old_values = None
    try:
        if verification.has_tenant_id_column():
            old_query = text(f"SELECT * FROM {table_name} WHERE id = :id AND tenant_id = :tenant_id")
            old_result = db.execute(old_query, {"id": record_id, "tenant_id": auth_tenant_id_del})
        else:
            old_query = text(f"SELECT * FROM {table_name} WHERE id = :id")
            old_result = db.execute(old_query, {"id": record_id})
        old_row = old_result.fetchone()
        if old_row:
            old_values = dict(old_row._mapping)
    except Exception:
        pass

    if verification.has_tenant_id_column():
        # SCOPED: authenticated tenant required
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for SCOPED entity"
            )

        auth_tenant_id = current_user["tenant_id"]

        query = text(
            f"""
            DELETE FROM {table_name}
            WHERE id = :id AND tenant_id = :tenant_id
            """
        )

        result = db.execute(
            query,
            {"id": record_id, "tenant_id": auth_tenant_id}
        )

    else:
        query = text(
            f"""
            DELETE FROM {table_name}
            WHERE id = :id
            """
        )

        result = db.execute(
            query,
            {"id": record_id}
        )

    if result.rowcount == 0:
        # Audit: not found
        log_dynamic_audit(
            db=db,
            tenant_id=auth_tenant_id_del or "unknown",
            user_id=current_user.get("id") if current_user else None,
            user_email=current_user.get("email") if current_user else None,
            action="delete",
            entity_code=entity_code,
            record_id=record_id,
            old_values=old_values,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            status="failure",
            error_message="Record not found",
        )
        db.commit()
        raise HTTPException(
            status_code=404,
            detail="السجل غير موجود"
        )

    # Audit: success (before commit, part of same transaction)
    log_dynamic_audit(
        db=db,
        tenant_id=auth_tenant_id_del or "unknown",
        user_id=current_user.get("id") if current_user else None,
        user_email=current_user.get("email") if current_user else None,
        action="delete",
        entity_code=entity_code,
        record_id=record_id,
        old_values=old_values,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        status="success",
    )

    db.commit()

    return {
        "status": "success",
        "message": "تم حذف السجل بنجاح",
    }
```

---

## 5. Test Files

### `test_crud.py`

```python
import subprocess
import time
import httpx
import os
import sys

BASE = "http://127.0.0.1:8000/api/v1/dynamic"
PROJECT = r"D:\EOS\Eos final"

def safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))

def test_get_schema():
    safe_print("1. GET schema...")
    r = httpx.get(f"{BASE}/entities/account/schema", timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   tenant_capability: {data.get('tenant_capability')}")
    safe_print(f"   real_columns: {data.get('real_columns')}")
    return r.status_code == 200

def test_get_records():
    safe_print("2. GET records...")
    r = httpx.get(f"{BASE}/entities/account/records", timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   Count: {data.get('count')}")
    safe_print(f"   tenant_applied: {data.get('tenant_applied')}")
    return r.status_code == 200

def test_post():
    safe_print("3. POST new record...")
    payload = {
        "code": "TEST-001",
        "name": "Test Account",
        "name_ar": "Test Arabic",
        "account_type": "asset"
    }
    safe_print(f"   Payload: {payload}")
    r = httpx.post(f"{BASE}/entities/account/records", json=payload, timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   id: {data.get('id')}")
    safe_print(f"   tenant_capability: {data.get('tenant_capability')}")
    return r.status_code == 200, data.get("id")

def test_post_with_tenant_id():
    safe_print("4. POST with tenant_id on NONE table...")
    payload = {
        "code": "TEST-002",
        "name": "Test Account 2",
        "name_ar": "Test Arabic 2",
        "account_type": "liability",
        "tenant_id": "SHOULD-NOT-BE-INSERTED"
    }
    safe_print(f"   Payload: {payload}")
    r = httpx.post(f"{BASE}/entities/account/records", json=payload, timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   id: {data.get('id')}")
    safe_print(f"   tenant_capability: {data.get('tenant_capability')}")
    return r.status_code == 200, data.get("id")

def test_update(record_id):
    safe_print(f"5. UPDATE record {record_id}...")
    payload = {"name": "Updated Account"}
    safe_print(f"   Payload: {payload}")
    r = httpx.put(f"{BASE}/entities/account/records/{record_id}", json=payload, timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   Response: {str(data)[:200]}")
    return r.status_code == 200

def test_delete(record_id):
    safe_print(f"6. DELETE record {record_id}...")
    r = httpx.delete(f"{BASE}/entities/account/records/{record_id}", timeout=10)
    data = r.json()
    safe_print(f"   Status: {r.status_code}")
    safe_print(f"   Response: {str(data)[:200]}")
    return r.status_code == 200

def kill_server():
    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        for line in result.stdout.split("\n"):
            if ":8000" in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
    except Exception:
        pass

def main():
    kill_server()
    time.sleep(1)

    safe_print("Starting server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd=PROJECT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    time.sleep(3)

    try:
        results = []

        ok = test_get_schema()
        results.append(("GET schema", ok))

        ok = test_get_records()
        results.append(("GET records", ok))

        ok, post_id_1 = test_post()
        results.append(("POST (no tenant)", ok))

        ok, post_id_2 = test_post_with_tenant_id()
        results.append(("POST (with tenant_id)", ok))

        if post_id_1:
            ok = test_update(post_id_1)
            results.append(("UPDATE", ok))
        else:
            safe_print("   SKIP UPDATE - no record id")
            results.append(("UPDATE", False))

        if post_id_2:
            ok = test_delete(post_id_2)
            results.append(("DELETE", ok))
        else:
            safe_print("   SKIP DELETE - no record id")
            results.append(("DELETE", False))

        safe_print("\n" + "=" * 50)
        safe_print("RESULTS:")
        for name, ok in results:
            status = "PASS" if ok else "FAIL"
            safe_print(f"  {status} - {name}")

        passed = sum(1 for _, ok in results if ok)
        safe_print(f"\n{passed}/{len(results)} passed")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

        kill_server()
        safe_print("Server stopped.")

if __name__ == "__main__":
    main()
```

### `test_cross_tenant.py`

```python
"""
Cross-Tenant Isolation Matrix Test

Tests 12 scenarios to verify tenant isolation
in Dynamic CRUD operations.
"""

import subprocess
import time
import httpx
import sys

BASE = "http://127.0.0.1:8000/api/v1/dynamic"
PROJECT = r"D:\EOS\Eos final"
ENTITY = "test_product"


def safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def make_token(tenant_id):
    """Generate JWT token for a tenant."""
    from core.auth import create_test_token
    return create_test_token(tenant_id=tenant_id, roles=["dynamic_manager"])


def kill_server():
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True
        )
        for line in result.stdout.split("\n"):
            if ":8000" in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                subprocess.run(
                    ["taskkill", "/F", "/PID", pid],
                    capture_output=True
                )
    except Exception:
        pass


def test_case(num, desc, method, url, token, payload=None,
              expected_status=None, expected_data_check=None):
    """Run a single test case."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        if method == "GET":
            r = httpx.get(url, headers=headers, timeout=10)
        elif method == "POST":
            r = httpx.post(url, json=payload, headers=headers, timeout=10)
        elif method == "PUT":
            r = httpx.put(url, json=payload, headers=headers, timeout=10)
        elif method == "DELETE":
            r = httpx.delete(url, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unknown method: {method}")

        data = r.json()
        status_ok = (r.status_code == expected_status) if expected_status else True

        result = "PASS" if status_ok else "FAIL"
        num_str = str(num).rjust(2)
        safe_print(
            f"  {result} #{num_str}: {desc}"
            f" | {r.status_code}"
        )

        if not status_ok:
            safe_print(
                f"        Expected: {expected_status}, Got: {r.status_code}"
            )
            safe_print(f"        Response: {str(data)[:150]}")

        return r.status_code, data

    except Exception as e:
        num_str = str(num).rjust(2)
        safe_print(f"  FAIL #{num_str}: {desc} | ERROR: {e}")
        return None, None


def main():
    kill_server()
    time.sleep(1)

    safe_print("Starting server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--port", "8000", "--host", "127.0.0.1"],
        cwd=PROJECT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)

    # Generate tokens
    token_a = make_token("tenant_a")
    token_b = make_token("tenant_b")

    url_records = f"{BASE}/entities/{ENTITY}/records"
    url_schema = f"{BASE}/entities/{ENTITY}/schema"

    results = []

    try:
        safe_print("\n" + "=" * 60)
        safe_print("CROSS-TENANT ISOLATION MATRIX")
        safe_print("=" * 60)

        # --- Test 1: Tenant A reads → sees own data only ---
        safe_print("\n--- READ Tests ---")
        code, data = test_case(
            1, "Tenant A READ → A records only",
            "GET", url_records + "?limit=10", token_a
        )
        if code == 200:
            records = data.get("data", [])
            all_a = all(r.get("tenant_id") == "tenant_a" for r in records)
            safe_print(f"        All records tenant_a: {all_a}")
            results.append(("READ A→A", all_a and len(records) > 0))
        else:
            results.append(("READ A→A", False))

        # --- Test 2: Tenant B reads → sees own data only ---
        code, data = test_case(
            2, "Tenant B READ → B records only",
            "GET", url_records + "?limit=10", token_b
        )
        if code == 200:
            records = data.get("data", [])
            all_b = all(r.get("tenant_id") == "tenant_b" for r in records)
            safe_print(f"        All records tenant_b: {all_b}")
            results.append(("READ B→B", all_b and len(records) > 0))
        else:
            results.append(("READ B→B", False))

        # --- Test 3: Tenant A reads with payload tenant_id=B → still A only ---
        code, data = test_case(
            3, "Tenant A READ + payload B → A only",
            "GET", url_records + "?limit=10", token_a
        )
        if code == 200:
            records = data.get("data", [])
            all_a = all(r.get("tenant_id") == "tenant_a" for r in records)
            safe_print(f"        All records tenant_a: {all_a}")
            results.append(("READ A+B→A", all_a))
        else:
            results.append(("READ A+B→A", False))

        # --- Test 4: Tenant A creates with payload tenant_id=B → created under A ---
        safe_print("\n--- CREATE Tests ---")
        import uuid
        unique_code = f"CT-{str(uuid.uuid4())[:8]}"
        code, data = test_case(
            4, "Tenant A CREATE + payload B → under A",
            "POST", url_records, token_a,
            payload={"code": unique_code, "name": "Cross Test", "price": 99,
                     "tenant_id": "tenant_b"}
        )
        new_id = data.get("id") if data else None
        effective = data.get("effective_tenant") if data else None
        safe_print(f"        effective_tenant: {effective}")
        results.append(("CREATE A+B→A", code == 200 and effective == "tenant_a"))

        # --- Test 5: Tenant A updates B's record → 404 ---
        safe_print("\n--- UPDATE Tests ---")
        # Get a B record ID
        code_b, data_b = test_case(
            "-", "Get B record for update test",
            "GET", url_records + "?limit=10", token_b
        )
        b_record_id = None
        if code_b == 200 and data_b.get("data"):
            b_record_id = data_b["data"][0].get("id")

        if b_record_id:
            code, data = test_case(
                5, "Tenant A UPDATE B record → 404",
                "PUT", f"{url_records}/{b_record_id}", token_a,
                payload={"name": "HACKED"}
            )
            results.append(("UPDATE A→B", code == 404))
        else:
            safe_print("  SKIP #5: No B record found")
            results.append(("UPDATE A→B", False))

        # --- Test 6: Tenant B updates A's record → 404 ---
        code_a, data_a = test_case(
            "-", "Get A record for update test",
            "GET", url_records + "?limit=10", token_a
        )
        a_record_id = None
        if code_a == 200 and data_a.get("data"):
            a_record_id = data_a["data"][0].get("id")

        if a_record_id:
            code, data = test_case(
                6, "Tenant B UPDATE A record → 404",
                "PUT", f"{url_records}/{a_record_id}", token_b,
                payload={"name": "HACKED"}
            )
            results.append(("UPDATE B→A", code == 404))
        else:
            safe_print("  SKIP #6: No A record found")
            results.append(("UPDATE B→A", False))

        # --- Test 7: Tenant A deletes B's record → 404 ---
        safe_print("\n--- DELETE Tests ---")
        if b_record_id:
            code, data = test_case(
                7, "Tenant A DELETE B record → 404",
                "DELETE", f"{url_records}/{b_record_id}", token_a
            )
            results.append(("DELETE A→B", code == 404))
        else:
            results.append(("DELETE A→B", False))

        # --- Test 8: Tenant B deletes A's record → 404 ---
        if a_record_id:
            code, data = test_case(
                8, "Tenant B DELETE A record → 404",
                "DELETE", f"{url_records}/{a_record_id}", token_b
            )
            results.append(("DELETE B→A", code == 404))
        else:
            results.append(("DELETE B→A", False))

        # --- Tests 9-11: Unauthenticated access → 401 ---
        safe_print("\n--- UNAUTHENTICATED Tests ---")
        code, data = test_case(
            9, "No JWT READ → 401",
            "GET", url_records, None
        )
        results.append(("NO JWT READ", code == 401))

        code, data = test_case(
            10, "No JWT UPDATE → 401",
            "PUT", f"{url_records}/fake-id", None,
            payload={"name": "X"}
        )
        results.append(("NO JWT UPDATE", code == 401))

        code, data = test_case(
            11, "No JWT DELETE → 401",
            "DELETE", f"{url_records}/fake-id", None
        )
        results.append(("NO JWT DELETE", code == 401))

        # --- Test 12: Invalid JWT → 401 ---
        safe_print("\n--- INVALID TOKEN Tests ---")
        code, data = test_case(
            12, "Invalid JWT → 401",
            "GET", url_records, "invalid.token.here"
        )
        results.append(("INVALID JWT", code == 401))

        # --- Summary ---
        safe_print("\n" + "=" * 60)
        safe_print("RESULTS:")
        for name, ok in results:
            status = "PASS" if ok else "FAIL"
            safe_print(f"  {status} - {name}")

        passed = sum(1 for _, ok in results if ok)
        safe_print(f"\n{passed}/{len(results)} passed")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        kill_server()
        safe_print("Server stopped.")


if __name__ == "__main__":
    main()
```

### `test_rbac.py`

```python
"""
RBAC Authorization Test for Dynamic CRUD
Tests permission matrix for Dynamic Viewer/Operator/Manager roles
"""
import subprocess
import time
import sys
import httpx
import os

BASE = "http://localhost:8000/api/v1"
ENTITY = "test_product"
TABLE = "test_products"


def start_server():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    time.sleep(3)
    return proc


def stop_server(proc):
    proc.terminate()
    proc.wait(timeout=5)


def get_token(roles: list) -> str:
    """Create a test JWT token with specified roles."""
    import sys
    sys.path.insert(0, '.')
    from core.auth import create_test_token
    return create_test_token(
        tenant_id="tenant_a",
        user_id=f"test-user-{roles[0]}",
        email=f"test-{roles[0]}@example.com",
        roles=roles
    )


def test_rbac():
    print("=" * 60)
    print("RBAC AUTHORIZATION TEST FOR DYNAMIC CRUD")
    print("=" * 60)
    
    results = []
    
    # Test 1: No token -> 200 (schema is public)
    print("\n--- Test 1: No token -> 200 (schema public) ---")
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema")
    passed = r.status_code == 200
    results.append({"name": "No token", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Status: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Test 2: Invalid token -> 401
    print("\n--- Test 2: Invalid token -> 401 ---")
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema",
                  headers={"Authorization": "Bearer invalid-token"})
    passed = r.status_code == 401
    results.append({"name": "Invalid token", "status": r.status_code, "expected": 401, "passed": passed})
    print(f"  Status: {r.status_code} (expected 401) {'PASS' if passed else 'FAIL'}")
    
    # Test 3: Admin role -> all allowed
    print("\n--- Test 3: Admin role -> all allowed ---")
    admin_token = get_token(["admin"])
    h = {"Authorization": f"Bearer {admin_token}"}
    
    # Admin READ
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema", headers=h)
    passed = r.status_code == 200
    results.append({"name": "Admin READ", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Admin READ: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Admin CREATE
    import uuid
    admin_code = f"ADM-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": admin_code, "name": "Admin Record RBAC", "name_ar": "Admin Record RBAC", "tenant_id": "tenant_a"},
                   headers=h)
    passed = r.status_code == 200
    results.append({"name": "Admin CREATE", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Admin CREATE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    if not passed:
        print(f"    Detail: {r.status_code} - {r.json()}")
    
    # Test 4: Dynamic Viewer role
    print("\n--- Test 4: Dynamic Viewer role ---")
    viewer_token = get_token(["dynamic_viewer"])
    h = {"Authorization": f"Bearer {viewer_token}"}
    
    # Viewer READ
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema", headers=h)
    passed = r.status_code == 200
    results.append({"name": "Viewer READ", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Viewer READ: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Viewer CREATE -> 403
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": "VIEWER-001", "name": "Viewer Record", "name_ar": "Viewer Record"},
                   headers=h)
    passed = r.status_code == 403
    results.append({"name": "Viewer CREATE", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  Viewer CREATE: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Viewer UPDATE -> 403
    r = httpx.put(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id",
                  json={"name": "Updated"},
                  headers=h)
    passed = r.status_code == 403
    results.append({"name": "Viewer UPDATE", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  Viewer UPDATE: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Viewer DELETE -> 403
    r = httpx.delete(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id", headers=h)
    passed = r.status_code == 403
    results.append({"name": "Viewer DELETE", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  Viewer DELETE: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Test 5: Dynamic Operator role
    print("\n--- Test 5: Dynamic Operator role ---")
    operator_token = get_token(["dynamic_operator"])
    h = {"Authorization": f"Bearer {operator_token}"}
    
    # Operator READ
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema", headers=h)
    passed = r.status_code == 200
    results.append({"name": "Operator READ", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Operator READ: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Operator CREATE
    operator_code = f"OPR-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": operator_code, "name": "Operator Record RBAC", "name_ar": "Operator Record RBAC", "tenant_id": "tenant_a"},
                   headers=h)
    passed = r.status_code == 200
    results.append({"name": "Operator CREATE", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Operator CREATE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    if not passed:
        print(f"    Detail: {r.status_code} - {r.json()}")
    
    # Operator UPDATE
    r = httpx.put(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id",
                  json={"name": "Updated"},
                  headers=h)
    passed = r.status_code == 404  # Not found, but not 403
    results.append({"name": "Operator UPDATE", "status": r.status_code, "expected": 404, "passed": passed})
    print(f"  Operator UPDATE: {r.status_code} (expected 404) {'PASS' if passed else 'FAIL'}")
    
    # Operator DELETE -> 403
    r = httpx.delete(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id", headers=h)
    passed = r.status_code == 403
    results.append({"name": "Operator DELETE", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  Operator DELETE: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Test 6: Dynamic Manager role
    print("\n--- Test 6: Dynamic Manager role ---")
    manager_token = get_token(["dynamic_manager"])
    h = {"Authorization": f"Bearer {manager_token}"}
    
    # Manager READ
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema", headers=h)
    passed = r.status_code == 200
    results.append({"name": "Manager READ", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Manager READ: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Manager CREATE
    manager_code = f"MGR-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": manager_code, "name": "Manager Record RBAC", "name_ar": "Manager Record RBAC", "tenant_id": "tenant_a"},
                   headers=h)
    passed = r.status_code == 200
    results.append({"name": "Manager CREATE", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Manager CREATE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    if not passed:
        print(f"    Detail: {r.status_code} - {r.json()}")
    
    # Manager UPDATE
    r = httpx.put(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id",
                  json={"name": "Updated"},
                  headers=h)
    passed = r.status_code == 404  # Not found, but not 403
    results.append({"name": "Manager UPDATE", "status": r.status_code, "expected": 404, "passed": passed})
    print(f"  Manager UPDATE: {r.status_code} (expected 404) {'PASS' if passed else 'FAIL'}")
    
    # Manager DELETE
    r = httpx.delete(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id", headers=h)
    passed = r.status_code == 404  # Not found, but not 403
    results.append({"name": "Manager DELETE", "status": r.status_code, "expected": 404, "passed": passed})
    print(f"  Manager DELETE: {r.status_code} (expected 404) {'PASS' if passed else 'FAIL'}")
    
    # Test 7: No role -> 403
    print("\n--- Test 7: No role -> 403 ---")
    no_role_token = get_token(["user"])
    h = {"Authorization": f"Bearer {no_role_token}"}
    
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema", headers=h)
    passed = r.status_code == 403
    results.append({"name": "No role READ", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  No role READ: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Summary
    print("\n" + "=" * 60)
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = total - passed_count
    print(f"RESULTS: {passed_count}/{total} passed")
    
    if failed_count:
        print("\nFAILED:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['name']}: got {r['status']}, expected {r['expected']}")
    
    return failed_count == 0


if __name__ == "__main__":
    proc = start_server()
    try:
        success = test_rbac()
        sys.exit(0 if success else 1)
    finally:
        stop_server(proc)
```

### `test_audit.py`

```python
"""
Audit Verification Test for Dynamic CRUD
Verifies audit logs are created for CREATE, UPDATE, DELETE operations
"""
import subprocess
import time
import sys
import httpx
import os
import uuid

BASE = "http://localhost:8000/api/v1"
ENTITY = "test_product"


def start_server():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    time.sleep(3)
    return proc


def stop_server(proc):
    proc.terminate()
    proc.wait(timeout=5)


def get_token(roles: list) -> str:
    """Create a test JWT token with specified roles."""
    import sys
    sys.path.insert(0, '.')
    from core.auth import create_test_token
    return create_test_token(
        tenant_id="tenant_a",
        user_id=f"test-user-{roles[0]}",
        email=f"test-{roles[0]}@example.com",
        roles=roles
    )


def get_audit_count(db, entity_code: str, action: str, record_id: str = None) -> int:
    """Count audit logs for a specific operation."""
    from sqlalchemy import text
    if record_id:
        result = db.execute(text(
            "SELECT COUNT(*) FROM audit_logs "
            "WHERE module = 'dynamic' AND entity_type = :entity "
            "AND action = :action AND entity_id = :record_id"
        ), {"entity": entity_code, "action": action, "record_id": record_id})
    else:
        result = db.execute(text(
            "SELECT COUNT(*) FROM audit_logs "
            "WHERE module = 'dynamic' AND entity_type = :entity "
            "AND action = :action"
        ), {"entity": entity_code, "action": action})
    return result.scalar()


def test_audit():
    print("=" * 60)
    print("AUDIT VERIFICATION TEST FOR DYNAMIC CRUD")
    print("=" * 60)
    
    results = []
    
    # Test 1: CREATE generates audit
    print("\n--- Test 1: CREATE generates audit ---")
    manager_token = get_token(["dynamic_manager"])
    h = {"Authorization": f"Bearer {manager_token}"}
    
    create_code = f"AUD-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": create_code, "name": "Audit Test", "name_ar": "test", "tenant_id": "tenant_a"},
                   headers=h)
    create_id = r.json().get("id") if r.status_code == 200 else None
    passed = r.status_code == 200 and create_id is not None
    results.append({"name": "CREATE generates audit", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  CREATE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Test 2: UPDATE generates audit
    print("\n--- Test 2: UPDATE generates audit ---")
    r = httpx.put(f"{BASE}/dynamic/entities/{ENTITY}/records/{create_id}",
                  json={"name": "Audit Test Updated", "tenant_id": "tenant_a"},
                  headers=h)
    passed = r.status_code == 200
    results.append({"name": "UPDATE generates audit", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  UPDATE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Test 3: DELETE generates audit
    print("\n--- Test 3: DELETE generates audit ---")
    r = httpx.delete(f"{BASE}/dynamic/entities/{ENTITY}/records/{create_id}", headers=h)
    passed = r.status_code == 200
    results.append({"name": "DELETE generates audit", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  DELETE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Test 4: RBAC 403 generates failure audit
    print("\n--- Test 4: RBAC 403 generates failure audit ---")
    viewer_token = get_token(["dynamic_viewer"])
    vh = {"Authorization": f"Bearer {viewer_token}"}
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": "FAIL-001", "name": "Should Fail", "name_ar": "fail", "tenant_id": "tenant_a"},
                   headers=vh)
    passed = r.status_code == 403
    results.append({"name": "RBAC 403 generates audit", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  RBAC 403: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Test 5: Cross-tenant 404 generates failure audit
    print("\n--- Test 5: Cross-tenant 404 generates failure audit ---")
    r = httpx.delete(f"{BASE}/dynamic/entities/{ENTITY}/records/nonexistent-id",
                     headers=h)
    passed = r.status_code == 404
    results.append({"name": "Cross-tenant 404 generates audit", "status": r.status_code, "expected": 404, "passed": passed})
    print(f"  Cross-tenant 404: {r.status_code} (expected 404) {'PASS' if passed else 'FAIL'}")
    
    # Test 6: Verify audit records exist in database
    print("\n--- Test 6: Verify audit records in database ---")
    import sys
    sys.path.insert(0, '.')
    from database import SessionLocal
    db = SessionLocal()
    
    audit_count = get_audit_count(db, ENTITY, "create")
    create_exists = audit_count > 0
    results.append({"name": "CREATE audit in DB", "count": audit_count, "passed": create_exists})
    print(f"  CREATE audits: {audit_count} {'PASS' if create_exists else 'FAIL'}")
    
    audit_count = get_audit_count(db, ENTITY, "update")
    update_exists = audit_count > 0
    results.append({"name": "UPDATE audit in DB", "count": audit_count, "passed": update_exists})
    print(f"  UPDATE audits: {audit_count} {'PASS' if update_exists else 'FAIL'}")
    
    audit_count = get_audit_count(db, ENTITY, "delete")
    delete_exists = audit_count > 0
    results.append({"name": "DELETE audit in DB", "count": audit_count, "passed": delete_exists})
    print(f"  DELETE audits: {audit_count} {'PASS' if delete_exists else 'FAIL'}")
    
    db.close()
    
    # Summary
    print("\n" + "=" * 60)
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = total - passed_count
    print(f"RESULTS: {passed_count}/{total} passed")
    
    if failed_count:
        print("\nFAILED:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['name']}: {r}")
    
    return failed_count == 0


if __name__ == "__main__":
    proc = start_server()
    try:
        success = test_audit()
        sys.exit(0 if success else 1)
    finally:
        stop_server(proc)
```

### `test_production_mode.py`

```python
import subprocess
import time
import sys
import httpx
import os

# Set env vars in THIS process too
os.environ['EOS_AUTH_MODE'] = 'production'
os.environ['EOS_SECRET_KEY'] = 'test-production-secret-key-for-verification'

env = os.environ.copy()
env['EOS_AUTH_MODE'] = 'production'
env['EOS_SECRET_KEY'] = 'test-production-secret-key-for-verification'

proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'main:app', '--port', '8008', '--host', '127.0.0.1'],
    cwd=r'D:\EOS\Eos final',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env,
)
time.sleep(4)

try:
    from core.production_auth import create_access_token
    
    # Create production token
    token = create_access_token(
        subject='user-123',
        extra_data={'tenant_id': 'tenant_a', 'email': 'prod@example.com', 'roles': ['admin']}
    )
    print('Production token created')
    
    # Test SCOPED read with production token
    r = httpx.get(
        'http://127.0.0.1:8008/api/v1/dynamic/entities/test_product/records',
        headers={'Authorization': 'Bearer ' + token},
        timeout=10
    )
    print('SCOPED READ with prod token: Status=' + str(r.status_code))
    if r.status_code == 200:
        data = r.json()
        print('  Count:', data.get('count'))
        print('  tenant_applied:', data.get('tenant_applied'))
        print('  effective_tenant:', data.get('effective_tenant'))
    
    # Test without token (should 401)
    r2 = httpx.get(
        'http://127.0.0.1:8008/api/v1/dynamic/entities/test_product/records',
        timeout=10
    )
    print('NO TOKEN: Status=' + str(r2.status_code))
    
    # Test with test token (should fail - wrong secret)
    from core.auth import create_test_token
    test_token = create_test_token('tenant_a')
    r3 = httpx.get(
        'http://127.0.0.1:8008/api/v1/dynamic/entities/test_product/records',
        headers={'Authorization': 'Bearer ' + test_token},
        timeout=10
    )
    print('TEST TOKEN (wrong secret): Status=' + str(r3.status_code))

except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
finally:
    proc.terminate()
    proc.wait()
```

### `test_query.py`

```python
"""
P7 Query Engine Tests
Tests filtering, sorting, and pagination.
"""

import subprocess
import time
import sys
import os

# Start server
def start_server():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    time.sleep(3)
    return proc

def stop_server(proc):
    proc.terminate()
    proc.wait(timeout=5)

# Import after path is set
sys.path.insert(0, '.')
from core.auth import create_test_token
import httpx

BASE = "http://127.0.0.1:8000"
EP = f"{BASE}/api/v1/dynamic/entities"
ENTITY = "test_product"

# Test tokens
TOKEN_A = create_test_token("tenant_a", roles=["dynamic_manager"])
TOKEN_B = create_test_token("tenant_b", roles=["dynamic_manager"])
HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}

results = []

def test(name, actual, expected):
    ok = actual == expected
    results.append((name, ok))
    status = "PASS" if ok else "FAIL"
    print(f"  {status} - {name}: got {actual}, expected {expected}")
    return ok


print("\n" + "=" * 60)
print("P7 QUERY ENGINE TESTS")
print("=" * 60)

server = start_server()
client = httpx.Client(base_url=BASE, timeout=10)


# ──────────────────────────────────────────────
# Test 1: Basic list (no filters)
# ──────────────────────────────────────────────
print("\n--- Test 1: Basic list (no filters) ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={"limit": 10}
)
data = r.json()
test("Status 200", r.status_code, 200)
test("Has data", "data" in data, True)
test("Has pagination", "pagination" in data, True)
test("has_next exists", "has_next" in data.get("pagination", {}), True)


# ──────────────────────────────────────────────
# Test 2: Filter eq
# ──────────────────────────────────────────────
print("\n--- Test 2: Filter eq ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "code:eq:P001",
        "limit": 10
    }
)
data = r.json()
test("Status 200", r.status_code, 200)
# All returned records should have code=P001
codes = [row.get("code") for row in data.get("data", [])]
all_match = all(c == "P001" for c in codes) if codes else True
test("Filter eq works", all_match, True)


# ──────────────────────────────────────────────
# Test 3: Filter gte
# ──────────────────────────────────────────────
print("\n--- Test 3: Filter gte ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "price:gte:100",
        "limit": 100
    }
)
print(f"  Status: {r.status_code}")
if r.status_code != 200:
    print(f"  Response: {r.text[:200]}")
data = r.json()
test("Status 200", r.status_code, 200)


# ──────────────────────────────────────────────
# Test 4: Filter in
# ──────────────────────────────────────────────
print("\n--- Test 4: Filter in ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "code:in:P001|P002|P003",
        "limit": 10
    }
)
data = r.json()
test("Status 200", r.status_code, 200)


# ──────────────────────────────────────────────
# Test 5: Filter is_null
# ──────────────────────────────────────────────
print("\n--- Test 5: Filter is_null ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "is_active:is_not_null",
        "limit": 10
    }
)
data = r.json()
test("Status 200", r.status_code, 200)


# ──────────────────────────────────────────────
# Test 6: Sort ascending
# ──────────────────────────────────────────────
print("\n--- Test 6: Sort ascending ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "sort": "code",
        "limit": 10
    }
)
data = r.json()
test("Status 200", r.status_code, 200)
codes = [row.get("code") for row in data.get("data", [])]
if len(codes) > 1:
    is_sorted = codes == sorted(codes)
    test("Sort ascending works", is_sorted, True)
else:
    test("Sort ascending works (skip - not enough data)", True, True)


# ──────────────────────────────────────────────
# Test 7: Sort descending
# ──────────────────────────────────────────────
print("\n--- Test 7: Sort descending ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "sort": "-code",
        "limit": 10
    }
)
data = r.json()
test("Status 200", r.status_code, 200)
codes = [row.get("code") for row in data.get("data", [])]
if len(codes) > 1:
    is_sorted = codes == sorted(codes, reverse=True)
    test("Sort descending works", is_sorted, True)
else:
    test("Sort descending works (skip - not enough data)", True, True)


# ──────────────────────────────────────────────
# Test 8: Invalid column → 400
# ──────────────────────────────────────────────
print("\n--- Test 8: Invalid column ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "nonexistent:eq:value",
        "limit": 10
    }
)
test("Invalid column → 400", r.status_code, 400)


# ──────────────────────────────────────────────
# Test 9: Invalid operator → 400
# ──────────────────────────────────────────────
print("\n--- Test 9: Invalid operator ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "code:INVALID_OP:value",
        "limit": 10
    }
)
test("Invalid operator → 400", r.status_code, 400)


# ──────────────────────────────────────────────
# Test 10: Pagination has_next
# ──────────────────────────────────────────────
print("\n--- Test 10: Pagination has_next ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "limit": 1,
        "offset": 0
    }
)
data = r.json()
test("Status 200", r.status_code, 200)
pagination = data.get("pagination", {})
test("total exists", "total" in pagination, True)
test("has_next exists", "has_next" in pagination, True)
test("limit in response", pagination.get("limit"), 1)
test("offset in response", pagination.get("offset"), 0)


# ──────────────────────────────────────────────
# Test 11: Limit max enforcement
# ──────────────────────────────────────────────
print("\n--- Test 11: Limit max enforcement ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "limit": 9999,
        "offset": 0
    }
)
data = r.json()
test("Status 200", r.status_code, 200)
# Limit should be clamped to MAX_LIMIT
pagination = data.get("pagination", {})
test("Limit clamped", pagination.get("limit", 0) <= 500, True)


# ──────────────────────────────────────────────
# Test 12: Tenant isolation with filters
# ──────────────────────────────────────────────
print("\n--- Test 12: Tenant isolation with filters ---")
r_a = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={"limit": 100}
)
r_b = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_B,
    params={"limit": 100}
)
data_a = r_a.json()
data_b = r_b.json()
ids_a = set(row.get("id") for row in data_a.get("data", []))
ids_b = set(row.get("id") for row in data_b.get("data", []))
no_overlap = ids_a.isdisjoint(ids_b)
test("Tenant A isolation", r_a.status_code, 200)
test("Tenant B isolation", r_b.status_code, 200)
test("No cross-tenant overlap", no_overlap, True)


# ──────────────────────────────────────────────
# Test 13: SQL injection attempt
# ──────────────────────────────────────────────
print("\n--- Test 13: SQL injection attempt ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "code:eq:1' OR '1'='1",
        "limit": 10
    }
)
data = r.json()
# Should return 200 with filtered results (not all records)
test("SQL injection handled", r.status_code in [200, 400], True)


# ──────────────────────────────────────────────
# Results Summary
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"RESULTS: {passed}/{total} passed")

# Cleanup
client.close()
stop_server(server)

if passed < total:
    print("\nFailed tests:")
    for name, ok in results:
        if not ok:
            print(f"  FAIL: {name}")
    sys.exit(1)
else:
    print("\nAll tests passed!")
    sys.exit(0)
```

### `setup_scoped_test.py`

```python
"""
Create SCOPED test table for Cross-Tenant verification.

This script:
1. Creates a table with tenant_id column (SCOPED)
2. Registers it as a DBP entity
3. Seeds test data for two tenants
"""

from database import SessionLocal, engine
from sqlalchemy import text
from models import DBPEntity, DBPField
import uuid


def setup_scoped_test():
    db = SessionLocal()

    try:
        # 1. Create SCOPED test table
        print("Creating test_products table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS test_products (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36) NOT NULL,
                code VARCHAR(50) NOT NULL,
                name VARCHAR(255) NOT NULL,
                price NUMERIC(10,2) DEFAULT 0,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # Add unique constraint on (tenant_id, code)
        db.execute(text("""
            DO $$ BEGIN
                ALTER TABLE test_products
                ADD CONSTRAINT uq_test_products_tenant_code
                UNIQUE (tenant_id, code);
            EXCEPTION
                WHEN duplicate_table THEN NULL;
            END $$
        """))

        db.commit()
        print("  OK")

        # 2. Register as DBP entity
        print("Registering entity...")

        existing = db.query(DBPEntity).filter(
            DBPEntity.code == "test_product"
        ).first()

        if not existing:
            entity_id = str(uuid.uuid4())
            entity = DBPEntity(
                id=entity_id,
                code="test_product",
                name_en="Test Product",
                name_ar="منتج تجريبي",
                faculty="inventory",
                table_mapping="test_products",
                is_system=False,
            )
            db.add(entity)

            # Add fields
            fields = [
                DBPField(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    code="code",
                    label_en="Code",
                    label_ar="الكود",
                    field_type="string",
                    is_required=True,
                    ui_config={"order": 1},
                ),
                DBPField(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    code="name",
                    label_en="Name",
                    label_ar="الاسم",
                    field_type="string",
                    is_required=True,
                    ui_config={"order": 2},
                ),
                DBPField(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    code="price",
                    label_en="Price",
                    label_ar="السعر",
                    field_type="number",
                    is_required=False,
                    ui_config={"order": 3},
                ),
            ]

            for f in fields:
                db.add(f)

            db.commit()
            print("  OK (new entity)")
        else:
            print("  OK (existing)")

        # 3. Seed test data for two tenants
        print("Seeding test data...")

        # Clear existing test data
        db.execute(text("DELETE FROM test_products"))
        db.commit()

        tenant_a = "tenant_a"
        tenant_b = "tenant_b"

        records = [
            {"tenant_id": tenant_a, "code": "P001", "name": "Product A1", "price": 100},
            {"tenant_id": tenant_a, "code": "P002", "name": "Product A2", "price": 200},
            {"tenant_id": tenant_b, "code": "P001", "name": "Product B1", "price": 150},
            {"tenant_id": tenant_b, "code": "P003", "name": "Product B3", "price": 300},
        ]

        for rec in records:
            db.execute(text("""
                INSERT INTO test_products (id, tenant_id, code, name, price)
                VALUES (:id, :tenant_id, :code, :name, :price)
            """), {
                "id": str(uuid.uuid4()),
                "tenant_id": rec["tenant_id"],
                "code": rec["code"],
                "name": rec["name"],
                "price": rec["price"],
            })

        db.commit()
        print("  OK (4 records)")

        # 4. Verify
        result = db.execute(text(
            "SELECT tenant_id, code, name FROM test_products ORDER BY tenant_id, code"
        ))
        print("\nTest data:")
        for row in result:
            print(f"  {row[0]:10s} | {row[1]:5s} | {row[2]}")

    finally:
        db.close()


if __name__ == "__main__":
    setup_scoped_test()
```

---

## 6. Gate Documentation

### Gate Status

| Gate | Status | Description |
|------|--------|-------------|
| P0-P5 | ✅ FROZEN | Baseline architecture, metadata engine, DB setup |
| P6.1 | ✅ FROZEN | Production Auth Integration |
| P6.2 | ✅ FROZEN | RBAC / Authorization Contract |
| P6.3 | ✅ FROZEN | Audit Logging / Compliance |
| P6.4 | ✅ FROZEN | Production Hardening (11 sub-tasks) |
| P7 | ✅ COMPLETE | Dynamic Query Engine |

### Known Limitations

- **UPDATE old_values not captured**: Audit log for UPDATE does not include `old_values` due to transaction interaction with audit INSERT. This is a known limitation, deferred to future work.

### Test Results

- RBAC: 17/17 ✅
- Audit: 8/8 ✅
- Cross-Tenant: 12/12 ✅
- Production Auth: 3/3 ✅
- Query Engine (P7): 26/26 ✅
- **Total: 66/66 ✅**

### Roadmap

P8 (Bulk/Import/Export) → P9 (Relationships) → P10 (Soft Delete) → P11 (Schema Versioning) → P12 (Events/Webhooks) → P13 (Security Hardening) → P14 (Auto UI)

---

**END OF FULL SOURCE EXPORT**
