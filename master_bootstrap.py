#!/usr/bin/env python3
"""
EOS DBP Master Bootstrap Script
يقوم بإنشاء المشروع الكامل وتشغيله تلقائياً
"""

import os
import sys
import subprocess
import time

# ═══════════════════════════════════════════════════
# 1. إنشاء هيكل المجلدات
# ═══════════════════════════════════════════════════
print("📁 Creating folder structure...")
os.makedirs("core", exist_ok=True)
os.makedirs("routers", exist_ok=True)

open("core/__init__.py", "w").close()
open("routers/__init__.py", "w").close()

print("✅ Folders created!")

# ═══════════════════════════════════════════════════
# 2. كتابة ملفات المشروع
# ═══════════════════════════════════════════════════
print("📝 Writing project files...")

with open("database.py", "w", encoding="utf-8") as f:
    f.write('''from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://eos:0100@127.0.0.1:5432/eos_main")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''')

with open("models.py", "w", encoding="utf-8") as f:
    f.write('''from sqlalchemy import Column, String, Boolean, JSON, DateTime, ForeignKey
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
''')

with open("setup_db.py", "w", encoding="utf-8") as f:
    f.write('''from database import engine, Base, SessionLocal
from sqlalchemy import text
from models import DBPEntity, DBPField

print("🔄 Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created!")

print("🔄 Seeding data...")
db = SessionLocal()

try:
    db.execute(text(\"\"\"
        INSERT INTO dbp_entities
        (code, name_en, name_ar, faculty, table_mapping, is_system)
        VALUES
        ('account', 'Account', 'حساب', 'finance', 'accounts', true)
        ON CONFLICT (code) DO NOTHING
    \"\"\"))
    db.commit()

    result = db.execute(
        text("SELECT id FROM dbp_entities WHERE code = 'account'")
    ).fetchone()

    if result:
        eid = result[0]

        db.execute(text(\"\"\"
            INSERT INTO dbp_fields
            (entity_id, code, label_en, label_ar, field_type, is_required, ui_config)
            VALUES
            (:eid, 'code', 'Code', 'الكود', 'string', true,
             '{"component": "input", "order": 1}'),
            (:eid, 'name', 'Name', 'الاسم', 'string', true,
             '{"component": "input", "order": 2}'),
            (:eid, 'account_type', 'Type', 'النوع', 'enum', true,
             '{"component": "select", "order": 3}')
            ON CONFLICT (entity_id, code) DO NOTHING
        \"\"\"), {"eid": eid})

        db.execute(text(\"\"\"
            UPDATE dbp_fields
            SET enum_values = '["asset", "liability", "equity"]'::jsonb
            WHERE code = 'account_type'
              AND entity_id = :eid
        \"\"\"), {"eid": eid})

        db.commit()
        print("✅ Data seeded successfully!")
    else:
        print("⚠️ Entity not found after insert")

except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()

finally:
    db.close()
''')

with open("core/metadata_engine.py", "w", encoding="utf-8") as f:
    f.write('''from sqlalchemy.orm import Session
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
''')

with open("routers/dynamic_crud.py", "w", encoding="utf-8") as f:
    f.write('''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any
import uuid

from database import get_db
from core.metadata_engine import MetadataEngine


router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Dynamic CRUD"]
)


@router.get("/entities/{entity_code}/schema")
async def get_schema(
    entity_code: str,
    db: Session = Depends(get_db)
):

    try:
        return {
            "status": "success",
            "data": MetadataEngine(db).get_full_schema(entity_code)
        }

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )


@router.get("/entities/{entity_code}/records")
async def list_records(
    entity_code: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):

    engine = MetadataEngine(db)

    entity = engine.get_entity_by_code(entity_code)

    if not entity or not entity.get("table_mapping"):
        raise HTTPException(
            status_code=404,
            detail="الكيان أو الجدول غير موجود"
        )

    query = text(
        f"SELECT * FROM {entity['table_mapping']} LIMIT :limit"
    )

    result = db.execute(
        query,
        {"limit": limit}
    )

    return {
        "status": "success",
        "data": [dict(row._mapping) for row in result],
        "count": result.rowcount
    }


@router.post("/entities/{entity_code}/records")
async def create_record(
    entity_code: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):

    engine = MetadataEngine(db)

    try:
        engine.validate_data(entity_code, payload)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    entity = engine.get_entity_by_code(entity_code)

    if not entity or not entity.get("table_mapping"):
        raise HTTPException(
            status_code=404,
            detail="الكيان غير موجود"
        )

    record_id = str(uuid.uuid4())

    payload["id"] = record_id
    payload["tenant_id"] = "system_tenant"

    cols = ", ".join(payload.keys())

    placeholders = ", ".join(
        [f":{key}" for key in payload.keys()]
    )

    query = text(
        f"""
        INSERT INTO {entity['table_mapping']}
        (id, tenant_id, {cols})
        VALUES
        (:id, :tenant_id, {placeholders})
        RETURNING id
        """
    )

    try:

        result = db.execute(
            query,
            payload
        )

        db.commit()

        return {
            "status": "success",
            "id": result.scalar()
        }

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
''')

with open("main.py", "w", encoding="utf-8") as f:
    f.write('''from fastapi import FastAPI
from routers import dynamic_crud


app = FastAPI(
    title="EOS Dynamic Business Platform",
    version="1.0.0"
)

app.include_router(dynamic_crud.router)


@app.get("/")
def root():
    return {
        "message": "EOS DBP Core is running!",
        "docs": "/docs"
    }
''')

print("✅ All files written!")

# ═══════════════════════════════════════════════════
# 3. تثبيت المتطلبات
# ═══════════════════════════════════════════════════

print("📦 Installing dependencies...")

subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "psycopg2-binary",
        "pydantic"
    ],
    check=True
)

print("✅ Dependencies installed!")

# ═══════════════════════════════════════════════════
# 4. إعداد قاعدة البيانات
# ═══════════════════════════════════════════════════

print("🗄️ Setting up database...")

try:

    subprocess.run(
        [sys.executable, "setup_db.py"],
        check=True
    )

except subprocess.CalledProcessError as e:

    print(f"❌ Database setup failed: {e}")
    print(
        "⚠️ تأكد من أن PostgreSQL يعمل وأن بيانات الاتصال صحيحة في database.py"
    )

    sys.exit(1)

# ═══════════════════════════════════════════════════
# 5. اختبار النظام
# ═══════════════════════════════════════════════════

print("\n" + "=" * 60)
print("🧪 Running tests...")
print("=" * 60)

print("🚀 Starting server...")

server_process = subprocess.Popen(
    [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--port",
        "8000"
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(4)

try:

    import urllib.request
    import json

    print("\n📋 Test 1: Get Schema")

    try:

        with urllib.request.urlopen(
            "http://127.0.0.1:8000/api/v1/dynamic/entities/account/schema"
        ) as response:

            data = json.loads(
                response.read().decode()
            )

            print(
                f"✅ Success: "
                f"{json.dumps(data, ensure_ascii=False, indent=2)}"
            )

    except Exception as e:

        print(f"❌ Failed: {e}")

    print("\n📋 Test 2: List Records")

    try:

        with urllib.request.urlopen(
            "http://127.0.0.1:8000/api/v1/dynamic/entities/account/records?limit=5"
        ) as response:

            data = json.loads(
                response.read().decode()
            )

            print(
                f"✅ Success: "
                f"Found {data.get('count', 0)} records"
            )

    except Exception as e:

        print(f"❌ Failed: {e}")

    print("\n📋 Test 3: Create Record")

    try:

        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/v1/dynamic/entities/account/records",
            data=json.dumps(
                {
                    "code": "1000-01",
                    "name": "Test Account",
                    "account_type": "asset"
                }
            ).encode(),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(req) as response:

            data = json.loads(
                response.read().decode()
            )

            print(
                f"✅ Success: "
                f"Created record with ID {data.get('id')}"
            )

    except Exception as e:

        print(f"❌ Failed: {e}")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS COMPLETED!")
    print("=" * 60)

    print(
        "\n🌐 Server is running at: "
        "http://127.0.0.1:8000"
    )

    print(
        "📚 API Docs: "
        "http://127.0.0.1:8000/docs"
    )

    print("\n⚠️ Press Ctrl+C to stop the server")

    server_process.wait()

except KeyboardInterrupt:

    print("\n\n🛑 Stopping server...")

    server_process.terminate()

    print("✅ Server stopped!")

except Exception as e:

    print(f"\n❌ Test failed: {e}")

    server_process.terminate()

    sys.exit(1)



