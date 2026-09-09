# سيناريوهات اختبار قوالب الصناعات — Industry Templates Test Scenarios

> **الإصدار:** 1.0.0
> **الحالة:** Draft
> **تاريخ الإنشاء:** 2026-08-18
> **المسؤول:** QA Lead / Industry Solutions Team
> **النطاق:** جميع قوالب الصناعات الستة في نظام EOS ERP
> **الهدف:** التحقق من صحة سير العمل End-to-End لكل صناعة مع بيانات محددة وقيم متوقعة

---

## 1. منهجية الاختبار — Test Methodology

### 1.1 دورة اختبار كل سيناريو

يتبع كل سيناريو الدورة الكاملة:

```
Onboarding → Setup → Daily Operations → Reporting → Edge Cases
الإدخال   → الإعداد → العمليات اليومية → التقارير   → الحالات الحدية
```

### 1.2 مستويات الشدة — Severity Levels

| الرمز | المستوى | الوصف |
|-------|---------|-------|
| 🔴 | Critical | فشل = Blocker — يمنع الإطلاق |
| 🟡 | High | فشل = Major — يحتاج إصلاح قبل الإطلاق |
| 🟢 | Medium | فشل = Minor — يمكن تأجيله |

### 1.3 معايير النجاح لكل خطوة

كل خطوة يجب أن تحقق:
- ✅ النتيجة المتوقعة المذكورة في الجدول
- ✅ عدم وجود أخطاء في الـ logs
- ✅ صحة القيود المحاسبية (إذا وُجدت)
- ✅ تحديث المخزون الصحيح (إذا وُجد)

### 1.4 بيئة الاختبار

| العنصر | القيمة |
|--------|--------|
| Database | PostgreSQL 16 — Test DB `eos_test_industry` |
| API Base URL | `https://api.test.eos-system.com/v1` |
| POS Terminal | 3 terminals (Pharmacy, Restaurant, Retail) |
| ETA Sandbox | `https://api.invoicing.eta.gov.eg/sandbox` |
| SMS Provider | Twilio Test Account |
| AI Service | EOS AI Engine — Staging Environment |

---

## 2. القطاع 1: صيدلية — Pharmacy

### سيناريو E2E: "دورة حياة الدواء من الاستلام إلى البيع"

**الوصف:** اختبار دورة حياة الدواء كاملة من إنشاء أمر الشراء حتى فحص انتهاء الصلاحية.

**البيانات الأساسية:**

| العنصر | القيمة |
|--------|--------|
| الدواء | Augmentin 1g (أوغمنتين جرام واحد) |
| الكود | DRG-AUG-1G |
| المورد | Pharco Pharmaceuticals |
| كود المورد | SUP-PHR-001 |
| الكمية المطلوبة | 500 علبة |
| سعر الشراء | 45 EGP / علبة |
| السعر الرسمي | 67.5 EGP / علبة |
| رقم التشغيلة | BN-2026-08 |
| تاريخ الانتهاء | 2028-06-30 |
| ضريبة القيمة المضافة | 14% |
| مبلغ البيع بالضريبة | 67.5 × 1.14 = 76.95 EGP |

---

#### الخطوة 1: إنشاء أمر الشراء — Create Purchase Order

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 1 من 10 |
| **الوحدة** | Purchasing Module |
| **الإجراء** | إنشاء أمر شراء جديد للمورد "Pharco" بـ 500 علبة Augmentin 1g بسعر 45 EGP للعلبة |
| **النتيجة المتوقعة** | PO# PO-2026-08-001 بإجمالي 22,500 EGP (500 × 45) مع حالة "Draft" |
| **التحقق** | `GET /api/v1/purchasing/po/PO-2026-08-001` → status: "draft", total: 22500 |

**البيانات المدخلة:**

```json
{
  "supplier_id": "SUP-PHR-001",
  "items": [
    {
      "item_id": "DRG-AUG-1G",
      "description": "Augmentin 1g Tablets",
      "quantity": 500,
      "unit": "box",
      "unit_price": 45.00,
      "currency": "EGP",
      "vat_rate": 0.14,
      "line_total": 22500.00
    }
  ],
  "expected_delivery": "2026-08-25",
  "payment_terms": "Net 60",
  "notes": "Request temperature-controlled transport"
}
```

**التحقق التفصيلي:**
- [ ] تم إنشاء رقم أمر الشراء PO-2026-08-001
- [ ] الحالة: Draft
- [ ] إجمالي القيمة: 500 × 45 = 22,500 EGP
- [ ] المورد مربوط بـ SUP-PHR-001
- [ ] جميع العناصر مدخلة بشكل صحيح

---

#### الخطوة 2: تأكيد أمر الشراء — Confirm PO → Accounting Entry

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 2 من 10 |
| **الوحدة** | Purchasing + Accounting Module |
| **الإجراء** | تأكيد أمر الشراء PO-2026-08-001 → إنشاء قيد محاسبي تلقائي |
| **النتيجة المتوقعة** | PO status → "Confirmed" + قيد: Debit: Creditors 22,500 / Credit: Purchases 22,500 |
| **التحقق** | `GET /api/v1/accounting/entries?po=PO-2026-08-001` → verify debit/credit |

**القيد المحاسبي المتوقع:**

| الحساب | المدين (Debit) | الدائن (Credit) | المرجع |
|--------|---------------|-----------------|--------|
| الحسابات الدائنة — موردين (Creditors) | 22,500.00 | — | PO-2026-08-001 |
| مشتريات — أدوية (Purchases) | — | 22,500.00 | PO-2026-08-001 |

**التحقق التفصيلي:**
- [ ] تغيرت حالة PO إلى "Confirmed"
- [ ] تم إنشاء قيد محاسبي آلي
- [ ] المدين = 22,500 (Creditors)
- [ ] الدائن = 22,500 (Purchases)
- [ ] المرجع يحتوي على رقم PO
- [ ] التاريخ = تاريخ اليوم

---

#### الخطوة 3: استلام الشحنة — Receive Shipment

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 3 من 10 |
| **الوحدة** | Warehouse + Inventory Module |
| **الإجراء** | استلام 500 علبة مع تسجيل رقم التشغيلة BN-2026-08 و تاريخ الانتهاء 2028-06 و أرقام التسلسل |
| **النتيجة المتوقعة** | Stock +500, Batch BN-2026-08 registered, Expiry 2028-06-30 |
| **التحقق** | `GET /api/v1/inventory/stock/DRG-AUG-1G` → qty: 500, batch: "BN-2026-08" |

**بيانات الاستلام:**

```json
{
  "po_number": "PO-2026-08-001",
  "received_items": [
    {
      "item_id": "DRG-AUG-1G",
      "quantity_received": 500,
      "batch_number": "BN-2026-08",
      "expiry_date": "2028-06-30",
      "serial_numbers": ["SN-AUG-00001", "SN-AUG-00002", "...", "SN-AUG-00500"],
      "storage_condition": "15-25°C",
      "condition_on_arrival": "Good"
    }
  ],
  "warehouse_id": "WH-PHARM-01",
  "received_by": "EMP-045",
  "receiving_date": "2026-08-20"
}
```

**التحقق التفصيلي:**
- [ ] تم استلام 500 علبة بالكامل
- [ ] رقم التشغيلة BN-2026-08 مسجل
- [ ] تاريخ الانتهاء 2028-06-30 مسجل
- [ ] تم ربط الأرقام التسلسلية (500 serial number)
- [ ] المخزون في WH-PHARM-01 = 500
- [ ] الحالة: "Received" / "Available"

---

#### الخطوة 4: التحقق من السعر الرسمي — Verify Official Drug Price

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 4 من 10 |
| **الوحدة** | Drug Registry Module |
| **الإجراء** | التحقق من السعر الرسمي للدواء من سجل الأدوية = 67.5 EGP |
| **النتيجة المتوقعة** | Drug registry price = 67.5 EGP, price_valid = true |
| **التحقق** | `GET /api/v1/pharmacy/drug-registry/DRG-AUG-1G` → official_price: 67.5 |

**التحقق التفصيلي:**
- [ ] السعر الرسمي مسجل في السجل = 67.5 EGP
- [ ] السعر لا يتجاوز الحد الأقصى للسجل
- [ ] markup مسموح به = (67.5 - 45) / 45 × 100 = 50%
- [ ] لا توجد منعات قانونية على البيع

---

#### الخطوة 5: بيع عبر POS — POS Sale

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 5 من 10 |
| **الوحدة** | POS + Inventory + Accounting Module |
| **الإجراء** | بيع 2 علبة Augmentin 1g عبر POS → 2 × 67.5 = 135 EGP + 14% VAT = 153.9 EGP |
| **النتيجة المتوقعة** | Invoice INV-POS-2026-08-001, total = 153.9 EGP, VAT = 18.9 EGP |
| **التحقق** | `GET /api/v1/pos/invoices/INV-POS-2026-08-001` → total: 153.9 |

**حساب البيع:**

```
Unit Price (Official):     67.50 EGP
Quantity:                  × 2
Subtotal:                  135.00 EGP
VAT (14%):                 18.90 EGP  (135 × 0.14)
Total:                     153.90 EGP
```

**بيانات البيع:**

```json
{
  "invoice_number": "INV-POS-2026-08-001",
  "items": [
    {
      "item_id": "DRG-AUG-1G",
      "batch_number": "BN-2026-08",
      "serial_numbers": ["SN-AUG-00003", "SN-AUG-00004"],
      "quantity": 2,
      "unit_price": 67.50,
      "vat_rate": 0.14,
      "vat_amount": 18.90,
      "line_total": 153.90
    }
  ],
  "payment_method": "cash",
  "customer_id": "CUST-001",
  "pharmacist_id": "PH-012",
  "prescription_required": false
}
```

**التحقق التفصيلي:**
- [ ] سعر الوحدة = 67.5 EGP (السعر الرسمي)
- [ ] الكمية = 2
- [ ] المجموع الفرعي = 135.00 EGP
- [ ] الضريبة = 135 × 0.14 = 18.90 EGP
- [ ] الإجمالي = 135 + 18.9 = 153.90 EGP
- [ ] رقم الفاتورة INV-POS-2026-08-001
- [ ] الدفع: نقداً

---

#### الخطوة 6: التحقق من خصم المخزون — Verify Stock Reduction

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 6 من 10 |
| **الوحدة** | Inventory Module |
| **الإجراء** | التحقق من تقليل المخزون بعد البيع: 500 - 2 = 498 |
| **النتيجة المتوقعة** | Stock = 498, movement log: -2, reason: "POS Sale" |
| **التحقق** | `GET /api/v1/inventory/stock/DRG-AUG-1G` → qty: 498 |

**حركة المخزون المتوقعة:**

| التاريخ | النوع | الكمية | المخزون المتبقي | المرجع |
|---------|-------|--------|----------------|--------|
| 2026-08-20 | استلام | +500 | 500 | PO-2026-08-001 |
| 2026-08-20 | بيع | -2 | 498 | INV-POS-2026-08-001 |

**التحقق التفصيلي:**
- [ ] المخزون الحالي = 498 علبة
- [ ] حركة المخزون مسجلة: -2
- [ ] السبب: "POS Sale"
- [ ] المرجع: INV-POS-2026-08-001
- [ ] لا توجد حركات مكررة

---

#### الخطوة 7: التحقق من القيد المحاسبي للبيع — Verify Sale Accounting Entry

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 7 من 10 |
| **الوحدة** | Accounting Module |
| **الإجراء** | التحقق من القيد المحاسبي التلقائي لعملية البيع |
| **النتيجة المتوقعة** | قيد محاسبي: Debit: Cash 153.90 / Credit: Sales 135.00 + Credit: VAT Payable 18.90 |
| **التحقق** | `GET /api/v1/accounting/entries?invoice=INV-POS-2026-08-001` |

**القيد المحاسبي المتوقع:**

| الحساب | المدين (Debit) | الدائن (Credit) | المرجع |
|--------|---------------|-----------------|--------|
| النقدية — صندوق (Cash) | 153.90 | — | INV-POS-2026-08-001 |
| إيرادات المبيعات (Sales Revenue) | — | 135.00 | INV-POS-2026-08-001 |
| ضريبة القيمة المضافة المستحقة (VAT Payable) | — | 18.90 | INV-POS-2026-08-001 |

**التحقق التفصيلي:**
- [ ] المدين = 153.90 (Cash)
- [ ] الدائن = 135.00 (Sales) + 18.90 (VAT Payable)
- [ ] المدين = الدائن (متوازن)
- [ ] المرجع يحتوي على رقم الفاتورة

---

#### الخطوة 8: إرسال الفاتورة للهيئة — Send Invoice to ETA

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 8 من 10 |
| **الوحدة** | E-Invoicing Module |
| **الإجراء** | إرسال فاتورة البيع إلى الهيئة المصرية للضرائب (ETA) عبر API |
| **النتيجة المتوقعة** | ETA UUID received, status: "Accepted", hash verification passed |
| **التحقق** | `GET /api/v1/e-invoicing/submissions/INV-POS-2026-08-001` → eta_status: "accepted" |

**بيانات الفاتورة الإلكترونية (ETAF):**

```json
{
  "internal_invoice_id": "INV-POS-2026-08-001",
  "eta_uuid": "uuid-generated-by-eta",
  "invoice_date": "2026-08-20",
  "invoice_type": "S",
  "buyer_type": "B",
  "buyer_tax_number": "123456789",
  "items": [
    {
      "item_code": "DRG-AUG-1G",
      "description": "Augmentin 1g Tablets",
      "quantity": 2,
      "unit_price": 67.50,
      "vat_amount": 18.90,
      "total": 153.90
    }
  ],
  "total_amount": 153.90,
  "vat_total": 18.90,
  "currency": "EGP"
}
```

**التحقق التفصيلي:**
- [ ] تم إرسال الفاتورة بنجاح إلى ETA
- [ ] تم استلام UUID من ETA
- [ ] الحالة: "Accepted"
- [ ] التوقيع الرقمي صحيح
- [ ] لا توجد أخطاء في التحقق من ETA

---

#### الخطوة 9: التحليل الذكي بعد 30 يوم — AI Analysis

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 9 من 10 |
| **الوحدة** | AI Analytics Module |
| **الإجراء** | بعد 30 يوم من البيع، تشغيل تحليل AI لأداء الدواء |
| **النتيجة المتوقعة** | تقرير: متوسط البيع اليومي، معدل الدوران، توقع الطلب القادم |
| **التحقق** | `GET /api/v1/ai/analysis/drug/DRG-AUG-1G?period=30d` |

**التحليل المتوقع (بعد 30 يوم بيانات تجريبية):**

| المؤشر | القيمة المتوقعة |
|--------|-----------------|
| إجمالي البيع (30 يوم) | ~120 علبة |
| المتوسط اليومي | ~4 علبات / يوم |
| معدل الدوران | 120 / 498 = 24.1% |
| أيام المخزون المتبقية | ~124 يوم |
| نقطة إعادة الطلب | ~60 علبة |
| توقع الطلب (30 يوم قادم) | ~130 علبة |

**التحقق التفصيلي:**
- [ ] التقرير يحتوي على جميع المؤشرات
- [ ] البيانات محدثة حتى تاريخ التشغيل
- [ ] التوصيات منطقية
- [ ] لا توجد بيانات مفقودة

---

#### الخطوة 10: تنبيه انتهاء الصلاحية — Expiry Alert Simulation

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 10 من 10 |
| **الوحدة** | Expiry Management Module |
| **الإجراء** | محاكاة تنبيه انتهاء صلاحية الدواء قبل 90 يوم |
| **النتيجة المتوقعة** | Alert generated, notification sent to pharmacy manager |
| **التحقق** | `GET /api/v1/pharmacy/expiry-alerts?item=DRG-AUG-1G` |

**سيناريو التنبيه:**

| التاريخ المحاكي | المدة المتبقية | نوع التنبيه | الإجراء المطلوب |
|----------------|----------------|-------------|----------------|
| 2028-04-01 | 90 يوم | ⚠️ تحذير | مراجعة الكمية |
| 2028-05-01 | 60 يوم | 🔶 تنبيه عاجل | خفض السعر أو التحويل |
| 2028-06-01 | 30 يوم | 🔴 تنبيه حرج | إيقاف البيع أو التخلص |
| 2028-06-30 | 0 يوم | ⛔ منتهي الصلاحية | حظر البيع نهائياً |

**التحقق التفصيلي:**
- [ ] تم إنشاء تنبيه في 90 يوم قبل الانتهاء
- [ ] الإشعار تم إرساله لمسؤول الصيدلية
- [ ] تم إنشاء تنبيه عند 60 يوم
- [ ] تم إنشاء تنبيه حرج عند 30 يوم
- [ ] عند تاريخ الانتهاء: البيع محظور 100%

---

### سيناريو خاص: المادة المخدرة — Controlled Substance (Narcotic)

**الدواء:** Tramadol 50mg (ترامادول)
**الكود:** DRG-TRM-50G
**الفئة:** Controlled Substance — Schedule III

---

#### الخطوة S1: محاكاة بيع بدون وصفة طبية — Sell Without Prescription → REJECT

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | S1 من 4 |
| **الوحدة** | POS + Controlled Substance Module |
| **الإجراء** | محاكاة بيع Tramadol عبر POS بدون وصفة طبية |
| **النتيجة المتوقعة** | REJECTED — "Prescription required for controlled substance" |
| **التحقق** | `POST /api/v1/pos/sale` → status: 400, error_code: "CONTROLLED_NO_RX" |

**بيانات المحاولة:**

```json
{
  "item_id": "DRG-TRM-50G",
  "quantity": 1,
  "prescription_id": null,
  "prescription_number": null,
  "doctor_name": null
}
```

**التحقق التفصيلي:**
- [ ] تم رفض العملية
- [ ] رسالة الخطأ واضحة: "وصفة طبية مطلوبة"
- [ ] لم يتم خصم المخزون
- [ ] لم يتم إنشاء فاتورة
- [ ] تم تسجيل محاولة البيع في السجل (audit log)

---

#### الخطوة S2: إدخال الوصفة الطبية — Enter Prescription → ALLOW

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | S2 من 4 |
| **الوحدة** | POS + Prescription Module |
| **الإجراء** | إدخال وصفة طبية صحيحة مع اسم الطبيب → البيع مسموح |
| **النتيجة المتوقعة** | ALLOWED — Sale completed successfully |
| **التحقق** | `POST /api/v1/pos/sale` → status: 200, sale_id: generated |

**بيانات الوصفة:**

```json
{
  "item_id": "DRG-TRM-50G",
  "quantity": 1,
  "prescription": {
    "prescription_number": "RX-2026-08-1234",
    "doctor_name": "Dr. Mohamed Hassan",
    "doctor_license": "MOH-2024-5678",
    "hospital": "Cairo University Hospital",
    "date": "2026-08-20",
    "quantity_prescribed": 30,
    "valid_until": "2026-09-20"
  }
}
```

**التحقق التفصيلي:**
- [ ] تم قبول العملية
- [ ] رقم الوصفة مسجل
- [ ] اسم الطبيب مسجل
- [ ] رقم الترخيص مسجل
- [ ] تم خصم المخزون
- [ ] تم إنشاء فاتورة

---

#### الخطوة S3: التحقق من السجل الخاص — Verify Special Log

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | S3 من 4 |
| **الوحدة** | Controlled Substance Log Module |
| **الإجراء** | التحقق من تسجيل عملية البيع في السجل الخاص للمواد المخدرة |
| **النتيجة المتوقعة** | Log entry with all prescription details, pharmacist signature, timestamp |
| **التحقق** | `GET /api/v1/pharmacy/controlled-log?drug=DRG-TRM-50G` |

**بيانات السجل المتوقعة:**

| الحقل | القيمة |
|-------|--------|
| التاريخ والوقت | 2026-08-20 HH:MM:SS |
| الدواء | Tramadol 50mg |
| رقم التشغيلة | BN-2026-08 |
| الكمية المباعة | 1 |
| رقم الوصفة | RX-2026-08-1234 |
| اسم الطبيب | Dr. Mohamed Hassan |
| رقم الترخيص | MOH-2024-5678 |
| الصيدلي | PH-012 |
| التوقيع الرقمي | Digital signature hash |
| المخزون المتبقي | 499 |

**التحقق التفصيلي:**
- [ ] السجل موجود في controlled_substance_log
- [ ] جميع الحقول مملوءة
- [ ] التوقيع الرقمي مسجل
- [ ] لا يمكن حذف أو تعديل السجل (immutable)

---

#### الخطوة S4: التقرير الشهري — Monthly Controlled Substance Report

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | S4 من 4 |
| **الوحدة** | Reporting + Controlled Substance Module |
| **الإجراء** | توليد التقرير الشهري للمواد المخدرة |
| **النتيجة المتوقعة** | Monthly report with total sales, remaining stock, all transactions |
| **التحقق** | `GET /api/v1/reports/controlled-substances/2026-08` |

**هيكل التقرير:**

```json
{
  "report_id": "CSR-2026-08",
  "period": "2026-08-01 to 2026-08-31",
  "controlled_items": [
    {
      "item_id": "DRG-TRM-50G",
      "opening_stock": 0,
      "received": 500,
      "sold": 1,
      "closing_stock": 499,
      "transactions": [
        {
          "date": "2026-08-20",
          "type": "Sale",
          "quantity": 1,
          "prescription": "RX-2026-08-1234",
          "doctor": "Dr. Mohamed Hassan"
        }
      ]
    }
  ]
}
```

**التحقق التفصيلي:**
- [ ] التقرير يتضمن جميع المواد المخدرة
- [ ] الأرصدة ابتدائية ونهائية صحيحة
- [ ] جميع المعاملات مدرجة
- [ ] يمكن تصديره كـ PDF
- [ ] يمكن إرساله للجهة Regulatory Authority

---

## 3. القطاع 2: مطعم — Restaurant/Cafe

### سيناريو E2E: "دورة الطلب من المطبخ إلى الفاتورة"

**البيانات الأساسية:**

| العنصر | القيمة |
|--------|--------|
| الوصفة | شاورما (Shawarma) |
| المكونات | 200g دجاج + 50g عيش + 30g صوص + 10g مخلل |
| تكلفة الوصفة | 28 EGP |
| سعر البيع | 45 EGP |
| المشروب | Pepsi — 10 EGP |
| البطاطس | French Fries — 20 EGP |
| رسوم التوصيل | 15 EGP |
| ضريبة القيمة المضافة | 14% |

---

#### الخطوة 1: إنشاء الوصفة — Create Recipe

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 1 من 8 |
| **الوحدة** | Recipe Management Module |
| **الإجراء** | إنشاء وصفة "Shawarma" مع المكونات والكميات |
| **النتيجة المتوقعة** | Recipe ID: REC-SHAW-001, cost: 28 EGP, margin: 37.8% |
| **التحقق** | `GET /api/v1/recipes/REC-SHAW-001` → cost: 28.00 |

**تفاصيل الوصفة:**

```json
{
  "recipe_id": "REC-SHAW-001",
  "name": "Shawarma",
  "category": "Main Course",
  "servings": 1,
  "ingredients": [
    {
      "item_id": "ING-CHKN-001",
      "name": "Chicken Breast",
      "quantity": 200,
      "unit": "gram",
      "unit_cost": 0.10,
      "line_cost": 20.00
    },
    {
      "item_id": "ING-BRAD-001",
      "name": "Pita Bread",
      "quantity": 50,
      "unit": "gram",
      "unit_cost": 0.08,
      "line_cost": 4.00
    },
    {
      "item_id": "ING-SUCE-001",
      "name": "Shawarma Sauce",
      "quantity": 30,
      "unit": "gram",
      "unit_cost": 0.08,
      "line_cost": 2.40
    },
    {
      "item_id": "ING-PCKL-001",
      "name": "Pickles",
      "quantity": 10,
      "unit": "gram",
      "unit_cost": 0.16,
      "line_cost": 1.60
    }
  ],
  "total_cost": 28.00,
  "selling_price": 45.00,
  "profit_margin": "37.8%"
}
```

**حساب التكلفة:**

```
Chicken:  200g × 0.10 EGP/g = 20.00 EGP
Bread:     50g × 0.08 EGP/g =  4.00 EGP
Sauce:     30g × 0.08 EGP/g =  2.40 EGP
Pickles:   10g × 0.16 EGP/g =  1.60 EGP
─────────────────────────────────────────────
Total Cost:                   28.00 EGP
Selling Price:                45.00 EGP
Gross Profit:                 17.00 EGP
Gross Margin:                 37.8%
```

**التحقق التفصيلي:**
- [ ] الوصفة REC-SHAW-001 منشأة
- [ ] 4 مكونات مسجلة
- [ ] التكلفة الإجمالية = 28.00 EGP
- [ ] سعر البيع = 45.00 EGP
- [ ] هامش الربح = 37.8%

---

#### الخطوة 2: طلب عبر POS — POS Order on Table #5

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 2 من 8 |
| **الوحدة** | POS + Order Management Module |
| **الإجراء** | تسجيل طلب على الطاولة رقم 5: 2 شاورما + 2 بيبسي + 1 بطاطس |
| **النتيجة المتوقعة** | Order ORD-2026-08-001, subtotal: 130 EGP, VAT: 18.20 EGP, total: 148.20 EGP |
| **التحقق** | `GET /api/v1/orders/ORD-2026-08-001` → total: 148.20 |

**حساب الطلب:**

```
2 × Shawarma:    2 × 45.00  =  90.00 EGP
2 × Pepsi:       2 × 10.00  =  20.00 EGP
1 × Fries:       1 × 20.00  =  20.00 EGP
─────────────────────────────────────────────
Subtotal:                     130.00 EGP
VAT (14%):                     18.20 EGP
Total:                        148.20 EGP
```

**بيانات الطلب:**

```json
{
  "order_id": "ORD-2026-08-001",
  "table_number": 5,
  "waiter_id": "WTR-003",
  "items": [
    {
      "recipe_id": "REC-SHAW-001",
      "name": "Shawarma",
      "quantity": 2,
      "unit_price": 45.00,
      "line_total": 90.00
    },
    {
      "item_id": "BEV-PEPS-001",
      "name": "Pepsi",
      "quantity": 2,
      "unit_price": 10.00,
      "line_total": 20.00
    },
    {
      "item_id": "SDE-FRYS-001",
      "name": "French Fries",
      "quantity": 1,
      "unit_price": 20.00,
      "line_total": 20.00
    }
  ],
  "subtotal": 130.00,
  "vat": 18.20,
  "total": 148.20,
  "status": "open"
}
```

**التحقق التفصيلي:**
- [ ] رقم الطلب ORD-2026-08-001
- [ ] الطاولة رقم 5
- [ ] 2 شاورما + 2 بيبسي + 1 بطاطس
- [ ] المجموع الفرعي = 130.00 EGP
- [ ] الضريبة = 18.20 EGP
- [ ] الإجمالي = 148.20 EGP

---

#### الخطوة 3: خصم المكونات تلقائياً — Auto Deduct Ingredients

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 3 من 8 |
| **الوحدة** | Inventory + Recipe Module |
| **الإجراء** | خصم المكونات تلقائياً من المخزون بعد تأكيد الطلب |
| **النتيجة المتوقعة** | Stock deducted: 400g chicken + 100g bread + 60g sauce + 20g pickles |
| **التحقق** | `GET /api/v1/inventory/stock/ING-CHKN-001` → verify deduction |

**المكونات المُخصمة (لـ 2 شاورما):**

| المكون | الكمية لكل وحدة | الكمية المطلوبة (×2) | المخزون قبل | المخزون بعد |
|--------|-----------------|---------------------|-------------|-------------|
| دجاج | 200g | 400g | 5000g | 4600g |
| عيش | 50g | 100g | 2000g | 1900g |
| صوص | 30g | 60g | 1500g | 1440g |
| مخلل | 10g | 20g | 800g | 780g |

**التحقق التفصيلي:**
- [ ] تم خصم 400g دجاج من المخزون
- [ ] تم خصم 100g عيش من المخزون
- [ ] تم خصم 60g صوص من المخزون
- [ ] تم خصم 20g مخلل من المخزون
- [ ] حركات المخزون مسجلة بالمرجع ORD-2026-08-001

---

#### الخطوة 4: طلب توصيل عبر التطبيق — Add Delivery Order

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 4 من 8 |
| **الوحدة** | Online Ordering + Delivery Module |
| **الإجراء** | إضافة طلب توصيل عبر تطبيق الهاتف مع رسوم توصيل 15 EGP |
| **النتيجة المتوقعة** | Delivery order DEL-2026-08-001, delivery_fee: 15 EGP |
| **التحقق** | `GET /api/v1/orders/DEL-2026-08-001` → type: "delivery", fee: 15.00 |

**بيانات طلب التوصيل:**

```json
{
  "order_id": "DEL-2026-08-001",
  "order_type": "delivery",
  "channel": "mobile_app",
  "customer": {
    "name": "Ahmed Ali",
    "phone": "+201234567890",
    "address": "15 Street, Maadi, Cairo"
  },
  "items": [
    {
      "recipe_id": "REC-SHAW-001",
      "quantity": 3,
      "unit_price": 45.00,
      "line_total": 135.00
    },
    {
      "item_id": "BEV-PEPS-001",
      "quantity": 3,
      "unit_price": 10.00,
      "line_total": 30.00
    }
  ],
  "subtotal": 165.00,
  "vat": 23.10,
  "delivery_fee": 15.00,
  "total": 203.10
}
```

**حساب التوصيل:**

```
Shawarma: 3 × 45.00  = 135.00 EGP
Pepsi:    3 × 10.00  =  30.00 EGP
─────────────────────────────────────
Subtotal:              165.00 EGP
VAT (14%):              23.10 EGP
Delivery Fee:           15.00 EGP
Total:                 203.10 EGP
```

**التحقق التفصيلي:**
- [ ] رقم الطلب: DEL-2026-08-001
- [ ] النوع: توصيل
- [ ] القناة: تطبيق الهاتف
- [ ] عنوان التوصيل مسجل
- [ ] رسوم التوصيل = 15.00 EGP
- [ ] الإجمالي = 203.10 EGP

---

#### الخطوة 5: تقرير إغلاق الوردية — Shift Close Report

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 5 من 8 |
| **الوحدة** | POS + Shift Management Module |
| **الإجراء** | إغلاق وردية الكاشير وإنشاء التقرير |
| **النتيجة المتوقعة** | Shift report with sales total, VAT, cash count |
| **التحقق** | `GET /api/v1/pos/shifts/SHIFT-2026-08-001` |

**بيانات تقرير الوردية:**

```json
{
  "shift_id": "SHIFT-2026-08-001",
  "cashier_id": "CSH-002",
  "start_time": "2026-08-20 10:00:00",
  "end_time": "2026-08-20 18:00:00",
  "sales_summary": {
    "total_orders": 45,
    "dine_in_orders": 30,
    "delivery_orders": 15,
    "gross_sales": 4500.00,
    "vat_collected": 630.00,
    "discounts": 150.00,
    "net_sales": 4350.00,
    "delivery_fees": 225.00,
    "grand_total": 4575.00
  },
  "payment_summary": {
    "cash": 2000.00,
    "card": 1500.00,
    "mobile_wallet": 1075.00,
    "total": 4575.00
  },
  "cash_count": {
    "expected": 2000.00,
    "actual": 2000.00,
    "difference": 0.00
  }
}
```

**التحقق التفصيلي:**
- [ ] إجمالي الطلبات = 45
- [ ] المبيعات الإجمالية = 4,500.00 EGP
- [ ] ضريبة القيمة المضافة = 630.00 EGP
- [ ] الخصومات = 150.00 EGP
- [ ] المبيعات الصافية = 4,350.00 EGP
- [ ] رسوم التوصيل = 225.00 EGP
- [ ] إجمالي المستحق = 4,575.00 EGP
- [ ] المدفوعات: نقداً 2,000 + كرت 1,500 + محفظة 1,075
- [ ] التسوية: الفرق = 0.00

---

#### الخطوة 6: حساب بقشيش النادل — Waiter Tip Calculation

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 6 من 8 |
| **الوحدة** | Tips Management Module |
| **الإجراء** | حساب بقشيش النادل WTR-003 من الوردية |
| **النتيجة المتوقعة** | Tips: 135.00 EGP (calculated from card payments) |
| **التحقق** | `GET /api/v1/pos/tips?waiter=WTR-003&shift=SHIFT-2026-08-001` |

**حساب البقشيش:**

```json
{
  "waiter_id": "WTR-003",
  "waiter_name": "Mohamed Salem",
  "shift_id": "SHIFT-2026-08-001",
  "tables_served": 12,
  "total_sales": 1800.00,
  "tips_received": {
    "cash_tips": 80.00,
    "card_tips": 55.00,
    "total_tips": 135.00
  },
  "tip_percentage": "7.5%"
}
```

**التحقق التفصيلي:**
- [ ] النادل: Mohamed Salem (WTR-003)
- [ ] عدد الطاولات المخدومة = 12
- [ ] إجمالي المبيعات = 1,800.00 EGP
- [ ] بقشيش نقداً = 80.00 EGP
- [ ] بقشيش كرت = 55.00 EGP
- [ ] إجمالي البقشيش = 135.00 EGP
- [ ] نسبة البقشيش = 7.5%

---

#### الخطوة 7: التحليل الأسبوعي — AI Weekly Analysis

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 7 من 8 |
| **الوحدة** | AI Analytics Module |
| **الإجراء** | تحليل AI لأداء المطعم للأسبوع |
| **النتيجة المتوقعة** | Weekly report with top items, peak hours, waste analysis |
| **التحقق** | `GET /api/v1/ai/analysis/restaurant/weekly?week=2026-W33` |

**التحليل الأسبوعي المتوقع:**

```json
{
  "period": "2026-W33 (Aug 14-20)",
  "top_selling_items": [
    {"item": "Shawarma", "quantity": 350, "revenue": 15750.00},
    {"item": "Pepsi", "quantity": 280, "revenue": 2800.00},
    {"item": "French Fries", "quantity": 150, "revenue": 3000.00}
  ],
  "peak_hours": [
    {"hour": "13:00-14:00", "orders": 45, "revenue": 6750.00},
    {"hour": "20:00-21:00", "orders": 40, "revenue": 6000.00}
  ],
  "waste_analysis": {
    "total_waste_cost": 280.00,
    "waste_percentage": "3.2%",
    "top_wasted_item": "Chicken Breast",
    "recommendation": "Reduce chicken prep by 10% on Sundays"
  },
  "revenue_trend": "+12% vs last week",
  "customer_satisfaction": "4.3/5.0"
}
```

**التحقق التفصيلي:**
- [ ] التقرير يحتوي على أعلى المبيعات
- [ ] ساعات الذروة محددة
- [ ] تحليل الهالك موجود
- [ ] التوصيات ذكية وقابلة للتنفيذ
- [ ] الاتجاه العام محسوب

---

#### الخطوة 8: تنبيه مخزون منخفض — Low Stock Alert for Chicken

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 8 من 8 |
| **الوحدة** | Inventory Alerts Module |
| **الإجراء** | تنبيه تلقائي عند انخفاض مخزون الدجاج عن الحد الأدنى |
| **النتيجة المتوقعة** | Alert: "Chicken stock below minimum (2kg remaining, min: 5kg)" |
| **التحقق** | `GET /api/v1/inventory/alerts?category=chicken&status=active` |

**بيانات التنبيه:**

```json
{
  "alert_id": "ALT-2026-08-001",
  "alert_type": "low_stock",
  "severity": "high",
  "item_id": "ING-CHKN-001",
  "item_name": "Chicken Breast",
  "current_stock": 2000,
  "minimum_stock": 5000,
  "unit": "gram",
  "days_until_stockout": 2.5,
  "suggested_reorder": 10000,
  "supplier": "Fresh Poultry Co.",
  "supplier_phone": "+201001234567"
}
```

**التحقق التفصيلي:**
- [ ] تم إنشاء تنبيه
- [ ] الشدة: عالية (high)
- [ ] المخزون الحالي = 2,000g
- [ ] الحد الأدنى = 5,000g
- [ ] أيام حتى النفاد = 2.5 يوم
- [ ] كمية إعادة الطلب المقترحة = 10,000g
- [ ] بيانات المورد متاحة

---

## 4. القطاع 3: عيادة — Medical Clinic

### سيناريو E2E: "رحلة المريض من الموعد إلى الفاتورة"

**البيانات الأساسية:**

| العنصر | القيمة |
|--------|--------|
| المريض | Ahmed Ibrahim |
| كود المريض | PAT-2026-001 |
| الطبيبة | Dr. Sara (Dental) |
| كود الطبيبة | DOC-SARA-001 |
| نوع الموعد | أسنان (Dental) |
| التاريخ | 2026-08-20 10:00 AM |
| الحساسية | بنسلين (Penicillin) |
| التشخيص | حشوة تكوينية — سن 14 |
| الوصفة | Amoxicillin 500mg |
| تكلفة الاستشارة | 300 EGP |
| تكلفة الحشوة | 800 EGP |
| شركة التأمين | Misr Insurance |
| نسبة التغطية | 80% |

---

#### الخطوة 1: حجز موعد — Book Appointment

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 1 من 8 |
| **الوحدة** | Appointment + SMS Module |
| **الإجراء** | حجز موعد للمريض "Ahmed" مع Dr. Sara (أسنان) في 20 أغسطس 10:00 صباحاً مع تذكير SMS |
| **النتيجة المتوقعة** | Appointment APT-2026-08-001, SMS reminder scheduled |
| **التحقق** | `GET /api/v1/appointments/APT-2026-08-001` → status: "confirmed" |

**بيانات الموعد:**

```json
{
  "appointment_id": "APT-2026-08-001",
  "patient_id": "PAT-2026-001",
  "patient_name": "Ahmed Ibrahim",
  "patient_phone": "+201123456789",
  "doctor_id": "DOC-SARA-001",
  "doctor_name": "Dr. Sara Hassan",
  "specialty": "Dental",
  "date": "2026-08-20",
  "time": "10:00",
  "duration_minutes": 30,
  "status": "confirmed",
  "sms_reminder": {
    "scheduled": true,
    "send_at": "2026-08-19 10:00:00",
    "message": "Reminder: your appointment tomorrow at 10:00 AM with Dr. Sara"
  }
}
```

**التحقق التفصيلي:**
- [ ] رقم الموعد: APT-2026-08-001
- [ ] المريض: Ahmed Ibrahim
- [ ] الطبيبة: Dr. Sara Hassan
- [ ] التاريخ والوقت: 2026-08-20 10:00
- [ ] المدة: 30 دقيقة
- [ ] الحالة: مؤكد (confirmed)
- [ ] تذكير SMS مجدول

---

#### الخطوة 2: فتح ملف المريض — Open Patient File

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 2 من 8 |
| **الوحدة** | Patient Management Module |
| **الإجراء** | فتح ملف المريض: التاريخ الطبي، الحساسيات: بنسلين |
| **النتيجة المتوقعة** | Patient file loaded with history and allergy info |
| **التحقق** | `GET /api/v1/patients/PAT-2026-001/medical-record` |

**ملف المريض:**

```json
{
  "patient_id": "PAT-2026-001",
  "name": "Ahmed Ibrahim",
  "age": 35,
  "gender": "Male",
  "blood_type": "O+",
  "allergies": [
    {
      "allergen": "Penicillin",
      "severity": "severe",
      "reaction": "Anaphylaxis",
      "verified_date": "2024-03-15"
    }
  ],
  "medical_history": [
    {
      "date": "2025-12-10",
      "doctor": "Dr. Sara Hassan",
      "diagnosis": "Dental caries — Tooth 26",
      "treatment": "Root canal",
      "notes": "No complications"
    },
    {
      "date": "2025-06-20",
      "doctor": "Dr. Ahmed Ali",
      "diagnosis": "Hypertension",
      "treatment": "Lisinopril 10mg",
      "notes": "Controlled"
    }
  ],
  "current_medications": [
    "Lisinopril 10mg — daily",
    "Aspirin 75mg — daily"
  ],
  "insurance": {
    "provider": "Misr Insurance",
    "policy_number": "MI-2026-45678",
    "coverage_percentage": 80,
    "valid_until": "2026-12-31"
  }
}
```

**التحقق التفصيلي:**
- [ ] ملف المريض مفتوح
- [ ] الحساسية مسجلة: بنسلين (severe)
- [ ] التاريخ الطبي موجود
- [ ] الأدوية الحالية مسجلة
- [ ] بيانات التأمين محدثة

---

#### الخطوة 3: تسجيل التشخيص والوصفة — Doctor Records Diagnosis

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 3 من 8 |
| **الوحدة** | Clinical + Prescription Module |
| **الإجراء** | تسجيل التشخيص: "حشوة تكوينية — سن 14" + وصفة "Amoxicillin 500mg" → تحذير حساسية |
| **النتيجة المتوقعة** | Diagnosis recorded + ALLERGY WARNING triggered |
| **التحقق** | `POST /api/v1/clinical/consultations` → allergy_warning: true |

**بيانات التشخيص:**

```json
{
  "consultation_id": "CON-2026-08-001",
  "patient_id": "PAT-2026-001",
  "doctor_id": "DOC-SARA-001",
  "appointment_id": "APT-2026-08-001",
  "diagnosis": {
    "primary": "Composite filling — Tooth 14",
    "icd_code": "K02.0",
    "notes": "Small cavity on tooth 14, no pulp involvement"
  },
  "procedures": [
    {
      "code": "D2391",
      "description": "Composite filling — one surface",
      "tooth": 14,
      "fee": 800.00
    }
  ],
  "prescriptions": [
    {
      "drug_id": "DRG-AMX-500",
      "drug_name": "Amoxicillin 500mg",
      "dosage": "500mg",
      "frequency": "Three times daily",
      "duration": "7 days",
      "quantity": 21,
      "allergy_warning": true,
      "allergy_detail": "Patient allergic to Penicillin — SEVERE"
    }
  ],
  "consultation_fee": 300.00
}
```

**تنبيه الحساسية:**

```
+================================================================+
| ALLERGY WARNING — CRITICAL                                     |
|                                                                  |
| Patient: Ahmed Ibrahim (PAT-2026-001)                            |
| Allergy: Penicillin (SEVERE — Anaphylaxis)                      |
|                                                                  |
| Prescribed Drug: Amoxicillin 500mg                               |
| Drug Class: PENICILLIN ANTIBIOTIC                                |
|                                                                  |
| Amoxicillin is a penicillin-class antibiotic.                    |
| Prescribing this drug to this patient is CONTRAINDICATED.        |
| Doctor must select an alternative antibiotic.                    |
+================================================================+
```

**التحقق التفصيلي:**
- [ ] تم تسجيل التشخيص
- [ ] تم تسجيل إجراء الحشوة (800 EGP)
- [ ] تم attempts لوصف Amoxicillin
- [ ] تم إطلاق تحذير الحساسية
- [ ] الطبيبة تم إبلاغها عن الحساسية
- [ ] يجب اختيار بديل: Azithromycin أو Erythromycin

---

#### الخطوة 4: إنشاء الفاتورة — Invoice

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 4 من 8 |
| **الوحدة** | Billing Module |
| **الإجراء** | إنشاء فاتورة: استشارة 300 + حشوة 800 = 1,100 EGP |
| **النتيجة المتوقعة** | Invoice INV-CLN-2026-001, total: 1,100 EGP |
| **التحقق** | `GET /api/v1/billing/invoices/INV-CLN-2026-001` → total: 1100.00 |

**بيانات الفاتورة:**

```json
{
  "invoice_id": "INV-CLN-2026-001",
  "patient_id": "PAT-2026-001",
  "doctor_id": "DOC-SARA-001",
  "items": [
    {
      "code": "CONSULT-DENTAL",
      "description": "Dental Consultation",
      "fee": 300.00
    },
    {
      "code": "D2391",
      "description": "Composite Filling — Tooth 14",
      "fee": 800.00
    }
  ],
  "subtotal": 1100.00,
  "vat_rate": 0.0,
  "vat_amount": 0.00,
  "total": 1100.00,
  "status": "unpaid"
}
```

**التحقق التفصيلي:**
- [ ] رقم الفاتورة: INV-CLN-2026-001
- [ ] الاستشارة: 300 EGP
- [ ] الحشوة: 800 EGP
- [ ] الإجمالي: 1,100 EGP
- [ ] لا ضريبة (خدمات طبية معفاة)
- [ ] الحالة: غير مدفوعة

---

#### الخطوة 5: التأمين — Insurance Coverage

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 5 من 8 |
| **الوحدة** | Insurance Module |
| **الإجراء** | خصم تأمين "Misr Insurance" بنسبة 80% → المريض يدفع 220، التأمين يدفع 880 |
| **النتيجة المتوقعة** | Insurance claim: 880 EGP, Patient copay: 220 EGP |
| **التحقق** | `GET /api/v1/billing/invoices/INV-CLN-2026-001` → insurance_paid: 880, patient_paid: 220 |

**حساب التأمين:**

```
Total Invoice:                1,100.00 EGP
Insurance Coverage:           80%
─────────────────────────────────────────────
Insurance Pays:    1,100 x 0.80 = 880.00 EGP
Patient Pays:      1,100 x 0.20 = 220.00 EGP
```

**بيانات مطالبة التأمين:**

```json
{
  "claim_id": "CLM-2026-08-001",
  "invoice_id": "INV-CLN-2026-001",
  "patient_id": "PAT-2026-001",
  "insurance_provider": "Misr Insurance",
  "policy_number": "MI-2026-45678",
  "coverage_percentage": 80,
  "total_amount": 1100.00,
  "insurance_amount": 880.00,
  "patient_copay": 220.00,
  "status": "submitted",
  "submitted_date": "2026-08-20"
}
```

**التحقق التفصيلي:**
- [ ] مطالبة التأمين: CLM-2026-08-001
- [ ] نسبة التغطية: 80%
- [ ] مبلغ التأمين: 880.00 EGP
- [ ] مبلغ المريض: 220.00 EGP
- [ ] الحالة: مرسلة (submitted)
- [ ] لا يوجد احتساب مزدوج

---

#### الخطوة 6: القيد المحاسبي — Accounting Entry

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 6 من 8 |
| **الوحدة** | Accounting Module |
| **الإجراء** | إنشاء القيد المحاسبي للفاتورة ومطالبة التأمين |
| **النتيجة المتوقعة** | Accounting entries for receivable, insurance, and revenue |
| **التحقق** | `GET /api/v1/accounting/entries?invoice=INV-CLN-2026-001` |

**القيد المحاسبي المتوقع:**

| الحساب | المدين (Debit) | الدائن (Credit) | المرجع |
|--------|---------------|-----------------|--------|
| حساب المريض المستحق (Patient Receivable) | 220.00 | — | INV-CLN-2026-001 |
| حساب التأمين المستحق (Insurance Receivable) | 880.00 | — | INV-CLN-2026-001 |
| إيرادات الاستشارات (Consultation Revenue) | — | 300.00 | INV-CLN-2026-001 |
| إجراءات طبية (Procedures Revenue) | — | 800.00 | INV-CLN-2026-001 |

**التحقق التفصيلي:**
- [ ] المدين: حساب المريض = 220.00
- [ ] المدين: حساب التأمين = 880.00
- [ ] الدائن: إيرادات الاستشارات = 300.00
- [ ] الدائن: إجراءات طبية = 800.00
- [ ] المدين الإجمالي = 1,100.00 = الدائن الإجمالي
- [ ] القيد متوازن

---

#### الخطوة 7: خصم المخزون — Stock Deduction for Materials

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 7 من 8 |
| **الوحدة** | Inventory Module |
| **الإجراء** | خصم مواد الحشوة المستخدمة في العلاج |
| **النتيجة المتوقعة** | Materials deducted from dental supplies inventory |
| **التحقق** | `GET /api/v1/inventory/stock?category=dental_materials` |

**المواد المُخصمة:**

| المادة | الكمية المستخدمة | المخزون قبل | المخزون بعد |
|--------|------------------|-------------|-------------|
| Composite Resin | 1 capsule | 45 capsules | 44 capsules |
| Etchant Gel | 1ml | 30 tubes | 29 tubes |
| Bonding Agent | 1 drop | 25 bottles | 24 bottles |
| Cotton Rolls | 5 pcs | 500 pcs | 495 pcs |
| Anesthesia (Lidocaine) | 1 cartridge | 100 cartridges | 99 cartridges |

**التحقق التفصيلي:**
- [ ] تم خصم جميع المواد المستخدمة
- [ ] حركات المخزون مسجلة
- [ ] المرجع: CON-2026-08-001

---

#### الخطوة 8: التحليل الشهري — AI Monthly Analysis

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 8 من 8 |
| **الوحدة** | AI Analytics Module |
| **الإجراء** | تحليل AI لأداء العيادة للشهر |
| **النتيجة المتوقعة** | Monthly report with revenue, patient stats, doctor performance |
| **التحقق** | `GET /api/v1/ai/analysis/clinic/monthly?month=2026-08` |

**التحليل الشهري:**

```json
{
  "period": "August 2026",
  "total_patients": 120,
  "new_patients": 35,
  "returning_patients": 85,
  "total_appointments": 150,
  "completed_appointments": 140,
  "no_shows": 10,
  "no_show_rate": "6.7%",
  "revenue": {
    "consultations": 36000.00,
    "procedures": 96000.00,
    "total": 132000.00
  },
  "insurance_claims": {
    "total_submitted": 85000.00,
    "total_approved": 82000.00,
    "approval_rate": "96.5%"
  },
  "doctor_performance": [
    {
      "doctor": "Dr. Sara Hassan",
      "patients": 60,
      "revenue": 66000.00,
      "avg_rating": 4.8
    }
  ],
  "ai_recommendations": [
    "Reduce no-show rate by sending SMS 2 hours before appointment",
    "Most common procedure: Composite filling — consider bulk material purchase"
  ]
}
```

**التحقق التفصيلي:**
- [ ] إجمالي المرضى = 120
- [ ] المرضى الجدد = 35
- [ ] معدل عدم الحضور = 6.7%
- [ ] الإيرادات = 132,000.00 EGP
- [ ] معدل موافقة التأمين = 96.5%
- [ ] التوصيات منطقية وقابلة للتنفيذ

---

## 5. القطاع 4: شركة مقاولات — Construction Company

### سيناريو E2E: "دورة مشروع من العقد للمستخلص"

**البيانات الأساسية:**

| العنصر | القيمة |
|--------|--------|
| المشروع | برج سكني — التجمع الخامس |
| رقم المشروع | PRJ-2026-001 |
| العميل | شركة العقارات المتحدة |
| الميزانية | 50,000,000 EGP |
| المدة | 24 شهر |
| البند الرئيسي | خرسانة — 5,000 م³ × 1,200 EGP = 6,000,000 EGP |
| مقاول باطن | شركة الإنشاءات الحديثة |

---

#### الخطوة 1: إنشاء مشروع — Create Project

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 1 من 9 |
| **الوحدة** | Project Management Module |
| **الإجراء** | إنشاء مشروع "برج سكني — التجمع الخامس" بميزانية 50M EGP |
| **النتيجة المتوقعة** | Project PRJ-2026-001 + WBS |
| **التحقق** | `GET /api/v1/projects/PRJ-2026-001` |

**بيانات المشروع:**

```json
{
  "project_id": "PRJ-2026-001",
  "name": "برج سكني — التجمع الخامس",
  "name_en": "Residential Tower — Fifth Settlement",
  "client_id": "CLT-001",
  "client_name": "شركة العقارات المتحدة",
  "start_date": "2026-01-15",
  "estimated_end_date": "2028-01-14",
  "budget": 50000000.00,
  "currency": "EGP",
  "status": "in_progress",
  "progress_percentage": 35,
  "manager": "Eng. Mohamed Hassan",
  "wbs": [
    {"code": "1.0", "name": "التصميم والتصاريح", "budget": 1500000, "progress": 100},
    {"code": "2.0", "name": "ال Basement والأساسات", "budget": 8000000, "progress": 100},
    {"code": "3.0", "name": "الهيكل الإنشائي", "budget": 20000000, "progress": 60},
    {"code": "4.0", "name": "التشطيبات", "budget": 15000000, "progress": 0},
    {"code": "5.0", "name": "الiltricals والميكانيكا", "budget": 5500000, "progress": 0}
  ]
}
```

---

#### الخطوة 2: إدخال BOQ — Enter Bill of Quantities

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 2 من 9 |
| **الوحدة** | Project BOQ Module |
| **الإجراء** | إدخال حصر كميات: خرسانة 5,000 م³ × 1,200 EGP = 6M |
| **النتيجة المتوقعة** | BOQ items linked to project |
| **التحقق** | `GET /api/v1/projects/PRJ-2026-001/boq` |

**بيانات BOQ:**

```json
{
  "boq_id": "BOQ-PRJ-001",
  "project_id": "PRJ-2026-001",
  "items": [
    {
      "boq_line": "3.1.1",
      "description": "خرسانة جاهزة C30",
      "unit": "m³",
      "quantity": 5000,
      "unit_price": 1200.00,
      "total": 6000000.00,
      "completed_qty": 3000,
      "completed_value": 3600000.00
    },
    {
      "boq_line": "3.1.2",
      "description": "حديد تسليح 10mm",
      "unit": "ton",
      "quantity": 800,
      "unit_price": 25000.00,
      "total": 20000000.00,
      "completed_qty": 480,
      "completed_value": 12000000.00
    },
    {
      "boq_line": "3.2.1",
      "description": "قوالب خشب",
      "unit": "m²",
      "quantity": 10000,
      "unit_price": 350.00,
      "total": 3500000.00,
      "completed_qty": 6000,
      "completed_value": 2100000.00
    }
  ],
  "total_boq_value": 29500000.00,
  "completed_value": 17700000.00,
  "completion_percentage": 60
}
```

---

#### الخطوة 3: أمر شراء مواد — Purchase Order

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 3 من 9 |
| **الوحدة** | Purchasing Module |
| **الإجراء** | أمر شراء خرسانة جاهزة من "شركة السويس للخرسانة" |
| **النتيجة المتوقعة** | PO-PRJ001-015 linked to project |
| **التحقق** | `GET /api/v1/purchasing/orders/PO-PRJ001-015` |

```json
{
  "po_number": "PO-PRJ001-015",
  "project_id": "PRJ-2026-001",
  "supplier_id": "SUP-045",
  "supplier_name": "شركة السويس للخرسانة",
  "order_date": "2026-08-19",
  "expected_delivery": "2026-08-21",
  "items": [
    {
      "item": "خرسانة جاهزة C30",
      "quantity": 500,
      "unit": "m³",
      "unit_price": 1150.00,
      "total": 575000.00
    }
  ],
  "subtotal": 575000.00,
  "vat": 80500.00,
  "total": 655500.00,
  "status": "approved",
  "project_cost_code": "3.1.1"
}
```

---

#### الخطوة 4: استلام مواد في الموقع — Receive Materials at Site

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 4 من 9 |
| **الوحدة** | Inventory Module |
| **الإجراء** | استلام 500 م³ خرسانة في موقع التجمع الخامس |
| **النتيجة المتوقعة** | Stock at site = 500 m³ |
| **التحقق** | `GET /api/v1/inventory/stock?warehouse=SITE-001` |

**حركة المخزون:**

```json
{
  "stock_movement_id": "SM-PRJ-2026-001",
  "warehouse_id": "SITE-001",
  "warehouse_name": "موقع التجمع الخامس",
  "product": "خرسانة جاهزة C30",
  "movement_type": "in",
  "quantity": 500,
  "unit": "m³",
  "unit_cost": 1150.00,
  "total_cost": 575000.00,
  "reference": "PO-PRJ001-015",
  "project_id": "PRJ-2026-001",
  "received_by": "Eng. Ali Mahmoud",
  "received_at": "2026-08-21T09:30:00Z"
}
```

---

#### الخطوة 5: تسجيل تكلفة المشروع — Record Project Cost

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 5 من 9 |
| **الوحدة** | Accounting Module |
| **الإجراء** | تسجيل تكلفة الخرسانة على المشروع |
| **النتيجة المتوقعة** | Debit: Project costs / Credit: Suppliers |
| **التحقق** | `GET /api/v1/accounting/entries?project=PRJ-2026-001` |

**القيد المحاسبي:**

| الحساب | المدين (Debit) | الدائن (Credit) | المرجع |
|--------|---------------|-----------------|--------|
| تكاليف مشروع — هيكل (Project Cost — Structure) | 575,000.00 | — | PO-PRJ001-015 |
| ضريبة المدخلات (Input VAT) | 80,500.00 | — | PO-PRJ001-015 |
| حساب الموردين (Creditors) | — | 655,500.00 | PO-PRJ001-015 |

---

#### الخطوة 6: مستخلص مقاول باطن — Subcontractor Progress Claim

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 6 من 9 |
| **الوحدة** | Project Billing Module |
| **الإجراء** | إصدار مستخلص #3 من مقاول باطن — 2,500,000 EGP + خصم تأمين 5% + ضريبة 1% |
| **النتيجة المتوقعة** | Progress Claim CLM-PRJ-003 |
| **التحقق** | `GET /api/v1/projects/PRJ-2026-001/claims/CLM-PRJ-003` |

**حساب المستخلص:**

```
قيمة الإنجاز:                     2,500,000.00 EGP
خصم التأمين (5%):                   -125,000.00 EGP
خصم الاحتفاظ (5%):                 -125,000.00 EGP
ضريبة القيمة المضافة (14%):          350,000.00 EGP
───────────────────────────────────────────────────
صافي المستخلص:                     2,600,000.00 EGP
```

```json
{
  "claim_id": "CLM-PRJ-003",
  "project_id": "PRJ-2026-001",
  "subcontractor_id": "SUB-012",
  "subcontractor_name": "شركة الإنشاءات الحديثة",
  "claim_number": 3,
  "period": "2026-07",
  "gross_amount": 2500000.00,
  "insurance_deduction": 125000.00,
  "retention_deduction": 125000.00,
  "vat": 350000.00,
  "net_amount": 2600000.00,
  "status": "approved",
  "approved_by": "Eng. Mohamed Hassan",
  "approved_date": "2026-08-18"
}
```

---

#### الخطوة 7: قيد المستخلص — Accounting Entry

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 7 من 9 |
| **الوحدة** | Accounting Module |
| **الإجراء** | تسجيل القيد المحاسبي للمستخلص |
| **النتيجة المتوقعة** | Balanced entry |

**القيد المحاسبي:**

| الحساب | المدين (Debit) | الدائن (Credit) | المرجع |
|--------|---------------|-----------------|--------|
| أعمال تحت تنفيذ (Work in Progress) | 2,500,000.00 | — | CLM-PRJ-003 |
| موردون فرعيون (Subcontractors) | — | 2,250,000.00 | CLM-PRJ-003 |
| خصم تأمين مستحق (Insurance Payable) | — | 125,000.00 | CLM-PRJ-003 |
| خصم احتفاظ مستحق (Retention Payable) | — | 125,000.00 | CLM-PRJ-003 |

**التحقق:** المدين (2,500,000) = الدائن (2,500,000) ✅

---

#### الخطوة 8: تحليل تقدم المشروع — AI Progress Analysis

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 8 من 9 |
| **الوحدة** | AI Analytics Module |
| **الإجراء** | تحليل AI لتقدم المشروع ومwarts التكلفة |

**التحليل:**

```json
{
  "project_id": "PRJ-2026-001",
  "analysis_date": "2026-08-19",
  "schedule_analysis": {
    "planned_progress": 47,
    "actual_progress": 35,
    "variance": -12,
    "status": "behind_schedule",
    "critical_path_delay": "12 days",
    "delayed_activities": ["الهيكل الإنشائي — الطابق الخامس"]
  },
  "cost_analysis": {
    "budgeted_cost": 17500000.00,
    "actual_cost": 18900000.00,
    "variance": 1400000.00,
    "cost_performance_index": 0.93,
    "status": "over_budget",
    "overrun主要原因": "ارتفاع سعر الخرسانة 8% عن التقدير"
  },
  "ai_recommendations": [
    "تسريع أعمال الهيكل بزيادة عدد العمال في الطابق الخامس",
    "إعادة التفاوض على سعر الخرسانة مع الموردين",
    "매핑 المخاطر: تأخر 12 يوم قد يزيد إلى 25 يوم إذا لم يتم اتخاذ إجراء"
  ],
  "forecast": {
    "estimated_completion": "2028-04-30",
    "delay_from_original": "3.5 months",
    "estimated_total_cost": 54200000.00
  }
}
```

---

#### الخطوة 9: تسجيل معدات — Asset Registration

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 9 من 9 |
| **الوحدة** | Asset Management Module |
| **الإجراء** | تسجيل معدات: أوناش + خلاطات مع إهلاك شهري |
| **النتيجة المتوقعة** | Assets registered with depreciation schedule |

```json
{
  "assets": [
    {
      "asset_code": "EQ-001",
      "name": "أوناش برجي 10 طن",
      "category": "معدات ثقيلة",
      "purchase_cost": 2500000.00,
      "purchase_date": "2025-12-01",
      "useful_life_months": 120,
      "salvage_value": 250000.00,
      "depreciation_method": "straight_line",
      "monthly_depreciation": 18750.00,
      "current_location": "موقع التجمع الخامس",
      "custodian": "Eng. Ali Mahmoud"
    },
    {
      "asset_code": "EQ-002",
      "name": "خلاطة خرسانة 1 م³",
      "category": "معدات ثقيلة",
      "purchase_cost": 800000.00,
      "purchase_date": "2025-12-01",
      "useful_life_months": 84,
      "salvage_value": 80000.00,
      "depreciation_method": "straight_line",
      "monthly_depreciation": 8571.43,
      "current_location": "موقع التجمع الخامس",
      "custodian": "Eng. Ali Mahmoud"
    }
  ]
}
```

---

## 6. القطاع 5: متجر تجزئة — Retail Store

### سيناريو E2E: "إدارة فروع متعددة + برنامج ولاء"

**البيانات الأساسية:**

| العنصر | القيمة |
|--------|--------|
| الفروع | 5 فروع (المعادي، مدينة نصر، 6 أكتوبر، الإسكندرية، المنصورة) |
| العميل | سارة أحمد (عضو ولاء ذهبي) |
| نقاط الولاء الحالية | 1,200 نقطة |
| الفرع | المعادي |
| نسبة خصم الولاء | 10% للعضوية الذهبية |

---

#### الخطوة 1: تحويل بين فروع — Inter-Branch Transfer

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 1 من 6 |
| **الوحدة** | Inventory Module |
| **الإجراء** | نقل 200 قطعة من المستودع المركزي لفرع المعادي |
| **النتيجة المتوقعة** | Stock reduced at central, increased at Maadi |
| **التحقق** | `GET /api/v1/inventory/stock?product=PRD-001` |

```json
{
  "transfer_id": "TRF-2026-08-001",
  "from_warehouse": "WH-CENTRAL",
  "to_warehouse": "WH-MAADI",
  "product_id": "PRD-001",
  "product_name": "سماعة بلوتوث — ر anthem",
  "quantity": 200,
  "unit_cost": 150.00,
  "total_value": 30000.00,
  "status": "completed",
  "completed_at": "2026-08-19T08:00:00Z"
}

// التحقق من الرصيد بعد التحويل:
// المستودع المركزي: 800 - 200 = 600
// فرع المعادي: 50 + 200 = 250
```

---

#### الخطوة 2: بيع ببرنامج ولاء — Loyalty Sale

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 2 من 6 |
| **الوحدة** | POS + CRM Module |
| **الإجراء** | العميلة سارة (ذهبية) تشتري بـ 500 EGP في فرع المعادي |
| **النتيجة المتوقعة** | 10% discount + 45 loyalty points |
| **التحقق** | `GET /api/v1/crm/customers/CUST-001` |

**حساب الولاء:**

```
قيمة الشراء:                          500.00 EGP
خصم العضوية الذهبية (10%):            -50.00 EGP
القيمة بعد الخصم:                     450.00 EGP
النقاط المكتسبة (1 نقطة / 10 EGP):    45 نقطة
النقاط الإجمالية بعد الشراء:         1,200 + 45 = 1,245 نقطة
```

```json
{
  "invoice_id": "POS-MDI-2026-0892",
  "customer_id": "CUST-001",
  "customer_name": "سارة أحمد",
  "loyalty_tier": "gold",
  "branch": "WH-MAADI",
  "items": [
    {"product": "سماعة بلوتوث", "qty": 1, "price": 350.00},
    {"product": "شاحن لاسلكي", "qty": 1, "price": 150.00}
  ],
  "subtotal": 500.00,
  "loyalty_discount": 50.00,
  "total_after_discount": 450.00,
  "payment_method": "card",
  "points_earned": 45,
  "total_points": 1245
}
```

---

#### الخطوة 3: تحديث ملف العميل — Update Customer Profile

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 3 من 6 |
| **الوحدة** | CRM Module |
| **الإجراء** | تحديث بيانات العميل بعد الشراء |
| **التحقق** | `GET /api/v1/crm/customers/CUST-001` |

```json
{
  "customer_id": "CUST-001",
  "name": "سارة أحمد",
  "loyalty_tier": "gold",
  "total_purchases": 12500.00,
  "total_points": 1245,
  "total_visits": 28,
  "average_basket": 446.43,
  "favorite_branch": "WH-MAADI",
  "favorite_category": "Electronics",
  "last_purchase": "2026-08-19",
  "customer_since": "2025-03-15"
}
```

---

#### الخطوة 4: مسح باركود — Barcode Scan

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 4 من 6 |
| **الوحدة** | POS Module |
| **الإجراء** | مسح باركود منتج في فرع المعادي |
| **النتيجة المتوقعة** | عرض الاسم + السعر + رصيد هذا الفرع |

```json
{
  "barcode": "8901234567890",
  "product_id": "PRD-001",
  "product_name": "سماعة بلوتوث — ر anthem",
  "current_branch_stock": 249,
  "price": 350.00,
  "currency": "EGP",
  "available_in_other_branches": [
    {"branch": " مدينة نصر", "stock": 120},
    {"branch": "6 أكتوبر", "stock": 85}
  ]
}
```

---

#### الخطوة 5: تقرير مبيعات مجمع — Consolidated Report

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 5 من 6 |
| **الوحدة** | Reporting Module |
| **الإجراء** | تقرير مبيعات يومي مجمع لـ 5 فروع |
| **التحقق** | `GET /api/v1/reports/sales/daily?date=2026-08-19` |

```json
{
  "report_date": "2026-08-19",
  "branches": [
    {"branch": "المعادي", "sales": 85000, "transactions": 142, "avg_basket": 598.59},
    {"branch": "مدينة نصر", "sales": 120000, "transactions": 195, "avg_basket": 615.38},
    {"branch": "6 أكتوبر", "sales": 65000, "transactions": 98, "avg_basket": 663.27},
    {"branch": "الإسكندرية", "sales": 95000, "transactions": 155, "avg_basket": 612.90},
    {"branch": "المنصورة", "sales": 45000, "transactions": 78, "avg_basket": 576.92}
  ],
  "total_sales": 410000.00,
  "total_transactions": 668,
  "overall_avg_basket": 613.77,
  "top_product": "سماعة بلوتوث — 85 قطعة",
  "top_branch_by_efficiency": "6 أكتوبر (أعلى مبيعات/م²)"
}
```

---

#### الخطوة 6: تحليل الفروع — AI Branch Analysis

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 6 من 6 |
| **الوحدة** | AI Analytics Module |
| **الإجراء** | تحليل ذكي لأداء الفروع |

```json
{
  "analysis_period": "August 2026",
  "branch_rankings": [
    {"rank": 1, "branch": "6 أكتوبر", "revenue_per_sqm": 850, "profit_margin": "32%", "recommendation": "Expand floor area"},
    {"rank": 2, "branch": "مدينة نصر", "revenue_per_sqm": 720, "profit_margin": "28%", "recommendation": "Optimize layout"},
    {"rank": 3, "branch": "المعادي", "revenue_per_sqm": 680, "profit_margin": "26%", "recommendation": "Add loyalty promotions"},
    {"rank": 4, "branch": "الإسكندرية", "revenue_per_sqm": 620, "profit_margin": "24%", "recommendation": "Review pricing"},
    {"rank": 5, "branch": "المنصورة", "revenue_per_sqm": 520, "profit_margin": "20%", "recommendation": "Increase marketing spend"}
  ],
  "ai_insights": [
    "فرع 6 أكتوبر يحقق أعلى ربحية/م² — يُنصح بتوسيعه",
    "فرع المنصورة يحتاج حملة تسويقية مستهدفة",
    "المبيعات الحمراء (weekends) أعلى 35% من weekdays"
  ]
}
```

---

## 7. القطاع 6: مصنع — Manufacturing

### سيناريو E2E: "دورة تصنيع من أمر الإنتاج للمنتج النهائي"

**البيانات الأساسية:**

| العنصر | القيمة |
|--------|--------|
| المنتج | كرسي مكتب — Model X500 |
| BOM | خشب 2م² + قماش 1م + مسامير 50 + عمالة 2 ساعة |
| تكلفة BOM | 350 EGP |
| أمر الإنتاج | 100 كرسي |
| مSR | 2 كرسي تالف |

---

#### الخطوة 1: إنشاء BOM — Create Bill of Materials

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 1 من 7 |
| **الوحدة** | Manufacturing Module |
| **الإجراء** | إنشاء قائمة مواد لـ "كرسي مكتب X500" |

```json
{
  "bom_id": "BOM-CHAIR-X500",
  "product_id": "PRD-CHAIR-X500",
  "product_name": "كرسي مكتب — Model X500",
  "version": "1.0",
  "quantity": 1,
  "unit": "piece",
  "materials": [
    {"item": "خشب زان", "quantity": 2, "unit": "m²", "unit_cost": 80.00, "total": 160.00},
    {"item": "قماش مبطن", "quantity": 1, "unit": "m", "unit_cost": 50.00, "total": 50.00},
    {"item": "مسامير ستانلس", "quantity": 50, "unit": "piece", "unit_cost": 0.40, "total": 20.00},
    {"item": "عجلات بластيك", "quantity": 5, "unit": "piece", "unit_cost": 6.00, "total": 30.00},
    {"item": "مكبس هيدروليكي", "quantity": 1, "unit": "piece", "unit_cost": 90.00, "total": 90.00}
  ],
  "labor": {
    "cutting": {"hours": 0.5, "rate": 50.00, "cost": 25.00},
    "assembly": {"hours": 0.8, "rate": 50.00, "cost": 40.00},
    "upholstery": {"hours": 0.5, "rate": 50.00, "cost": 25.00}
  },
  "total_material_cost": 350.00,
  "total_labor_cost": 90.00,
  "total_bom_cost": 440.00
}
```

---

#### الخطوة 2: أمر إنتاج — Production Order

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 2 من 7 |
| **الوحدة** | Manufacturing Module |
| **الإجراء** | إنشاء أمر إنتاج 100 كرسي |
| **النتيجة المتوقعة** | MO-2026-045 + material reservation |

```json
{
  "production_order_id": "MO-2026-045",
  "bom_id": "BOM-CHAIR-X500",
  "product": "كرسي مكتب — Model X500",
  "quantity_planned": 100,
  "quantity_unit": "piece",
  "planned_start": "2026-08-20",
  "planned_end": "2026-08-22",
  "work_center": "WC-ASSEMBLY-01",
  "materials_required": [
    {"item": "خشب زان", "total_needed": 200, "unit": "m²", "reserved": 200},
    {"item": "قماش مبطن", "total_needed": 100, "unit": "m", "reserved": 100},
    {"item": "مسامير ستانلس", "total_needed": 5000, "unit": "piece", "reserved": 5000},
    {"item": "عجلات بластيك", "total_needed": 500, "unit": "piece", "reserved": 500},
    {"item": "مكبس هيدروليكي", "total_needed": 100, "unit": "piece", "reserved": 100}
  ],
  "status": "planned"
}
```

---

#### الخطوة 3: خصم المواد الخام — Deduct Raw Materials

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 3 من 7 |
| **الوحدة** | Inventory Module |
| **الإجراء** | خصم المواد من المخزون لأمر الإنتاج |

| المادة | الكمية قبل | الكمية المخصومة | الكمية بعد |
|--------|-----------|----------------|-----------|
| خشب زان | 500 م² | 200 م² | 300 م² |
| قماش مبطن | 300 م | 100 م | 200 م |
| مسامير ستانلس | 15,000 قطعة | 5,000 قطعة | 10,000 قطعة |
| عجلات بластيك | 2,000 قطعة | 500 قطعة | 1,500 قطعة |
| مكبس هيدروليكي | 150 قطعة | 100 قطعة | 50 قطعة |

---

#### الخطوة 4: تسجيل مراحل الإنتاج — Record Production Stages

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 4 من 7 |
| **الوحدة** | Manufacturing Module |
| **الإجراء** | تسجيل: قطع → تجميع → تنجيد → تعبئة |

```json
{
  "production_order_id": "MO-2026-045",
  "stages": [
    {
      "stage": "cutting",
      "name": "قطع الخشب",
      "start": "2026-08-20T08:00:00",
      "end": "2026-08-20T12:00:00",
      "operator": "Worker-Ahmed",
      "quantity_completed": 100,
      "defects": 0
    },
    {
      "stage": "assembly",
      "name": "تجميع الهيكل",
      "start": "2026-08-20T13:00:00",
      "end": "2026-08-21T10:00:00",
      "operator": "Worker-Ali",
      "quantity_completed": 100,
      "defects": 0
    },
    {
      "stage": "upholstery",
      "name": "التنجيد",
      "start": "2026-08-21T11:00:00",
      "end": "2026-08-21T16:00:00",
      "operator": "Worker-Khaled",
      "quantity_completed": 98,
      "defects": 2
    },
    {
      "stage": "packaging",
      "name": "التعبئة والتغليف",
      "start": "2026-08-22T08:00:00",
      "end": "2026-08-22T10:00:00",
      "operator": "Worker-Mahmoud",
      "quantity_completed": 98,
      "defects": 0
    }
  ]
}
```

---

#### الخطوة 5: استلام المنتج النهائي — Receive Finished Goods

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 5 من 7 |
| **الوحدة** | Inventory Module |
| **الإجراء** | استلام 98 كرسي (2 تالف) |

```json
{
  "receipt_id": "WHR-MO-2026-045",
  "production_order_id": "MO-2026-045",
  "finished_goods": {
    "product": "كرسي مكتب — Model X500",
    "quantity": 98,
    "unit_cost": 440.00,
    "total_value": 43120.00
  },
  "damaged_goods": {
    "product": "كرسي مكتب — Model X500 (تالف)",
    "quantity": 2,
    "unit_cost": 440.00,
    "total_value": 880.00,
    "damage_reason": " defeito في التنجيد — قماش مقطوع",
    "damage_stage": "upholstery"
  },
  "waste_percentage": "2.0%",
  "accepted_by": "QC-Engineer-Sami"
}
```

---

#### الخطوة 6: قيد تكلفة الإنتاج — Cost Accounting Entry

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 6 من 7 |
| **الوحدة** | Accounting Module |
| **الإجراء** | تسجيل تكلفة الإنتاج |

**القيد المحاسبي:**

| الحساب | المدين (Debit) | الدائن (Credit) | المرجع |
|--------|---------------|-----------------|--------|
| مخزون منتج نهائي — كرسي X500 | 43,120.00 | — | MO-2026-045 |
| خسائر إنتاج (Production Loss) | 880.00 | — | MO-2026-045 |
| مخزون مواد خام — خشب | — | 16,000.00 | MO-2026-045 |
| مخزون مواد خام — قماش | — | 5,000.00 | MO-2026-045 |
| مخزون مواد خام — مسامير | — | 2,000.00 | MO-2026-045 |
| مخزون مواد خام — عجلات | — | 3,000.00 | MO-2026-045 |
| مخزون مواد خام — مكبس | — | 9,000.00 | MO-2026-045 |
| أجور العمالة | — | 9,000.00 | MO-2026-045 |

**التحقق:** المدين (44,000) = الدائن (44,000) ✅

---

#### الخطوة 7: تحليل الهدر — AI Waste Analysis

| العنصر | التفاصيل |
|--------|----------|
| **الخطوة** | 7 من 7 |
| **الوحدة** | AI Analytics Module |
| **الإجراء** | تحليل الهدر في الإنتاج |

```json
{
  "analysis_period": "MO-2026-045",
  "waste_analysis": {
    "total_produced": 100,
    "defective": 2,
    "waste_percentage": "2.0%",
    "industry_average": "1.2%",
    "status": "above_average",
    "root_cause": "مرحلة التنجيد — قماش مقطوع",
    "waste_cost": 880.00,
    "annual_projected_waste": 31680.00
  },
  "ai_recommendations": [
    "فحص جودة القماش قبل التنجيد — زيادة الفحص قبل بدء المرحلة",
    "تدريب Worker-Khaled على تقنيات التنجيد الصحيحة",
    "شراء قماش إضافي 5% كاحتياطي لتغطية الهدر المتوقع"
  ],
  "stage_breakdown": [
    {"stage": "قطع", "defects": 0, "waste_pct": "0%"},
    {"stage": "تجميع", "defects": 0, "waste_pct": "0%"},
    {"stage": "تنجيد", "defects": 2, "waste_pct": "2%"},
    {"stage": "تعبئة", "defects": 0, "waste_pct": "0%"}
  ]
}
```

---

## 8. ملخص تغطية الاختبار — Test Coverage Summary

| # | القطاع | سيناريوهات E2E | خطوات التحقق | حالات خاصة |
|---|--------|---------------|-------------|------------|
| 1 | صيدلية | 2 | 14 | أدوية متحكم فيها |
| 2 | مطعم/كافيه | 1 | 8 | Dine-in + Delivery + وصفات |
| 3 | عيادة طبية | 1 | 8 | حساسية + تأمين |
| 4 | مقاولات | 1 | 9 | BOQ + مستخلصات + معدات |
| 5 | متجر تجزئة | 1 | 6 | فروع متعددة + ولاء + باركود |
| 6 | مصنع | 1 | 7 | BOM + مراحل إنتاج + هدر |
| **الإجمالي** | **6 قطاعات** | **7 سيناريوهات** | **52 نقطة تحقق** | **4 حالات خاصة** |

---

## 9. معايير النجاح — Pass Criteria

| المستوى | الشرط | الاستخدام |
|---------|-------|----------|
| **إطلاق MVP** | 0 فشل في 🔴_critical + ≤ 3 فشل في 🟡_high | المرحلة الأولى |
| **إطلاق رسمي** | 0 فشل في 🔴 + 0 فشل في 🟡 + ≤ 5 في 🟢 | المرحلة الثانية |
| **تحديث دوري** | Regression: 0 فشل في 🔴 | كل sprint |

---

## 10. أدوات الاختبار — Recommended Test Tools

| الأداة | الغرض | الاستخدام |
|--------|-------|----------|
| **Playwright** | E2E Testing | اختبار POS وال Wizard والشاشات الرئيسية |
| **Pytest** | Unit + Integration | اختبار الخدمات والم business logic |
| **Postman / Bruno** | API Testing | اختبار جميع endpoints |
| **k6** | Load Testing | اختبار الأداء تحت الضغط (POS concurrent) |
| **Factory Boy** | Test Data | توليد بيانات اختبار واقعية |
| **GitHub Actions** | CI/CD | تشغيل الاختبارات تلقائياً |

---

## 11. بيئة الاختبار — Test Environment

| العنصر | القيمة |
|--------|--------|
| Database | PostgreSQL 16 — Test DB `eos_test_industry` |
| API Base URL | `https://api.test.eos-system.com/v1` |
| POS Terminals | 3 (Pharmacy, Restaurant, Retail) |
| ETA Sandbox | `https://api.invoicing.eta.gov.eg/sandbox` |
| SMS Provider | Twilio Test Account |
| AI Service | EOS AI Engine — Staging |
|CI/CD | GitHub Actions |

---

*نهاية وثيقة سيناريوهات اختبار القوالب القطاعية*
