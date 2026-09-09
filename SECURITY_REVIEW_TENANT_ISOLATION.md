# 🔒 مراجعة أمنية: عزل المستأجرين (Tenant Isolation) — EOS-Release-1.1

> تقرير فحص **فعلي** (قراءة + إصلاح محدود معتمد) لمسار IDOR/عزل المستأجرين.
> نفّذ حسب قرار المستخدم: مراجعة IDOR + عزل أولًا قبل أي ترقية إلى Business Factory.

---

## 1) التصنيف الصحيح (تصحيب من المستخدم)

**النتيجة الأصلية في `ai_features.py` لم تكن "IDOR نشط يسرّب بيانات" — بل endpointe **معطوب (Broken)**:
- `get_model(mid)` و`get_prediction(pid)` بدون `tenant_id` (بارامتر إجباري بلا default) → يرمي `TypeError` قبل الوصول لأي استعلام SQL.
- أي لا تسريب بيانات، بل كسر وظيفي (DoS جزئي على الوظيفة) — الـ endpoint لا يعمل لأي أحد.

**الدرس المنهجي الحقيقي:** الـ patch الأصلي عدّل تواقيع الـ engine layer لكن لم يُمسح كل نقاط الاستدعاء (call sites). في `ai_features.py` وحده فلق نقطتان. السؤال: كم ملفًا من الـ93 محركًا لديه نفس الثغرة؟ → هذا ما حُلّ الآن بالفحص المنهجي.

---

## 2) إصلاح اعتمد (الخطوة 1) — تصحيح نقطتين معطوبتين

تمت إضافة `user["tenant_id"]` لنقطتين في `routers/ai_features.py` (نفس النمط المستخدم فعلًا في :56/:61):

| السطر | قبل | بعد |
|---|---|---|
| `ai_features.py:44` | `AIEngine(db).get_model(mid)` | `AIEngine(db).get_model(mid, user["tenant_id"])` |
| `ai_features.py:106` | `AIEngine(db).get_prediction(pid)` | `AIEngine(db).get_prediction(pid, user["tenant_id"])` |

**تحقق:** `python -m py_compile` ناجح لكل من `ai_features.py`, `system.py`, `ai_engine.py`.

**نتيجة الفحص الشامل لنقاط الاستدعاء لجميع الدوال ذات التوقيع المغيّر** (get_model, update_model, get_prediction, acknowledge_prediction, acknowledge_recommendation, _get_recommendation, resolve_anomaly, _get_anomaly, update_data_import) — **كلها الآن موسومة بـ tenant_id** ✅
- `ai_engine.py:82, 163, 227, 303` (استدعاءات داخلية) ✅
- `ai_features.py:44, 56, 61, 88, 106, 121, 125, 172, 216` ✅
- `system.py:124-125` ✅

---

## 3) الفحص المنهجي (الخطوة 2) — أهم النتائج

بحث عبر **كل** الـ core engines + routers عن النمط `WHERE id=:id` بلا `tenant_id`، ثم تحقق من قاعدة البيانات أي هذه الجداول **تحتوي عمود `tenant_id`** (أي مرشحة للـ IDOR الحقيقي).

### 3.1) جداول بها `tenant_id` لكن تعديلات تتم بمعرف فقط (مرشحة للـ IDOR — تحتاج معالجة)

| الملف | الأسطر | الجدول | الاستعلام |
|---|---|---|---|
| `approve_api.py` | 199, 220, 224, 243 | `dbp_approve_requests` | UPDATE بمعرف فقط |
| `compliance_engine.py` | 79 | `dbp_compliance_checks` | UPDATE بمعرف فقط |
| `custom_api.py` | 86, 113, 225, 280, 385, 437, 452, 456 | `dbp_custom_*` + `dbp_workflow_instances_v2` | DELETE/UPDATE بمعرف فقط |
| `docs_api.py` | 109, 281, 298 | `dbp_doc_folders` / `dbp_doc_files` | DELETE/UPDATE بمعرف فقط |
| `manufacturing_api.py` | 367, 380, 397, 466 | `dbp_mfg_orders` / `dbp_mfg_material_issues` | UPDATE بمعرف فقط |
| `notify_api.py` | 257 | `dbp_notify_rules` | UPDATE بمعرف فقط |
| `services_api.py` | 164, 228, 309, 434, 496, 672, 687, 752, 834, 853 | `dbp_svc_*` (10 جداول) | UPDATE بمعرف فقط |
| `trading_api.py` | 617, 684, 745, 921, 979, 1054, 1219 | `dbp_trading_*` (7 جداول) | UPDATE بمعرف فقط |
| `validation_ops.py` | 91, 228 | `dbp_validation_rules` | UPDATE بمعرف فقط |
| `edge_region.py` | 110 | `dbp_edge_sync_log` | UPDATE بمعرف فقط |
| `saas_journey.py` | 138, 162, 186 | `dbp_saas_journeys` | UPDATE بمعرف فقط |

### 3.2) جداول بـ `WHERE id=:id` لكن **بلا عمود `tenant_id`** (منصة/عامة — ليست IDOR، تحتاج RBAC لا tenant)
`dbp_edge_nodes`, `dbp_network_topology`, `dbp_blockchain_nodes`, `dbp_platform_features`, `dbp_saas_features`.

### 3.3) نمط أساسي لوحظ (يجب توثيقه بدقة في التقرير)

العديد من الـ endpoints (مثل `docs_api.delete_folder`, `approve_api.cancel_request`) تقوم أولًا بـ **SELECT فحص ملكية بـ `tenant_id`** ثم تنفذ UPDATE/DELETE **بالمعرف فقط**. هذا "آمن بنيويًا" فقط طالما فحص الملكية سبقه، لكنه:
- **نمط هش** يكرر اعتماد منطق التحقق في كل نقطة يدويًا.
- **عرضة لـ TOCTOU** (سباق بين الفحص والتعليق).
- **غير متناسق** — أحيانًا الفحص بمعرف+tenant، أحيانًا منفصل، أحيانًا غائب (كما في `approve_api.decision` الذي لا يبدو فيه فحص ملكية واضح قبل UPDATE في المقاطع المعروضة).

**الخلاصة:** هذا يؤكد **الدقة الكاملة للدرس المنهجي** — لم تكن نقطتان مفلتتان، بل **عشرات المواقع (40+ استعلام) عبر 8+ راوترات ومحركات** في جداول تملك `tenant_id`. التصحيح اليدوي التقطيعي لا يمكن أن يغطي 400 جدول/1027 endpoint.

---

## 4) التوصيات (مرتبة بالأولوية)

1. **لا يُعتبر أي ملف "مقفول أمنيًا" بعد التصحيح النقطي** — إغلاق ملف يتطلب مرور الفحص المنهجي على كل نقاط استدعاء كل دالة غُيّر توقيعها (تم الآن لـ ai/system).
2. **تفعيل type-checking (مypy strict / pyright)**: غير مثبّت حاليًا وليس في requirements.txt. نوع "missing required positional argument" يُشتبه تلقائيًا وقت الـ build وليس runtime — كان سيكشف السطرين الأصليين (وأي نظير) دون قراءة ملف ملف.
3. **الحل البنيوي الجذري: PostgreSQL Row-Level Security (RLS)** — يمنع التسريب حتى لو نسي الكود تمرير `tenant_id`. هذا الوحيد الذي يوقف الفئة كلها بدل اعتماد انضباط كل نقطة.
4. **إغلاق ملف الـ IDOR لن يحدث على أي راوتر** إلا بعد (grep المُنظّم + mypy) مرة واحدة على الأقل لكل الـ93 محرك.
5. **بعد نجاح ذلك فقط**، يمكن العودة لمخطط Business Factory / DNA.

---

## 5) حدود هذا الفحص والخطوة التالية

استُبعدت من "IDOR مؤكد" الحالات التي يحدث فيها SELECT ملكية موسوم بـ tenant قبل التعديل (لأسباب دقة التصنيف). الفحص الدقيق لكل endpoint يحتاج مراجعة ما قبل/بعد السطر لكل موقع من القائمة 3.1.

**أولوية الفحص اليدوي المقترحة (الأعلى خطورة/أكثرها عرضة):**
- `services_api.py` (10 جداول + قراءات/تعديلات)
- `trading_api.py` (7 جداول + أرصدة مالية)
- `approve_api.py` (قرارات الموافقة)
- `custom_api.py` (DBP custom records + workflow v2)

**قرار مقترح للمستخدم:** البدء بمعالجة القائمة 3.1 (تطبيق نفس نمط الـ patch السابق مع فحص ملكية) ثم تغطية بـ mypy + تقييم اعتماد RLS.
