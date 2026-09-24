# EOS User Guide

## 1. Getting Started

**Login**
- Enter your email and password at the login screen.
- If this is your first login, you'll be guided through the onboarding wizard to set up your company profile.

**Onboarding Wizard**
- **Welcome**: Introduction to EOS.
- **Company Information**: Enter your company name and industry.
- **Recommended Modules**: View modules suggested for your industry.
- **Invite Team Members**: Add colleagues by email (optional, can skip).
- **Completion**: Quick links to start using EOS.

## 2. Dashboard Overview

The **Executive Dashboard** (Home) provides a real-time snapshot of your business:

- **Overview Tab**: Entity counts, pending approvals, workflows needing attention.
- **Attention Tab**: Items requiring your action.
- **Financial Tab**: Invoices, bills, aging reports.
- **Activity Tab**: Recent events and rule firings.
- **Risks Tab**: Identified business risks with suggested actions.

Use the **global search** (top right) to quickly find records across all modules.

## 3. Ask EOS (AI Copilot)

Access the AI Copilot from the sidebar or dashboard:

- Ask natural language questions about your business data.
- Examples:
  - "Show me all overdue invoices"
  - "What's the status of Project Alpha?"
  - "Generate a cash flow summary for last month"
- The AI provides responses with sources and suggested actions.

## 4. Managing Records

**Business Objects Explorer**
- Browse all entity types (Projects, Contracts, Invoices, etc.).
- Click an entity type to view its records.

**Entity Page**
- View, create, edit, and delete records.
- Use filters and search to find specific records.
- Related records are linked and accessible from the detail view.

## 5. Workflows & Approvals

**Workflows**
- View active workflow instances.
- See the current state and history of each workflow.

**Approvals**
- Pending approvals appear on the dashboard.
- Approve or reject requests with comments.
- Workflow state transitions are automatically recorded.

## 6. Financial Management

**Financial Module**
- **Accounts Receivable**: Manage customer invoices and payments.
- **Accounts Payable**: Track supplier bills and payments.
- **Aging Reports**: View outstanding balances by age bucket.
- **Currency Support**: Multi-currency transactions with SAR as default.

## 7. Builder (Creating Custom Objects)

Use the **Builder** to extend EOS with custom business objects:

1. Navigate to **Builder** in the sidebar.
2. Click **Create New Entity**.
3. Define fields (text, number, date, boolean, relation).
4. Set permissions (admin/member access).
5. Publish to make the entity available across EOS.

Custom entities appear in the Business Objects Explorer and can be used in workflows and reports.

## 8. Settings & Configuration

Access **Settings** from the sidebar:

- **General**: Company name, timezone, currency, fiscal year.
- **Appearance**: Language and theme settings.
- **Notifications**: Configure email, push, and SMS notifications.
- **Security**: Change password and manage sessions.
- **Integrations**: Connect external services.
- **Billing**: Manage subscription and payment methods.

## 9. API Reference

EOS provides a RESTful API for programmatic access:

**Base URL**: `/api/v1`

**Authentication**:
- POST `/auth/token` - Obtain access token
- POST `/auth/refresh` - Refresh expired token
- POST `/auth/logout` - Invalidate session

**Core Endpoints**:
- GET/POST `/metadata` - List/create entity definitions
- GET/POST `/entities/{code}` - List/create records
- GET/PUT/DELETE `/entities/{code}/{id}` - Read/update/delete records
- GET `/settings` - Fetch tenant settings
- POST `/ai/chat` - Interact with AI copilot

**Documentation**: Full OpenAPI spec available at `/docs` (Swagger UI).

## 10. Troubleshooting

**Common Issues**:

| Issue | Solution |
|-------|----------|
| Login fails | Verify email/password; check if account is locked. |
| Data not loading | Check network connection; try refreshing the page. |
| AI not responding | Ensure you have sufficient credits; try a simpler query. |
| Workflow stuck | Check if approver is available; contact admin. |
| Missing permissions | Request role upgrade from administrator. |

**Getting Help**:
- In-app AI Copilot can answer many support questions.
- Contact your system administrator for account issues.
- API errors include HTTP status codes for debugging.

---

*EOS v1.0 - 2TO Business Operating System*
