"""EOS Builder models."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from ..db import Base


class BuilderObject(Base):
    __tablename__ = "builder_objects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    object_type = Column(String(50), nullable=False, default="entity")
    parent_object_id = Column(String(36), nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuilderField(Base):
    __tablename__ = "builder_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    object_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    field_type = Column(String(50), nullable=False)
    is_required = Column(Boolean, nullable=False, default=False)
    is_unique = Column(Boolean, nullable=False, default=False)
    default_value = Column(Text, nullable=True)
    options = Column(JSON, nullable=True)
    validation_rules = Column(JSON, nullable=True)
    display_config = Column(JSON, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuilderRelation(Base):
    __tablename__ = "builder_relations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    source_object_id = Column(String(36), nullable=False, index=True)
    target_object_id = Column(String(36), nullable=False, index=True)
    relation_type = Column(String(50), nullable=False)
    source_field = Column(String(100), nullable=True)
    target_field = Column(String(100), nullable=True)
    is_required = Column(Boolean, nullable=False, default=False)
    cascade_delete = Column(Boolean, nullable=False, default=False)
    display_config = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class BuilderWorkflow(Base):
    __tablename__ = "builder_workflows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    object_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)
    trigger_config = Column(JSON, nullable=True)
    steps = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuilderRule(Base):
    __tablename__ = "builder_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    object_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(50), nullable=False)
    when_clause = Column(JSON, nullable=True)
    if_clause = Column(JSON, nullable=True)
    then_actions = Column(JSON, nullable=True)
    else_actions = Column(JSON, nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuilderView(Base):
    __tablename__ = "builder_views"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    object_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    view_type = Column(String(50), nullable=False)
    columns = Column(JSON, nullable=True)
    filters = Column(JSON, nullable=True)
    sorts = Column(JSON, nullable=True)
    layout = Column(JSON, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuilderDashboard(Base):
    __tablename__ = "builder_dashboards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    layout = Column(JSON, nullable=True)
    widgets = Column(JSON, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuilderWidget(Base):
    __tablename__ = "builder_widgets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dashboard_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    widget_type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=True)
    data_source = Column(JSON, nullable=True)
    position = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuilderAutomation(Base):
    __tablename__ = "builder_automations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    object_id = Column(String(36), nullable=True, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)
    trigger_config = Column(JSON, nullable=True)
    conditions = Column(JSON, nullable=True)
    actions = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_run_at = Column(DateTime, nullable=True)
    run_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuilderExport(Base):
    __tablename__ = "builder_exports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    export_type = Column(String(50), nullable=False)
    export_format = Column(String(20), nullable=False, default="json")
    config = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    file_path = Column(String(1000), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
