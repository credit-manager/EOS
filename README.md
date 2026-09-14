# 2TO EOS

> **2TO EOS is an AI-native Business Operating System that turns a company's business model, data, rules, workflows, and financial reality into one continuously intelligent operating system.**
>
> **2TO EOS هو نظام تشغيل أعمال ذكي مبني على الذكاء الاصطناعي، يحول نموذج الشركة وبياناتها وقواعدها وعملياتها وحقيقتها المالية إلى منظومة تشغيل واحدة ذكية وقابلة للتطوير.**

EOS is **not** an ERP in the traditional sense — the ERP is the *first, most important application* running on the platform. EOS makes the business model itself (objects, relations, rules, workflows, events, financial impact) executable as software.

The core unit is the **Business Object**, with its full context: data, relationships, rules, permissions, workflow, documents, events, financial impact, analytics, AI context, and audit history — forming a **Business Graph** in which a company's operations read as one business story, not twenty disconnected tables.

## Product map

```
                    2TO EOS
                       │
        ┌──────────────┴──────────────┐
        │                             │
   EOS PLATFORM                  EOS AI
        │                             │
 ┌──────┼────────┐              ┌─────┼─────┐
 │      │        │              │     │     │
Data   Rules   Workflow       Agents Tools Reasoning
 │      │        │              │     │     │
 └──────┴────────┴──────────────┴─────┴─────┘
                       │
                  BUSINESS GRAPH
                       │
       ┌───────────────┼────────────────┐
       │               │                │
     ERP          INDUSTRY PACKS    CUSTOM APPS
       │               │                │
 Accounting       Construction      Customer Objects
 Procurement      Retail            Customer Workflows
 CRM              Manufacturing     Customer Apps
 HR               Healthcare
 Inventory        Logistics
```

## Architecture

The rebuild follows one production runtime and explicit boundaries:

- `backend/app` — application and domain code.
- `backend/tests` — executable contract tests (green suite = released).
- `frontend` — the only web UI source.
- `infra` — local/production infrastructure definitions.
- PostgreSQL is the production database; SQLite is used for fast local/CI validation.

## Current status

**Foundation** for the Business Operating Platform. The existing modules (Construction Pack, financial core, workflow, audit, notifications, rate limiting, metadata) act as *reference implementations* for the platform.

Not yet delivered: AI Workforce, Business Graph, Globalization, Integration Hub, Developer Platform, Enterprise administration.

## Next phase: EOS Operating Platform V1

Ranked in dependency order — the first four are the platform substrate every later pillar consumes:

1. **Metadata Engine V2** — the Foundation's metadata layer as the universal schema source.
2. **Policy Engine** — mandatory/optional policies attaching to objects and flows.
3. **Rules Engine** — `WHEN event IF condition THEN action(s)`.
4. **Event Bus** — durable business events (`invoice.posted`, `budget.threshold_exceeded`, ...) that drive workflow, automation, notifications, AI, analytics, integration, audit.
5. **Workflow V2** — state machine with timeout, escalation, delegation, conditions, compensation.
6. **Business Graph** — entity story API (Customer → Opportunities → Contracts → Projects → Invoices → Payments).
7. **Document Intelligence** — OCR, classification, extraction, matching, validation (supplier invoices = first ROI).
8. **Integration Hub** — REST/webhooks/OAuth/queues/retries/dead-letter + connectors.
9. **Reporting/Analytics Engine** — financial + operational + executive KPIs, every KPI drillable to source.
10. **AI Tool Registry** — tools registered as capabilities with policies and audit.
11. **AI Workforce** — governed agents (finance, procurement, sales, HR, project, executive); each agent has tools, permissions, policies, limits, approval requirements, audit.
12. **Globalization Engine** — country packs (tax, e-invoice, statutory reports, currency, fiscal calendar, compliance).
13. **EOS Builder** — create objects, fields, relations, rules, workflows, views, reports, automations without touching core.
14. **Developer SDK** — extension surface for partners and marketplace apps.
15. **Marketplace foundation** — install/distribute packs and apps.

Every phase ships with executable behavior evidence (tests), not just green lint results.