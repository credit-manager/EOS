# ═══════════════════════════════════════════════
# EOS Platform — Comprehensive README
# ═══════════════════════════════════════════════

# EOS Dynamic ERP Platform

**Enterprise Operating System** — منصة توليد أنظمة ERP ديناميكية مدعومة بالذكاء الاصطناعي

![License](https://img.shields.io/badge/license-proprietary-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.141-green.svg)
![PostgreSQL](https://img.shields.io/badge/postgresql-15+-blue.svg)

---

## 📖 نظرة عامة | Overview

EOS ليست نظام ERP تقليدي، بل هي **منصة لتوليد أنظمة ERP** مخصصة لأي نشاط تجاري من خلال:

- **نواة واحدة** (Core Foundation) تحتوي على الوحدات الأساسية (المحاسبة، الموارد البشرية، المخزون...)
- **محرك ذكاء اصطناعي** يحول وصف النشاط الطبيعي إلى إعدادات نظام كاملة
- **حزم صناعية** (Industry Packs) لكل قطاع (مقاولات، سياحة، تجارة، تصنيع...)
- **تخصيص ديناميكي** بدون كتابة كود إضافي

### الميزات الرئيسية

✅ **توليد تلقائي**: صف نشاطك بالكلام العادي → احصل على ERP كامل  
✅ **متعدد الصناعات**: نفس النواة تدعم جميع الأنشطة  
✅ **تكامل محاسبي**: جميع العمليات تصب في دفتر الأستاذ العام  
✅ **سير عمل ديناميكي**: workflows قابلة للتكوين  
✅ **تعدد المستأجرين**: SaaS architecture مع عزل تام للبيانات  
✅ **ثنائي اللغة**: عربي / English  

---

## 🏗️ بنية النظام | Architecture

```
┌─────────────────────────────────────────────────────┐
│                  EOS PLATFORM                        │
├─────────────────────────────────────────────────────┤
│  AI Composer → Industry Detection → Module Selection│
│                      ↓                               │
│  ┌──────────────┬──────────────┬─────────────────┐  │
│  │  Foundation  │   Industry   │    AI Engine    │  │
│  │  - Accounting│  - Tourism   │  - Understanding│  │
│  │  - HR        │  - Construction                 │  │
│  │  - Inventory │  - Manufacturing                │  │
│  │  - CRM       │  - Retail                       │  │
│  └──────────────┴──────────────┴─────────────────┘  │
│                      ↓                               │
│         Metadata + Business Rules + Workflows        │
│                      ↓                               │
│              Dynamic CRUD + UI Generation            │
│                      ↓                               │
│           Tenant-Specific ERP Instance               │
└─────────────────────────────────────────────────────┘
```

### الطبقات المعمارية

| الطبقة | الوصف | الحالة |
|--------|-------|--------|
| **Layer 1: Foundation** | المحاسبة، الموارد البشرية، المنصة الأساسية | ✅ مكتمل |
| **Layer 2: Industry Packs** | حزم مخصصة لكل صناعة | 🟡 قيد التطوير |
| **Layer 3: Configuration** | تخصيص العملاء عبر Builder | ✅ مكتمل جزئيًا |
| **Layer 4: AI** | فهم الأعمال التجاري وتوليد الإعدادات | 🟡 قيد التطوير |

---

## 🚀 البدء السريع | Quick Start

### المتطلبات المسبقة

- Python 3.12+
- PostgreSQL 15+
- Redis (اختياري للإنتاج)

### 1. استنساخ المشروع

```bash
git clone <repository-url>
cd eos-system
```

### 2. تثبيت التبعيات

```bash
pip install -r requirements.txt
```

### 3. إعداد البيئة

```bash
# انسخ ملف المثال
cp .env.example .env

# عدّل القيم في .env
# أهم متغير: DATABASE_URL
DATABASE_URL=postgresql://user:password@localhost:5432/eos_platform
SECRET_KEY=<generate-random-32-char-string>
```

### 4. تهيئة قاعدة البيانات

```bash
# تشغيل الترحيلات
alembic upgrade head

# أو إنشاء الجداول يدويًا (للتنمية فقط)
python -c "from database import engine; from models import Base; Base.metadata.create_all(bind=engine)"
```

### 5. تشغيل الخادم

```bash
# تنمية
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# إنتاج
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 6. الوصول للنظام

- **API Documentation**: http://localhost:8000/docs
- **React Frontend**: http://localhost:8000/ui
- **Health Check**: http://localhost:8000/health

---

## 📦 الوحدات المتاحة | Available Modules

### الوحدات الأساسية (Foundation)

| الوحدة | الوصف | الحالة |
|--------|-------|--------|
| `accounting` | الحسابات العامة، القيود، الميزانية | ✅ |
| `hr` | الموظفون، الرواتب، الحضور | ✅ |
| `inventory` | المخازن، الأصناف، الحركات | ✅ |
| `procurement` | المشتريات، الموردون | ✅ |
| `sales` | المبيعات، العملاء، الفواتير | ✅ |
| `projects` | إدارة المشاريع، التكاليف | ✅ |
| `fixed_assets` | الأصول الثابتة، الإهلاك | ✅ |
| `commerce` | التجارة الإلكترونية | 🟡 |

### حزم الصناعات (Industry Packs)

| الصناعة | الكيانات المخصصة | الحالة |
|---------|------------------|--------|
| **السياحة** | باقات، حجوزات، فنادق، رحلات، تأشيرات | ✅ |
| **المقاولات** | مشاريع، عقود، BOQ، مقاولين من الباطن | 🟡 |
| **التصنيع** | BOM، أوامر إنتاج، مراكز عمل | 🟡 |
| **المطاعم** | وصفات، مكونات، طاولات، POS | 🟡 |
| **التجزئة** | فروع، نقاط بيع، ولاء عملاء | 🟡 |

---

## 🤖 الذكاء الاصطناعي | AI Features

### AI Business Composer

حوّل وصف النشاط إلى نظام ERP كامل:

**مثال بالعربية:**
```
"أريد نظام ERP لشركة سياحة وسفر متخصص في العمرة والحج، 
أحتاج إدارة باقات سياحية، حجوزات فنادق، تأشيرات، ومرشدين سياحيين"
```

**مثال بالإنجليزية:**
```
"I need an ERP for a construction company with project management, 
subcontractors, BOQ tracking, and progress certificates"
```

النتيجة:
1. اكتشاف الصناعة تلقائيًا (Tourism / Construction)
2. تفعيل الوحدات المطلوبة
3. إنشاء الكيانات المخصصة
4. ربط العمليات بالمحاسبة
5. توليد سير العمل

---

## 🔧 التخصيص والتوليد | Customization & Generation

### استخدام Builder Engine

```python
from core.builder_engine import BuilderEngine

builder = BuilderEngine(tenant_id="your_tenant")

# إنشاء كيان مخصص
builder.create_entity(
    name="Tour Package",
    code="tour_package",
    fields=[
        {"name": "title", "type": "string", "required": True},
        {"name": "duration_days", "type": "integer"},
        {"name": "price", "type": "decimal"},
        {"name": "destination", "type": "string"},
    ]
)

# نشر التغييرات
builder.publish()
```

### Dynamic CRUD API

بعد إنشاء الكيان، يتوفر API تلقائيًا:

```bash
# إنشاء سجل
POST /api/v1/dynamic/tour_package
{
  "title": "عمرة رمضان المميزة",
  "duration_days": 10,
  "price": 5000.00,
  "destination": "مكة المكرمة"
}

# قراءة السجلات
GET /api/v1/dynamic/tour_package?tenant_id=your_tenant

# تحديث
PUT /api/v1/dynamic/tour_package/{id}

# حذف
DELETE /api/v1/dynamic/tour_package/{id}
```

---

## 🔐 الأمان والصلاحيات | Security

### الميزات الأمنية

- ✅ **JWT Authentication** مع Access/Refresh tokens
- ✅ **2FA Support** (TOTP)
- ✅ **RBAC** (Role-Based Access Control)
- ✅ **Tenant Isolation** (عزل تام بين المستأجرين)
- ✅ **Rate Limiting** (حماية من DDoS)
- ✅ **Audit Logging** (سجل تدقيق شامل)
- ✅ **Input Validation** (حماية من SQL Injection)

### إعداد الصلاحيات

```python
# إنشاء دور مخصص
POST /api/v1/roles
{
  "name": "Tourism Manager",
  "permissions": [
    "tour_package:create",
    "tour_package:read",
    "tour_package:update",
    "booking:approve"
  ]
}
```

---

## 📊 التكامل المحاسبي | Accounting Integration

جميع العمليات التجارية تُترجم تلقائيًا إلى قيود محاسبية:

### مثال: حجز سياحي

```
1. استلام دفعة الحجز:
   من حـ/البنك          1000
     إلى حـ/مدفوعات مقدمة    1000

2. تأكيد الحجز (إيراد):
   من حـ/مدفوعات مقدمة   1000
     إلى حـ/إيرادات السياحة  1000

3. تكلفة الفندق:
   من حـ/تكلفة فنادق      700
     إلى حـ/الموردين        700

4. العمولة:
   من حـ/الموردين        100
     إلى حـ/إيرادات عمولات  100
```

أنماط الحسابات مُعدّة مسبقًا لكل صناعة.

---

## 🧪 الاختبار | Testing

### تشغيل الاختبارات

```bash
# كل الاختبارات
pytest tests/ -v

# مع تغطية الكود
pytest tests/ --cov=core --cov=routers --cov-report=html

# اختبارات محددة
pytest tests/test_tourism.py -v
pytest tests/test_security.py -m tenant_isolation

# اختبارات سريعة (بدون integration)
pytest tests/ -m "not slow"
```

### كتابة اختبار جديد

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.unit
@pytest.mark.phase1
def test_create_booking():
    response = client.post("/api/v1/bookings", json={
        "package_id": 1,
        "customer_name": "Test Customer",
        "travel_date": "2025-01-15"
    })
    assert response.status_code == 200
    assert "booking_id" in response.json()["data"]
```

---

## 📈 خارطة الطريق | Roadmap

### المرحلة 0 ✅ (مكتمل)
- [x] إصلاح استيراد Session في analytics_engine
- [x] إضافة psutil و openpyxl لـ requirements
- [x] اختبار Smoke Test (import main)
- [x] إنشاء .env.example موثق

### المرحلة 1 🟡 (قيد التنفيذ)
- [x] إعداد pytest مع fixtures
- [x] إنشاء GitHub Actions CI pipeline
- [ ] توحيد Schema management تحت Alembic
- [ ] تحويل اختبارات HTTP الحالية لـ pytest

### المرحلة 2 ⏳ (مخطط)
- [ ] إزالة الازدواجية (sales.py vs sales_api.py)
- [ ] مراجعة المحركات الـ 60+ في core/

### المرحلة 3 ⏳ (مخطط)
- [ ] مراجعة أمنية مستقلة (Pen-test)
- [ ] تفعيل Rate Limiting شامل
- [ ] Secrets Management حقيقي

### المرحلة 4 ⏳ (مخطط)
- [ ] توثيق API كامل عبر OpenAPI/Swagger
- [ ] رسم مخطط معماري تفصيلي
- [ ] أمثلة استخدام مفصلة

### المرحلة 5 ⏳ (مخطط)
- [ ] رفع كود React المصدري
- [ ] Load Testing بـ Locust/k6
- [ ] Billing حقيقي مع بوابة دفع
- [ ] دعم لغات إضافية (i18n)
- [ ] شهادات امتثال (SOC 2, ISO 27001)

---

## 📞 الدعم والتواصل | Support

- **الموقع الإلكتروني**: (قريبًا)
- **البريد الإلكتروني**: support@eos-platform.com
- **التوثيق الكامل**: http://localhost:8000/docs

---

## 📄 الترخيص | License

جميع الحقوق محفوظة © 2025 EOS Platform

---

## 🙏 المساهمون | Contributors

شكرًا لكل من ساهم في بناء هذه المنصة!

---

*تم البناء بحب ☕ في الشرق الأوسط*
