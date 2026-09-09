"""
EOS System — Audit Log Model
"""
from sqlalchemy import Column, String, DateTime, Text, JSON
from datetime import datetime
from app.db.session import Base


class AuditLog(Base):
    """Audit trail for all system operations."""
    
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), index=True, nullable=False)
    user_id = Column(String(36), index=True)
    user_email = Column(String(255))
    action = Column(String(50), nullable=False, index=True)  # create, update, delete, login, logout
    module = Column(String(50), nullable=False, index=True)  # accounting, inventory, hr, sales, auth
    entity_type = Column(String(100))  # e.g. "Account", "Product", "Employee"
    entity_id = Column(String(36))
    entity_name = Column(String(255))
    old_values = Column(JSON)  # Previous state
    new_values = Column(JSON)  # New state
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_id = Column(String(36))
    status = Column(String(20), default="success")  # success, failure
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "action": self.action,
            "module": self.module,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "ip_address": self.ip_address,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
