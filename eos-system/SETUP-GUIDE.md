# EOS System — Setup Guide
## دليل الإعداد والتشغيل

> الإصدار: 1.0 | التاريخ: 2026-08-19

---

## المتطلبات

### Backend
- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose (اختياري)

### Frontend
- Node.js 18+
- npm أو yarn

---

## التشغيل المحلي

### 1. استنساخ المشروع

```bash
cd "D:\EOS\Eos final\eos-system"
```

### 2. إعداد قاعدة البيانات

#### باستخدام Docker
```bash
docker-compose up -d postgres redis
```

#### يدوياً
1. تأكد من تثبيت PostgreSQL 16
2. قم بإنشاء قاعدة بيانات جديدة:
```sql
CREATE DATABASE eos_main;
CREATE USER eos WITH PASSWORD 'eos_secret';
GRANT ALL PRIVILEGES ON DATABASE eos_main TO eos;
```

### 3. إعداد Backend

```bash
cd backend

# إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate  # Windows

# تثبيت التبعيات
pip install -r requirements.txt

# نسخ ملف الإعدادات
cp .env.example .env

# تطبيق الترحيلات
alembic upgrade head

# تشغيل الخادم
uvicorn app.main:app --reload --port 8000
```

### 4. إعداد Frontend

```bash
cd frontend

# تثبيت التبعيات
npm install

# تشغيل الخادم
npm run dev
```

---

## الوصول للخدمات

| الخدمة | الرابط |
|--------|--------|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/api/docs |
| **PostgreSQL** | localhost:5432 |
| **Redis** | localhost:6379 |

---

## بيانات الدخول التجريبية

### مستخدم تجريبي
- **البريد الإلكتروني**: admin@eos-demo.com
- **كلمة المرور**: Admin@123
- **معرف المؤسسة**: eos-demo

---

## هيكل المجلدات

```
eos-system/
├── backend/
│   ├── alembic/          # ترحيلات قاعدة البيانات
│   ├── app/
│   │   ├── api/v1/       # واجهات API
│   │   ├── core/         # الإعدادات والأمان
│   │   ├── db/           # جلسات قاعدة البيانات
│   │   ├── middleware/    # الوسطاء
│   │   ├── models/       # نماذج SQLAlchemy
│   │   └── main.py       # التطبيق الرئيسي
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── layouts/      # التخطيطات
│   │   ├── pages/        # الصفحات
│   │   ├── services/     # خدمات API
│   │   ├── stores/       # إدارة الحالة
│   │   ├── styles/       # الأنماط
│   │   ├── types/        # أنواع TypeScript
│   │   └── hooks/        # Custom Hooks
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

---

## أوامر مفيدة

### Backend
```bash
# تطبيق الترحيلات
alembic upgrade head

# إنشاء ترحيل جديد
alembic revision --autogenerate -m "description"

# تشغيل الاختبارات
pytest

# فحص الكود
flake8 app/
mypy app/
```

### Frontend
```bash
# تشغيل الخادم
npm run dev

# بناء المشروع
npm run build

# فحص الكود
npm run lint

# تنظيف الكود
npm run lint -- --fix
```

---

## حل المشاكل

### مشكلة: قاعدة البيانات غير متصلة
```bash
# تأكد من تشغيل PostgreSQL
docker-compose up -d postgres
```

### مشكلة: Port 8000 مستخدم
```bash
# تغيير المنفذ في uvicorn
uvicorn app.main:app --reload --port 8001
```

### مشكلة: تبعيات Frontend
```bash
# حذف node_modules وإعادة التثبيت
rm -rf node_modules package-lock.json
npm install
```

---

*EOS System — Setup Guide v1.0*
