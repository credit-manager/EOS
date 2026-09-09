import sys
sys.path.insert(0, r'D:\EOS\Eos final\eos-system\backend')

from sqlalchemy import inspect as sa_inspect
from app.models.sales_ext import Supplier
from app.models.eta_invoice import EtaInvoice

# Inspect Supplier mapper
supplier_mapper = sa_inspect(Supplier)
print('=== Supplier Mapper Properties ===')
for attr in supplier_mapper.iterate_properties:
    print(f'  Property: {attr.key}, back_populates={getattr(attr, "back_populates", None)}')

print()
print('=== Checking for eta_invoices ===')
if hasattr(Supplier, 'eta_invoices'):
    print('Supplier.eta_invoices: EXISTS')
else:
    print('Supplier.eta_invoices: MISSING')

# Check EtaInvoice mapper
eta_mapper = sa_inspect(EtaInvoice)
print()
print('=== EtaInvoice Mapper Properties ===')
for attr in eta_mapper.iterate_properties:
    print(f'  Property: {attr.key}, back_populates={getattr(attr, "back_populates", None)}')