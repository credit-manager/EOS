from sqlalchemy import Column, String, Boolean, Integer, Text, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base
import uuid

class DBPEntity(Base):
    __tablename__ = "dbp_entities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True, default="platform")  # FIXED: Was nullable=True
    code = Column(String(100), unique=True, nullable=False, index=True)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    faculty = Column(String(50), nullable=False)
    table_mapping = Column(String(100))
    is_system = Column(Boolean, default=False)
    metadata_schema = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DBPField(Base):
    __tablename__ = "dbp_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id = Column(
        String(36),
        ForeignKey("dbp_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    code = Column(String(100), nullable=False)
    label_en = Column(String(255))
    label_ar = Column(String(255))
    field_type = Column(String(50), nullable=False)
    is_required = Column(Boolean, default=False)
    ui_config = Column(JSON, default={})
    enum_values = Column(JSON, default=[])
    is_sensitive = Column(Boolean, default=False)
    writable_roles = Column(JSON, default=[])
    visible_roles = Column(JSON, default=[])
    validation_rules = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPRelationship(Base):
    __tablename__ = "dbp_relationships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id = Column(
        String(36),
        ForeignKey("dbp_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    code = Column(String(100), nullable=False)
    target_entity_code = Column(String(100), nullable=False)
    relationship_type = Column(
        String(20), nullable=False, default="one_to_many"
    )
    source_column = Column(String(100), nullable=False)
    target_column = Column(String(100), nullable=False, default="id")
    lookup_field = Column(String(100), default="name_en")
    is_required = Column(Boolean, default=False)
    tenant_scope = Column(Boolean, default=True)
    on_delete = Column(String(20), default="restrict")
    junction_table = Column(String(100), default="")
    junction_source_col = Column(String(100), default="")
    junction_target_col = Column(String(100), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPEntityVersion(Base):
    __tablename__ = "dbp_entity_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id = Column(
        String(36),
        ForeignKey("dbp_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    schema_snapshot = Column(JSON, nullable=False)
    change_type = Column(String(50), nullable=False)
    changed_by = Column(String(100), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    change_summary = Column(Text, nullable=True)


class DBPRowRule(Base):
    __tablename__ = "dbp_row_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id = Column(
        String(36),
        ForeignKey("dbp_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filter_column = Column(String(100), nullable=False)
    filter_type = Column(String(20), nullable=False, default="equals")
    filter_value = Column(String(500), nullable=True)
    allowed_roles = Column(JSON, default=[])
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPEvent(Base):
    __tablename__ = "dbp_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    entity_code = Column(String(100), nullable=False, index=True)
    record_id = Column(String(36), nullable=True)
    user_id = Column(String(100), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPWebhook(Base):
    __tablename__ = "dbp_webhooks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    code = Column(String(100), unique=True, nullable=False)
    target_url = Column(String(500), nullable=False)
    entity_code = Column(String(100), nullable=False, index=True)
    event_types = Column(JSON, nullable=False, default=[])
    secret = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    custom_headers = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPWebhookDelivery(Base):
    __tablename__ = "dbp_webhook_deliveries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_id = Column(
        String(36),
        ForeignKey("dbp_webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id = Column(
        String(36),
        ForeignKey("dbp_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, default=0)
    last_response_code = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ──────────────────────────────────────────────────────────────
# P15 NOTIFICATION MODELS
# ──────────────────────────────────────────────────────────────

class DBPNotification(Base):
    __tablename__ = "dbp_notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    channel = Column(String(20), nullable=False, default="in_app", index=True)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=True)
    notification_type = Column(String(50), nullable=False, default="info", index=True)
    entity_code = Column(String(100), nullable=True)
    record_id = Column(String(36), nullable=True)
    event_id = Column(String(36), nullable=True)
    action_url = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPNotificationTemplate(Base):
    __tablename__ = "dbp_notification_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    code = Column(String(100), nullable=False, index=True)
    channel = Column(String(20), nullable=False, default="in_app")
    notification_type = Column(String(50), nullable=False, default="info")
    title_template = Column(String(500), nullable=False)
    message_template = Column(Text, nullable=True)
    event_type = Column(String(50), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPNotificationPreference(Base):
    __tablename__ = "dbp_notification_preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    notification_type = Column(String(50), nullable=False)
    channel = Column(String(20), nullable=False, default="in_app")
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ──────────────────────────────────────────────────────────────
# P16 DASHBOARD / ANALYTICS MODELS
# ──────────────────────────────────────────────────────────────

class DBPDashboard(Base):
    __tablename__ = "dbp_dashboards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    code = Column(String(100), nullable=False, index=True)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    description = Column(Text, nullable=True)
    layout = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    owner_user_id = Column(String(100), nullable=True)
    allowed_roles = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DBPDashboardWidget(Base):
    __tablename__ = "dbp_dashboard_widgets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dashboard_id = Column(
        String(36),
        ForeignKey("dbp_dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(100), nullable=False)
    widget_type = Column(String(50), nullable=False, default="kpi")
    title = Column(String(255), nullable=False)
    title_ar = Column(String(255))
    entity_code = Column(String(100), nullable=False)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=1)
    height = Column(Integer, default=1)
    query_config = Column(JSON, default={})
    style_config = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPKPI(Base):
    __tablename__ = "dbp_kpis"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    code = Column(String(100), nullable=False, index=True)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    entity_code = Column(String(100), nullable=False)
    aggregation = Column(String(20), nullable=False)
    column_name = Column(String(100), nullable=True)
    filters = Column(JSON, default=[])
    group_by = Column(String(100), nullable=True)
    date_field = Column(String(100), nullable=True)
    date_range = Column(String(20), nullable=True)
    format_type = Column(String(20), default="number")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ──────────────────────────────────────────────────────────────
# P17 WORKFLOW MODELS
# ──────────────────────────────────────────────────────────────

class DBPWorkflowDefinition(Base):
    __tablename__ = "dbp_workflow_definitions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    code = Column(String(100), nullable=False, index=True)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    description = Column(Text, nullable=True)
    entity_code = Column(String(100), nullable=False, index=True)
    is_active = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    sla_hours = Column(Integer, nullable=True)
    escalation_hours = Column(Integer, nullable=True)
    config = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DBPWorkflowState(Base):
    __tablename__ = "dbp_workflow_states"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(
        String(36),
        ForeignKey("dbp_workflow_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    code = Column(String(100), nullable=False)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    state_type = Column(String(20), nullable=False, default="pending")
    is_initial = Column(Boolean, default=False)
    is_final = Column(Boolean, default=False)
    allowed_roles = Column(JSON, default=[])
    config = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPWorkflowTransition(Base):
    __tablename__ = "dbp_workflow_transitions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(
        String(36),
        ForeignKey("dbp_workflow_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    code = Column(String(100), nullable=False)
    name_en = Column(String(255), nullable=False)
    from_state_id = Column(
        String(36),
        ForeignKey("dbp_workflow_states.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_state_id = Column(
        String(36),
        ForeignKey("dbp_workflow_states.id", ondelete="CASCADE"),
        nullable=False,
    )
    action = Column(String(50), nullable=False, default="approve")
    required_roles = Column(JSON, default=[])
    conditions = Column(JSON, default=[])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPWorkflowInstance(Base):
    __tablename__ = "dbp_workflow_instances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    workflow_id = Column(
        String(36),
        ForeignKey("dbp_workflow_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    entity_code = Column(String(100), nullable=False)
    record_id = Column(String(36), nullable=False, index=True)
    current_state_id = Column(
        String(36),
        ForeignKey("dbp_workflow_states.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(String(20), nullable=False, default="active", index=True)
    initiated_by = Column(String(100), nullable=False)
    priority = Column(Integer, default=0)
    due_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    wf_metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DBPWorkflowAction(Base):
    __tablename__ = "dbp_workflow_actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    instance_id = Column(
        String(36),
        ForeignKey("dbp_workflow_instances.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    transition_id = Column(
        String(36),
        ForeignKey("dbp_workflow_transitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    action = Column(String(50), nullable=False)
    from_state = Column(String(100), nullable=True)
    to_state = Column(String(100), nullable=True)
    performed_by = Column(String(100), nullable=False)
    comment = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPDataJob(Base):
    __tablename__ = "dbp_data_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    code = Column(String(100), nullable=False, index=True)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    job_type = Column(String(50), nullable=False)
    entity_code = Column(String(100), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="pending")
    priority = Column(Integer, default=0)
    config = Column(JSON, default={})
    result = Column(JSON, default={})
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DBPValidationRule(Base):
    __tablename__ = "dbp_validation_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    entity_id = Column(
        String(36),
        ForeignKey("dbp_entities.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    field_code = Column(String(100), nullable=True, index=True)
    rule_type = Column(String(50), nullable=False, index=True)
    rule_config = Column(JSON, default={})
    name_en = Column(String(255), nullable=True)
    name_ar = Column(String(255), nullable=True)
    severity = Column(String(20), default="error")
    is_active = Column(Boolean, default=True)
    condition_config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ──────────────────────────────────────────────────────────────
# P21 ERP FOUNDATION
# ──────────────────────────────────────────────────────────────

class DBPCompany(Base):
    __tablename__ = "dbp_companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    legal_name = Column(String(255))
    tax_number = Column(String(100))
    commercial_registration = Column(String(100))
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(50))
    phone = Column(String(50))
    email = Column(String(200))
    website = Column(String(200))
    base_currency = Column(String(10), default="SAR")
    fiscal_year_start_month = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPBranch(Base):
    __tablename__ = "dbp_branches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("dbp_companies.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(50))
    phone = Column(String(50))
    is_headquarters = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPDepartment(Base):
    __tablename__ = "dbp_departments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("dbp_companies.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("dbp_departments.id", ondelete="SET NULL"), nullable=True)
    branch_id = Column(String(36), ForeignKey("dbp_branches.id", ondelete="SET NULL"), nullable=True)
    code = Column(String(50), nullable=False)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    cost_center_id = Column(String(36), nullable=True)
    manager_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPFiscalYear(Base):
    __tablename__ = "dbp_fiscal_years"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("dbp_companies.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_closed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPCurrency(Base):
    __tablename__ = "dbp_currencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    code = Column(String(10), nullable=False)
    name_en = Column(String(100), nullable=False)
    name_ar = Column(String(100))
    symbol = Column(String(10))
    decimal_places = Column(Integer, default=2)
    is_base = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DBPCostCenter(Base):
    __tablename__ = "dbp_cost_centers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("dbp_companies.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    parent_id = Column(String(36), ForeignKey("dbp_cost_centers.id", ondelete="SET NULL"), nullable=True)
    budget_amount = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
