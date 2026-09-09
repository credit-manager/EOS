# طبقة الذكاء الاصطناعي - AI Layer Architecture

> **EOS Enterprise Operating System**
> **الإصدار:** 1.0 | **آخر تحديث:** 2026-08-18 | **الحالة:** Production-Ready Architecture

---

## جدول المحتويات

1. [نظرة عامة على طبقة الذكاء الاصطناعي](#1-نظرة-عامة-على-طبقة-الذكاء-الاصطناعي)
2. [معمارية الذكاء الاصطناعي](#2-معمارية-الذكاء-الاصطناعي)
3. [ميزات الذكاء الاصطناعي حسب الوحدة](#3-ميزات-الذكاء-الاصطناعي-حسب-الوحدة)
4. [نماذج الذكاء الاصطناعي المستخدمة](#4-نماذج-الذكاء-الاصطناعي-المستخدمة)
5. [متطلبات تقنية للـ AI Layer](#5-متطلبات-تقنية-للـ-ai-layer)
6. [تكلفة الذكاء الاصطناعي](#6-تكلفة-الذكاء-الاصطناعي)
7. [خطة تطوير AI](#7-خطة-تطوير-ai)
8. [الأمان والخصوصية في AI](#8-الأمان-والخصوصية-في-ai)

---

## 1. نظرة عامة على طبقة الذكاء الاصطناعي

### 1.1 AI كبنية تحتية وليس كميزة منفصلة

طبقة الذكاء الاصطناعي في EOS هي **طبقة أفقية** (Horizontal Layer) تخدم **جميع الوحدات** في النظام. ليست AI ميزة منفصلة، بل هي **بنية تحتية** (Infrastructure) مدمجة في كل وحدة.

```
+-------------------------------------------------------+
|              طبقة العرض (Presentation)                 |
|  +------+ +------+ +------+ +------+ +------+ +-----+ |
|  |محاسبة| |مخزون| |مبيعات| |موارد| |خدمة | | AI  | |
|  |      | |      | | CRM  | |بشرية| |عملاء| |Copil| |
|  +--+---+ +--+---+ +--+---+ +--+---+ +--+---+ +--+--+ |
+----+--------+--------+--------+--------+---------+------+
|     +--------+--------+--------+--------+---------+     |
|                    AI Layer (الطبقة الأفقية)            |
|  +----------+ +----------+ +----------+ +----------+  |
|  |  NLP     | |Predictive| | Document | | Anomaly  |  |
|  |  Engine  | |Analytics | |   AI     | |Detection |  |
|  +----------+ +----------+ +----------+ +----------+  |
+-------------------------------------------------------+
|                 Model Infrastructure                    |
|  MLflow | Airflow | Feature Store | pgvector          |
+-------------------------------------------------------+
```

**المبدأ الأساسي:** كل وحدة في EOS يمكنها الاستفادة من خدمات الذكاء الاصطناعي عبر API موحدة. لا يتطلب دمج AI أي تغيير في بنية الوحدة الأساسية.

### 1.2 المعمارية الأساسية: Python FastAPI Microservice

طبقة الذكاء الاصطناعي مبنية كـ **microservice** مستقلة باستخدام Python FastAPI. هذا يوفر:

- **عزل الاهتمامات:** خدمات AI منفصلة عن منطق الأعمال الأساسي
- **قابلية التوسع:** يمكن توسيع خدمات AI بشكل مستقل عن باقي النظام
- ** Bugs Isolation:** أي مشكلة في AI لا تؤثر على باقي الخدمات
- **Deployment مستقل:** نشر تحديثات AI بدون إعادة نشر باقي النظام
- **Team specialization:** فريق AI متخصص يعمل بشكل مستقل

```
eos-ai-service/
+-- app/
|   +-- main.py                    # FastAPI application entry
|   +-- config.py                  # Configuration management
|   +-- dependencies.py            # Dependency injection
|   |
|   +-- api/                       # API Layer
|   |   +-- v1/
|   |   |   +-- copilot.py         # AI Copilot endpoints
|   |   |   +-- classification.py  # Text classification
|   |   |   +-- prediction.py      # Predictive analytics
|   |   |   +-- anomaly.py         # Anomaly detection
|   |   |   +-- ocr.py             # Document processing
|   |   |   +-- sentiment.py       # Sentiment analysis
|   |   |   +-- recommend.py       # Recommendation engine
|   |   |   +-- forecast.py        # Time series forecasting
|   |   |   +-- summarize.py       # Text summarization
|   |   |   +-- segment.py         # Customer segmentation
|   |   +-- deps.py                # Shared API dependencies
|   |
|   +-- core/                      # Core Business Logic
|   |   +-- copilot/
|   |   |   +-- engine.py          # Copilot conversation engine
|   |   |   +-- context.py         # Context management
|   |   |   +-- tools.py           # Function calling tools
|   |   |   +-- prompts.py         # Prompt templates
|   |   +-- nlp/
|   |   |   +-- classifier.py      # Text classifier
|   |   |   +-- extractor.py       # Entity extraction
|   |   |   +-- similarity.py      # Semantic similarity
|   |   +-- predictive/
|   |   |   +-- demand.py          # Demand forecasting
|   |   |   +-- cashflow.py        # Cash flow prediction
|   |   |   +-- churn.py           # Employee/customer churn
|   |   |   +-- sales.py           # Sales forecasting
|   |   +-- anomaly/
|   |   |   +-- detector.py        # Anomaly detection engine
|   |   |   +-- rules.py           # Rule-based detection
|   |   |   +-- patterns.py        # Pattern recognition
|   |   +-- document/
|   |   |   +-- ocr.py             # OCR processing
|   |   |   +-- parser.py          # Document parsing
|   |   |   +-- extractor.py       # Data extraction
|   |   +-- recommend/
|   |   |   +-- engine.py          # Recommendation engine
|   |   |   +-- collaborative.py   # Collaborative filtering
|   |   |   +-- content.py         # Content-based filtering
|   |   +-- sentiment/
|   |       +-- analyzer.py        # Sentiment analysis
|   |       +-- aspects.py         # Aspect-based sentiment
|   |
|   +-- models/                    # Data Models (Pydantic)
|   |   +-- requests.py            # API request models
|   |   +-- responses.py           # API response models
|   |   +-- internal.py            # Internal data models
|   |   +-- database.py            # SQLAlchemy models
|   |
|   +-- infrastructure/            # Infrastructure Layer
|   |   +-- mlflow_client.py       # MLflow integration
|   |   +-- vector_store.py        # pgvector integration
|   |   +-- feature_store.py       # Feature store client
|   |   +-- cache.py               # Redis caching
|   |   +-- queue.py               # Message queue (RabbitMQ)
|   |   +-- storage.py             # Object storage (S3/MinIO)
|   |
|   +-- tenants/                   # Multi-tenant Support
|   |   +-- isolation.py           # Data isolation
|   |   +-- context.py             # Tenant context
|   |   +-- usage.py               # Usage tracking
|   |
|   +-- utils/                     # Utilities
|       +-- text.py                # Text processing
|       +-- metrics.py             # Metrics collection
|       +-- logging.py             # Structured logging
|       +-- security.py            # Security utilities
|
+-- training/                      # Model Training
|   +-- pipelines/
|   |   +-- classify.py            # Classification training
|   |   +-- forecast.py            # Forecasting training
|   |   +-- anomaly.py             # Anomaly detection training
|   |   +-- sentiment.py           # Sentiment training
|   +-- data/
|   |   +-- prep.py                # Data preparation
|   |   +-- augment.py             # Data augmentation
|   +-- evaluation/
|       +-- metrics.py             # Evaluation metrics
|       +-- report.py              # Training reports
|
+-- tests/
|   +-- unit/
|   +-- integration/
|   +-- performance/
|
+-- docker/
|   +-- Dockerfile
|   +-- Dockerfile.training
|   +-- docker-compose.yml
|
+-- alembic/versions/              # Database Migrations
+-- requirements.txt
+-- pyproject.toml
+-- alembic.ini
+-- .env.example
```

### 1.3 إدارة النماذج وإصداراتها - Model Management and Versioning

نستخدم **MLflow** لإدارة دورة حياة النماذج. كل نموذج له:

- **Version tracking:** تتبع جميع الإصدارات مع المقاييس
- **Stage management:** Development > Staging > Production > Archived
- **Artifact storage:** حفظ النموذج والـ tokenizer والـ config
- **A/B testing:** اختبار أداء الإصدارات المختلفة
- **Rollback capability:** التراجع لإصدار سابق عند المشاكل

**Model Registry Structure in MLflow:**

```python
model_registry = {
    "expense_classifier": {
        "versions": {
            "1": {"stage": "Production", "accuracy": 0.94, "date": "2026-03-01"},
            "2": {"stage": "Staging", "accuracy": 0.96, "date": "2026-06-15"},
            "3": {"stage": "Development", "accuracy": 0.97, "date": "2026-08-01"},
        },
        "tags": {"domain": "accounting", "type": "classification"},
        "artifacts": ["model.pkl", "tokenizer", "config.json"],
    },
    "demand_forecaster": {
        "versions": {
            "1": {"stage": "Production", "mape": 12.3, "date": "2026-04-01"},
            "2": {"stage": "Staging", "mape": 9.8, "date": "2026-07-20"},
        },
        "tags": {"domain": "inventory", "type": "time_series"},
        "artifacts": ["model.pkl", "scaler", "features.json"],
    },
}
```

**دورة حياة النموذج:**

```
Development --> Staging --> Production --> Archived
      ^            |           |
      +------------+-----------+
         (Retrain on new data)
```

### 1.4 AI متعدد المستأجرين - Multi-Tenant AI

**عزل البيانات** هو المبدأ الأساسي: بيانات كل tenant تُستخدم **فقط** لتدريب نماذج هذا الـ tenant.

```
+-------------------------------------------------+
|         Tenant Isolation Architecture           |
+-------------------------------------------------+
|                                                   |
|  Tenant A          Tenant B          Tenant C    |
|  +---------+      +---------+      +---------+  |
|  | Data A  |      | Data B  |      | Data C  |  |
|  +----+----+      +----+----+      +----+----+  |
|       |                |                |        |
|       v                v                v        |
|  +---------+      +---------+      +---------+  |
|  | Model A |      | Model B |      | Model C |  |
|  |(Custom) |      |(Custom) |      |(Custom) |  |
|  +----+----+      +----+----+      +----+----+  |
|       |                |                |        |
|       v                v                v        |
|  +--------------------------------------------+ |
|  |     Shared Base Models (Optional)           | |
|  |  - General NLP (no tenant data)             | |
|  |  - Pre-trained foundation models            | |
|  |  - Common embeddings                        | |
|  +--------------------------------------------+ |
|                                                   |
+-------------------------------------------------+
```

**أنواع النماذج حسب العزل:**

| النوع | الوصف | العزل |
|-------|-------|-------|
| **Shared Model** | نموذج عام يخدم جميع المستأجرين | لا يوجد عزل - نفس النموذج للجميع |
| **Tenant-Specific** | نموذج مخصص لكل tenant | عزل كامل - كل tenant له نموذج خاص |
| **Hybrid** | نموذج عام + fine-tuning لكل tenant | عزل جزئي - قاعدة مشتركة + تخصيص |

**隔离 المعايير:**
- كل طلب AI يحتوي على `tenant_id` إجباري
- جميع الاستعلامات تمر بفلتر `WHERE tenant_id = X`
- التخزين المؤقت (Cache) مفصول لكل tenant
- السجلات (Logs) لا تحتوي على بيانات مستأجرين آخرين
- مسارات تخزين النماذج منفصلة لكل tenant


---

## 2. معمارية الذكاء الاصطناعي - Detailed Architecture

### 2.1 المعمارية الكاملة

```
+-----------------------------------------------------------------------+
|                      AI Layer Architecture                              |
+-----------------------------------------------------------------------+
|                                                                         |
|  +---------------------------------------------------------------+    |
|  |                  AI Gateway (API Gateway)                      |    |
|  |                                                                 |    |
|  |  +--------------+ +--------------+ +--------------+            |    |
|  |  | Rate Limiting | |   Routing    | |   Caching    |            |    |
|  |  | (per tenant)  | | (per model)  | |  (Redis)     |            |    |
|  |  +--------------+ +--------------+ +--------------+            |    |
|  |  +--------------+ +--------------+ +--------------+            |    |
|  |  | Cost Tracking | |Auth/Throttle | |Load Balancer |            |    |
|  |  | (per tenant)  | | (per plan)   | | (round-robin)|            |    |
|  |  +--------------+ +--------------+ +--------------+            |    |
|  +----------------------------+------------------------------------+    |
|                               |                                         |
|  +----------------------------+------------------------------------+    |
|  |                  AI Service Engine                               |    |
|  |                                                                 |    |
|  |  +--------------+  +--------------+  +--------------+          |    |
|  |  |  NLP Engine   |  |  Predictive  |  |   Document   |          |    |
|  |  |               |  |  Analytics   |  |   AI         |          |    |
|  |  | - Text Classif|  | - Demand     |  | - OCR        |          |    |
|  |  | - Entity Ext  |  | - Cash Flow  |  | - Parsing    |          |    |
|  |  | - Similarity  |  | - Churn      |  | - Extraction |          |    |
|  |  | - Keywords    |  | - Sales      |  | - Validation |          |    |
|  |  +--------------+  +--------------+  +--------------+          |    |
|  |                                                                 |    |
|  |  +--------------+  +--------------+  +--------------+          |    |
|  |  |   Anomaly    |  |  Recommend   |  |    Smart     |          |    |
|  |  |  Detection   |  |   Engine     |  |  Automation  |          |    |
|  |  |              |  |              |  |              |          |    |
|  |  | - Statistical|  | - Collab.    |  | - Workflow   |          |    |
|  |  | - ML-based   |  | - Content    |  | - Triggers   |          |    |
|  |  | - Rule-based |  | - Hybrid     |  | - Scheduling |          |    |
|  |  +--------------+  +--------------+  +--------------+          |    |
|  |                                                                 |    |
|  |  +--------------+  +--------------+  +--------------+          |    |
|  |  |  Sentiment   |  |    AI        |  |   Forecast   |          |    |
|  |  |  Analysis    |  |  Copilot     |  |   Engine     |          |    |
|  |  |              |  |              |  |              |          |    |
|  |  | - Text Sent. |  | - Chat       |  | - Time Series|          |    |
|  |  | - Aspect     |  | - Context    |  | - Regression |          |    |
|  |  | - Trend      |  | - Tools      |  | - Ensemble   |          |    |
|  |  +--------------+  +--------------+  +--------------+          |    |
|  +-----------------------------------------------------------------+    |
|                               |                                         |
|  +----------------------------+------------------------------------+    |
|  |              Model Infrastructure                                |    |
|  |                                                                 |    |
|  |  +--------------+  +--------------+  +--------------+          |    |
|  |  |    MLflow     |  |   Airflow    |  |    Feature   |          |    |
|  |  | Model Registry|  |  Training    |  |    Store     |          |    |
|  |  |              |  |  Pipelines   |  |              |          |    |
|  |  | - Versioning |  | - Scheduled  |  | - Feature    |          |    |
|  |  | - Staging    |  | - Triggered  |  |   Computation|          |    |
|  |  | - A/B Testing|  | - Monitoring |  | - Feature    |          |    |
|  |  +--------------+  +--------------+  |   Serving    |          |    |
|  |                                       +--------------+          |    |
|  |  +--------------+  +--------------+  +--------------+          |    |
|  |  |  pgvector    |  |    Redis     |  |  MinIO / S3  |          |    |
|  |  | Vector Store |  |    Cache     |  |  Artifact    |          |    |
|  |  |              |  |              |  |  Storage     |          |    |
|  |  | - Embeddings |  | - Predictions|  |              |          |    |
|  |  | - Similarity |  | - Embeddings |  | - Models     |          |    |
|  |  | - Search     |  | - Sessions   |  | - Datasets   |          |    |
|  |  +--------------+  +--------------+  +--------------+          |    |
|  +-----------------------------------------------------------------+    |
|                                                                         |
+-----------------------------------------------------------------------+
```

### 2.2 AI Gateway - بوابة الذكاء الاصطناعي

الـ Gateway هو نقطة الدخول الوحيدة لجميع خدمات AI. يوفر:

1. **Rate Limiting per tenant:** تحديد عدد الطلبات لكل مستأجر حسب الخطة
2. **Model Selection Routing:** توجيه الطلب للنموذج المناسب
3. **Response Caching:** تخزين الاستجابات المتكررة لتقليل التكلفة
4. **Cost Tracking per tenant:** تتبع التكلفة لكل مستأجر للفوترة
5. **Authentication & Authorization:** التحقق من هوية المستأجر وصلاحياته
6. **Load Balancing:** توزيع الحمل بين نسخ الخادم المتعددة

```python
class AIGateway:
    """
    بوابة الذكاء الاصطناعي - نقطة الدخول الوحيدة لجميع خدمات AI
    """

    def __init__(self):
        self.rate_limiter = TenantRateLimiter()
        self.model_router = ModelSelectionRouter()
        self.cache = ResponseCache()
        self.cost_tracker = CostTracker()
        self.auth = AIAuthMiddleware()

    async def process_request(self, request: AIRequest) -> AIResponse:
        # 1. التحقق من الصلاحيات
        await self.auth.verify(request.tenant_id, request.service)

        # 2. فحص Rate Limiting
        await self.rate_limiter.check(request.tenant_id, request.service)

        # 3. فحص الكاش
        cached = await self.cache.get(request)
        if cached:
            return cached

        # 4. اختيار النموذج المناسب
        model = self.model_router.select(
            service=request.service,
            tenant_plan=request.tenant_plan,
            cost_budget=request.cost_budget,
        )

        # 5. تنفيذ الطلب
        response = await model.predict(request)

        # 6. حفظ في الكاش
        await self.cache.set(request, response)

        # 7. تتبع التكلفة
        await self.cost_tracker.track(
            tenant_id=request.tenant_id,
            service=request.service,
            tokens=response.tokens_used,
            cost=response.estimated_cost,
        )

        return response
```

### 2.3 Rate Limiting حسب المستأجر والخطة

```python
RATE_LIMITS = {
    "starter": {
        "copilot": {"rpm": 10, "tpm": 10000},
        "predictions": {"rpm": 5, "tpm": 5000},
        "ocr": {"rpm": 3, "documents_per_day": 50},
    },
    "professional": {
        "copilot": {"rpm": 50, "tpm": 100000},
        "predictions": {"rpm": 30, "tpm": 50000},
        "ocr": {"rpm": 20, "documents_per_day": 500},
    },
    "enterprise": {
        "copilot": {"rpm": 200, "tpm": 500000},
        "predictions": {"rpm": 100, "tpm": 200000},
        "ocr": {"rpm": 100, "documents_per_day": 5000},
    },
}
```

**المصطلحات:**
- **RPM:** Requests Per Minute (طلبات في الدقيقة)
- **TPM:** Tokens Per Minute (توكن في الدقيقة)

### 2.4 Response Caching Strategy

```python
CACHE_STRATEGIES = {
    "copilot_chat": {
        "ttl": 0,  # لا يوجد caching للمحادثات (وقت حقيقي)
        "key": "tenant:{tenant_id}:copilot:{session_id}",
    },
    "expense_classification": {
        "ttl": 86400,  # 24 ساعة
        "key": "tenant:{tenant_id}:classify:{text_hash}",
    },
    "demand_forecast": {
        "ttl": 3600,  # ساعة واحدة
        "key": "tenant:{tenant_id}:forecast:{product_id}:{horizon}",
    },
    "anomaly_detection": {
        "ttl": 300,  # 5 دقائق
        "key": "tenant:{tenant_id}:anomaly:{dataset_hash}",
    },
    "sentiment_analysis": {
        "ttl": 604800,  # 7 أيام (المشاعر لا تتغير بسرعة)
        "key": "tenant:{tenant_id}:sentiment:{text_hash}",
    },
}
```

### 2.5 Model Selection Router

```python
class ModelSelectionRouter:
    """
    اختيار النموذج المناسب بناءً على الخدمة وخطة المستأجر وميزانية التكلفة.
    """

    MODEL_TIERS = {
        "copilot": {
            "starter": "gpt-4o-mini",       # أرخص وسريع
            "professional": "gpt-4o",        # متوازن
            "enterprise": "gpt-4o + claude", # أعلى جودة
        },
        "classification": {
            "starter": "shared-bert",        # نموذج مشترك
            "professional": "tenant-bert",   # نموذج خاص
            "enterprise": "fine-tuned-llm", # LLM مخصص
        },
        "forecasting": {
            "starter": "prophet-lite",       # خفيف
            "professional": "prophet-full",  # كامل
            "enterprise": "ensemble",        # مجموعة نماذج
        },
    }

    def select(
        self,
        service: str,
        tenant_plan: str,
        cost_budget: float | None = None,
    ) -> AIModel:
        model_name = self.MODEL_TIERS[service][tenant_plan]

        if cost_budget:
            # إذا كانت الميزانية محدودة، اختر نموذج أرخص
            model_name = self.optimize_for_cost(model_name, cost_budget)

        return self.load_model(model_name)
```



---

## 3. ميزات الذكاء الاصطناعي حسب الوحدة

### 3.1 AI في المحاسبة - Accounting AI

#### 3.1.1 تصنيف المصروفات الآلي - Auto Expense Categorization

تعلم من القيود السابقة وصنف المصروفات تلقائياً. عند إدخال مصروف جديد، يحلل النظام الوصف والمبلغ اسم المورد ويقترح التصنيف المناسب.

```python
class ExpenseClassifier:
    """
    تصنيف المصروفات تلقائياً بناءً على وصف المعاملة.
    يتعلم من القيود السابقة ويصنف مصروفات جديدة.
    """

    CATEGORIES = [
        "رواتب وأجور",
        "إيجار",
        "مرافق (كهرباء، ماء، غاز)",
        "مواد تموينية",
        "معدات وأجهزة",
        "صيانة وإصلاح",
        "سفن ونقل",
        "اتصالات وإنترنت",
        "تأمين",
        "ضرائب ورسوم",
        "تسويق وإعلان",
        "تدريب وتطوير",
        "استشارات وخدمات مهنية",
        "قرض وفوائد",
        "أخرى",
    ]

    async def classify(
        self,
        description: str,
        amount: float,
        vendor: str | None = None,
        tenant_id: str = None,
    ) -> ClassificationResult:
        """
        تصنيف مصروف بناءً على الوصف والمبلغ واسم المورد.

        Returns:
            ClassificationResult:
                - category: التصنيف المقترح
                - confidence: مستوى الثقة (0-1)
                - alternatives: تصنيفات بديلة مرتبة
                - reasoning: سبب التصنيف
                - requires_review: هل يحتاج مراجعة يدوية
        """
        historical_entries = await self.get_tenant_history(tenant_id)
        embedding = await self.embed(description)

        similar_entries = await self.vector_store.search(
            embedding,
            tenant_id=tenant_id,
            top_k=10,
        )

        prediction = await self.model.predict(
            text=description,
            amount=amount,
            vendor=vendor,
            similar_entries=similar_entries,
        )

        if prediction.confidence < 0.7:
            return ClassificationResult(
                category=prediction.category,
                confidence=prediction.confidence,
                alternatives=prediction.alternatives,
                reasoning=prediction.explanation,
                requires_review=True,
            )

        return ClassificationResult(
            category=prediction.category,
            confidence=prediction.confidence,
            alternatives=prediction.alternatives,
            reasoning=prediction.explanation,
            requires_review=False,
        )
```

**مثال على الاستخدام:**
```
Input: "فاتورة كهرباء شركة sprawt - 2,450 ريال"
Output:
  category: "مرافق (كهرباء، ماء، غاز)"
  confidence: 0.96
  alternatives: ["إيجار", "صيانة وإصلاح"]
  requires_review: false
```

#### 3.1.2 كشف الأخطاء المحاسبية - Accounting Error Detection

```python
class AccountingErrorDetector:
    """
    اكتشاف أخطاء محاسبية وقيود غير متوازنة أو مشبوهة.
    """

    async def detect_errors(
        self,
        journal_entries: list[JournalEntry],
        tenant_id: str,
    ) -> list[AccountingError]:
        errors = []

        for entry in journal_entries:
            # 1. فحص التوازن (Debit = Credit)
            if abs(entry.total_debit - entry.total_credit) > 0.01:
                errors.append(AccountingError(
                    type="UNBALANCED_ENTRY",
                    severity="HIGH",
                    entry_id=entry.id,
                    description=f"قيود غير متوازنة: مدين {entry.total_debit} / دائن {entry.total_credit}",
                ))

            # 2. فحص المبالغ المشبوهة (statistical outlier)
            if await self.is_amount_anomaly(entry, tenant_id):
                errors.append(AccountingError(
                    type="SUSPICIOUS_AMOUNT",
                    severity="MEDIUM",
                    entry_id=entry.id,
                    description=f"المبلغ {entry.amount} غير مألوف لهذا类型 من الحسابات",
                ))

            # 3. فحص التكرار (duplicate entries)
            if await self.is_duplicate(entry, tenant_id):
                errors.append(AccountingError(
                    type="DUPLICATE_ENTRY",
                    severity="HIGH",
                    entry_id=entry.id,
                    description="يوجد قيد مماثل تم إدخاله مسبقاً",
                ))

            # 4. فحص التصنيف الخاطئ
            category_check = await self.check_classification(entry, tenant_id)
            if not category_check.valid:
                errors.append(AccountingError(
                    type="MISCLASSIFIED",
                    severity="LOW",
                    entry_id=entry.id,
                    description=f"الحساب '{entry.account}' قد لا يكون مناسباً لهذا النوع من المعاملات",
                ))

            # 5. فحص القيود خارج الفترة الزمنية
            if entry.date not in self.current_period(tenant_id):
                errors.append(AccountingError(
                    type="WRONG_PERIOD",
                    severity="MEDIUM",
                    entry_id=entry.id,
                    description=f"التاريخ {entry.date} خارج الفترة المحاسبية الحالية",
                ))

        return errors
```

**أنواع الأخطاء المكتشفة:**

| النوع | الخطورة | الوصف |
|-------|---------|-------|
| `UNBALANCED_ENTRY` | HIGH | قيود مدين لا تساوي دائن |
| `SUSPICIOUS_AMOUNT` | MEDIUM | مبلغ غير مألوف إحصائياً |
| `DUPLICATE_ENTRY` | HIGH | قيد مكرر |
| `MISCLASSIFIED` | LOW | تصنيف خاطئ للحساب |
| `WRONG_PERIOD` | MEDIUM | قيد في فترة زمنية خاطئة |

#### 3.1.3 تنبؤ التدفقات النقدية - Cash Flow Prediction

```python
class CashFlowPredictor:
    """
    توقع الإيرادات والمصروفات对未来 30/60/90 يوم.
    """

    async def predict(
        self,
        tenant_id: str,
        horizon_days: list[int] = [30, 60, 90],
    ) -> CashFlowPrediction:
        """
        التنبؤ بالتدفقات النقدية未来.

        يعتمد على:
        - تاريخ التدفقات النقدية السابقة
        - الفواتير المستحقة (Accounts Receivable)
        - الالتزامات المستحقة (Accounts Payable)
        - أنماط الموسمية
        - اتفاقيات الدفع مع العملاء والموردين
        """

        # جمع البيانات التاريخية
        historical = await self.get_historical_cashflow(tenant_id, months=24)

        # جمع الفواتير المستحقة
        receivables = await self.get_receivables(tenant_id)
        payables = await self.get_payables(tenant_id)

        # حساب الميزات
        features = self.extract_features(
            historical=historical,
            receivables=receivables,
            payables=payables,
        )

        # التنبؤ لكل أفق زمني
        predictions = {}
        for horizon in horizon_days:
            pred = await self.model.predict(
                features=features,
                horizon=horizon,
            )
            predictions[horizon] = {
                "inflow": pred.inflow,
                "outflow": pred.outflow,
                "net": pred.net,
                "confidence_interval": pred.ci,
                "risk_level": pred.risk,  # LOW, MEDIUM, HIGH
            }

        return CashFlowPrediction(
            predictions=predictions,
            recommendations=self.generate_recommendations(predictions),
            alerts=self.check_alerts(predictions),
        )
```

#### 3.1.4 توحيد الموردين - Vendor Deduplication

```python
class VendorDeduplicator:
    """
    اكتشاف الموردين المكررين عبر تحليل:
    - الاسم وال地址 (mediocre similarity)
    - رقم الهاتف والبريد الإلكتروني
    - رقم السجل التجاري
    - أنماط الفوترة
    """

    async def find_duplicates(
        self,
        tenant_id: str,
        threshold: float = 0.85,
    ) -> list[VendorDuplicateGroup]:
        vendors = await self.get_all_vendors(tenant_id)
        groups = []

        for vendor in vendors:
            embedding = await self.embed_vendor(vendor)
            similar = await self.vector_store.search(
                embedding,
                tenant_id=tenant_id,
                threshold=threshold,
                exclude_ids=[vendor.id],
            )
            if similar:
                groups.append(VendorDuplicateGroup(
                    primary=vendor,
                    duplicates=similar,
                    confidence=max(s.confidence for s in similar),
                ))

        return groups
```

#### 3.1.5 تحليل الربحية - Profitability Analysis

```python
class ProfitabilityAnalyzer:
    """
    تحليل هامش الربح لكل منتج/خدمة/عميل.
    """

    async def analyze(
        self,
        tenant_id: str,
        dimension: str,  # "product", "service", "customer", "department"
    ) -> ProfitabilityReport:
        data = await self.get_revenue_and_costs(tenant_id, dimension)

        analysis = {
            "dimension_items": [],
            "overall_margin": 0,
            "trend": "",  # "improving", "declining", "stable"
            "insights": [],
            "recommendations": [],
        }

        for item in data.items:
            margin = (item.revenue - item.cost) / item.revenue if item.revenue else 0
            trend = await self.calculate_trend(item.id, months=12)

            analysis["dimension_items"].append({
                "name": item.name,
                "revenue": item.revenue,
                "cost": item.cost,
                "margin": margin,
                "trend": trend,
                "percentile": self.calculate_percentile(margin, data.all_margins),
            })

            # AI insights
            if margin < data.industry_benchmark:
                analysis["insights"].append(
                    f"هامش ربح '{item.name}' ({margin:.1%}) أقل من متوسط الصناعة"
                )

        analysis["recommendations"] = await self.generate_recommendations(analysis)
        return ProfitabilityReport(**analysis)
```

#### 3.1.6 اقتراح القيود الدفترية - Journal Entry Suggestions

```python
class JournalEntrySuggester:
    """
    اقتراح حسابات دفترية بناءً على وصف المعاملة.
    """

    async def suggest(
        self,
        description: str,
        amount: float,
        tenant_id: str,
    ) -> list[JournalEntrySuggestion]:
        """
       مثال:
        Input: "دفعة إيجار شهري 5000 ريال"
        Output: [
            {debit: "مصاريف إيجار", credit: "بنك", amount: 5000},
        ]

        Input: "بيع منتج X للعميل Y - 10000 ريال"
        Output: [
            {debit: "حساب العميل Y", credit: "إيرادات المبيعات", amount: 8928.57},
            {debit: "ضريبة القيمة المضافة", credit: "ض.م.م. خصم", amount: 1071.43},
        ]
        """
        similar_entries = await self.find_similar_descriptions(description, tenant_id)
        suggestions = await self.model.generate_suggestions(
            description=description,
            amount=amount,
            similar_entries=similar_entries,
            chart_of_accounts=await self.get_chart_of_accounts(tenant_id),
        )
        return suggestions
```



### 3.2 AI في المخزون - Inventory AI

#### 3.2.1 توقع الطلب - Demand Forecasting

```python
class DemandForecaster:
    """
    تحليل تاريخ المبيعات للتنبؤ بالطلب未来.
    يعتمد على Prophet + Ensemble مع مراعاة العوامل الموسمية.
    """

    async def forecast(
        self,
        tenant_id: str,
        product_id: str | None = None,
        category: str | None = None,
        horizon_days: int = 90,
    ) -> DemandForecast:
        """
        التنبؤ بالطلب未来.

        العوامل المدروسة:
        - تاريخ المبيعات (Sales history)
        - العطل والأعياد (Holidays)
        - العروض الترويجية (Promotions)
        - الاتجاه العام (Trend)
        - الموسمية (Seasonality)
        - الأحداث الخاصة (Special events)
        """

        # جمع بيانات المبيعات التاريخية
        sales_data = await self.get_sales_history(
            tenant_id, product_id, category, months=24
        )

        # جمع بيانات العروض والأعياد
        promotions = await self.get_promotions(tenant_id)
        holidays = await self.get_holidays(tenant_id)

        # التنبؤ
        forecast = await self.model.forecast(
            data=sales_data,
            promotions=promotions,
            holidays=holidays,
            horizon=horizon_days,
        )

        return DemandForecast(
            product_id=product_id,
            forecasts=[
                ForecastPoint(
                    date=f.date,
                    predicted_demand=f.demand,
                    lower_bound=f.ci_lower,
                    upper_bound=f.ci_upper,
                    confidence=f.confidence,
                )
                for f in forecast.points
            ],
            trend=forecast.trend,
            seasonality_pattern=forecast.seasonality,
            accuracy_score=forecast.mape,
        )
```

#### 3.2.2 تنبيهات إعادة الطلب الذكية - Smart Reorder Alerts

```python
class SmartReorderAlertSystem:
    """
    بدل الحد الثابت (Fixed Reorder Point)، يتعلم من أنماط الاستهلاك الفعلية.
    """

    async def check_reorder(
        self,
        tenant_id: str,
        product_id: str,
    ) -> ReorderSuggestion | None:

        # جمع بيانات الاستهلاك
        consumption = await self.get_consumption_pattern(tenant_id, product_id)

        # حساب متوسط الاستهلاك اليومي مع الاتجاه
        daily_avg = consumption.mean_daily
        trend = consumption.trend  # "increasing", "decreasing", "stable"
        variability = consumption.std_dev

        # حساب نقطة إعادة الطلب الديناميكية
        lead_time = await self.get_supplier_lead_time(tenant_id, product_id)
        safety_stock = self.calculate_safety_stock(
            daily_avg=daily_avg,
            lead_time=lead_time,
            variability=variability,
            service_level=0.95,  # 95% service level
        )

        reorder_point = (daily_avg * lead_time) + safety_stock

        current_stock = await self.get_current_stock(tenant_id, product_id)

        if current_stock <= reorder_point:
            # حساب الكمية المثلى للطلب (EOQ)
            optimal_qty = self.calculate_eoq(
                annual_demand=daily_avg * 365,
                ordering_cost=await self.get_ordering_cost(tenant_id, product_id),
                holding_cost=await self.get_holding_cost(tenant_id, product_id),
            )

            return ReorderSuggestion(
                product_id=product_id,
                current_stock=current_stock,
                reorder_point=reorder_point,
                suggested_quantity=optimal_qty,
                urgency=self.calculate_urgency(current_stock, daily_avg, lead_time),
                expected_stockout_date=self.estimate_stockout(
                    current_stock, daily_avg
                ),
                reasoning=f"المخزون الحالي ({current_stock}) أقل من نقطة إعادة الطلب ({reorder_point:.0f})",
            )

        return None
```

#### 3.2.3 تحسين مستويات المخزون - Inventory Optimization

```python
class InventoryOptimizer:
    """
    اقتراح الكمية المثلى للطلب لكل منتج لتجنب نقص المخزون والمخزون الزائد.
    """

    async def optimize(
        self,
        tenant_id: str,
    ) -> InventoryOptimizationReport:
        products = await self.get_all_products(tenant_id)
        recommendations = []

        for product in products:
            forecast = await self.forecaster.forecast(
                tenant_id, product.id, horizon_days=90
            )

            current = await self.get_current_stock(tenant_id, product.id)

            # حساب المخزون الزائد المحتمل
            excess = self.detect_excess_stock(
                current_stock=current.quantity,
                forecasted_demand=forecast.total_predicted,
                holding_cost=product.holding_cost_per_unit,
            )

            # حساب النقص المحتمل
            shortage_risk = self.calculate_shortage_risk(
                current_stock=current.quantity,
                forecasted_demand=forecast,
                lead_time=product.lead_time,
            )

            recommendations.append(ProductRecommendation(
                product_id=product.id,
                current_stock=current.quantity,
                recommended_stock=forecast.total_predicted * 1.2,  # 20% buffer
                excess_quantity=excess.quantity if excess else 0,
                shortage_risk=shortage_risk,
                action=self.determine_action(current.quantity, forecast, excess, shortage_risk),
            ))

        return InventoryOptimizationReport(
            total_products=len(products),
            products_with_excess=sum(1 for r in recommendations if r.excess_quantity > 0),
            products_with_shortage_risk=sum(1 for r in recommendations if r.shortage_risk > "LOW"),
            recommendations=recommendations,
        )
```

#### 3.2.4 اكتشاف التسرب - Shrinkage Detection

```python
class ShrinkageDetector:
    """
    اكتشاف فروقات غير طبيعية في المخزون (تسرب، سرقة، أخطاء جرد).
    """

    async def detect(
        self,
        tenant_id: str,
        threshold_sigma: float = 3.0,
    ) -> list[ShrinkageAlert]:
        alerts = []

        # جمع نتائج الجرد الأخيرة
        inventory_movements = await self.get_movements(tenant_id, days=90)

        for product in await self.get_all_products(tenant_id):
            movements = inventory_movements.filter(product_id=product.id)

            # حساب التوقع vs الفعلي
            expected = self.calculate_expected_stock(movements)
            actual = await self.get_physical_count(tenant_id, product.id)

            if actual is None:
                continue

            variance = actual - expected
            variance_pct = variance / expected if expected else 0

            # فحص إذا كان الفرق إحصائياً كبيراً
            historical_variance = self.get_historical_variance(
                movements, window=30
            )

            if abs(variance) > threshold_sigma * historical_variance.std:
                alerts.append(ShrinkageAlert(
                    product_id=product.id,
                    expected=expected,
                    actual=actual,
                    variance=variance,
                    variance_percentage=variance_pct,
                    severity=self.classify_severity(variance_pct),
                    possible_causes=self.suggest_causes(variance, movements),
                ))

        return alerts
```

#### 3.2.5 تصنيف ABC الذكي - Smart ABC Classification

```python
class SmartABCClassifier:
    """
    تصنيف المنتجات حسب الأهمية ديناميكياً.
    بدل Classification الثابت، يتحدث تلقائياً مع تغير أنماط المبيعات.
    """

    async def classify(
        self,
        tenant_id: str,
    ) -> ABCClassificationReport:
        products = await self.get_products_with_sales(tenant_id, months=12)

        # حساب revenue contribution لكل منتج
        scored = []
        for product in products:
            revenue = await self.get_annual_revenue(tenant_id, product.id)
            profit_margin = await self.get_profit_margin(tenant_id, product.id)
            demand_variability = await self.get_demand_variability(tenant_id, product.id)

            # Composite score with weighted factors
            score = (
                0.6 * revenue +
                0.25 * profit_margin +
                0.15 * (1 - demand_variability)  # less variable = more important
            )
            scored.append((product, score))

        # ترتيب وتصنيف
        scored.sort(key=lambda x: x[1], reverse=True)
        cumulative = 0
        total = sum(s for _, s in scored)

        classifications = []
        for product, score in scored:
            cumulative += score / total

            if cumulative <= 0.70:
                cls = "A"  # High value - top 70%
            elif cumulative <= 0.90:
                cls = "B"  # Medium value - next 20%
            else:
                cls = "C"  # Low value - last 10%

            classifications.append(ProductClassification(
                product_id=product.id,
                classification=cls,
                score=score,
                revenue_contribution=score / total,
                recommendation=self.get_recommendation(cls, product),
            ))

        return ABCClassificationReport(classifications=classifications)
```

#### 3.2.6 تنبيهات انتهاء الصلاحية - Expiry Alerts

```python
class ExpiryAlertSystem:
    """
    توقع المنتجات ستنتهي صلاحيتها واقتراح إجراءات.
    """

    async def check(
        self,
        tenant_id: str,
    ) -> list[ExpiryAlert]:
        alerts = []

        expiring = await self.get_expiring_products(tenant_id, days=180)

        for product in expiring:
            days_until = (product.expiry_date - date.today()).days

            # حساب نسبة المخزون المتبقي
            stock = await self.get_stock(tenant_id, product.id)
            consumption_rate = await self.get_consumption_rate(tenant_id, product.id)

            # هل يمكن بيع المخزون قبل انتهاء الصلاحية?
            can_sell = stock.quantity / consumption_rate.daily if consumption_rate.daily > 0 else 0

            if can_sell > days_until:
                # لا يمكن بيع كل المخزون قبل الانتهاء
                alerts.append(ExpiryAlert(
                    product_id=product.id,
                    expiry_date=product.expiry_date,
                    days_remaining=days_until,
                    current_stock=stock.quantity,
                    consumption_rate=consumption_rate.daily,
                    shortage=stock.quantity - (consumption_rate.daily * days_until),
                    urgency="HIGH" if days_until < 30 else "MEDIUM",
                    suggestions=[
                        "تخفيض السعر للترويج (Flash Sale)",
                        "تحويل إلى فرع آخر مع طلب أعلى",
                        "التبرع بالمخزون المتبقٍ",
                        "إعادة التفاوض مع المورد للاستبدال",
                    ],
                ))

        return alerts
```



### 3.3 AI في المبيعات والـ CRM - Sales & CRM AI

#### 3.3.1 تقييم Leads الذكي - Smart Lead Scoring

```python
class LeadScorer:
    """
    تقييم احتمال تحويل كل lead بناءً على البيانات التاريخية.
    """

    async def score(
        self,
        tenant_id: str,
        lead_id: str,
    ) -> LeadScore:
        """
        تقييم lead بناءً على:
        - بيانات الشركة (الحجم، الصناعة، الموقع)
        - سلوك التفاعل ( زيارات الموقع، فتح الإيميلات)
        - التوقيت (多久 من أول تواصل)
        - التشابه مع العملاء الحاليين
        """

        lead = await self.get_lead(tenant_id, lead_id)

        features = {
            # بيانات Lead
            "company_size": lead.company_size,
            "industry": lead.industry,
            "budget_range": lead.budget,
            "decision_maker": lead.has_decision_maker,

            # سلوك التفاعل
            "website_visits": lead.website_visits_count,
            "email_opens": lead.email_open_count,
            "demo_requested": lead.demo_requested,
            "pricing_page_views": lead.pricing_views,

            # التوقيت
            "days_since_first_contact": lead.days_since_contact,
            "response_time_avg": lead.avg_response_hours,

            # التشابه مع العملاء المحولة
            "similarity_to_customers": await self.calculate_similarity(
                lead, tenant_id
            ),
        }

        prediction = await self.model.predict(features)

        return LeadScore(
            lead_id=lead_id,
            score=prediction.probability,  # 0-100
            grade=self.probability_to_grade(prediction.probability),
            factors=prediction.feature_importance,
            recommended_action=self.get_recommended_action(prediction.probability),
            estimated_close_date=prediction.estimated_close,
            similar_leads_that_converted=prediction.similar_converted,
        )
```

#### 3.3.2 تنبؤ بإتمام الصفقات - Deal Closure Prediction

```python
class DealClosurePredictor:
    """
    توقع أي صفقات ستُغلق بنجاح خلال فترة محددة.
    """

    async def predict_pipeline(
        self,
        tenant_id: str,
        horizon_days: int = 30,
    ) -> PipelineForecast:
        deals = await self.get_active_deals(tenant_id)

        predictions = []
        for deal in deals:
            features = await self.extract_deal_features(deal)

            prediction = await self.model.predict(features)

            predictions.append(DealPrediction(
                deal_id=deal.id,
                deal_name=deal.name,
                value=deal.value,
                probability=prediction.probability,
                expected_close=prediction.expected_date,
                stage_forecast=prediction.next_stage,
                risk_factors=prediction.risks,
                recommendations=prediction.actions,
            ))

        # ملخص Pipeline
        total_value = sum(p.value for p in predictions)
        weighted_value = sum(p.value * p.probability for p in predictions)

        return PipelineForecast(
            predictions=predictions,
            summary={
                "total_pipeline_value": total_value,
                "weighted_pipeline_value": weighted_value,
                "deals_likely_to_close": sum(1 for p in predictions if p.probability > 0.7),
                "deals_at_risk": sum(1 for p in predictions if p.probability < 0.3),
                "forecast_accuracy": await self.get_forecast_accuracy(tenant_id),
            },
        )
```

#### 3.3.3 اقتراح خطوة التالية - Next Best Action

```python
class NextBestActionEngine:
    """
    اقتراح أفضل إجراء لكل عميل محتمل بناءً على مرحلته وسلوكه.
    """

    async def suggest(
        self,
        tenant_id: str,
        deal_id: str,
    ) -> list[NextBestAction]:
        deal = await self.get_deal_with_history(tenant_id, deal_id)

        # تحليل تاريخ التفاعل
        interactions = await self.get_interactions(deal_id)
        last_interaction = interactions[-1] if interactions else None

        # تحديد المرحلة الحالية
        stage = deal.current_stage

        # اقتراحات حسب المرحلة
        suggestions = []

        if stage == "NEW_LEAD":
            suggestions.append(NextBestAction(
                action="إرسال إيميل ترحيبي مع Case Study",
                priority="HIGH",
                channel="email",
                timing="خلال 24 ساعة",
                reasoning="العملاء الذين يردون خلال 24 ساعة لديهم نسبة تحويل أعلى بـ 3x",
            ))

        elif stage == "QUALIFIED":
            suggestions.append(NextBestAction(
                action="جدولة عرض توضيحي (Demo)",
                priority="HIGH",
                channel="phone",
                timing="خلال 48 ساعة",
                reasoning="Demo تزيد احتمال التحويل بنسبة 40%",
            ))

        elif stage == "PROPOSAL":
            suggestions.append(NextBestAction(
                action="متابعة العرض بخطاب توضيحي",
                priority="MEDIUM",
                channel="email",
                timing="بعد 3 أيام من إرسال العرض",
                reasoning="المتابعة في الوقت المناسب تقلل فقدان الصفقات",
            ))

        # AI-powered suggestions based on successful patterns
        ai_suggestions = await self.model.suggest(
            deal=deal,
            similar_deals=await self.find_similar_deals(deal, tenant_id),
            successful_patterns=await self.get_successful_patterns(tenant_id),
        )

        suggestions.extend(ai_suggestions)

        return sorted(suggestions, key=lambda s: s.priority)
```

#### 3.3.4 تحليل مشاعر العملاء - Customer Sentiment Analysis

```python
class CustomerSentimentAnalyzer:
    """
    تحليل رسائل وتعليقات العملاء لفهم مشاعرهم وملاحظاتهم.
    """

    async def analyze(
        self,
        tenant_id: str,
        customer_id: str,
        texts: list[str],
    ) -> SentimentAnalysis:

        results = []
        for text in texts:
            # تحليل المشاعر العام
            overall = await self.sentiment_model.analyze(text)

            # تحليل المشاعر حسب الجوانب (Aspect-based)
            aspects = await self.aspect_model.analyze(text)

            results.append(TextSentiment(
                text=text,
                overall_sentiment=overall.label,  # positive, negative, neutral
                confidence=overall.confidence,
                aspects=[
                    AspectSentiment(
                        aspect=a.aspect,  # "product", "service", "price", "delivery"
                        sentiment=a.sentiment,
                        confidence=a.confidence,
                        keywords=a.keywords,
                    )
                    for a in aspects
                ],
            ))

        # ملخص المشاعر
        return SentimentAnalysis(
            overall_trend=self.calculate_trend(results),
            positive_ratio=sum(1 for r in results if r.overall_sentiment == "positive") / len(results),
            negative_ratio=sum(1 for r in results if r.overall_sentiment == "negative") / len(results),
            aspect_summary=self.summarize_aspects(results),
            alerts=self.check_urgent_issues(results),
            recommendations=self.generate_recommendations(results),
        )
```

#### 3.3.5 Segmentation ذكي - Smart Customer Segmentation

```python
class SmartSegmentation:
    """
    تقسيم العملاء تلقائياً إلى مجموعات بناءً على:
    - القيمة (Monetary)
    - التكرار (Frequency)
    - الحداثة (Recency)
    - السلوك (Behavior)
    """

    async def segment(
        self,
        tenant_id: str,
    ) -> SegmentationReport:
        customers = await self.get_all_customers(tenant_id)

        features = []
        for customer in customers:
            rfm = await self.calculate_rfm(customer)
            behavior = await self.get_behavior_features(customer)
            features.append({**rfm, **behavior})

        # Clustering with K-Means
        clusters = await self.clustering_model.fit(features)

        # تسمية المجموعات
        segments = self.label_clusters(clusters)

        return SegmentationReport(
            segments=[
                Segment(
                    name=seg.name,
                    description=seg.description,
                    customer_count=seg.count,
                    avg_value=seg.avg_value,
                    avg_frequency=seg.avg_frequency,
                    characteristics=seg.characteristics,
                    recommended_strategy=seg.strategy,
                )
                for seg in segments
            ],
            total_customers=len(customers),
        )

    def label_clusters(self, clusters) -> list[Segment]:
        """
        أمثلة على التسميات:
        - VIP: قيمة عالية، تكرار عالي، حديث
        - Loyal: قيمة متوسطة، تكرار عالي
        - At Risk: قيمة عالية لكن غير نشط
        - New: حديث، قيمة منخفضة
        - Churning: في طريقه للمغادرة
        """
        pass
```

#### 3.3.6 تنبؤ بمعدل التحويل - Stage Conversion Prediction

```python
class StageConversionPredictor:
    """
    توقع معدل تحويل كل stage في Pipeline.
    """

    async def predict(
        self,
        tenant_id: str,
    ) -> ConversionPrediction:
        pipeline_stages = await self.get_pipeline_stages(tenant_id)

        predictions = []
        for stage in pipeline_stages:
            deals_in_stage = await self.get_deals_in_stage(tenant_id, stage.id)

            conversion_rate = await self.predict_conversion_rate(
                stage=stage,
                deals=deals_in_stage,
                historical_data=await self.get_stage_history(tenant_id, stage.id),
            )

            predictions.append(StagePrediction(
                stage_name=stage.name,
                deals_count=len(deals_in_stage),
                total_value=sum(d.value for d in deals_in_stage),
                predicted_conversion_rate=conversion_rate,
                predicted_conversions=int(len(deals_in_stage) * conversion_rate),
                avg_time_in_stage=stage.avg_days,
                bottleneck_score=self.calculate_bottleneck(deals_in_stage),
            ))

        return ConversionPrediction(
            predictions=predictions,
            overall_conversion=self.calculate_overall(predictions),
            bottleneck_stages=[p for p in predictions if p.bottleneck_score > 0.7],
        )
```



### 3.4 AI في الموارد البشرية - HR AI

#### 3.4.1 تنبؤ بمعدل التسرب - Employee Churn Prediction

```python
class EmployeeChurnPredictor:
    """
    توقع الموظفين المعرضين لل离职 (mushrakoon lil-inqida') بناءً على:
    - أنماط الحضور والغياب
    - تقييمات الأداء
    - مدة الخدمة
    - الراتب والتقدم الوظيفي
    - نشاط المنصة الداخلي
    """

    async def predict(
        self,
        tenant_id: str,
    ) -> ChurnPredictionReport:

        employees = await self.get_active_employees(tenant_id)

        predictions = []
        for emp in employees:
            features = {
                "tenure_months": emp.tenure_months,
                "performance_score": emp.latest_performance_score,
                "salary_band": emp.salary_band,
                "last_promotion_months": emp.months_since_last_promotion,
                "attendance_pattern": await self.get_attendance_pattern(emp),
                "overtime_hours": emp.avg_monthly_overtime,
                "leave_utilization": emp.leave_utilization_rate,
                "training_hours": emp.training_hours_last_year,
                "manager_rating": emp.manager_satisfaction_score,
                "engagement_score": emp.engagement_survey_score,
                "salary_vs_market": emp.salary_percentile_market,
            }

            prediction = await self.model.predict(features)

            predictions.append(EmployeeChurnPrediction(
                employee_id=emp.id,
                employee_name=emp.name,
                department=emp.department,
                churn_probability=prediction.probability,
                risk_level=self.probability_to_risk(prediction.probability),
                key_factors=prediction.feature_importance,
                recommended_actions=prediction.actions,
                estimated_cost_of_loss=self.calculate_replacement_cost(emp),
            ))

        # ترتيب حسب الخطورة
        predictions.sort(key=lambda p: p.churn_probability, reverse=True)

        return ChurnPredictionReport(
            predictions=predictions,
            high_risk_count=sum(1 for p in predictions if p.risk_level == "HIGH"),
            total_estimated_cost=sum(p.estimated_cost_of_loss for p in predictions if p.risk_level == "HIGH"),
            retention_recommendations=self.generate_retention_plan(predictions),
        )
```

#### 3.4.2 تحليل الأداء - Performance Pattern Analysis

```python
class PerformanceAnalyzer:
    """
    تحليل أنماط الحضور والإنتاجية.
    """

    async def analyze(
        self,
        tenant_id: str,
        employee_id: str,
        period_months: int = 12,
    ) -> PerformanceAnalysis:

        employee = await self.get_employee(tenant_id, employee_id)

        # جمع بيانات الأداء
        attendance = await self.get_attendance_data(employee_id, period_months)
        tasks = await self.get_task_completion(employee_id, period_months)
        reviews = await self.get_peer_reviews(employee_id, period_months)
        goals = await self.get_goal_progress(employee_id, period_months)

        analysis = PerformanceAnalysis(
            employee_id=employee_id,

            # أنماط الحضور
            attendance_patterns={
                "punctuality_score": self.calculate_punctuality(attendance),
                "absence_frequency": len([a for a in attendance if a.type == "ABSENT"]),
                "late_arrivals": len([a for a in attendance if a.is_late]),
                "trend": self.calculate_attendance_trend(attendance),
            },

            # الإنتاجية
            productivity_metrics={
                "tasks_completed": len([t for t in tasks if t.status == "DONE"]),
                "avg_completion_time": self.avg_completion_time(tasks),
                "on_time_delivery": self.on_time_rate(goals),
                "quality_score": self.quality_metrics(tasks),
                "trend": self.calculate_productivity_trend(tasks),
            },

            # أنماط مشبوهة (للإشراف)
            anomalies=self.detect_anomalies(attendance, tasks),

            # التوصيات
            recommendations=await self.generate_recommendations(
                attendance, tasks, reviews, goals
            ),
        )

        return analysis

    def detect_anomalies(self, attendance, tasks):
        """
        اكتشاف أنماط حضور مشبوهة:
        - غياب متكرر في أيام محددة
        - تأخر منهجي
        - أنماط غير طبيعية في الإجازات
        """
        anomalies = []

        # فحص نمط الغياب
        absent_days = [a for a in attendance if a.type == "ABSENT"]
        absent_weekdays = [a.date.weekday() for a in absent_days]
        if absent_weekdays:
            most_common = max(set(absent_weekdays), key=absent_weekdays.count)
            if absent_weekdays.count(most_common) > len(absent_days) * 0.5:
                anomalies.append({
                    "type": "PATTERN_ABSENCE",
                    "description": f"غياب متكرر يوم {self.weekday_name(most_common)}",
                    "severity": "MEDIUM",
                })

        return anomalies
```

#### 3.4.3 اقتراح برامج التدريب - Training Recommendation

```python
class TrainingRecommender:
    """
    اقتراح برامج تدريب بناءً على فجوات المهارات.
    """

    async def recommend(
        self,
        tenant_id: str,
        employee_id: str,
    ) -> list[TrainingRecommendation]:

        employee = await self.get_employee(tenant_id, employee_id)
        role_requirements = await self.get_role_requirements(employee.role_id)

        # حساب فجوات المهارات
        skill_gaps = []
        for req in role_requirements.required_skills:
            current_level = employee.skill_level(req.skill_id)
            required_level = req.minimum_level

            if current_level < required_level:
                skill_gaps.append({
                    "skill": req.skill_name,
                    "current": current_level,
                    "required": required_level,
                    "gap": required_level - current_level,
                    "importance": req.importance_weight,
                })

        # ترتيب الفجوات حسب الأهمية
        skill_gaps.sort(key=lambda g: g["gap"] * g["importance"], reverse=True)

        # اقتراح برامج تدريب
        recommendations = []
        for gap in skill_gaps[:5]:  # Top 5 gaps
            available_courses = await self.find_courses(
                skill=gap["skill"],
                level=gap["required"],
                format=employee.preferred_learning_style,
            )

            if available_courses:
                recommendations.append(TrainingRecommendation(
                    skill_gap=gap["skill"],
                    current_level=gap["current"],
                    target_level=gap["required"],
                    suggested_courses=available_courses[:3],
                    estimated_hours=courses[0].estimated_hours,
                    expected_impact=self.estimate_impact(gap),
                ))

        return recommendations
```

#### 3.4.4 تحسين الجدولة - Schedule Optimization

```python
class ScheduleOptimizer:
    """
    اقتراح أفضل جدولة للورديات بناءً على:
    - قوانين العمل (ساعات العمل، الإجازات)
    - تفضيلات الموظفين
    - الحمل المتوقع
    - مهارات كل موظف
    """

    async def optimize_shifts(
        self,
        tenant_id: str,
        department_id: str,
        start_date: date,
        days: int = 30,
    ) -> OptimizedSchedule:

        employees = await self.get_employees(tenant_id, department_id)
        demand_forecast = await self.forecast_workload(tenant_id, department_id, days)

        # Constraints
        constraints = {
            "max_hours_per_week": 48,
            "min_rest_between_shifts": 8,
            "max_consecutive_days": 6,
            "required_skills_per_shift": await self.get_shift_requirements(department_id),
            "employee_preferences": await self.get_preferences(employees),
            "approved_leaves": await self.get_approved_leaves(employees, days),
        }

        # تحسين الجدولة
        optimized = await self.optimizer.solve(
            employees=employees,
            demand=demand_forecast,
            constraints=constraints,
            objective="minimize_overtime + maximize_fairness + match_demand",
        )

        return OptimizedSchedule(
            schedule=optimized.schedule,
            metrics={
                "overtime_hours": optimized.total_overtime,
                "coverage_rate": optimized.coverage_percentage,
                "preference_match": optimized.preference_satisfaction,
                "cost": optimized.total_cost,
            },
            warnings=optimized.violations,
            comparison=await self.compare_with_current(optimized, tenant_id),
        )
```

#### 3.4.5 كشف الممارسات غير العادية - Unusual Practice Detection

```python
class UnusualPracticeDetector:
    """
    اكتشاف أنماط حضور مشبوهة وcompliance violations.
    """

    async def detect(
        self,
        tenant_id: str,
    ) -> list[ComplianceAlert:

        employees = await self.get_all_employees(tenant_id)
        alerts = []

        for emp in employees:
            attendance = await self.get_recent_attendance(emp.id, days=90)

            # 1. buddy punching detection (تسجيل حضور بالنيابة)
            if self.detect_buddy_punching(attendance):
                alerts.append(ComplianceAlert(
                    employee_id=emp.id,
                    type="BUDDY_PUNCHING_SUSPECTED",
                    description="يوجد تداخل في أوقات تسجيل الحضور مع موظف آخر",
                    severity="HIGH",
                ))

            # 2. excessive overtime
            if self.detect_excessive_overtime(attendance):
                alerts.append(ComplianceAlert(
                    employee_id=emp.id,
                    type="EXCESSIVE_OVERTIME",
                    description="ساعات عمل إضافية تتجاوز الحد القانوني",
                    severity="MEDIUM",
                ))

            # 3. irregular break patterns
            if self.detect_irregular_breaks(attendance):
                alerts.append(ComplianceAlert(
                    employee_id=emp.id,
                    type="IRREGULAR_BREAKS",
                    description="أنماط استراحة غير منتظمة",
                    severity="LOW",
                ))

        return alerts
```



### 3.5 AI في خدمة العملاء - Customer Service AI

#### 3.5.1 تصنيف التذاكر آلياً - Auto Ticket Classification

```python
class TicketClassifier:
    """
    تصنيف التذاكر آلياً حسب:
    - الأولوية (Urgency)
    - القسم المسؤول (Department)
    - نوع المشكلة (Type)
    - المشاعر (Sentiment)
    """

    async def classify(
        self,
        tenant_id: str,
        ticket: Ticket,
    ) -> TicketClassification:

        # تحليل نص التذكرة
        text_features = await self.extract_text_features(ticket.description)

        # التصنيف المتعدد
        classifications = await self.model.classify(
            text=ticket.description,
            subject=ticket.subject,
            customer_history=await self.get_customer_history(ticket.customer_id),
        )

        return TicketClassification(
            ticket_id=ticket.id,
            priority=classifications.priority,  # LOW, MEDIUM, HIGH, CRITICAL
            department=classifications.department,  # "billing", "technical", "sales"
            category=classifications.category,
            sentiment=classifications.sentiment,
            language=ticket.language,
            suggested_assignment=classifications.recommended_agent,
            estimated_resolution_time=classifications.eta,
            is_escalation_needed=classifications.priority in ["HIGH", "CRITICAL"],
        )
```

#### 3.5.2 اقتراح الإجابات - AI Response Suggestions

```python
class ResponseSuggester:
    """
    اقتراح ردود من قاعدة المعرفة بناءً على محتوى التذكرة.
    """

    async def suggest(
        self,
        tenant_id: str,
        ticket_id: str,
    ) -> list[ResponseSuggestion]:

        ticket = await self.get_ticket(tenant_id, ticket_id)

        # البحث الدلالي في قاعدة المعرفة
        knowledge_results = await self.vector_store.search(
            query=ticket.description,
            tenant_id=tenant_id,
            collection="knowledge_base",
            top_k=5,
        )

        # اقتراحات AI
        ai_suggestions = await self.llm.generate(
            prompt=f"""بناءً على التذكرة التالية، اقترح 3 ردود مناسبة:

            الموضوع: {ticket.subject}
            الوصف: {ticket.description}
            عميل: {ticket.customer_name}

            قد:"
            temperature=0.3,
        )

        # دمج النتائج
        suggestions = []

        for kb in knowledge_results:
            suggestions.append(ResponseSuggestion(
                source="knowledge_base",
                content=kb.content,
                relevance_score=kb.score,
                article_id=kb.article_id,
            ))

        for ai in ai_suggestions:
            suggestions.append(ResponseSuggestion(
                source="ai_generated",
                content=ai.text,
                confidence=ai.confidence,
                requires_review=True,
            ))

        return sorted(suggestions, key=lambda s: s.relevance_score, reverse=True)
```

#### 3.5.3 تحليل الرضا - Satisfaction Analysis

```python
class SatisfactionAnalyzer:
    """
    تحليل مشاعر العملاء من التقييمات والمراجعات.
    """

    async def analyze(
        self,
        tenant_id: str,
        period_days: int = 30,
    ) -> SatisfactionReport:

        # جمع التقييمات والمراجعات
        ratings = await self.get_ratings(tenant_id, period_days)
        reviews = await self.get_reviews(tenant_id, period_days)
        csat_data = await self.get_csat_responses(tenant_id, period_days)

        # تحليل المشاعر
        sentiment_results = []
        for review in reviews:
            sentiment = await self.sentiment_model.analyze(review.text)
            sentiment_results.append({
                "review": review,
                "sentiment": sentiment,
            })

        # اكتشاف المشاكل المتكررة
        common_issues = await self.extract_common_issues(reviews)

        return SatisfactionReport(
            overall_score=self.calculate_overall_score(ratings, csat_data),
            nps_score=self.calculate_nps(csat_data),
            sentiment_distribution=self.distribution(sentiment_results),
            common_issues=common_issues,
            improvement_areas=self.identify_areas(common_issues),
            positive_highlights=self.extract_positive(sentiment_results),
            trend=self.calculate_trend(tenant_id, period_days * 3),
        )
```

#### 3.5.4 تنبؤ بحجم التذاكر - Ticket Volume Forecast

```python
class TicketVolumeForecaster:
    """
    توقع حجم التذاكر未来 لتخطيط الموارد.
    """

    async def forecast(
        self,
        tenant_id: str,
        horizon_days: int = 30,
    ) -> TicketVolumeForecast:

        historical = await self.get_ticket_history(tenant_id, months=12)

        forecast = await self.model.forecast(
            data=historical,
            horizon=horizon_days,
            include_seasonality=True,
        )

        return TicketVolumeForecast(
            daily_forecasts=[
                DailyForecast(
                    date=f.date,
                    expected_tickets=f.predicted,
                    confidence_interval=(f.lower, f.upper),
                    peak_hours=f.peak_hours,
                )
                for f in forecast.points
            ],
            staffing_recommendation=self.calculate_staffing(forecast),
            resource_warnings=self.check_resource_gaps(forecast),
        )
```

#### 3.5.5 اكتشاف المشاكل المتكررة - Recurring Issue Detection

```python
class RecurringIssueDetector:
    """
    اكتشاف أنماط المشاكل الشائعة وتجميعها.
    """

    async def detect(
        self,
        tenant_id: str,
        period_days: int = 30,
    ) -> list[RecurringIssue]:

        tickets = await self.get_resolved_tickets(tenant_id, period_days)

        # تجميع حسب التشابه الدلالي
        clusters = await self.cluster_tickets(tickets)

        issues = []
        for cluster in clusters:
            if cluster.size >= 3:  # على الأقل 3 تذاكر مشابهة
                issues.append(RecurringIssue(
                    issue_id=cluster.id,
                    title=cluster.representative_title,
                    description=cluster.summary,
                    frequency=cluster.size,
                    affected_customers=cluster.unique_customers,
                    avg_resolution_time=cluster.avg_resolution_time,
                    suggested_root_cause=cluster.suggested_cause,
                    suggested_fix=cluster.suggested_fix,
                    auto_solution=self.generate_auto_solution(cluster),
                ))

        return sorted(issues, key=lambda i: i.frequency, reverse=True)
```

### 3.6 AI Copilot - المساعد الذكي التفاعلي

AI Copilot هو واجهة تفاعلية تسمح للمستخدمين بالتحدث مع النظام بلغة طبيعية. يعمل كمساعد ذكي عبر جميع وحدات النظام.

#### 3.6.1 Chat Interface - واجهة المحادثة

```python
class AICopilot:
    """
    مساعد ذكي تفاعلي - يفهم أوامر بلغة طبيعية ويتفاعل مع جميع وحدات EOS.
    """

    SYSTEM_PROMPT = """أنت مساعد ذكي لـ EOS Enterprise Operating System.
    يمكنك المساعدة في:
    - المحاسبة: القيود الدفترية، التقارير المالية، التصنيفات
    - المخزون: مستويات المخزون، إعادة الطلب، التوقعات
    - المبيعات: العملاء المحتملون، الصفقات، التوقعات
    - الموارد البشرية: الموظفين، الحضور، الأداء
    - خدمة العملاء: التذاكر، الرضا، الإجابات

    قواعدك:
    - تحدث بالعربية الفصحى البسيطة
    - اقتصر إجاباتك على معلومات موثوقة فقط
    - إذا لم تكن متأكداً، اشرح ذلك
    - احترم خصوصية البيانات - لا تشارك بيانات مستأجرين آخرين
    """

    async def chat(
        self,
        tenant_id: str,
        session_id: str,
        user_message: str,
        context: CopilotContext | None = None,
    ) -> CopilotResponse:

        # استرجاع تاريخ المحادثة
        history = await self.get_conversation_history(session_id)

        # بناء السياق
        full_context = await self.build_context(
            tenant_id=tenant_id,
            user_message=user_message,
            existing_context=context,
        )

        # اختيار الأدوات المتاحة
        tools = self.get_available_tools(tenant_id)

        # استدعاء LLM مع Function Calling
        response = await self.llm.chat(
            system=self.SYSTEM_PROMPT,
            messages=history + [{"role": "user", "content": user_message}],
            tools=tools,
            context=full_context,
        )

        # معالجة tool calls
        if response.tool_calls:
            for tool_call in response.tool_calls:
                result = await self.execute_tool(tool_call, tenant_id)
                response.add_tool_result(tool_call.id, result)

        # حفظ المحادثة
        await self.save_message(session_id, "user", user_message)
        await self.save_message(session_id, "assistant", response.content)

        return CopilotResponse(
            content=response.content,
            actions_taken=response.tool_results,
            suggestions=await self.generate_suggestions(response, context),
            confidence=response.confidence,
        )
```

#### 3.6.2 أمثلة على الاستفسارات

```
المحاسبة:
  User: "ايه أكتر مننتاج بيع الشهر ده؟"
  AI: "أكثر منتج مبيعاً هذا الشهر هو [اسم المنتج] بإجمالي مبيعات
       [المبلغ] ريال من [عدد] وحدة. مقارنة بالشهر السابق، زادت
       المبيعات بنسبة [%]."

  User: "اعمللي ملخص المبيعات للربع الأول"
  AI: "ملخص مبيعات الربع الأول 2026:
       - إجمالي الإيرادات: [المبلغ] ريال
       - عدد المعاملات: [العدد]
       - متوسط قيمة الطلب: [المبلغ] ريال
       - أعلى منتج: [اسم المنتج]
       - أفضل عميل: [اسم العميل]
       [إحصائيات إضافية]"

المخزون:
  User: "كم رصيد المخزون من product X?"
  AI: "رصيد المخزون الحالي لـ [اسم المنتج]:
       - الكمية المتاحة: [العدد] وحدة
       - المحجوز: [العدد] وحدة
       - المطلب: [العدد] وحدة
       - حالة إعادة الطلب: [ᴗ/✗]"

المحاسبة:
  User: "اعمللي تقرير الأرباح والخسائر"
  AI: "تقرير الأرباح والخسائر لـ [الفترة]:
       - الإيرادات: [المبلغ] ريال
       - التكاليف: [المبلغ] ريال
       - صافي الربح: [المبلغ] ريال
       - هامش الربح: [%]
       [تفاصيل حسب الفئات]"

الموارد البشرية:
  User: "مين الموظفين اللي غايبين النهارده؟"
  AI: "الغياب اليوم [التاريخ]:
       - [اسم الموظف 1] - [القسم] - [السبب إن وجد]
       - [اسم الموظف 2] - [القسم] - [السبب إن وجد]
       المجموع: [العدد] من أصل [العدد] موظف"

خدمة العملاء:
  User: "امتى آخر فاتورة للعميل Y؟"
  AI: "آخر فاتورة للعميل [اسم العميل]:
       - رقم الفاتورة: [الرقم]
       - التاريخ: [التاريخ]
       - المبلغ: [المبلغ] ريال
       - الحالة: [مدفوعة/مستحقة/متأخرة]"

التوقعات:
  User: "تنبألي بمبيعات الشهر الجاي"
  AI: "توقع مبيعات الشهر القادم [اسم الشهر]:
       - المتوقع: [المبلغ] ريال (±[الت Greyzone])
       - الاتجاه العام: [صاعد/هابط/مستقر]
       - الموسمية: [ملاحظات]
       - الثقة: [%]"

الكشف:
  User: "لقيت أي معاملات مشبوهة؟"
  AI: "تم فحص المعاملات واكتشفت:
       1. [وصف المعاملة] - سبب الاشتباه: [السبب]
       2. [وصف المعاملة] - سبب الاشتباه: [السبب]
       إجمالي المعاملات المشبوهة: [العدد]"
```

#### 3.6.3 Smart Suggestions - اقتراحات ذكية أثناء العمل

```python
class SmartSuggestionEngine:
    """
    اقتراحات ذكية تظهر للمستخدم أثناء العمل.
    """

    SUGGESTION_TRIGGERS = {
        # عند فتح صفحة المحاسبة
        "accounting_dashboard": [
            {
                "condition": "has_unbalanced_entries",
                "suggestion": "يوجد {count} قيود غير متوازنة تحتاج مراجعة",
                "action": "navigate_to_errors",
            },
            {
                "condition": "month_end_approaching",
                "suggestion": "نهاية الشهر خلال {days} أيام - يُنصح ببدء الإقفال المحاسبي",
                "action": "start_closing",
            },
        ],

        # عند فتح صفحة المخزون
        "inventory_dashboard": [
            {
                "condition": "low_stock_items > 0",
                "suggestion": "{count} منتجات وصلت للحد الأدنى - هل تريد رؤية طلبات إعادة الطلب؟",
                "action": "show_reorder",
            },
            {
                "condition": "has_expiring_products",
                "suggestion": "{count} منتجات ستنتهي صلاحيتها خلال 30 يوم",
                "action": "show_expiring",
            },
        ],

        # عند إنشاء عميل محتمل جديد
        "new_lead": [
            {
                "condition": "always",
                "suggestion": "相似 عملاء محولوا بنجاح: {similar_customers}",
                "action": "show_similar_deals",
            },
        ],
    }

    async def get_suggestions(
        self,
        tenant_id: str,
        current_page: str,
        user_context: dict,
    ) -> list[SmartSuggestion]:

        triggers = self.SUGGESTION_TRIGGERS.get(current_page, [])
        suggestions = []

        for trigger in triggers:
            if await self.evaluate_condition(trigger["condition"], tenant_id, user_context):
                suggestion_text = await self.format_suggestion(
                    trigger["suggestion"], tenant_id, user_context
                )
                suggestions.append(SmartSuggestion(
                    text=suggestion_text,
                    action=trigger["action"],
                    priority=trigger.get("priority", "MEDIUM"),
                    dismissible=True,
                ))

        return suggestions
```

#### 3.6.4 Voice Interface - دعم الأوامر الصوتية

```python
class VoiceInterface:
    """
    دعم الأوامر الصوتية للمستخدمين.
    """

    async def process_voice(
        self,
        tenant_id: str,
        audio_data: bytes,
        language: str = "ar",
    ) -> CopilotResponse:
        """
        معالجة أمر صوتي:
        1. تحويل الصوت إلى نص (STT)
        2. معالجة النص كأمر عادي
        3. تحويل الاستجابة إلى صوت (TTS)
        """

        # Speech to Text
        text = await self.stt_model.transcribe(
            audio=audio_data,
            language=language,
        )

        # معالجة الأمر
        response = await self.copilot.chat(
            tenant_id=tenant_id,
            session_id=None,
            user_message=text,
        )

        # Text to Speech
        audio_response = await self.tts_model.synthesize(
            text=response.content,
            language=language,
        )

        return CopilotVoiceResponse(
            text=response.content,
            audio=audio_response,
            original_text=text,
        )
```



---

## 4. نماذج الذكاء الاصطناعي المستخدمة

### 4.1 جدول النماذج الكامل

| المهمة | النموذج | النوع | الاستخدام | التكلفة التقريبية |
|--------|---------|-------|----------|------------------|
| NLP / Chat | GPT-4o | LLM API | AI Copilot (المحادثة الرئيسية) | $5/1M input tokens |
| NLP / Chat (Light) | GPT-4o-mini | LLM API | AI Copilot (المهام البسيطة) | $0.15/1M input tokens |
| NLP / Chat (Alt) | Claude 3.5 Sonnet | LLM API | AI Copilot (بديل + التحليل) | $3/1M input tokens |
| Text Classification | Fine-tuned BERT | Custom Model | تصنيف التذاكر، تصنيف المصروفات | مجاني (Maghrib) |
| Time Series | Prophet | Open Source | Demand forecasting | مجاني (Maghrib) |
| Time Series (Advanced) | LightGBM + Prophet Ensemble | Open Source | Sales forecasting متقدم | مجاني (Maghrib) |
| Anomaly Detection | Isolation Forest | Custom Model | كشف التسرب، الأخطاء المحاسبية | مجاني (Maghrib) |
| Anomaly Detection (Stat) | Z-Score + IQR | Statistical | كشف القيم الشاذة السريعة | مجاني (Maghrib) |
| OCR | AWS Textract | Cloud API | معالجة الفواتير والمستندات | $0.015/page |
| OCR (Alt) | Tesseract OCR | Open Source | معالجة المستندات (بديل محلي) | مجاني |
| Sentiment Analysis | Fine-tuned RoBERTa | Custom Model | تحليل مشاعر العملاء | مجاني (Maghrib) |
| Embeddings | text-embedding-3-small | API | البحث الدلالي، التشابه | $0.02/1M tokens |
| Embeddings (Alt) | all-MiniLM-L6-v2 | Open Source | التضمينات المحلية | مجاني (Maghrib) |
| Document Summarization | GPT-4o-mini | API | تلخيص التقارير | $0.15/1M input tokens |
| Recommendations | Collaborative Filtering | Custom | اقتراح المنتجات/الإجراءات | مجاني (Maghrib) |
| Clustering | K-Means + HDBSCAN | Open Source | تصنيف العملاء | مجاني (Maghrib) |
| Chat (Local) | Mistral 7B | Open Source | Copilot محلي (اختياري) | مجاني (Maghrib) |

### 4.2 استراتيجية اختيار النموذج

```python
class ModelSelectionStrategy:
    """
    استراتيجية اختيار النموذج بناءً على:
    1. التكلفة (Cost)
    2. الجودة (Quality)
    3. السرعة (Latency)
    4. الخصوصية (Privacy)
    """

    SELECTION_MATRIX = {
        "high_privacy": {
            "description": "بيانات حساسة لا يمكن إرسالها لـ API خارجي",
            "prefer": "local_models",
            "fallback": "fine_tuned_small",
        },
        "low_latency": {
            "description": "يجب أن يكون الرد فوري (أقل من 200ms)",
            "prefer": "small_local_model",
            "fallback": "fast_api_model",
        },
        "high_quality": {
            "description": "جودة الإجابة أهم من السرعة والتكلفة",
            "prefer": "gpt4o_or_claude",
            "fallback": "fine_tuned_llm",
        },
        "cost_sensitive": {
            "description": "التكلفة هي الأولوية",
            "prefer": "open_source_models",
            "fallback": "gpt4o_mini",
        },
    }
```

### 4.3 Fine-Tuning Pipeline

```python
class FineTuningPipeline:
    """
    خط أنابيب التدريب الدقيق (Fine-tuning) للنماذج المخصصة.
    """

    async def fine_tune(
        self,
        model_name: str,
        tenant_id: str,
        training_data: list[dict],
    ) -> FineTuneResult:
        """
        تدريب دقيق لنموذج على بيانات المستأجر.

        Steps:
        1. تحضير البيانات (Data Preparation)
        2. تقسيم Train/Validation/Test
        3. التدريب مع Early Stopping
        4. التقييم على Test Set
        5. تسجيل في MLflow
        6. نشر إذا كانت الأفضل
        """

        # 1. تحضير البيانات
        prepared = await self.prepare_data(training_data)

        # 2. تقسيم البيانات
        train, val, test = self.split_data(prepared, ratios=[0.7, 0.15, 0.15])

        # 3. التدريب
        training_run = await self.train(
            base_model=model_name,
            train_data=train,
            val_data=val,
            hyperparams=self.default_hyperparams(model_name),
            early_stopping_patience=5,
        )

        # 4. التقييم
        evaluation = await self.evaluate(training_run.model, test)

        # 5. التسجيل
        mlflow_run = await self.log_to_mlflow(
            model=training_run.model,
            metrics=evaluation,
            params=training_run.params,
            tenant_id=tenant_id,
        )

        # 6. النشر (إذا كانت الأفضل)
        should_promote = await self.check_if_best(
            model_name=model_name,
            current_metrics=evaluation,
        )

        if should_promote:
            await self.promote_to_production(mlflow_run)

        return FineTuneResult(
            run_id=mlflow_run.id,
            metrics=evaluation,
            promoted=should_promote,
        )
```

---

## 5. متطلبات تقنية للـ AI Layer

### 5.1 API Endpoints

#### Copilot Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `POST` | `/api/v1/ai/copilot/chat` | إرسال رسالة للمساعد الذكي |
| `POST` | `/api/v1/ai/copilot/voice` | إرسال أمر صوتي |
| `GET` | `/api/v1/ai/copilot/sessions/{session_id}` | جلب جلسة محادثة |
| `GET` | `/api/v1/ai/copilot/sessions/{session_id}/history` | جلب تاريخ المحادثة |
| `DELETE` | `/api/v1/ai/copilot/sessions/{session_id}` | حذف جلسة محادثة |
| `GET` | `/api/v1/ai/copilot/suggestions` | جلب اقتراحات ذكية |

#### Classification Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `POST` | `/api/v1/ai/classify/expense` | تصنيف مصروف |
| `POST` | `/api/v1/ai/classify/batch` | تصنيف دفعة مصروفات |
| `POST` | `/api/v1/ai/classify/ticket` | تصنيف تذكرة دعم |
| `PUT` | `/api/v1/ai/classify/feedback` | تغذية راجعة للتصنيف |

#### Prediction Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `POST` | `/api/v1/ai/predict/demand` | توقع الطلب |
| `POST` | `/api/v1/ai/predict/cashflow` | توقع التدفقات النقدية |
| `POST` | `/api/v1/ai/predict/churn` | توقع تسرب العملاء/الموظفين |
| `POST` | `/api/v1/ai/predict/sales` | توقع المبيعات |
| `POST` | `/api/v1/ai/predict/conversion` | توقع معدل التحويل |
| `GET` | `/api/v1/ai/predict/pipeline/{tenant_id}` | توقع Pipeline المبيعات |

#### Detection Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `POST` | `/api/v1/ai/detect/anomaly` | كشف القيم الشاذة |
| `POST` | `/api/v1/ai/detect/errors` | كشف الأخطاء المحاسبية |
| `POST` | `/api/v1/ai/detect/shrinkage` | كشف التسرب في المخزون |
| `POST` | `/api/v1/ai/detect/duplicates` | كشف التكرار (موردين/عملاء) |

#### Document Processing Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `POST` | `/api/v1/ai/ocr/extract` | استخراج بيانات من مستند |
| `POST` | `/api/v1/ai/ocr/invoice` | معالجة فاتورة بالـ OCR |
| `POST` | `/api/v1/ai/ocr/receipt` | معالجة إيصال بالـ OCR |
| `POST` | `/api/v1/ai/summarize/report` | تلخيص تقرير |
| `POST` | `/api/v1/ai/summarize/document` | تلخيص مستند |

#### Analysis Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `POST` | `/api/v1/ai/sentiment/analyze` | تحليل مشاعر نص |
| `POST` | `/api/v1/ai/sentiment/batch` | تحليل مشاعر دفعة |
| `POST` | `/api/v1/ai/recommend/products` | اقتراح منتجات |
| `POST` | `/api/v1/ai/recommend/actions` | اقتراح إجراءات |
| `POST` | `/api/v1/ai/segment/customers` | تقسيم العملاء |
| `GET` | `/api/v1/ai/analytics/dashboard/{tenant_id}` | لوحة تحليلات ذكية |

#### Forecasting Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `POST` | `/api/v1/ai/forecast/sales` | توقع المبيعات |
| `POST` | `/api/v1/ai/forecast/demand` | توقع الطلب |
| `POST` | `/api/v1/ai/forecast/revenue` | توقع الإيرادات |
| `POST` | `/api/v1/ai/forecast/ticket-volume` | توقع حجم التذاكر |

#### Model Management Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `GET` | `/api/v1/ai/models` | جلب جميع النماذج المسجلة |
| `GET` | `/api/v1/ai/models/{model_name}/versions` | جلب إصدارات نموذج |
| `POST` | `/api/v1/ai/models/{model_name}/promote` | ترقية إصدار للإنتاج |
| `GET` | `/api/v1/ai/models/{model_name}/metrics` | جلب مقاييس أداء نموذج |
| `GET` | `/api/v1/ai/usage/{tenant_id}` | جلب استخدام AI للمستأجر |

### 5.2 Database Tables for AI

```sql
-- ============================================
-- 1. سجل النماذج - Model Registry
-- ============================================
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    model_type VARCHAR(50) NOT NULL,        -- 'classification', 'forecast', 'anomaly', etc.
    domain VARCHAR(50) NOT NULL,            -- 'accounting', 'inventory', 'sales', 'hr', 'crm'
    status VARCHAR(20) NOT NULL DEFAULT 'development',  -- 'development', 'staging', 'production', 'archived'
    mlflow_run_id VARCHAR(100),             -- MLflow experiment run ID
    mlflow_model_uri VARCHAR(500),          -- MLflow model URI
    metrics JSONB DEFAULT '{}',             -- {'accuracy': 0.95, 'f1': 0.93, etc.}
    hyperparameters JSONB DEFAULT '{}',     -- Model hyperparameters
    training_data_size INTEGER,
    training_duration_seconds FLOAT,
    model_size_bytes BIGINT,
    inference_latency_ms FLOAT,
    description TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(model_name, model_version)
);

CREATE INDEX idx_ai_models_domain ON ai_models(domain);
CREATE INDEX idx_ai_models_status ON ai_models(status);
CREATE INDEX idx_ai_models_name ON ai_models(model_name);

-- ============================================
-- 2. سجل التنبؤات - Prediction Logs
-- ============================================
CREATE TABLE ai_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    model_id UUID NOT NULL REFERENCES ai_models(id),
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20) NOT NULL,

    -- Prediction Details
    service VARCHAR(50) NOT NULL,           -- 'copilot', 'classify', 'predict', 'detect', etc.
    input_data JSONB NOT NULL,              -- Input features
    output_data JSONB NOT NULL,             -- Prediction results
    confidence FLOAT,
    latency_ms FLOAT,

    -- Context
    user_id UUID REFERENCES users(id),
    module VARCHAR(50),                     -- 'accounting', 'inventory', 'sales', etc.
    entity_type VARCHAR(50),                -- 'expense', 'lead', 'ticket', etc.
    entity_id UUID,

    -- Cost
    tokens_used INTEGER DEFAULT 0,
    estimated_cost_usd FLOAT DEFAULT 0,

    -- Feedback
    user_feedback VARCHAR(20),              -- 'correct', 'incorrect', 'partial'
    feedback_notes TEXT,
    corrected_output JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_predictions_tenant ON ai_predictions(tenant_id);
CREATE INDEX idx_ai_predictions_model ON ai_predictions(model_id);
CREATE INDEX idx_ai_predictions_service ON ai_predictions(service);
CREATE INDEX idx_ai_predictions_created ON ai_predictions(created_at);

-- ============================================
-- 3. بيانات التدريب - Training Data
-- ============================================
CREATE TABLE ai_training_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    model_name VARCHAR(100) NOT NULL,

    -- Data
    input_text TEXT NOT NULL,
    expected_output JSONB NOT NULL,
    source VARCHAR(50),                     -- 'user_feedback', 'system_generated', 'manual'
    source_entity_type VARCHAR(50),
    source_entity_id UUID,

    -- Quality
    quality_score FLOAT,                    -- 0-1
    validated BOOLEAN DEFAULT FALSE,
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_training_tenant ON ai_training_data(tenant_id);
CREATE INDEX idx_ai_training_model ON ai_training_data(model_name);

-- ============================================
-- 4. مقاييس أداء النماذج - Model Performance
-- ============================================
CREATE TABLE ai_model_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES ai_models(id),
    tenant_id UUID REFERENCES tenants(id),  -- NULL for shared models

    -- Metrics
    metric_name VARCHAR(50) NOT NULL,       -- 'accuracy', 'precision', 'recall', 'f1', 'mape', etc.
    metric_value FLOAT NOT NULL,
    metric_period VARCHAR(20),              -- 'daily', 'weekly', 'monthly'
    period_start TIMESTAMP,
    period_end TIMESTAMP,

    -- Sample
    sample_size INTEGER,
    evaluation_dataset VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_performance_model ON ai_model_performance(model_id);

-- ============================================
-- 5. تتبع استخدام المستأجرين - Tenant Usage
-- ============================================
CREATE TABLE ai_tenant_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),

    -- Usage Period
    usage_date DATE NOT NULL,

    -- Usage Metrics
    total_requests INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd FLOAT DEFAULT 0,

    -- By Service
    copilot_requests INTEGER DEFAULT 0,
    copilot_tokens INTEGER DEFAULT 0,
    classify_requests INTEGER DEFAULT 0,
    predict_requests INTEGER DEFAULT 0,
    detect_requests INTEGER DEFAULT 0,
    ocr_documents INTEGER DEFAULT 0,
    ocr_cost_usd FLOAT DEFAULT 0,
    sentiment_requests INTEGER DEFAULT 0,
    recommend_requests INTEGER DEFAULT 0,
    summarize_requests INTEGER DEFAULT 0,

    -- Rate Limits
    rate_limit_hits INTEGER DEFAULT 0,      -- Number of rate limit violations

    -- Cost Breakdown
    cost_breakdown JSONB DEFAULT '{}',      -- Detailed cost per model

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(tenant_id, usage_date)
);

CREATE INDEX idx_ai_usage_tenant ON ai_tenant_usage(tenant_id);
CREATE INDEX idx_ai_usage_date ON ai_tenant_usage(usage_date);

-- ============================================
-- 6. سجل محادثات AI Copilot
-- ============================================
CREATE TABLE ai_copilot_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID NOT NULL REFERENCES users(id),

    -- Session
    session_id VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(255),                     -- Auto-generated title

    -- Context
    active_module VARCHAR(50),              -- Which module user is currently in
    context_data JSONB DEFAULT '{}',        -- Additional context (current page, etc.)

    -- Stats
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd FLOAT DEFAULT 0,

    -- Status
    status VARCHAR(20) DEFAULT 'active',    -- 'active', 'closed', 'archived'

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP
);

CREATE INDEX idx_ai_conv_tenant ON ai_copilot_conversations(tenant_id);
CREATE INDEX idx_ai_conv_user ON ai_copilot_conversations(user_id);
CREATE INDEX idx_ai_conv_session ON ai_copilot_conversations(session_id);

-- ============================================
-- 7. رسائل AI Copilot
-- ============================================
CREATE TABLE ai_copilot_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES ai_copilot_conversations(id),

    -- Message
    role VARCHAR(20) NOT NULL,              -- 'user', 'assistant', 'system', 'tool'
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text', -- 'text', 'markdown', 'json', 'image'

    -- Tool Calls (for assistant messages)
    tool_calls JSONB,                       -- [{name, args, result}]
    tool_call_id VARCHAR(100),              -- For tool result messages

    -- Metadata
    model_used VARCHAR(100),
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    latency_ms FLOAT,
    confidence FLOAT,

    -- Feedback
    user_feedback VARCHAR(20),              -- 'helpful', 'not_helpful', NULL
    feedback_comment TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_msg_conversation ON ai_copilot_messages(conversation_id);
CREATE INDEX idx_ai_msg_created ON ai_copilot_messages(created_at);
```

### 5.3 Cost Management - إدارة التكلفة

```python
class CostManager:
    """
    إدارة تكلفة الذكاء الاصطناعي لكل مستأجر.
    """

    async def track_usage(
        self,
        tenant_id: str,
        service: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
    ):
        """تتبع استخدام AI لكل طلب"""

        # حساب التكلفة
        cost = self.calculate_cost(model, tokens_input, tokens_output)

        # حفظ في قاعدة البيانات
        await self.db.insert("ai_tenant_usage", {
            "tenant_id": tenant_id,
            "usage_date": date.today(),
            "service": service,
            "model": model,
            "tokens": tokens_input + tokens_output,
            "cost_usd": cost,
        })

        # فحص الحد الشهري
        monthly_total = await self.get_monthly_total(tenant_id)
        tenant_plan = await self.get_tenant_plan(tenant_id)

        if monthly_total > tenant_plan.ai_monthly_limit:
            await self.alert_overage(tenant_id, monthly_total, tenant_plan.ai_monthly_limit)

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """حساب التكلفة لكل نموذج"""

        PRICING = {
            "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
            "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
            "claude-3.5-sonnet": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
            "text-embedding-3-small": {"input": 0.02 / 1_000_000, "output": 0},
            "textract": {"input": 0.015, "output": 0},  # per page
        }

        pricing = PRICING.get(model, {"input": 0, "output": 0})
        return (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
```

### 5.4 Infrastructure Requirements

```yaml
# docker-compose.ai.yml
version: '3.8'

services:
  ai-gateway:
    build: ./docker/Dockerfile
    ports:
      - "8100:8000"
    environment:
      - DATABASE_URL=postgresql://eos:password@db:5432/eos_ai
      - REDIS_URL=redis://redis:6379/1
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - RABBITMQ_URL=amqp://rabbitmq:5672
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    depends_on:
      - db
      - redis
      - mlflow
      - rabbitmq
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'

  ai-training:
    build: ./docker/Dockerfile.training
    environment:
      - DATABASE_URL=postgresql://eos:password@db:5432/eos_ai
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - MINIO_ENDPOINT=minio:9000
    depends_on:
      - db
      - mlflow
      - minio
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  db:
    image: pgvector/pgvector:pg16
    volumes:
      - ai_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=eos_ai
      - POSTGRES_USER=eos
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    ports:
      - "5433:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    volumes:
      - redis_data:/data

  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.10.0
    ports:
      - "5001:5000"
    environment:
      - MLFLOW_TRACKING_URI=http://localhost:5000
      - MLFLOW_S3_ENDPOINT_URL=http://minio:9000
    volumes:
      - mlflow_data:/mlflow

  minio:
    image: minio/minio
    ports:
      - "9001:9000"
      - "9002:9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"

  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports:
      - "5673:5672"
      - "15673:15672"
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  airflow:
    image: apache/airflow:2.8.0
    ports:
      - "8081:8080"
    environment:
      - AIRFLOW__CORE__EXECUTOR=CeleryExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://eos:password@db:5432/airflow
      - AIRFLOW__CELERY__BROKER_URL=amqp://rabbitmq:5672
    volumes:
      - ./training/dags:/opt/airflow/dags
    depends_on:
      - rabbitmq
      - db

volumes:
  ai_data:
  redis_data:
  mlflow_data:
  minio_data:
  rabbitmq_data:
```



---

## 6. تكلفة الذكاء الاصطناعي - AI Pricing

### 6.1 جدول التكلفة للمستخدم والمستأجر

| الميزة | التكلفة الشهرية | الوحدة | ملاحظات |
|--------|-----------------|--------|---------|
| AI Copilot Basic | $5 | لكل مستخدم | 100 استفسار/شهر، GPT-4o-mini |
| AI Copilot Pro | $15 | لكل مستخدم | استفسارات غير محدودة، GPT-4o |
| AI Copilot Enterprise | $25 | لكل مستخدم | + Custom instructions، + Voice، + API access |
| Predictive Analytics | $20 | لكل مستأجر | جميع ميزات التنبؤ (demand, cashflow, sales) |
| Anomaly Detection | $15 | لكل مستأجر | كشف التسرب والأخطاء وال JsonRequestBehavior |
| Document AI (OCR) | $0.10 | لكل مستند | Pay-per-use، يشمل استخراج البيانات |
| Advanced Analytics | $50 | لكل مستأجر | Custom dashboards + AI reports |
| Smart Recommendations | $10 | لكل مستأجر | Product/action recommendations |
| Sentiment Analysis | $10 | لكل مستأجر | تحليل مشاعر العملاء |
| Custom Model Training | $200 | لكل مهمة | Fine-tuning نموذج مخصص للمستأجر |

### 6.2 حزم الاشتراك

```python
AI_PLANS = {
    "starter_ai": {
        "price_monthly": 0,
        "includes": [
            "AI Copilot Basic (50 queries/month)",
            "Auto-categorization (shared model)",
        ],
        "overage": {
            "copilot_query": "$0.10/query",
        },
    },
    "professional_ai": {
        "price_monthly": 299,
        "includes": [
            "AI Copilot Pro (unlimited)",
            "Auto-categorization (tenant model)",
            "Basic predictions (demand, cashflow)",
            "Anomaly detection",
            "500 OCR documents/month",
        ],
        "overage": {
            "ocr_document": "$0.10/document",
        },
    },
    "enterprise_ai": {
        "price_monthly": 999,
        "includes": [
            "AI Copilot Enterprise (unlimited + voice)",
            "All AI features unlimited",
            "Custom model training",
            "5000 OCR documents/month",
            "Advanced analytics",
            "Priority support",
            "SLA guarantee (99.9% uptime)",
        ],
        "overage": {
            "ocr_document": "$0.05/document",
        },
    },
}
```

### 6.3 Cost Optimization Strategies

```python
class CostOptimizer:
    """
    استراتيجيات لتقليل تكلفة AI.
    """

    strategies = {
        "1_model_tiering": {
            "description": "استخدام نماذج مختلفة حسب تعقيد المهمة",
            "example": "GPT-4o-mini للمهام البسيطة، GPT-4o للمهام المعقدة",
            "savings": "40-60%",
        },
        "2_response_caching": {
            "description": "تخزين استجابات AI المتكررة",
            "example": "تصنيف نفس النص مرتين = cached response",
            "savings": "20-30%",
        },
        "3_batch_processing": {
            "description": "معالجة الأدلة الكبيرة في batch بدل واحد تلو الآخر",
            "example": "تصنيف 1000 مصروف في batch بدلاً من 1000 طلب منفصل",
            "savings": "15-25%",
        },
        "4_local_models": {
            "description": "استخدام نماذج محلية للمهام البسيطة",
            "example": "Tesseract OCR محلي بدلاً من Textract",
            "savings": "80-100%",
        },
        "5_smart_routing": {
            "description": "توجيه الطلبات للنموذج الأقل تكلفة الم满足 للشروط",
            "example": "تصنيف نص بسيط → BERT محلي، نص معقد → GPT-4o",
            "savings": "30-50%",
        },
    }
```

---

## 7. خطة تطوير AI - AI Development Roadmap

### 7.1 المراحل الزمنية

| المرحلة | الميزات | التوقيت | الأولوية |
|---------|---------|---------|----------|
| **v1.0 - Foundation** | AI Copilot Basic (محادثة نصية)، Auto-categorization (مصروفات)، Basic predictions (demand, cashflow) | الشهر 5-8 | P0 - Critical |
| **v1.1 - Enhanced** | Expense error detection، Vendor deduplication، Smart reorder alerts، Ticket auto-classification | الشهر 8-10 | P1 - High |
| **v1.5 - Intelligence** | Demand forecasting متقدم، Anomaly detection كامل، Sentiment analysis، Customer segmentation، Lead scoring | الشهر 9-12 | P1 - High |
| **v1.7 - Automation** | Smart suggestions أثناء العمل، Recurring issue detection، Schedule optimization، Profitability analysis | الشهر 12-14 | P2 - Medium |
| **v2.0 - Advanced** | AI Copilot متقدم (صوت + custom instructions)، Custom models per tenant، ML pipeline كامل، A/B testing للنماذج | الشهر 13-18 | P2 - Medium |
| **v2.5 - Enterprise** | Explainable AI (XAI)، Federated learning، Real-time model updates، AI marketplace | الشهر 18-24 | P3 - Future |

### 7.2 تفاصيل كل مرحلة

#### المرحلة v1.0 - Foundation (الشهر 5-8)

```
الأولوية: P0 - Critical
الفريق المطلوب: 2 Backend + 1 ML Engineer + 1 Frontend

الميزات:
1. AI Copilot Basic
   - واجهة محادثة أساسية
   - أوامر بلغة طبيعية
   - وصول للبيانات الأساسية (أرصدة، فواتير، مبيعات)
   - 50 استفسار/شهر للمستخدم

2. Auto-categorization
   - تصنيف المصروفات آلياً
   - نموذج BERT مشترك لجميع المستأجرين
   - تعلم من القيود السابقة
   - دقة مستهدفة: 90%+

3. Basic Predictions
   - توقع الطلب (Prophet)
   - توقع التدفقات النقدية (Prophet)
   - تقارير يومية/أسبوعية/شهرية
```

#### المرحلة v1.1 - Enhanced (الشهر 8-10)

```
الأولوية: P1 - High
الفريق المطلوب: 2 Backend + 1 ML Engineer

الميزات:
1. Expense Error Detection
   - كشف القيود غير المتوازنة
   - كشف التكرار
   - كشف المبالغ المشبوهة

2. Vendor Deduplication
   - اكتشاف الموردين المكررين
   - اقتراح الدمج

3. Smart Reorder Alerts
   - تنبيهات إعادة الطلب الذكية
   - حساب EOQ

4. Ticket Auto-Classification
   - تصنيف التذاكر حسب الأولوية والقسم
   - اقتراح الإجابات من قاعدة المعرفة
```

#### المرحلة v1.5 - Intelligence (الشهر 9-12)

```
الأولوية: P1 - High
الفريق المطلوب: 2 Backend + 2 ML Engineers

الميزات:
1. Advanced Demand Forecasting
   - LightGBM + Prophet ensemble
   - مراعاة العروض والأعياد
   - دقة مستهدفة: MAPE < 15%

2. Full Anomaly Detection
   - Isolation Forest + Z-Score
   - كشف التسرب في المخزون
   - كشف الأخطاء المحاسبية

3. Sentiment Analysis
   - تحليل مشاعر العملاء
   - Aspect-based sentiment

4. Customer Segmentation
   - RFM + Behavioral clustering
   - Dinamik classification

5. Lead Scoring
   - تقييم العملاء المحتملين
   - تنبؤ بإتمام الصفقات
```

#### المرحلة v2.0 - Advanced (الشهر 13-18)

```
الأولوية: P2 - Medium
الفريق المطلوب: 2 Backend + 2 ML Engineers + 1 DevOps

الميزات:
1. Advanced AI Copilot
   - دعم الصوت (STT + TTS)
   - Custom instructions لكل مستخدم
   - AI Copilot API للمطورين
   - Memory عبر الجلسات

2. Custom Models per Tenant
   - Fine-tuning لكل tenant
   - Feature store خاص
   - Model versioning كامل

3. ML Pipeline
   - Auto-retraining
   - Model monitoring
   - A/B testing framework
   - Canary deployments للنماذج

4. Explainable AI (XAI)
   - SHAP values للتنبؤات
   - Reasoning chains للقرارات
   - Audit trail كامل
```

---

## 8. الأمان والخصوصية في AI - Security & Privacy

### 8.1 مبادئ الأمان الأساسية

```
+-----------------------------------------------------------+
|              Security & Privacy Principles                  |
+-----------------------------------------------------------+
|                                                             |
|  1. Data Isolation                                          |
|     بيانات كل tenant تُستخدم فقط لنماذج هذا الـ tenant     |
|     لا يوجد cross-tenant training بدون موافقة صريحة       |
|                                                             |
|  2. GDPR Compliance                                        |
|     Right to be forgotten: حذف بيانات AI عند طلب العميل    |
|     Data minimization: أدنى قدر من البيانات المطلوبة        |
|     Purpose limitation: استخدام البيانات للغرض المحدد فقط   |
|                                                             |
|  3. Audit Trail                                             |
|     كل قرار AI مسجل مع المدخلات والمخرجات والسبب           |
|     يمكن تتبع أي توصية لفهم سببها                          |
|                                                             |
|  4. Explainability                                          |
|     AI يجب أن يشرح توصياته                                 |
|     SHAP values للتنبؤات                                    |
|     Reasoning chains للقرارات المهمة                        |
|                                                             |
|  5. Human-in-the-loop                                       |
|     القرارات المهمة تتطلب تأكيد بشري                       |
|     AI يقترح، الإنسان يقرر                                  |
|     للمالية: لا تلقائي ل转账 lớn hơn حد محدد               |
|                                                             |
|  6. Encryption                                              |
|     Encryption at rest: AES-256                             |
|     Encryption in transit: TLS 1.3                          |
|     API keys encryption: hashed + salted                    |
|                                                             |
|  7. Access Control                                          |
|     Role-based access للخدمات AI                            |
|     Tenant-level isolation في جميع الطبقات                  |
|     API key rotation دوري                                   |
|                                                             |
+-----------------------------------------------------------+
```

### 8.2 Data Isolation Architecture

```python
class TenantDataIsolation:
    """
    عزل بيانات المستأجرين في جميع طبقات AI.
    """

    async def ensure_isolation(self, tenant_id: str):
        """
        ضمان عزل البيانات في كل طلب AI.

        الطبقات:
        1. Application Layer: tenant_id في كل استعلام
        2. Database Layer: Row-Level Security (RLS)
        3. Cache Layer: مفاتيح Cache مسبوقة بـ tenant_id
        4. Model Layer: نماذج منفصلة لكل tenant
        5. Storage Layer: مسارات تخزين منفصلة
        6. Log Layer: لا بيانات مستأجرين آخرين في السجلات
        """
        pass

    # Database Level - Row Level Security
    RLS_POLICIES = """
    -- كل جدول AI له policy يضمن عزل المستأجر
    ALTER TABLE ai_predictions ENABLE ROW LEVEL SECURITY;

    CREATE POLICY tenant_isolation ON ai_predictions
        USING (tenant_id = current_setting('app.current_tenant')::uuid);

    ALTER TABLE ai_copilot_conversations ENABLE ROW LEVEL SECURITY;

    CREATE POLICY tenant_isolation ON ai_copilot_conversations
        USING (tenant_id = current_setting('app.current_tenant')::uuid);

    -- ... same for all AI tables
    """

    # Cache Level
    CACHE_KEY_TEMPLATE = "tenant:{tenant_id}:ai:{service}:{identifier}"

    # Storage Level
    STORAGE_PATH_TEMPLATE = "tenants/{tenant_id}/ai/{model_name}/{version}/"
```

### 8.3 Audit Trail for AI Decisions

```python
class AIAuditTrail:
    """
    سجل تدقيق كامل لكل قرار AI.
    """

    async def log_decision(
        self,
        tenant_id: str,
        service: str,
        model_name: str,
        model_version: str,
        input_data: dict,
        output_data: dict,
        confidence: float,
        user_id: str,
        reasoning: str | None = None,
        shap_values: dict | None = None,
    ):
        """
        تسجيل كل قرار AI مع:
        - المدخلات الكاملة
        - المخرجات الكاملة
        - مستوى الثقة
        - التفسير (إن وجد)
        - SHAP values (للتنبؤات)
        - المستخدم الذي طلب القرار
        """

        await self.db.insert("ai_audit_log", {
            "id": generate_uuid(),
            "tenant_id": tenant_id,
            "service": service,
            "model_name": model_name,
            "model_version": model_version,
            "input_hash": hash_json(input_data),
            "input_data_encrypted": self.encrypt(input_data),
            "output_data": output_data,
            "confidence": confidence,
            "reasoning": reasoning,
            "shap_values": shap_values,
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "ip_address": None,  # من request context
            "request_id": None,  # من request context
        })
```

### 8.4 Human-in-the-Loop for Critical Decisions

```python
class HumanInTheLoop:
    """
    ضمان المراجعة البشرية للقرارات المهمة.
    """

    CRITICAL_SERVICES = [
        "financial_transfer",      # تحويلات مالية
        "journal_entry_auto",      # قيود دفترية تلقائية كبيرة
        "employee_termination",    # إجراءات إنهاء الخدمة
        "contract_generation",     # توليد عقود
        "payment_approval",        # موافقة على مدفوعات كبيرة
    ]

    THRESHOLDS = {
        "financial_transfer_amount": 50000,  # أكثر من 50,000 ريال
        "journal_entry_amount": 100000,      # أكثر من 100,000 ريال
        "employee_action_confidence": 0.8,   # أقل من 80% ثقة
    }

    async def check_if_human_review_needed(
        self,
        service: str,
        action_data: dict,
        ai_confidence: float,
    ) -> HumanReviewDecision:

        if service in self.CRITICAL_SERVICES:
            return HumanReviewDecision(
                requires_human=True,
                reason="Critical service - requires human approval",
                assigned_to=await self.get_approver(service, action_data),
                timeout_hours=24,
            )

        if action_data.get("amount", 0) > self.THRESHOLDS["financial_transfer_amount"]:
            return HumanReviewDecision(
                requires_human=True,
                reason=f"Amount {action_data['amount']} exceeds threshold",
                assigned_to=await self.get_financial_approver(action_data),
                timeout_hours=48,
            )

        if ai_confidence < self.THRESHOLDS["employee_action_confidence"]:
            return HumanReviewDecision(
                requires_human=True,
                reason=f"Low confidence ({ai_confidence:.1%})",
                assigned_to=await self.get_manager(action_data),
                timeout_hours=24,
            )

        return HumanReviewDecision(requires_human=False)
```

### 8.5 Model Security

```python
class ModelSecurity:
    """
    أمان النماذج وحماية الملكية الفكرية.
    """

    MEASURES = {
        "1_model_encryption": {
            "description": "تشفير النماذج المحفوظة",
            "implementation": "AES-256 encryption for model artifacts at rest",
        },
        "2_access_control": {
            "description": "تحكم في الوصول للنماذج",
            "implementation": "RBAC + API key authentication",
        },
        "3_model_signing": {
            "description": "توقيع النماذج لمنع التلاعب",
            "implementation": "Digital signatures + checksums",
        },
        "4_adversarial_protection": {
            "description": "حماية من الهجمات التضليلية",
            "implementation": "Input validation + anomaly detection on inputs",
        },
        "5_data_poisoning_detection": {
            "description": "كشف تسمم بيانات التدريب",
            "implementation": "Data quality checks + outlier detection in training data",
        },
        "6_model_versioning": {
            "description": "版本追踪 كامل للنماذج",
            "implementation": "MLflow model registry + immutable versions",
        },
    }
```

### 8.6 Compliance Checklist

```python
COMPLIANCE_CHECKLIST = {
    "GDPR": [
        "Right to access: المستخدم يمكنه طلب جميع بيانات AI الخاصة به",
        "Right to erasure: حذف جميع بيانات AI عند طلب المستأجر",
        "Data portability: تصدير بيانات AI بصيغة قياسية",
        "Consent management: موافقة صريحة قبل استخدام البيانات للتدريب",
        "Privacy by design: خصوصية مدمجة في التصميم",
        "Data Protection Impact Assessment (DPIA): تقييم الأثر على الخصوصية",
    ],
    "SOC2": [
        "Audit logging: سجل تدقيق كامل",
        "Access controls: تحكم في الوصول",
        "Encryption: تشفير البيانات",
        "Incident response: خطة الاستجابة للحوادث",
        "Vendor management: إدارة الموردين",
    ],
    "ISO27001": [
        "Information security management system (ISMS)",
        "Risk assessment and treatment",
        "Security controls implementation",
        "Continuous monitoring and improvement",
    ],
    "LOCAL_REGULATIONS": [
        "arParams حسب الدولة المستهدفة",
        "خادم البيانات في المنطقة الجغرافية المناسبة",
        "الامتثال للقوانين المحلية لحماية البيانات",
    ],
}
```

---

## 9. مقياس أداء AI - AI Performance Metrics

### 9.1 KPIs الرئيسية

| المقياس | الهدف | طريقة القياس |
|---------|-------|-------------|
| AI Copilot Response Time | < 2 ثانية (95th percentile) | Latency monitoring |
| Classification Accuracy | > 92% | F1-Score على test set |
| Forecast Accuracy (MAPE) | < 15% | Mean Absolute Percentage Error |
| Anomaly Detection Precision | > 85% | True positives / Total positives |
| OCR Accuracy | > 95% | Character-level accuracy |
| Sentiment Accuracy | > 88% | F1-Score on labeled data |
| AI Copilot User Satisfaction | > 4.2/5 | User feedback ratings |
| Cost per AI Request | < $0.01 (average) | Total cost / Total requests |
| Model Retraining Frequency | Monthly | Scheduled pipeline |
| Uptime | 99.9% | SLA monitoring |

### 9.2 Monitoring Dashboard

```python
class AIMonitoringDashboard:
    """
    لوحة مراقبة أداء AI في الوقت الحقيقي.
    """

    async def get_dashboard(self, tenant_id: str) -> MonitoringDashboard:
        return MonitoringDashboard(
            # Performance Metrics
            real_time_metrics={
                "requests_per_minute": await self.get_rpm(tenant_id),
                "avg_latency_ms": await self.get_avg_latency(tenant_id),
                "error_rate": await self.get_error_rate(tenant_id),
                "cache_hit_rate": await self.get_cache_hit_rate(tenant_id),
            },

            # Cost Metrics
            cost_metrics={
                "daily_cost": await self.get_daily_cost(tenant_id),
                "monthly_cost": await self.get_monthly_cost(tenant_id),
                "cost_per_request": await self.get_cost_per_request(tenant_id),
                "cost_trend": await self.get_cost_trend(tenant_id, days=30),
            },

            # Model Performance
            model_metrics={
                "classification_accuracy": await self.get_classification_metrics(tenant_id),
                "forecast_accuracy": await self.get_forecast_metrics(tenant_id),
                "anomaly_precision": await self.get_anomaly_metrics(tenant_id),
            },

            # Usage Metrics
            usage_metrics={
                "total_users_using_ai": await self.get_active_ai_users(tenant_id),
                "copilot_sessions": await self.get_copilot_sessions(tenant_id),
                "top_services": await self.get_top_services(tenant_id),
            },

            # Alerts
            alerts=await self.get_active_alerts(tenant_id),
        )
```

---

## 10. ملخص - Summary

طبقة الذكاء الاصطناعي في EOS هي **بنية تحتية أفقية** تخدم جميع الوحدات. النقاط الأساسية:

1. **Multi-tenant AI**: عزل تام لبيانات كل مستأجر
2. **Microservice Architecture**: FastAPI microservice مستقلة وقابلة للتوسع
3. **Model Management**: MLflow لإدارة دورة حياة النماذج
4. **Cost Control**: تتبع التكلفة لكل مستأجر + Rate limiting حسب الخطة
5. **Security First**: تشفير + عزل + Audit trail + Human-in-the-loop
6. **Progressive Rollout**: 6 مراحل تطوير على 24 شهر
7. **Horizontal Integration**: API موحدة تخدم جميع الوحدات بدون تغيير في البنية الأساسية

---

> **EOS Enterprise Operating System** | AI Layer Architecture v1.0
> آخر تحديث: 2026-08-18

