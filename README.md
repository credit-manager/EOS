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

**22 modules delivered** as the Business Operating Platform foundation:

- **Platform Substrate (15 modules):** Metadata Engine V2, Policy Engine, Rules Engine, Event Bus (persistent + delayed), Workflow V2 (SLA + escalation), Business Graph (auto-discovery), Document Intelligence, Integration Hub, Reporting/Analytics (CSV/PDF export), AI Tool Registry + Governance (policies, limits, escalation, audit), Globalization Engine (pluggable country packs: Egypt, Saudi Arabia), EOS Builder, Developer SDK, Marketplace (industry pack registry + install).

- **Industry Packs (22 domain modules):** Construction (full: 18 models, 40+ endpoints, KPIs, dashboards, rules, financial integration), Financial Core (45+ routes, multi-currency, double-entry journal), Workflow, Audit, Notifications, Rate Limiting, Security Headers, Request Logging, Caching, API Versioning, GZip Compression.

- **AI Governance Layer:** 17 built-in policies (finance, procurement, project, executive, general), policy evaluation engine (permit/deny/escalate), rate limits, human escalation, full audit trail.

- **Pluggable Pack Architecture:** Country Pack Registry (EG, SA) + Industry Pack Registry (Construction, Retail, Manufacturing) with dynamic registration and one-click install.

- **Frontend:** React 19 + Vite 7 + Tailwind — 25+ pages (Workspace, Projects, Contracts, BOQs, Procurement, Financial, AI Governance, etc.).

- **Data:** 391+ API endpoints, 108+ data models, 22 domain modules, SQLite demo database with seeded data.

Not yet delivered: Document Intelligence (OCR/classification), Integration Hub (webhooks/OAuth/queues), Developer SDK (API key auth + extensions), Industry Packs (Retail/Manufacturing full implementations).

## Delivered modules (EOS Operating Platform V1)

| # | Module | Status |
|---|--------|--------|
| 1 | Metadata Engine V2 | ✅ Delivered |
| 2 | Policy Engine | ✅ Delivered |
| 3 | Rules Engine | ✅ Delivered |
| 4 | Event Bus (persistent + delayed) | ✅ Delivered |
| 5 | Workflow V2 (SLA + escalation) | ✅ Delivered |
| 6 | Business Graph (auto-discovery) | ✅ Delivered |
| 7 | Document Intelligence | 🔲 Pending |
| 8 | Integration Hub | 🔲 Pending |
| 9 | Reporting/Analytics (CSV/PDF) | ✅ Delivered |
| 10 | AI Tool Registry + Governance | ✅ Delivered |
| 11 | AI Workforce (governed agents) | ✅ Delivered |
| 12 | Globalization Engine (pluggable packs) | ✅ Delivered |
| 13 | EOS Builder | ✅ Delivered |
| 14 | Developer SDK | ✅ Delivered |
| 15 | Marketplace (industry pack registry) | ✅ Delivered |

## Remaining work

1. Document Intelligence — OCR, classification, extraction, matching, validation.
2. Integration Hub — REST/webhooks/OAuth/queues/retries/dead-letter + connectors.
3. Industry Packs — full Retail and Manufacturing implementations.
4. Developer SDK — API key auth + extension surface for partners.
5. Enterprise admin — SSO, multi-tenant management.

Every phase ships with executable behavior evidence (tests), not just green lint results.
