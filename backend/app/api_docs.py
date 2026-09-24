from fastapi import FastAPI


def configure_api_docs(app: FastAPI) -> None:
    """Configure OpenAPI/Swagger documentation for the 2TO EOS API."""

    app.title = "2TO EOS — AI-native Business Operating System API"
    app.description = """
2TO EOS is an AI-native Business Operating System that integrates metadata management,
policy compliance, workflow orchestration, and real-time analytics into a unified platform.

The API provides comprehensive endpoints for:
- Authentication and user management
- Metadata and schema management
- Record CRUD operations across all business domains
- Policy enforcement and compliance rules
- Event-driven architecture and workflow automation
- Audit logging and reporting
- Document and financial operations
- Construction and manufacturing modules
- Globalization and marketplace integrations
- AI-powered analytics and graph queries
- SDK support and third-party integrations
- Retail operations and health monitoring
"""
    app.version = "1.0.0"
    app.contact = {"name": "2TO EOS Team"}
    app.license_info = {"name": "MIT"}
    app.openapi_tags = [
        {"name": "auth", "description": "Authentication and authorization endpoints"},
        {"name": "metadata", "description": "Metadata and schema management"},
        {"name": "records", "description": "Record CRUD operations"},
        {"name": "policy", "description": "Policy enforcement and compliance"},
        {"name": "rules", "description": "Business rules engine"},
        {"name": "events", "description": "Event-driven architecture and webhooks"},
        {"name": "workflow", "description": "Workflow orchestration and automation"},
        {"name": "audit", "description": "Audit logging and activity tracking"},
        {"name": "notifications", "description": "Notification management and delivery"},
        {"name": "reporting", "description": "Analytics and reporting endpoints"},
        {"name": "documents", "description": "Document management and storage"},
        {"name": "financial", "description": "Financial operations and accounting"},
        {"name": "construction", "description": "Construction project management"},
        {"name": "globalization", "description": "Internationalization and localization"},
        {"name": "marketplace", "description": "Marketplace and integration catalog"},
        {"name": "builder", "description": "Low-code builder and UI components"},
        {"name": "sdk", "description": "SDK and developer tooling"},
        {"name": "integrations", "description": "Third-party system integrations"},
        {"name": "ai", "description": "AI-powered analytics and predictions"},
        {"name": "graph", "description": "Graph queries and relationship mapping"},
        {"name": "health", "description": "System health and monitoring"},
        {"name": "retail", "description": "Retail operations and point-of-sale"},
        {"name": "manufacturing", "description": "Manufacturing and production management"},
    ]
    app.docs_url = "/docs"
    app.redoc_url = "/redoc"
    app.openapi_url = "/openapi.json"
