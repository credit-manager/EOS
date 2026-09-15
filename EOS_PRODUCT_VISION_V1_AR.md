# 2TO EOS Operating Platform V1 — تعريف المنتج وخطة البناء

**الحالة:** وثيقة المنتج/المعمارية المرجعية المقترحة.
**الهدف:** تحويل EOS من ERP متعدد الوحدات إلى **AI-native Business Operating System**، مع إعادة استخدام النواة الموجودة وعدم إعادة بناء ما يعمل.

## 1. التعريف الرسمي (North Star)

> **2TO EOS هو نظام تشغيل أعمال ذكي مبني على الذكاء الاصطناعي، يحوّل نموذج الشركة وبياناتها وقواعدها وعملياتها وحقيقتها المالية إلى منظومة تشغيل واحدة ذكية وقابلة للتطوير.**

الـ ERP ليس تعريف المنتج بالكامل؛ بل هو أول **Industry/Application Pack** مرجعي يعمل فوق المنصة.

```text
2TO EOS
├── EOS Platform: Data, Policy, Rules, Workflow, Events, Graph, Analytics
├── EOS AI: Tools, Agents, Approvals, Audit, Reasoning
├── ERP Core: Financial truth + operational packs
├── Industry Packs: Construction أولاً، ثم retail/manufacturing/…
└── Customer Apps: objects/workflows/views معرفة من العميل عبر EOS Builder
```

## 2. المشكلة، العميل، والوعد

### المشكلة

الشركة المتوسطة تعمل بين المحاسبة وExcel وWhatsApp والبريد وCRM وإدارة المشاريع والوثائق والأنظمة الحكومية. النتيجة هي إدخال مكرر، موافقات يدوية، سياق ضائع، قرارات بطيئة، واعتماد على ذاكرة الموظفين بدلاً من نظام يفهم العمل.

### العميل المثالي الأول (ICP)

شركات 50–1,000 موظفاً، متعددة الأقسام أو المواقع، ولديها مشاريع ومشتريات ومالية وموافقات؛ البداية المقترحة هي **الإنشاءات، والتوزيع، والعقار، والتجارة والخدمات المهنية** في الأسواق الناشئة. لا تبدأ الشركة بـ Fortune 500 أو micro-business.

### الوعد التجاري

> **صف طريقة عمل شركتك؛ يقوم EOS بنمذجتها وأتمتتها وتشغيلها وفهمها، مع أثر مالي وحوكمة قابلين للتدقيق.**

لا نبيع “ERP فيه 500 ميزة”، ولا “chatbot”. نبيع نظاماً يربط العمل التشغيلي بقراراته وموافقاته وأثره المالي.

## 3. مبادئ المنتج غير القابلة للتفاوض

1. **Business Object قبل الشاشة أو module.** كل Customer أو Project أو Invoice كائن حي له بيانات وعلاقات وسياسات وworkflow ووثائق وأحداث وأثر مالي وتحليلات وسجل تدقيق وسياق AI.
2. **Business Graph قبل الجداول المتفرقة.** يرى المستخدم وAI القصة التجارية والعلاقات، لا 20 جدولاً بلا سياق.
3. **Financial truth domain-controlled.** يمكن للعميل توسيع CRM/Operations/Custom Objects؛ لكن ledger/posting/balances/periods/currency/tax تبقى نواة محكومة لا Dynamic CRUD.
4. **Policy قبل automation وAI.** لا أداة أو agent ينفذ قبل tenant/object/action/field policy، limits، وسجل تدقيق؛ والـ AI لا يوافق على عمله.
5. **Event + outbox قبل integration وautomation الحساسة.** لا تعتبر callback في الذاكرة Event Bus إنتاجياً.
6. **Drill-to-source دائماً.** كل KPI وتوصية AI يجب أن تعرض المصدر والكائنات والقيود التي بُنيت عليها.
7. **Builder يولّد تجربة محكومة، لا CRUD generator فقط.** object definition يجب أن ينتج API/UI/search/audit/permissions/workflow/AI context وفق lifecycle متوافق.
8. **Pack composability.** Industry وcountry packs تضيف objects/rules/workflows/reports/compliance عبر contracts versioned، لا عبر forks من EOS Core.

## 4. تجربة المستخدم: ثلاث طبقات فقط

### 4.1 Workspace — “ما الذي يحتاج انتباهي؟”

الصفحة الرئيسية لكل مستخدم تعرض: My Tasks، My Approvals، Alerts، records الحديثة، KPIs وفق الدور، risks/overdue، وتوصيات AI. لا تكون Dashboard ثابتة فقط؛ بل feed مرتبط بtenant والrole والسياسات.

### 4.2 Business View — “قصة هذا الكائن”

فتح Project أو Supplier أو Customer يفتح صفحة موحدة ذات tabs: Overview، العلاقات/Graph، Financial، Timeline/Events، Documents، Workflow/Approvals، Risks، Analytics، Audit وAI. تختلف tabs وفق تعريف object والسياسة، لا وفق sidebar ثابت فقط.

### 4.3 Ask EOS — طبقة command آمنة

Ask EOS يترجم النية إلى أدوات allowlisted:

```text
Intent → tenant + permission scope → tool plan → source-backed result
     → draft action (إن وُجد) → human approval/policy → execute → audit
```

المرحلة الأولى **read-only executive intelligence**: “ما الموردون الذين تجاوزوا الميزانية؟” مع مصادر وروابط records. المرحلة التالية تصنع drafts فقط (notification/requisition)، ولا تنفذ posting أو تغيير bank account أو self-approval.

## 5. نموذج Business Object وBusiness Graph

### العقد الموحد للكائن

```text
BusinessObjectDefinition
├── identity: code, version, lifecycle
├── fields: types, validation, calculated/default fields
├── relations: target object, cardinality, integrity
├── views: list/detail/board/timeline/form
├── policies: object/field/action/approval visibility
├── workflow binding and rules
├── document requirements
├── event contracts
├── reporting dimensions/measures
├── financial mapping (reference only; financial core owns posting)
└── AI context/tool exposure policy
```

### ما يعاد استخدامه من المستودع الحالي

* `metadata` و`records` هما بداية definition/record validation/relations/versioning.
* `graph` يمكن أن يصبح read model للقصة التجارية بعد استبدال traversal المكلف بmaterialized edges/indexes.
* `workflow`, `rules`, `events`, `reporting`, `audit` هي بذور primitives المنصة.
* `financial` يبقى domain-controlled ledger؛ و`construction` يصبح أول Industry Pack مرجعي.

### ما يجب تغييره

لا تخزن business graph فقط كـ JSON relation محسوب عند القراءة. أضف relational graph projection/outbox consumers، uniqueness/tenant indexes، versioned event schemas، وdrill-down references. لا تجعل metadata تنشئ جداول مالية ديناميكية أو تتجاوز accounting invariants.

## 6. EOS Builder: Business Model Compiler

Builder ليس صفحة metadata واحدة؛ إنه lifecycle محكوم:

```text
Draft definition → validate compatibility → preview UI/API/policies
→ publish immutable version → migrate/projection if required → activate
→ monitor adoption/errors → deprecate/retire safely
```

### إمكانات V1 المطلوبة

1. Object، field، relation، validation، view وpermission policy.
2. Workflow binding، rule binding، document requirement، report dimension/measure.
3. Preview في tenant sandbox ونشر versioned مع rollback/compatibility policy.
4. Generated list/detail/form/search API contract، لا code generation داخل customer runtime.
5. Audit كامل لمن غيّر التعريف ومن نشره، وإدارة migration checklist.

### ما لا ندخله في V1

لا JavaScript arbitrary في metadata، لا arbitrary SQL، ولا customer-defined AI tool يملك write access مباشرة. الامتداد أولاً بواسطة declarative contracts وallowlisted actions.

## 7. طبقة الحوكمة: Policy، Workflow، Rules، Events

| طبقة | مسؤوليتها | لا ينبغي أن تفعل |
|---|---|---|
| Policy Engine | tenant/role/object/field/action/approval decision، deny-by-default | لا تربط policy بالـ frontend فقط. |
| Workflow V2 | state/transition/actor/condition/assignment/delegation/timeout/escalation/compensation/history | لا تختزل في status field. |
| Rules Engine | WHEN/IF/THEN/ELSE، priority، idempotency، safe actions | لا تنفذ recursion غير محدودة أو side effects بلا delivery state. |
| Event Platform | versioned domain events + transactional outbox + consumers/retry/DLQ/replay | لا تعتبر DB log أو in-process callback broker. |

### نموذج التنفيذ الآمن

```text
Command transaction
  ├── validate policy + domain invariants
  ├── persist domain change
  ├── persist outbox event atomically
  └── commit

Worker
  ├── publish versioned event
  ├── execute idempotent consumers/rules
  ├── retry with backoff
  └── dead-letter + observable failure state
```

## 8. Financial Core: مصدر الحقيقة

السلسلة المرجعية هي:

```text
Business activity → operational record → approved financial intent
→ domain validation → journal posting → immutable ledger/audit → reports
```

مبادئ V1: لا posting بلا balance/invariants/period policy؛ correction عبر reversal لا تعديل صامت؛ mappings بين object وfinancial intent خاضعة للمراجعة؛ currency/tax/period لا تأتي من fields حرة؛ وكل payment/invoice/procurement flow يربط المصدر التشغيلي بالقيد المالي.

## 9. Analytics وDocument Intelligence وIntegration

### Analytics

ثلاثة مستويات: operational (sales/procurement/projects)، financial (P&L/cash/AR/AP/budget/variance)، executive (growth/risk/working capital/project health). كل KPI يحتفظ بـ query definition وrecord references وpermission filter وdrill-to-source. لا تنفذ analytics كبيرة بتحميل JSON records كلها إلى Python.

### Document Intelligence (أول use case ROI)

```text
Secure upload → malware/type/size checks → object storage → OCR/classification
→ extraction → supplier/PO/GRN/entity matching → duplicate/tax validation
→ human review/approval → financial posting → audit
```

ابدأ بـ Supplier Invoice intake؛ فهو يثبت graph/workflow/rules/financial truth وAI assistance في رحلة واحدة.

### Integration Hub

Core services: REST/OpenAPI أولاً، webhooks signed، OAuth/API keys، secrets vault، mappings، schedules، delivery logs، queues/retries/DLQ وconnector health. GraphQL لا يضاف إلا لحالة قراءة مركبة تثبت الحاجة. أول connectors: email، payments/bank import، e-invoicing أو tax حسب السوق المختار، ثم WhatsApp بإذن وأثر تدقيقي.

## 10. EOS AI وAI Workforce

### AI Tool Registry

كل tool يعرّف input schema/output schema، required permission، tenant scope، data classification، rate/cost limit، هل هو read/draft/execute، وaudit event. لا يصل النموذج إلى SQL أو database session.

### Agents V1

ابدأ بـ **Executive Agent** و**Procurement Agent** فقط:

| Agent | يسمح له | ممنوع عنه |
|---|---|---|
| Executive | query KPIs، explain risk، graph summary، pending approvals | write/approve/post financial transaction. |
| Procurement | search suppliers، compare quotes، draft requisition/PO | approve own PO، تغيير bank account، posting. |

كل action write هو Draft → policy check → explicit approver → execution → audit. لا AI Workforce متعددة agents قبل تثبيت tool governance وobservability وevaluation suite.

## 11. Packs والسوق والاقتصاد

### Country packs

`Globalization Engine` يعرّف locale/timezone/currency/decimal/numbering/fiscal calendar/tax/e-invoice/compliance contracts. Egypt/Saudi/UAE packs تنفذ هذه contracts؛ لا تفرع EOS إلى “نسخة مصر”.

### Industry packs

`Construction Pack` هو المرجع الأول ويجب أن يثبت entities/rules/workflows/reports/KPIs وfinancial mappings. Retail أو Manufacturing لا تبدأ قبل أن تكتمل contracts الخاصة بالpacks والـ Builder lifecycle.

### نموذج الإيراد

1. Core SaaS per tenant/user/usage tier.
2. Industry وlocalization packs.
3. AI usage بحدود تكلفة وميزات governance.
4. Enterprise: SSO، advanced security، dedicated infrastructure، SLA/governance.
5. Professional services وشبكة implementation/integration partners.
6. Marketplace revenue share بعد SDK/extension isolation، لا قبله.

## 12. التميز القابل للدفاع عنه

ليس moat هو عدد modules. الـ moat المقترح:

```text
Business Model Compiler
+ business graph and source-linked analytics
+ financial truth
+ governed automation and AI tools
+ localization/industry pack contracts
+ accumulated tenant-specific operating context
```

تزداد قيمة المنتج داخلياً كلما زادت objects/relations/workflows والأحداث التي يفهمها بصورة مرخّصة وقابلة للتدقيق. لا تدّع network effect خارجي قبل marketplace/partner ecosystem حقيقي.

## 13. معمارية الهدف وقرارات الحدود

```text
Web Workspace / Builder / Ask EOS
             │
API Gateway + Identity + Policy Decision Point
             │
Commands ── Domain services ── PostgreSQL (tenant controls + audit)
             │                        │
             └── Transactional Outbox ┘
                         │
                    Broker + Workers
       ┌──────────┬──────┼───────┬──────────────┐
       │          │      │       │              │
   Graph projection Rules Workflow Integrations Analytics/AI tools
       │          │      │       │              │
     Search    DLQ/Retry  Tasks  Connector logs  warehouse/read models
```

* API nodes stateless؛ workers مستقلة وقابلة للتوسع؛ Redis cache/rate-limit فقط.
* PostgreSQL هو operational source of truth؛ object storage للوثائق؛ analytics read models/warehouse لاحقاً.
* tenant isolation في application **و** DB defense-in-depth (RLS where operationally viable).
* OpenAPI/event schema versions هي public contracts؛ لا تعرّض ORM models كـ SDK.

## 14. خريطة تنفيذ Operating Platform V1

### المرحلة 0 — تثبيت الاتجاه (2–3 أسابيع)

* اعتماد هذه الوثيقة وdecision records للـ tenant/policy/event/financial/AI boundaries.
* **توحيد الواجهة المشحونة** حول `api.ts` وsession/refresh/logout وCatalog/Entity/Metadata Studio الموجودين، بدلاً من Appين متنافسين.
* إزالة claim أن ما هو backend prototype لا يعمل؛ فصل `implemented`, `integrated`, `production-safe` في backlog.
* قبول: browser E2E لتسجيل الدخول/refresh/logout، وWorkspace واحد يمكن الوصول منه إلى dynamic entity.

### المرحلة 1 — Demo Operating Loop (6–10 أسابيع)

* Demo Workspace وBusiness View موحدان.
* Customer → Opportunity → Contract → Project → Procurement → Supplier Invoice → Approval → Payment.
* Graph story، workflow approval، rule firing/event timeline، KPI drill-to-source مرئية.
* Executive Agent read-only يعرض الإجابة والمصادر، ولا ينفذ كتابة.
* قبول: demo tenant seeded/resettable، role-based scenarios، E2E موثوق، ولا mock data في المسار الأساسي.

### المرحلة 2 — Platform safety and scale (3–5 أشهر)

* Policy decision point موحد/custom roles/field actions وIDOR suite/RLS plan.
* Workflow V2 وoutbox/broker/workers/DLQ/idempotency/event contracts.
* metadata lifecycle وBuilder publish/compatibility/rollback، atomic record/version writes.
* analytics read model، document invoice intake، financial controls الأساسية.
* قبول: rollback/restart/duplicate/concurrency/load tests، telemetry/alerts، migrations/release job وbackup/restore drill.

### المرحلة 3 — Commercial platform expansion (6–12 شهراً)

* Integration Hub/connectors، Egypt ثم GCC globalization packs، Construction Pack hardened.
* Procurement Agent draft actions، AI evaluations/cost budgets/approval governance.
* SDK/extension isolation ثم marketplace foundation وشبكة partners.
* قبول: أول عميل production في vertical واحد، evidence لوقت implementation وROI، وcompliance/security review.

## 15. المقاييس والبوابات

| البوابة | مقياس نجاح عملي |
|---|---|
| Demo | إكمال الرحلة end-to-end في أقل من 15 دقيقة؛ كل AI/KPI يملك sources؛ لا خطوات mock مخفية. |
| Product fit | زمن نمذجة object/workflow جديد، نسبة workflows التي تعمل بلا spreadsheets، approval cycle time. |
| Operational value | duplicate entry أقل، invoice processing time، overdue/exception resolution، budget-risk detection. |
| Trust | tenant/IDOR suite 100% للـ critical APIs؛ audit coverage للـ commands/tools؛ zero unapproved AI writes. |
| Reliability | outbox delivery success، DLQ age، workflow SLA، RPO/RTO وrestore drill. |
| Unit economics | AI cost per completed task، implementation days per tenant، gross margin لكل pack. |

## 16. ما لا نبنيه الآن

* لا نضيف CRM/HR/Inventory modules عشوائياً لملء قائمة features.
* لا نبني multi-agent workforce أو marketplace قبل tools/policy/events/observability.
* لا نحول Financial Core إلى metadata CRUD.
* لا نربط service modules مباشرة ببعضها أو نضيف integrations بلا outbox/retry/audit.
* لا نعد بGlobal expansion قبل country-pack contracts وcompliance owner.

## 17. القرار التنفيذي المطلوب

اعتماد **EOS Operating Platform V1** كبرنامج المنتج التالي، مع جعل `Construction + Financial` مرجعاً واحداً لإثبات المنصة. ترتيب الاستثمار:

```text
Shipped frontend unification
→ Demo operating loop
→ policy/event/workflow safety
→ Builder + analytics/document intake
→ AI governed actions
→ country/industry packs and ecosystem
```

بهذا يكون EOS “منصة تشغيل أعمال” قابلة للبناء والبيع والدفاع عنها، لا مجرد ERP أصغر أو مجموعة prototypes غير متكاملة.
