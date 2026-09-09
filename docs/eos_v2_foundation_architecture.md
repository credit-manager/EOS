# EOS DBP v2 Foundation ERP Architecture

## Decision

EOS v2 uses a **hybrid metadata-first architecture**:

- The platform's arbitrary business objects remain metadata-defined and use the dynamic record engine.
- Core ERP primitives that require strong transactional invariants (Sales Orders, Purchase Orders, Inventory balances/movements, Employees, Projects, Accounting) have explicit domain aggregates and dedicated persistence.
- Both paths share the same tenant context, authorization, event/outbox and operational boundaries.

This avoids turning critical accounting/inventory invariants into untyped JSON while preserving EOS's ability to generate industry-specific entities dynamically.

## Foundation module contract

Every foundation module provides:

1. immutable domain invariants;
2. tenant-scoped application operations;
3. tenant-scoped persistence;
4. authenticated API transport;
5. database uniqueness/check constraints where applicable;
6. tests for invalid state and tenant isolation.

## Current modules

- Sales: order lines, totals, lifecycle transitions.
- Purchasing: order lines, totals, lifecycle transitions.
- Inventory: signed movements and non-negative stock balances.
- HR: tenant-unique employee numbers and employment identity.
- Projects: tenant-unique project codes and valid date ranges.

## Boundary rule

Foundation modules must not read the legacy database or mutate legacy schemas. Cross-module references are UUID identities and must be resolved through an explicit application boundary. Accounting integration is performed through deterministic posting instructions rather than direct table writes.
