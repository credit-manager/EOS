"""EOS Builder service."""
from datetime import datetime

from sqlalchemy.orm import Session

from .models import (
    BuilderAutomation,
    BuilderDashboard,
    BuilderField,
    BuilderObject,
    BuilderRelation,
    BuilderRule,
    BuilderView,
    BuilderWidget,
    BuilderWorkflow,
)


class BuilderService:
    def __init__(self, db: Session):
        self.db = db

    # Objects

    def create_object(self, tenant_id: str, data: dict) -> BuilderObject:
        obj = BuilderObject(tenant_id=tenant_id, **data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_object(self, object_id: str, tenant_id: str) -> BuilderObject | None:
        return self.db.query(BuilderObject).filter(BuilderObject.id == object_id, BuilderObject.tenant_id == tenant_id).first()

    def list_objects(self, tenant_id: str) -> list[BuilderObject]:
        return self.db.query(BuilderObject).filter(BuilderObject.tenant_id == tenant_id, BuilderObject.is_active).order_by(BuilderObject.name).all()

    def update_object(self, object_id: str, tenant_id: str, data: dict) -> BuilderObject | None:
        obj = self.get_object(object_id, tenant_id)
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        obj.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete_object(self, object_id: str, tenant_id: str) -> bool:
        obj = self.get_object(object_id, tenant_id)
        if not obj:
            return False
        self.db.delete(obj)
        self.db.commit()
        return True

    # Fields

    def create_field(self, object_id: str, tenant_id: str, data: dict) -> BuilderField | None:
        obj = self.get_object(object_id, tenant_id)
        if not obj:
            return None
        field = BuilderField(object_id=object_id, tenant_id=tenant_id, **data)
        self.db.add(field)
        self.db.commit()
        self.db.refresh(field)
        return field

    def list_fields(self, object_id: str, tenant_id: str) -> list[BuilderField]:
        return self.db.query(BuilderField).filter(BuilderField.object_id == object_id, BuilderField.tenant_id == tenant_id).order_by(BuilderField.sort_order).all()

    # Relations

    def create_relation(self, tenant_id: str, data: dict) -> BuilderRelation:
        rel = BuilderRelation(tenant_id=tenant_id, **data)
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)
        return rel

    def list_relations(self, tenant_id: str) -> list[BuilderRelation]:
        return self.db.query(BuilderRelation).filter(BuilderRelation.tenant_id == tenant_id).all()

    # Workflows

    def create_workflow(self, tenant_id: str, data: dict) -> BuilderWorkflow:
        wf = BuilderWorkflow(tenant_id=tenant_id, **data)
        self.db.add(wf)
        self.db.commit()
        self.db.refresh(wf)
        return wf

    def list_workflows(self, tenant_id: str) -> list[BuilderWorkflow]:
        return self.db.query(BuilderWorkflow).filter(BuilderWorkflow.tenant_id == tenant_id).all()

    # Rules

    def create_rule(self, tenant_id: str, data: dict) -> BuilderRule:
        rule = BuilderRule(tenant_id=tenant_id, **data)
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def list_rules(self, tenant_id: str) -> list[BuilderRule]:
        return self.db.query(BuilderRule).filter(BuilderRule.tenant_id == tenant_id).all()

    # Views

    def create_view(self, tenant_id: str, data: dict) -> BuilderView:
        view = BuilderView(tenant_id=tenant_id, **data)
        self.db.add(view)
        self.db.commit()
        self.db.refresh(view)
        return view

    def list_views(self, tenant_id: str) -> list[BuilderView]:
        return self.db.query(BuilderView).filter(BuilderView.tenant_id == tenant_id).all()

    # Dashboards

    def create_dashboard(self, tenant_id: str, data: dict) -> BuilderDashboard:
        dash = BuilderDashboard(tenant_id=tenant_id, **data)
        self.db.add(dash)
        self.db.commit()
        self.db.refresh(dash)
        return dash

    def list_dashboards(self, tenant_id: str) -> list[BuilderDashboard]:
        return self.db.query(BuilderDashboard).filter(BuilderDashboard.tenant_id == tenant_id).all()

    # Widgets

    def create_widget(self, dashboard_id: str, tenant_id: str, data: dict) -> BuilderWidget | None:
        dash = self.db.query(BuilderDashboard).filter(BuilderDashboard.id == dashboard_id, BuilderDashboard.tenant_id == tenant_id).first()
        if not dash:
            return None
        widget = BuilderWidget(dashboard_id=dashboard_id, tenant_id=tenant_id, **data)
        self.db.add(widget)
        self.db.commit()
        self.db.refresh(widget)
        return widget

    def list_widgets(self, dashboard_id: str, tenant_id: str) -> list[BuilderWidget]:
        return self.db.query(BuilderWidget).filter(BuilderWidget.dashboard_id == dashboard_id, BuilderWidget.tenant_id == tenant_id).all()

    # Automations

    def create_automation(self, tenant_id: str, data: dict) -> BuilderAutomation:
        auto = BuilderAutomation(tenant_id=tenant_id, **data)
        self.db.add(auto)
        self.db.commit()
        self.db.refresh(auto)
        return auto

    def list_automations(self, tenant_id: str) -> list[BuilderAutomation]:
        return self.db.query(BuilderAutomation).filter(BuilderAutomation.tenant_id == tenant_id).all()

    # Export

    def export_schema(self, tenant_id: str) -> dict:
        objects = self.list_objects(tenant_id)
        all_fields = []
        for obj in objects:
            all_fields.extend(self.list_fields(obj.id, tenant_id))
        return {
            "objects": objects,
            "fields": all_fields,
            "relations": self.list_relations(tenant_id),
            "workflows": self.list_workflows(tenant_id),
            "rules": self.list_rules(tenant_id),
            "views": self.list_views(tenant_id),
            "dashboards": self.list_dashboards(tenant_id),
            "automations": self.list_automations(tenant_id),
        }
