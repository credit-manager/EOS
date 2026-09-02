# دليل التثبيت السريع لنظام ERP

## المتطلبات الأساسية

قبل البدء، تأكد من تثبيت البرامج التالية:

### 1. Docker و Docker Compose (الطريقة الموصى بها)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- الإصدار المطلوب: Docker 20.x أو أحدث
- Docker Compose 2.x أو أحدث

### 2. التثبيت اليدوي (بديل)
- **Python**: 3.10 أو أحدث
- **Node.js**: 18.x أو أحدث
- **PostgreSQL**: 15.x أو أحدث (اختياري عند استخدام Docker)
- **Redis**: 7.x أو أحدث (اختياري عند استخدام Docker)

## طريقة التثبيت باستخدام Docker (الأسهل)

### الخطوة 1: استنساخ المشروع
```bash
git clone <repository-url>
cd erp-system
```

### الخطوة 2: نسخ ملف البيئة
```bash
cp .env.example .env
```

### الخطوة 3: تعديل متغيرات البيئة (اختياري)
افتح ملف `.env` وقم بتعديل القيم حسب حاجتك، خاصة:
- `SECRET_KEY`: قم بتغييره إلى قيمة عشوائية آمنة
- `DB_PASSWORD`: قم بتغيير كلمة مرور قاعدة البيانات

### الخطوة 4: بدء جميع الخدمات
```bash
cd docker
docker-compose up -d
```

### الخطوة 5: التحقق من حالة الخدمات
```bash
docker-compose ps
```

يجب أن ترى جميع الخدمات بحالة `healthy` أو `running`.

### الخطوة 6: الوصول إلى التطبيق
- **الواجهة الأمامية (Frontend)**: http://localhost:3000
- **واجهة API (Backend)**: http://localhost:8000
- **توثيق API**: http://localhost:8000/docs
- **قاعدة البيانات**: localhost:5432
- **Redis**: localhost:6379

### الخطوة 7: إيقاف الخدمات
```bash
docker-compose down
```

لحذف البيانات أيضاً:
```bash
docker-compose down -v
```

## طريقة التثبيت اليدوي

### الجزء الأول: إعداد Backend

#### 1. تثبيت Python والتبعيات
```bash
cd backend

# إنشاء بيئة افتراضية
python -m venv venv

# تفعيل البيئة الافتراضية
# على Linux/Mac:
source venv/bin/activate
# على Windows:
venv\Scripts\activate

# تثبيت التبعيات
pip install -r requirements.txt
```

#### 2. إعداد قاعدة البيانات
```bash
# إنشاء قاعدة البيانات
createdb erp_db

# أو باستخدام psql
psql -U postgres
CREATE DATABASE erp_db;
\q
```

#### 3. تشغيل الترحيلات (Migrations)
```bash
# ترقية قاعدة البيانات
alembic upgrade head
```

#### 4. تشغيل خادم Backend
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

الآن يمكنك الوصول إلى:
- API: http://localhost:8000
- توثيق API: http://localhost:8000/docs

### الجزء الثاني: إعداد Frontend

#### 1. تثبيت Node.js والتبعيات
```bash
cd frontend

# تثبيت التبعيات
npm install
```

#### 2. تشغيل خادم التطوير
```bash
npm run dev
```

الآن يمكنك الوصول إلى:
- التطبيق: http://localhost:3000

### الجزء الثالث: تطبيق سطح المكتب (اختياري)

#### 1. تثبيت Electron
```bash
cd desktop
npm install
```

#### 2. تشغيل تطبيق سطح المكتب
```bash
npm run electron:dev
```

#### 3. بناء التطبيق للإنتاج
```bash
npm run electron:build
```

## إنشاء أول مستخدم (مدير النظام)

بعد تثبيت النظام، قم بإنشاء حساب المدير:

### طريقة 1: عبر API
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@company.com",
    "username": "admin",
    "password": "SecurePassword123!",
    "full_name": "مدير النظام"
  }'
```

### طريقة 2: عبر سطر الأوامر (Backend)
```bash
cd backend
source venv/bin/activate

python -c "
from app.models import User
from app.utils.security import get_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import session

engine = create_engine('postgresql://postgres:postgres@localhost:5432/erp_db')
db = session.Session(bind=engine)

user = User(
    email='admin@company.com',
    username='admin',
    hashed_password=get_password_hash('SecurePassword123!'),
    full_name='مدير النظام',
    is_superuser=True
)

db.add(user)
db.commit()
print('تم إنشاء حساب المدير بنجاح')
"
```

## التحقق من التثبيت

### اختبار Backend
```bash
# فحص حالة النظام
curl http://localhost:8000/health

# يجب أن تحصل على:
# {"status":"healthy","service":"نظام ERP المتكامل","version":"1.0.0"}
```

### اختبار Frontend
افتح المتصفح واذهب إلى http://localhost:3000

يجب أن تظهر صفحة تسجيل الدخول.

## حل المشاكل الشائعة

### المشكلة: خطأ في الاتصال بقاعدة البيانات
**الحل**: تأكد من أن PostgreSQL يعمل ويمكنك الاتصال به:
```bash
# مع Docker
docker-compose ps

# بدون Docker
pg_isready -h localhost -p 5432
```

### المشكلة: خطأ في تثبيت التبعيات
**الحل**: امسح الذاكرة المؤقتة وأعد التثبيت:
```bash
# Python
pip cache purge
pip install -r requirements.txt

# Node.js
rm -rf node_modules package-lock.json
npm install
```

### المشكلة: المنفذ مشغول
**الحل**: غيّر المنفذ في ملف `.env` أو `docker-compose.yml`

### المشكلة: خطأ CORS
**الحل**: تأكد من إضافة عنوان Frontend إلى `ALLOWED_ORIGINS` في `.env`

## الخطوات التالية

1. **تسجيل الدخول**: استخدم حساب المدير الذي أنشأته
2. **إعداد الشركة**: اذهب إلى الإعدادات وأدخل بيانات شركتك
3. **إضافة المستخدمين**: أنشئ حسابات للموظفين
4. **تكوين الوحدات**: فعّل الوحدات التي تحتاجها (مبيعات، مشتريات، مخزون، إلخ)
5. **استيراد البيانات**: إن وجدت بيانات سابقة

## الدعم والمساعدة

للحصول على المساعدة:
- راجع الوثائق في مجلد `docs/`
- تحقق من سجلات الأخطاء:
  ```bash
  # Docker
  docker-compose logs -f
  
  # Backend
  tail -f backend/logs/app.log
  ```

## التحديث

### مع Docker
```bash
docker-compose pull
docker-compose up -d
```

### بدون Docker
```bash
# Backend
git pull
pip install -r requirements.txt
alembic upgrade head

# Frontend
git pull
npm install
npm run build
```

---

**ملاحظة**: هذا دليل التثبيت الأساسي. للحصول على معلومات أكثر تفصيلاً، راجع الوثائق الكاملة في مجلد `docs/`.
