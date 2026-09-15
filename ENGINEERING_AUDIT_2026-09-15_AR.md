# مراجعة هندسية وجاهزية الإنتاج لمنصة 2TO EOS

**تاريخ/خط أساس المراجعة:** 2026-09-15، مع إعادة تحقق مقابل `b34c07d` والفرع الحالي
**النطاق:** الكود المصدري، الترحيلات، الاختبارات، CI/CD، Docker/Compose، وثائق النشر، والواجهة التي تُبنى فعلياً. هذه ترجمة عربية موجزة ومكافئة من حيث الاستنتاجات للتقرير التفصيلي الإنجليزي في `ENGINEERING_AUDIT_2026-09-15.md`؛ ولا تستنتج اكتمال ميزة من README أو من وجود route فقط.

**وثيقة المنتج المبنية على هذه النتائج:** [`EOS_PRODUCT_VISION_V1_AR.md`](EOS_PRODUCT_VISION_V1_AR.md).

## أ. الملخص التنفيذي

EOS اليوم تطبيق FastAPI صغير ذو وحدات متعددة. أعيد تدقيق هذه النسخة بعد commit `b34c07d` الذي أصلح backend refresh-token، بوابة CI، أسرار production، وNginx API proxy. وهو ليس بعدُ **نظام تشغيل أعمال أصلياً للذكاء الاصطناعي**. توجد نواة حقيقية للسجلات الديناميكية متعددة المستأجرين، وتوثيق تدقيق، ومصادقة بجلسات محفوظة، ومكوّنات أولية لسير العمل والقواعد والأحداث والرسم البياني والتقارير، إضافة إلى دفتر أستاذ مالي ومجال إنشاءات واسع. لكن هذه المكوّنات لا تكوّن منصة واحدة متكاملة: التطبيق أقرب إلى prototype لخلفية ERP للإنشاءات له طموحات منصة.

أكبر مشكلة تكامل هي أن `frontend/src/main.tsx` يشغّل `frontend/src/App.tsx`، بينما واجهة الكتالوج/الكيانات/استديو الميتاداتا الأحدث موجودة في `frontend/src/components/App.tsx` ولا يمكن الوصول إليها. الواجهة المشحونة لا تعرض السجلات الديناميكية أو الرسم البياني أو سير العمل أو القواعد أو الأحداث أو تقارير التحليلات، ولا تستطيع عرض القصة المطلوبة: كائن أعمال ← علاقة ← سير عمل ← قاعدة ← حدث ← تحليلات ← AI.

**الحكم النهائي:**

| نوع الجاهزية | الحالة | السبب الدقيق |
|---|---|---|
| عرض احترافي (Demo) | **غير جاهز** | الخلفية تملك بعض اللبنات، لكن الواجهة لا تقدم رحلة أعمال كاملة ولا AI أو Graph/Workflow/Rules UI. |
| إنتاج فعلي | **غير جاهز** | توجد ثغرات تكامل مصادقة، Event Bus غير متين، تفويض مجزأ، وضوابط محاسبية وتشغيلية ناقصة؛ وملاحظة الاختبار المحلية تحتاج تحققاً في CI المدعوم. |
| EOS Platform كاملة | **غير جاهز** | لا يوجد AI أو Document Intelligence أو Integration Hub أو SDK/Marketplace أو Builder متكامل. |

### تصحيحات إعادة التحقق بعد `b34c07d`

النتائج القديمة التالية **استُبدلت صراحةً**: backend refresh-token hash lookup وrotation/reuse protection **مطبقة**؛ Nginx **يمرّر** `/api/` إلى `backend:8000`؛ CI يثبت dependencies ويشغّل audits وfailure gates بلا `continue-on-error`؛ Compose يطلب production secrets بدلاً من placeholder password؛ و`httpx>=0.28,<1` معلن في test extra. finding المصادقة المتبقي هو **defect تكامل في الواجهة المشحونة فقط**: root `App.tsx` لا يستخدم مسار refresh/logout/configurable client الموجود أصلاً.

## ب. جرد المستودع وما تم التحقق منه

| المجال | الموجود فعلياً | التقييم |
|---|---|---|
| الإعداد الجذري | `pyproject.toml` وAlembic وCompose وDocker و`.env.example` وREADME/DEPLOYMENT | لا يوجد lockfile/constraints لبايثون؛ يوجد `package-lock.json` للواجهة فقط. |
| وحدات الخلفية | `auth`, `metadata`, `records`, `workflow`, `rules`, `events`, `graph`, `reporting`, `audit`, `notification`, `lookup` | يتم تضمين الـ routers في `backend/app/main.py` ومعظمها SQLAlchemy متزامن. |
| ERP | `financial`, `construction` مع `reports`/`export`/permissions قديمة | معمارية متنافسة: كائنات JSON ديناميكية مقابل جداول ERP ثابتة. |
| الواجهة | App جذري و20+ مكوّن وi18n وعميل API بسيط | التطبيق الذي يبنى هو shell ERP القديم؛ Catalog/Entity/MetadataStudio غير مدمجة. |
| قاعدة البيانات | 16 ترحيلاً حتى `0014`، بما فيها revision IDs غير رقمية | تم بنجاح upgrade لقاعدة SQLite جديدة؛ لم نتحقق محلياً من PostgreSQL. |
| الاختبارات | 20 وحدة اختبار backend | لا توجد اختبارات frontend أو E2E أو load/concurrency حقيقية. |
| CI/CD | workflow واحد: lint/migrations/tests/audits/frontend build | لا نشر أو image publishing أو rollback أو runtime migration. |

## ج. ما هو مكتمل فعلاً

1. **مصادقة مرتبطة بالمستأجر وجلسات محفوظة:** التسجيل ينشئ tenant وuser وعضوية admin، ثم audit/event/session. التوكن يتضمن access+refresh، والتحديث يلغي الجلسة القديمة وينشئ جلسة جديدة. `require_principal` يتحقق من التوقيع والانتهاء والجلسة والمستخدم والعضوية والدور. كلمات المرور PBKDF2-HMAC-SHA256 مع salt. هذا أساس صالح، لا نظام هوية مؤسسي كامل.
2. **سجلات أعمال ديناميكية:** metadata المنشورة تتحكم في الأنواع، required/nullability، default، computed/readonly، validation أساسي، CRUD permissions، علاقات records، filter، version، audit، events، وبدء workflow اختياري. الاستعلامات الأساسية تقيّد بـ `tenant_id`.
3. **الدفتر المالي الأساسي:** إنشاء draft والتحقق من ملكية الحسابات وتوازن المدين/الدائن؛ عند posting يقفل الحسابات، يتحقق من السطور، ويسجل audit/event. هذه وظيفة ledger حقيقية وليست بيانات واجهة وهمية.
4. **خدمات منصة أولية:** تعريفات/instances workflow ومهام موافقة؛ قواعد WHEN/IF/THEN بسيطة؛ graph يمر عبر relation fields حتى عمق 3؛ reports محفوظة count/sum/avg/min/max. جداول audit/notifications/system_events محفوظة.
5. **مجال الإنشاءات واسع في الخلفية:** مشاريع، عقود، BOQ/budgets، مطالبات، أوامر تغيير، subcontracts، procurement، PO، GRN، invoices وpayments. الواجهة تعرض subset فقط.
6. **تحصين تشغيلي أساسي:** request ID، headers، CORS allowlist، حد حجم body، timeout، GZip، rate limits، metrics/health وDocker health checks.

## د. ما هو جزئي أو مضلل

| المكوّن | الحالة | الفجوة الدقيقة |
|---|---|---|
| Metadata Engine V2 | **جزئي** | يوجد version/publish/validation، لكن record لا يخزن metadata version ولا توجد compatibility/retire/rollback؛ المالية والإنشاءات تتجاوز metadata. |
| Policy / RBAC | **جزئي** | permissions للـ metadata هي admin/member CRUD فقط؛ permissions ERP خريطة roles ثابتة منفصلة؛ لا custom roles أو field/action/approval policy موحد أو RLS. |
| Workflow V2 | **جزئي** | states/transitions/conditions/role approvals/history/events موجودة؛ لا assignment فردي، delegation، escalation، timers، retry، compensation أو concurrency lock. |
| Rules | **نموذج أولي** | شروط AND مسطّحة وثلاثة actions فقط؛ لا idempotency أو retry/DLQ وتعمل في نفس session والطلب. |
| Event Bus | **نموذج أولي** | `SystemEvent` event log في DB، لكن subscribers callbacks في الذاكرة وداخل العملية، لا broker/outbox/consumer offsets/replay/DLQ/backpressure. |
| Business Graph | **جزئي** | API قصة علاقات للقراءة فقط؛ لا edge store أو visual explorer أو graph search/analytics/scalable traversal. |
| Reporting/Analytics | **جزئي** | report محفوظ موجود، لكن يجلب كل records للمستأجر إلى Python للفلترة/grouping؛ لا UI له ولا SQL aggregation أو scheduling/cache/share policy. |
| Financial Core | **جزئي** | journals balanced/posting موجودة؛ لا fiscal close، tax، FX/currency، AP/AR/reconciliation، reversals/immutability أو statutory exports. |
| Construction ERP | **جزئي** | schemas/services واسعة، لكن لا رحلة UI/Workflow كاملة ولا وثائق/approvals/reporting متحقق منها end-to-end. |
| Globalization | **نموذج أولي** | Arabic/RTL toggle فقط؛ لا timezone/locale decimal/date/currency/tax/fiscal/e-invoicing. |
| Deployment | **جزئي** | Compose موجود وNginx يمرر `/api/` إلى backend؛ لكن لا Alembic release job ولا IaC أو topology إنتاجي. |

## هـ. ما هو مفقود

* **AI:** لا tool registry، LLM provider، agents، prompt management، context builder، permission-aware tools، audit/approval أو observability للـ AI.
* **Document Intelligence:** لا upload/storage/OCR/classification/extraction/matching/validation أو document-triggered workflow.
* **Integration Hub:** لا OAuth/API keys/inbound-outbound webhooks/adapters/queue/retry/DLQ/logs/secrets lifecycle.
* **منصة مطورين:** لا EOS Builder كامل أو SDK أو marketplace أو extension isolation.
* **هوية مؤسسية:** لا password reset/verification، MFA/SSO/SCIM، lockout، session/device management، custom RBAC موحد أو RLS.
* **واجهة منصة:** لا Graph Explorer أو Rule/Workflow designers أو AI Copilot أو workspace يربط primitives بوحدات ERP.

## و. نتائج الأمن (من CRITICAL إلى LOW)

لم يظهر في المسح الثابت المراجع **CRITICAL** مثبت، لكن البنود التالية تمنع الإنتاج:

### HIGH — EOS-SEC-01: التوكنات قابلة للقراءة من JavaScript وتسجيل الخروج لا يلغي الجلسة

* **الدليل:** `frontend/src/App.tsx`، `handleLogin` يخزن `data.access_token` في `localStorage` تحت `token`، و`handleLogout` يمسحه محلياً فقط. `/auth/logout` وhelper `refreshToken` الموجودان في الخلفية/`api.ts` غير مستخدمين من التطبيق المشحون.
* **سيناريو الاستغلال:** XSS بنفس الـ origin أو script ضار يقرأ bearer token. بعد الضغط على Logout يبقى التوكن المسروق/القديم صالحاً حتى TTL لأن الجلسة لم تُلغَ في server.
* **الإصلاح/اختبار:** BFF أو refresh cookie بـ HttpOnly+Secure+SameSite وaccess token في الذاكرة؛ استدعاء logout؛ browser test يؤكد أن `/auth/me` يرجع 401 بعد logout.

### HIGH — EOS-SEC-02: لا حدّ متين بين transaction وآثار events/rules الجانبية

* **الدليل:** `backend/app/events/service.py:publish` يضيف event ثم `_dispatch` callbacks synchronously؛ `rules/engine.py:_on_event` ينفذ actions في DB session نفسه ويمتص أخطاء handlers بعد logging.
* **الأثر:** يمكن حفظ event دون side effect المقصود، ولا توجد retry بعد restart؛ وإذا أضيف side effect خارجي لاحقاً يمكن أن يحدث قبل rollback للمعاملة. خطر نزاهة عالٍ للموافقات والماليات.
* **الإصلاح/اختبار:** transactional outbox وworker وبroker وdelivery state/idempotency/DLQ؛ اختبارات rollback/restart/duplicate.

### MEDIUM — EOS-SEC-03: تفويض ثابت ومجزأ

* **الدليل:** `permissions.py` role map ثابت، و`records/router.py:_allowed` يطبق CRUD metadata، و`metadata/router.py:_permissions` يطبق نموذجاً آخر.
* **الأثر:** route جديد يمكن أن يتجاوز policy المناسبة؛ لا يمكن فرض object/field/action policies على exports/reports/graph/events/AI.
* **الإصلاح:** policy service موحد، deny-by-default، واختبارات كل role/resource/field/tenant.

### INFO — EOS-SEC-04: ملاحظة بيئة الاختبار المحلية تحتاج إعادة تحقق في CI

* **الدليل والتصحيح:** `pyproject.toml` يعلن صراحة `httpx>=0.28,<1` في test extra. فشل `pytest -q` كان في بيئة المراجعة المحلية Python 3.14، حيث طلب Starlette TestClient resolved حزمة `httpx2`. لذلك ليس هذا دليلاً على نقص `httpx` في المشروع أو كسر backend refresh. لا يوجد lockfile لبايثون، لذا resolution المحلي غير مثبت.
* **الحكم/الإصلاح:** finding بيئة/قابلية إعادة تحقق فقط حتى يتكرر على clean CI مدعوم Python 3.11/3.12؛ احتفظ بـ `httpx` المعلن، وسجل resolved packages، وأضف lock/constraints فقط إذا كانت reproducibility دقيقة متطلب إصدار.

### LOW — EOS-SEC-05: CSP وحافة المتصفح غير مكتملة

* **الدليل:** headers للـ API موجودة و`frontend/nginx.conf` يضبط `/api/` مع `proxy_pass http://backend:8000`، لكن لا يضبط CSP ولا SRI.
* **الإصلاح:** CSP ملائم لأصول Vite، HTTPS gateway، وفحص headers للواجهة وAPI.

**ضوابط إيجابية مثبتة:** توقيع JWT وclaims/expiry، refresh rotation، password hashing، tenant predicates لسجلات metadata، حد body، CORS، rate limit، والتحقق من secret في production.

## ز. نتائج المعمارية والخلفية والبيانات والأداء

* الحدود الحالية router → service/model عملية، لكنها ليست فصل domain/application/infrastructure واضحاً. `construction/service.py` كبير جداً (قرابة 1,900 سطر) وهو نقطة coupling وصيانة عالية.
* transactions للكتابات غالباً تجمع record/audit/event/workflow جيداً، لكن synchronous callbacks تلغي failure isolation ولا تمنح durable delivery.
* records هي JSON؛ الفلاتر تستخدم JSON expressions، والتقارير تحمل كل rows إلى الذاكرة. هذا مناسب مبدئياً عند 10 tenants وبيانات صغيرة. عند 100 tenants يلزم indexing/selective materialization للحقول الساخنة؛ عند 1,000 users/tenants يلزم workers/search/async reports؛ عند 10,000 tenants يلزم RLS/partition-or-shard/quota/broker/analytics منفصل.
* optimistic concurrency للسجل ليس atomic SQL CAS: عمليتا PATCH متوازيتان تستطيعان قراءة version نفسه ثم overwrite. metadata version هو `max(version)+1` بلا unique constraint/lock، لذلك يمكن تكرار version عند concurrent create.
* ترحيلات SQLite من الصفر نجحت حتى `0014`. لا يكفي هذا لإثبات PostgreSQL أو downgrade/online migration أو backup/restore. لا يوجد RLS ولا tenant-scoped composite FK عامة.
* توجد request IDs/logs/metrics/health؛ لا توجد tracing وalerts وSentry وworker correlation وload/chaos tests أو runbook للنسخ/الاستعادة.

## ح. نتائج الواجهة وتجربة المنتج

* التطبيق المبني فعلياً هو root `App.tsx`، وبالتالي `components/App.tsx` و`CatalogPage` و`EntityPage` و`MetadataStudio` dead/unintegrated.
* صفحات الواجهة تستعمل `fetch('/api/v1/...')` مباشرة بدلاً من `api.ts` و`VITE_API_URL`. هذا عدم اتساق integration/portability، وليس فشل Compose routing: Nginx يمرر `/api/` الآن إلى `backend:8000`.
* backend refresh/logout مكتمل، لكن root UI المشحون لا يستهلكه: يخزن access token فقط في `localStorage`، لا يستدعي `refreshToken`، ويمسح الحالة محلياً بلا `/auth/logout`. لا feedback عند login failure (`if (!response.ok) return`) ولا route authorization أو browser routes عميقة.
* القائمة تعرض ERP pages فقط؛ لا workspace catalog أو Graph أو workflow/rules/events/metadata/AI. كما لا تظهر واجهة للمسار المتقدم للإنشاءات (PO/receipt/invoice/payment) رغم وجود backend.
* RTL موجود، لكن locale-aware dates/numbers/currency/timezones/accessibility/responsiveness لا توجد لها أدلة اختبار.

## ط. الاختبارات وCI/CD وDocker والنشر

* **نجح محلياً:** ترحيل SQLite الجديد، `ruff check backend main.py`، وfrontend lint/Prettier/production build.
* **ملاحظة بيئة محلية:** `pytest -q` فشل في collection قبل assertions في Python 3.14 المراجع بسبب طلب `httpx2` من Starlette resolved. وبما أن `httpx>=0.28,<1` معلن بالفعل، فهذا ليس defect في `pyproject.toml` ولا دليلاً على فشل backend suite؛ يحتاج clean CI على Python 3.12.
* الاختبارات الموجودة API-centric وتغطي auth/metadata/records/workflow/events/rules/graph/reporting/finance/construction. المفقود: frontend unit/component/E2E، browser token tests، PostgreSQL production migration evidence محلياً، contract generation، concurrency/load/chaos/DLQ، SAST/secret scan وfull stack deploy smoke.
* CI يشغّل SQLite وPostgreSQL وdependency audits وfrontend build، لكن Docker test فقط عند push إلى main وليس PR، ويستخدم SQLite memory ولا يتحقق من production migrations. لا registry/signing/deploy/rollback/IaC/post-deploy test.
* Docker multistage وhealth checks موجودان، لكن container يعمل root، لا يشغّل Alembic قبل serving، والـ frontend لا يتكامل مع API ذاتياً.

## ي. نشر موصى به

انشر frontend كـ static app منفصل فقط مع `VITE_API_URL` صريح، أو اضبط Nginx `/api` proxy. انشر API containers خلف HTTPS ingress/load balancer، وworkers منفصلة. استخدم managed PostgreSQL مع PITR/backups وmanaged Redis للـ cache/rate limits لا كبديل event durability. شغّل Alembic كـ release job مقفل قبل API rollout. استخدم outbox+broker+workers قبل أي automation مالي/approval. Vercel مناسب للواجهة الثابتة لا لتشغيل monorepo كاملاً الذي يحتاج API stateful dependency وعمالاً دائمين.

## ك. خريطة Roadmap

| بند roadmap | الحالة | الدليل المختصر |
|---|---|---|
| Metadata Engine V2 | **جزئي** | definitions/validation/computed/version موجودة؛ لا lifecycle compatibility ولا single source of truth. |
| Policy Engine | **نموذج أولي** | `policy.py` شروط بسيطة، والتفويض منفصل. |
| Rules Engine | **نموذج أولي** | شروط/actions بسيطة synchronous. |
| Event Bus | **نموذج أولي** | event log + in-process dispatch فقط. |
| Workflow V2 | **جزئي** | transitions/approvals موجودة؛ lifecycle مؤسسي مفقود. |
| Business Graph | **جزئي** | relation story API فقط. |
| Document Intelligence | **مفقود** | لا OCR/document code. |
| Integration Hub | **مفقود** | لا webhooks/OAuth/adapters. |
| Reporting/Analytics | **جزئي** | saved KPI/feed بلا UI scalable. |
| AI Tool Registry / AI Workforce | **مفقود** | لا AI module/dependency/provider/agent. |
| Globalization | **نموذج أولي** | RTL/translation toggle فقط. |
| EOS Builder / SDK / Marketplace | **مفقود** | لا builder lifecycle ولا SDK أو extension marketplace. |

## ل. عيوب فعلية قابلة لإعادة الإنتاج

| المعرف | الخطورة | الملف/الدالة | المشكلة وطريقة إعادة الإنتاج | الإصلاح واختبار الانحدار |
|---|---|---|---|---|
| EOS-BUG-01 | HIGH | `frontend/src/App.tsx:handleLogin/handleLogout` | **backend refresh rotation وlogout endpoints تم إصلاحهما/تنفيذهما.** لكن UI المشحون لا يستخدمهما: يخزن `token`/`user` فقط، لا يستدعي `refreshToken` ولا `/auth/logout`. سجّل الدخول ثم Logout واستعمل token السابق مع `/api/v1/auth/me`: يبقى صالحاً حتى TTL. | وحّد shipped App مع API/session architecture القائمة؛ refresh قبل expiry وserver logout؛ browser test يتوقع 401. |
| EOS-BUG-02 | MEDIUM | `events/service.py:publish` و`rules/engine.py:_on_event` | handler يرفع exception ثم publish/commit/restart: event محفوظ ولا retry للـ side effect. | outbox/worker/DLQ/idempotency؛ restart/duplicate/rollback tests. |
| EOS-BUG-03 | MEDIUM | `metadata/router.py:create_entity` | concurrent creates للـ tenant/code نفسه يمكن أن تحسب `max+1` نفسه. | unique `(tenant_id, code, version)` + retry/lock؛ concurrency test. |
| EOS-BUG-04 | MEDIUM | `records/router.py:update_record` | عمليتا PATCH تقرآن version N قبل commit ثم كلتاهما تكتبان، فيضيع تحديث. | SQL UPDATE WHERE version + rowcount؛ simultaneous PATCH test. |

## م. أسرع طريق إلى Demo-Ready EOS

لا تعِد بناء النواة. استعمل metadata/records/workflow/rules/graph/reporting الموجودة، ونفّذ فقط الآتي:

1. وحّد تطبيقَي الواجهة واجعل catalog/entity/metadata studio قابلة للوصول في workspace واحد مع API base موحّد.
2. أنشئ entities demo: **Customer, Opportunity, Contract, Project, Procurement Request, Supplier Invoice, Payment** وعلاقاتها؛ استعمل endpoints الإنشاءات القائمة فقط حيث تقدم dependency حقيقية.
3. أضف panels تستدعي APIs القائمة: graph story، workflow state/approval، rule execution/event history، وsaved report مع drill-to-source.
4. seed tenant واحداً ببيانات واقعية وأدوار، workflow للموافقة، وقاعدة high-value invoice تنشر event/notification/audit؛ لا ترحّل إلى payment/journal قبل approval.
5. بعد وضع tool boundary على server، أضف **AI copilot read-only** بأدوات allowlisted: summary للـ record/graph/pending approvals/report؛ سجّل prompt/tool call، ولا تسمح SQL حر أو write tools.
6. اختبر browser journey: login → workspace → customer/opportunity/contract/project → procurement/invoice → approval → payment/journal → analytics → copilot. أضف E2E وdemo reset deterministic.

## ن. P0 إلى P3

| الأولوية | المهمة | التعقيد | قبول العمل والاختبارات |
|---|---|---|---|
| P0 | توحيد shipped frontend مع platform App/API/session architecture القائمة | متوسط | workspace واحد reachable، ويستخدم `VITE_API_URL` وrefresh rotation وserver logout فعلياً، مع errors/loading وbrowser tests. |
| P0 | دمج App المتنافسين ضمن التوحيد | متوسط | لا dead production App؛ catalog/entity/studio قابلة للوصول وE2E. |
| P0 | atomic metadata/record writes | متوسط | unique version وCAS، مع concurrent tests. |
| P1 | Demo Workspace والرحلة الكاملة | متوسط | customer→payment مع graph/workflow/rule/event/report ظاهرة وPlaywright/Cypress. |
| P1 | عرض lifecycle الإنشاءات/الماليات الضروري فقط | متوسط | procurement→invoice→payment validation/audit/UI وcontract tests. |
| P1 | Graph/Workflow/Rules/Events/Reports panels | متوسط | inspection وpermission tests لكل panel. |
| P1 | read-only AI copilot foundation | عالٍ | tools server-side allowlisted، audit، no DB/write direct، adversarial auth tests. |
| P2 | outbox/broker/workers/DLQ/idempotency | عالٍ | rollback/restart/duplicate/replay/load evidence. |
| P2 | authorization موحد + tenant defense | عالٍ | deny-by-default، custom policies، IDOR suite وربما PostgreSQL RLS. |
| P2 | financial controls وproduction operations | عالٍ | periods/reversals/tax/currency/reconciliation وPITR/restore/alerts/TLS/migration job. |
| P3 | metadata lifecycle/builder، docs/integrations/globalization/SDK/marketplace/workforce | عالٍ جداً | schema evolution، sandbox، regional/security/reliability acceptance suites. |

## س. Scorecard (0–10)

| المجال | الدرجة | التبرير |
|---|---:|---|
| Architecture | 4 | بداية modular جيدة، لكن dual architecture/global synchronous state وconstruction hotspot. |
| Backend | 6 | CRUD/services حقيقية، وrefresh/session protections وCI security gates مطبقة؛ boundaries/reliability غير ناضجة. |
| Frontend | 3 | يبنى وصفحات ERP/RTL، لكن platform UI غير مشحونة وshipped App يتجاوز architecture الـAPI/session الموجودة. |
| Database | 5 | ORM/migrations/SQLite fresh؛ JSON scale/RLS/PG/online safety ناقصة. |
| Security | 5 | refresh rotation وCI audits وproduction-secret requirements حسّنت الأساس؛ token storage/authz/event delivery ما زالت تمنع الإنتاج. |
| Authentication | 6 | sessions وrefresh lookup/rotation/reuse protection وhashing مطبقة؛ لا enterprise lifecycle والواجهة المشحونة لا تستعملها. |
| Authorization | 3 | membership موجودة لكن policy static/mجزأة. |
| Multi-tenancy | 5 | core scoped؛ لا RLS أو proof كامل لكل pack. |
| Metadata / Dynamic records | 5 / 5 | نواة مفيدة، لا lifecycle آمن أو CAS/scale كامل. |
| Workflow / Rules / Events | 4 / 3 / 2 | skeleton مفيد؛ rules/event ليست durable enterprise infrastructure. |
| Business Graph | 3 | API relation story وليس experience/layer كامل. |
| Financial Core / Construction | 4 / 4 | نواة ledger وschema breadth؛ لا controls/lifecycle/UX كامل. |
| Analytics / AI readiness | 3 / 0 | KPI backend غير متكامل UI/scalable؛ AI غير موجود. |
| Testing / CI-CD | 3 / 5 | test intent جيد لكن local collection observation وE2E/ops مفقودة؛ CI dependencies/audits/gates جيدة بلا `continue-on-error`. |
| Docker / Deployment | 5 / 3 | build/health وNginx API proxy وproduction secrets موجودة؛ لا migration job/topology/rollback. |
| Observability / Documentation / UX | 4 / 3 / 3 | IDs/logging basics؛ runbooks/architecture truth وworkspace UX ناقصة. |
| Demo / Production / Platform completeness | 2 / 2 / 2 | يجب إنجاز P0/P1 ثم P2 قبل الادعاءات. |

## ع. Definition of Done

### Demo Ready

- [ ] workspace منشور واحد مع API base وrefresh/logout سليمين.
- [ ] رحلة seeded: Customer → Opportunity → Contract → Project → Procurement → Invoice → Approval → Payment.
- [ ] form metadata + graph + workflow + rule/event/audit + KPI drill-to-source ظاهرة للمستخدم.
- [ ] loading/error/empty states وroles وdemo reset وbrowser E2E.
- [ ] copilot read-only، permission-aware، audited، بأدوات server-side allowlisted.

### Production Ready

- [ ] كل P0/P1/P2، dependency build مقفل وCI نظيف على PostgreSQL.
- [ ] outbox/workers/DLQ/idempotency واختبارات failure/restart/concurrency/load.
- [ ] authorization موحد وtenant/IDOR defense عبر كل API/export/report/graph/event.
- [ ] accounting controls قانونية/محاسبية وimmutable audit/reversal بعد مراجعة مختص مالي.
- [ ] TLS/secrets/migration gating/PITR+restore drill/monitoring-alerts-tracing/runbooks.

### EOS Platform V1

- [ ] أسس الإنتاج أعلاه وmetadata builder lifecycle-safe وSDK.
- [ ] graph/rule/workflow builders، scalable analytics، integrations وdocument intelligence.
- [ ] AI registry/agents مع permission context/approval/audit/quotas/observability.
- [ ] globalization (locale/timezone/currency/tax/fiscal/e-invoicing) وmarketplace/extensions مع isolation.
