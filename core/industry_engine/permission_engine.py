"""
EOS Industry Engine — Permission Engine
RBAC per module, entity, and action.
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class PermissionAction(str, Enum):
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    APPROVE = "approve"
    EXPORT = "import"
    IMPORT = "export"
    PRINT = "print"
    ASSIGN = "assign"


class AccessLevel(str, Enum):
    NONE = "none"
    OWN = "own"          # Own records only
    DEPARTMENT = "department"  # Department records
    BRANCH = "branch"    # Branch records
    COMPANY = "company"  # Company records
    TENANT = "tenant"    # All tenant records
    PLATFORM = "platform"  # Platform-level


@dataclass
class Permission:
    code: str
    name: str
    name_ar: str
    module: str
    entity: str
    action: PermissionAction
    access_level: AccessLevel = AccessLevel.TENANT
    description: str = ""


@dataclass
class Role:
    code: str
    name: str
    name_ar: str
    description: str = ""
    permissions: List[str] = field(default_factory=list)  # Permission codes
    is_system: bool = False  # System roles can't be deleted
    hierarchy_level: int = 0  # Higher = more authority


@dataclass
class PermissionGrant:
    """A specific permission grant for a user on an entity instance."""
    user_id: str
    permission_code: str
    entity_code: str
    entity_id: str
    access_level: AccessLevel
    granted_by: str
    granted_at: str


class PermissionEngine:
    """
    Manages roles, permissions, and access control.
    Each module registers its permissions; roles compose them.
    """

    def __init__(self):
        self._permissions: Dict[str, Permission] = {}
        self._roles: Dict[str, Role] = {}
        self._grants: Dict[str, PermissionGrant] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register built-in platform roles and permissions."""
        # System roles
        self.register_role(Role(
            code="platform_owner", name="Platform Owner", name_ar="مالك المنصة",
            description="Full platform access", is_system=True, hierarchy_level=100,
        ))
        self.register_role(Role(
            code="tenant_admin", name="Tenant Admin", name_ar="مدير المستأجر",
            description="Full tenant access", is_system=True, hierarchy_level=90,
        ))
        self.register_role(Role(
            code="manager", name="Manager", name_ar="مدير",
            description="Department manager", hierarchy_level=70,
        ))
        self.register_role(Role(
            code="accountant", name="Accountant", name_ar="محاسب",
            description="Accounting staff", hierarchy_level=50,
        ))
        self.register_role(Role(
            code="user", name="User", name_ar="مستخدم",
            description="Regular user", hierarchy_level=30,
        ))
        self.register_role(Role(
            code="viewer", name="Viewer", name_ar="مشاهد",
            description="Read-only access", hierarchy_level=10,
        ))

    def register_permission(self, perm: Permission):
        """Register a permission."""
        self._permissions[perm.code] = perm

    def register_role(self, role: Role):
        """Register a role."""
        self._roles[role.code] = role

    def get_permission(self, code: str) -> Optional[Permission]:
        return self._permissions.get(code)

    def get_role(self, code: str) -> Optional[Role]:
        return self._roles.get(code)

    def get_all_permissions(self) -> Dict[str, Permission]:
        return dict(self._permissions)

    def get_all_roles(self) -> Dict[str, Role]:
        return dict(self._roles)

    def get_permissions_for_role(self, role_code: str) -> List[Permission]:
        """Get all permissions assigned to a role."""
        role = self._roles.get(role_code)
        if not role:
            return []
        return [self._permissions[p] for p in role.permissions if p in self._permissions]

    def get_permissions_for_module(self, module_code: str) -> List[Permission]:
        """Get all permissions for a module."""
        return [p for p in self._permissions.values() if p.module == module_code]

    def check_permission(self, user_role: str, permission_code: str) -> bool:
        """Check if a role has a specific permission."""
        role = self._roles.get(user_role)
        if not role:
            return False
        # Platform owner has all permissions
        if role.hierarchy_level >= 100:
            return True
        return permission_code in role.permissions

    def check_access_level(self, user_role: str, permission_code: str, record_scope: str) -> bool:
        """Check if a role's access level is sufficient for a record scope."""
        perm = self._permissions.get(permission_code)
        if not perm:
            return False

        role = self._roles.get(user_role)
        if not role:
            return False

        # Hierarchy check
        level_order = {
            AccessLevel.NONE: 0, AccessLevel.OWN: 1, AccessLevel.DEPARTMENT: 2,
            AccessLevel.BRANCH: 3, AccessLevel.COMPANY: 4, AccessLevel.TENANT: 5,
            AccessLevel.PLATFORM: 6,
        }
        scope_order = level_order.get(AccessLevel(record_scope), 0)
        perm_order = level_order.get(perm.access_level, 0)

        return scope_order <= perm_order or role.hierarchy_level >= 90

    def grant_permission(self, user_id: str, permission_code: str, entity_code: str,
                         entity_id: str, access_level: AccessLevel, granted_by: str) -> PermissionGrant:
        """Grant a specific permission to a user."""
        grant = PermissionGrant(
            user_id=user_id, permission_code=permission_code,
            entity_code=entity_code, entity_id=entity_id,
            access_level=access_level, granted_by=granted_by, granted_at="now",
        )
        key = f"{user_id}:{permission_code}:{entity_code}:{entity_id}"
        self._grants[key] = grant
        return grant

    def revoke_permission(self, user_id: str, permission_code: str, entity_code: str, entity_id: str):
        """Revoke a permission grant."""
        key = f"{user_id}:{permission_code}:{entity_code}:{entity_id}"
        self._grants.pop(key, None)

    def get_user_grants(self, user_id: str) -> List[PermissionGrant]:
        """Get all permission grants for a user."""
        return [g for g in self._grants.values() if g.user_id == user_id]

    def register_module_permissions(self, module_code: str, entity_code: str, entity_name: str, entity_name_ar: str):
        """Convenience: register standard CRUD permissions for a module entity."""
        for action in PermissionAction:
            code = f"{module_code}.{entity_code}.{action.value}"
            self.register_permission(Permission(
                code=code, name=f"{entity_name} {action.value.title()}",
                name_ar=f"{entity_name_ar} {action.value}",
                module=module_code, entity=entity_code, action=action,
            ))
        # Add permissions to roles
        admin_role = self._roles.get("tenant_admin")
        if admin_role:
            for action in PermissionAction:
                code = f"{module_code}.{entity_code}.{action.value}"
                if code not in admin_role.permissions:
                    admin_role.permissions.append(code)

    def export_roles(self) -> List[Dict[str, Any]]:
        """Export roles for templates."""
        return [{
            "code": r.code, "name": r.name, "name_ar": r.name_ar,
            "permissions": r.permissions, "hierarchy_level": r.hierarchy_level,
        } for r in self._roles.values() if not r.is_system]
