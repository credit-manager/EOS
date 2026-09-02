# EOS ERP Frontend - واجهة المستخدم

منصة EOS لإدارة الموارد المؤسسية - الواجهة الأمامية الحديثة

## 🚀 التقنيات المستخدمة

- **React 18** - مكتبة الواجهة الأساسية
- **Vite** - أداة البناء السريعة
- **Ant Design** - نظام التصميم والمكونات
- **React Router** - التنقل بين الصفحات
- **TanStack Query** - إدارة حالة الخادم
- **Zustand** - إدارة الحالة العامة
- **i18next** - الترجمة وتعدد اللغات
- **Framer Motion** - الرسوم المتحركة
- **Recharts** - الرسوم البيانية

## 📦 التثبيت

```bash
# تثبيت المكتبات
npm install

# تشغيل وضع التطوير
npm run dev

# بناء للإنتاج
npm run build

# معاينة الإنتاج
npm run preview
```

## 🌐 اللغات المدعومة

- 🇸🇦 العربية (افتراضي)
- 🇬🇧 English
- 🇫🇷 Français
- 🇩🇪 Deutsch
- 🇪🇸 Español
- 🇨🇳 中文

## 📁 بنية المشروع

```
frontend/
├── src/
│   ├── components/       # المكونات القابلة لإعادة الاستخدام
│   │   ├── Layout.jsx    # التخطيط الرئيسي
│   │   └── ProtectedRoute.jsx
│   ├── pages/           # صفحات التطبيق
│   │   ├── LoginPage.jsx
│   │   ├── DashboardPage.jsx
│   │   ├── IndustriesPage.jsx
│   │   ├── BuilderPage.jsx
│   │   ├── EntitiesPage.jsx
│   │   ├── ReportsPage.jsx
│   │   └── SettingsPage.jsx
│   ├── services/        # خدمات API
│   │   └── api.js
│   ├── styles/          # الأنماط العامة
│   │   └── index.css
│   ├── utils/           # أدوات مساعدة
│   │   └── i18n.js
│   ├── App.jsx          # مكون التطبيق الرئيسي
│   └── main.jsx         # نقطة الدخول
├── public/              # الملفات الثابتة
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

## 🎨 الميزات

### 1. تصميم متجاوب
- يعمل على جميع أحجام الشاشات
- دعم RTL للعربية
- وضع ليلي/نهاري

### 2. تعدد اللغات
- تغيير اللغة فورياً
- حفظ تفضيل اللغة
- 6 لغات مدعومة

### 3. أداء عالي
- تحميل سريع بالـ Code Splitting
- Lazy Loading للصفحات
- تحسين الصور والأصول

### 4. أمان
- حماية المسارات
- تخزين آمن للـ Tokens
- Intercepters للمصادقة

## 🔗 الاتصال مع Backend

الواجهة مهيأة للاتصال بـ:
- Base URL: `/api`
- Proxy إلى: `http://localhost:8000`

## 📊 الصفحات الرئيسية

| الصفحة | الوصف |
|--------|-------|
| Login | تسجيل الدخول |
| Dashboard | لوحة التحكم والمؤشرات |
| Industries | اختيار القطاع الصناعي |
| Builder | منشئ ERP بالذكاء الاصطناعي |
| Entities | إدارة الكيانات الديناميكية |
| Reports | التقارير المالية والتشغيلية |
| Settings | الإعدادات والملف الشخصي |

## 🛠️ التطوير

```bash
# فحص الأخطاء
npm run lint

# تشغيل الاختبارات
npm run test

# بناء مع تحليل الحجم
npm run build -- --report
```

## 📝 الترخيص

جميع الحقوق محفوظة © 2024 EOS Platform
