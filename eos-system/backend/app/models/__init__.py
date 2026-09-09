"""
EOS System — Models Package
"""
from app.models.tenant import Tenant
from app.models.user import User
from app.models.rbac import Role, Permission, UserRole, RolePermission
from app.models.audit import AuditLog
from app.models.accounting import Account, JournalEntry, JournalEntryLine
from app.models.accounting_ext import (
    AccountingPeriod, CostCenter, BankAccount, Tax,
    BankReconciliation, BankReconciliationLine, AccountStatement,
)
from app.models.inventory import Category, Product, Warehouse, StockMovement
from app.models.inventory_ext import UnitOfMeasure, ProductVariant, StockTake, StockTakeItem, BillOfMaterials, BOMItem
from app.models.hr import Department, Position, Employee, AttendanceRecord
from app.models.hr_ext import (
    JobTitle, LeaveType, Leave, Payroll, PayrollItem,
    Evaluation, Training, TrainingEnrollment,
)
from app.models.sales import Customer, Lead, Opportunity, Quote, QuoteItem
from app.models.eta_invoice import EtaInvoice, EtaInvoiceLine
from app.models.sales_ext import (
    Supplier, PurchaseOrder, PurchaseOrderItem,
    SalesOrder, SalesOrderItem,
    CustomerPayment, SupplierPayment,
    SalesInvoice, SalesInvoiceLine,
    SupplierInvoice, SupplierInvoiceLine,
    OpportunityStage,
)
from app.models.projects import Project, Task, TimeEntry
from app.models.infrastructure import (
    FiscalYear, Currency, ExchangeRate, CompanyProfile,
    Notification, File, CustomField, NumberSequence,
)
from app.models.ai import (
    AIModel, AIPrediction, AICopilotConversation, AICopilotMessage,
    AITenantUsage, AITrainingData,
)
from app.models.industry_templates import (
    PharmacyProduct, PharmacySale, PharmacyAlert,
    Recipe, RecipeIngredient, RestaurantTable, RestaurantOrder,
    RetailBranch, RetailPriceList, RetailPriceListItem, RetailPromotion,
)

__all__ = [
    # Core
    "Tenant",
    "User",

    # RBAC
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",

    # Audit
    "AuditLog",

    # Accounting
    "Account",
    "JournalEntry",
    "JournalEntryLine",
    "AccountingPeriod",
    "CostCenter",
    "BankAccount",
    "Tax",
    "BankReconciliation",
    "BankReconciliationLine",
    "AccountStatement",

    # Inventory
    "Category",
    "Product",
    "Warehouse",
    "StockMovement",
    "UnitOfMeasure",
    "ProductVariant",
    "StockTake",
    "StockTakeItem",
    "BillOfMaterials",
    "BOMItem",

    # HR
    "Department",
    "Position",
    "Employee",
    "AttendanceRecord",
    "JobTitle",
    "LeaveType",
    "Leave",
    "Payroll",
    "PayrollItem",
    "Evaluation",
    "Training",
    "TrainingEnrollment",

    # Sales & CRM
    "Customer",
    "Lead",
    "Opportunity",
    "Quote",
    "QuoteItem",
    "EtaInvoice",
    "EtaInvoiceLine",
    "Supplier",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "SalesOrder",
    "SalesOrderItem",
    "CustomerPayment",
    "SupplierPayment",
    "SalesInvoice",
    "SalesInvoiceLine",
    "SupplierInvoice",
    "SupplierInvoiceLine",
    "OpportunityStage",

    # Projects
    "Project",
    "Task",
    "TimeEntry",

    # Infrastructure
    "FiscalYear",
    "Currency",
    "ExchangeRate",
    "CompanyProfile",
    "Notification",
    "File",
    "CustomField",
    "NumberSequence",
]
