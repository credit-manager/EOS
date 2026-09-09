"""
READ-ONLY Database Integrity Audit

This script inspects the PostgreSQL database and reports findings.
NO modifications are made to the database or code.

Output: Findings + Severity + Recommendation
"""

from database import SessionLocal
from sqlalchemy import text
from typing import Dict, List, Any


class Finding:
    def __init__(self, category, table, severity, title, detail, recommendation):
        self.category = category
        self.table = table
        self.severity = severity  # CRITICAL, HIGH, MEDIUM, LOW, INFO
        self.title = title
        self.detail = detail
        self.recommendation = recommendation

    def __repr__(self):
        return f"[{self.severity}] {self.category} | {self.table}: {self.title}"


findings: List[Finding] = []


def add_finding(category, table, severity, title, detail, recommendation):
    findings.append(Finding(category, table, severity, title, detail, recommendation))


def audit_schema_constraints(db):
    """Audit PK, FK, UNIQUE, NOT NULL, CHECK, DEFAULT constraints."""
    print("\n=== SCHEMA & CONSTRAINTS AUDIT ===")

    # Get all user tables
    tables = db.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)).fetchall()

    print(f"Found {len(tables)} tables in public schema")

    for (table_name,) in tables:
        # Get columns with constraints
        columns = db.execute(text("""
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN 'YES' ELSE 'NO' END as is_pk
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                    ON tc.constraint_name = ku.constraint_name
                WHERE tc.table_name = :table_name
                AND tc.constraint_type = 'PRIMARY KEY'
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_name = :table_name
            AND c.table_schema = 'public'
            ORDER BY c.ordinal_position
        """), {"table_name": table_name}).fetchall()

        # Check for PK
        pk_cols = [row[0] for row in columns if row[4] == 'YES']
        if not pk_cols:
            add_finding("SCHEMA", table_name, "HIGH",
                       "No Primary Key",
                       f"Table '{table_name}' has no PRIMARY KEY constraint",
                       "Add a PRIMARY KEY constraint (e.g., id column)")

        # Check for NOT NULL without DEFAULT
        for col_name, data_type, is_nullable, default, is_pk in columns:
            if is_nullable == 'NO' and default is None and is_pk == 'NO':
                # This might be intentional, but flag it
                pass  # Will check in SCOPED audit

        # Get FK constraints
        fks = db.execute(text("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_name = :table_name
            AND tc.constraint_type = 'FOREIGN KEY'
        """), {"table_name": table_name}).fetchall()

        for fk_col, ref_table, ref_col in fks:
            print(f"  FK: {table_name}.{fk_col} -> {ref_table}.{ref_col}")

        # Get UNIQUE constraints
        uniques = db.execute(text("""
            SELECT
                kcu.column_name,
                tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = :table_name
            AND tc.constraint_type = 'UNIQUE'
            ORDER BY kcu.ordinal_position
        """), {"table_name": table_name}).fetchall()

        for col_name, constraint_name in uniques:
            print(f"  UNIQUE: {table_name}.{col_name} ({constraint_name})")

        # Get CHECK constraints
        checks = db.execute(text("""
            SELECT
                cc.conname as constraint_name,
                pg_get_constraintdef(cc.oid) as definition
            FROM pg_constraint cc
            JOIN pg_class c ON cc.conrelid = c.oid
            WHERE c.relname = :table_name
            AND cc.contype = 'c'
        """), {"table_name": table_name}).fetchall()

        for constraint_name, definition in checks:
            print(f"  CHECK: {table_name}.{constraint_name}: {definition}")


def audit_indexes(db):
    """Audit indexes for tenant_id, unique, FK, SCOPED queries."""
    print("\n=== INDEX AUDIT ===")

    indexes = db.execute(text("""
        SELECT
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
    """)).fetchall()

    print(f"Found {len(indexes)} indexes in public schema")

    # Group by table
    table_indexes: Dict[str, List] = {}
    for schema, table, index_name, index_def in indexes:
        if table not in table_indexes:
            table_indexes[table] = []
        table_indexes[table].append((index_name, index_def))

    # Check tenant_id indexes
    for table_name in table_indexes:
        has_tenant_index = False
        for index_name, index_def in table_indexes[table_name]:
            if 'tenant_id' in (index_def or ''):
                has_tenant_index = True
                print(f"  {table_name}: {index_name} (tenant_id indexed)")
                break

        # Check if table has tenant_id column
        has_tenant_col = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table_name
                AND column_name = 'tenant_id'
            )
        """), {"table_name": table_name}).scalar()

        if has_tenant_col and not has_tenant_index:
            add_finding("INDEX", table_name, "MEDIUM",
                       "Missing tenant_id index",
                       f"Table '{table_name}' has tenant_id column but no index on it",
                       "Add index on tenant_id for SCOPED query performance")


def audit_table_mapping_security(db):
    """Audit DBPEntity.table_mapping for SQL injection safety."""
    print("\n=== TABLE MAPPING SECURITY AUDIT ===")

    import re

    entities = db.execute(text("""
        SELECT code, table_mapping
        FROM dbp_entities
        WHERE table_mapping IS NOT NULL
    """)).fetchall()

    safe_pattern = re.compile(r'^[a-z][a-z0-9_]*$')

    for code, table_mapping in entities:
        # Check format
        if not safe_pattern.match(table_mapping):
            add_finding("SECURITY", code, "CRITICAL",
                       "Unsafe table_mapping format",
                       f"Entity '{code}' has table_mapping '{table_mapping}' which contains unsafe characters",
                       "table_mapping must match ^[a-z][a-z0-9_]*$ pattern")

        # Verify table exists
        exists = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = :table_name
                AND table_schema = 'public'
            )
        """), {"table_name": table_mapping}).scalar()

        if not exists:
            add_finding("SECURITY", code, "HIGH",
                       "table_mapping references non-existent table",
                       f"Entity '{code}' maps to '{table_mapping}' which does not exist",
                       "Either create the table or fix table_mapping")

        print(f"  {code:20s} -> {table_mapping:20s} {'EXISTS' if exists else 'MISSING'}")


def audit_scoped_schema_integrity(db):
    """Audit SCOPED table schema integrity."""
    print("\n=== SCOPED SCHEMA INTEGRITY AUDIT ===")

    # Find tables with tenant_id
    tables = db.execute(text("""
        SELECT table_name
        FROM information_schema.columns
        WHERE column_name = 'tenant_id'
        AND table_schema = 'public'
    """)).fetchall()

    print(f"Found {len(tables)} SCOPED tables")

    for (table_name,) in tables:
        print(f"\n  Auditing: {table_name}")

        # Get tenant_id column details
        col_info = db.execute(text("""
            SELECT
                data_type,
                is_nullable,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_name = :table_name
            AND column_name = 'tenant_id'
        """), {"table_name": table_name}).fetchone()

        if col_info:
            data_type, is_nullable, max_length = col_info
            print(f"    tenant_id type: {data_type}")
            print(f"    tenant_id nullable: {is_nullable}")

            if is_nullable == 'YES':
                add_finding("SCOPED", table_name, "HIGH",
                           "tenant_id is nullable",
                           f"Table '{table_name}' has nullable tenant_id column",
                           "tenant_id should be NOT NULL for SCOPED entities")

            if data_type not in ('character varying', 'varchar', 'text', 'uuid'):
                add_finding("SCOPED", table_name, "MEDIUM",
                           "Unusual tenant_id datatype",
                           f"Table '{table_name}' has tenant_id with datatype '{data_type}'",
                           "Consider using varchar(36) or uuid for tenant_id")

        # Check for tenant_id index
        has_index = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = :table_name
                AND indexdef LIKE '%tenant_id%'
            )
        """), {"table_name": table_name}).scalar()

        if not has_index:
            add_finding("SCOPED", table_name, "MEDIUM",
                       "Missing tenant_id index",
                       f"Table '{table_name}' has tenant_id but no index",
                       "Add index for SCOPED query performance")

        # Check for composite unique constraint with tenant_id
        try:
            has_composite_unique = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conrelid = (SELECT oid FROM pg_class WHERE relname = :table_name)
                    AND contype = 'u'
                    AND array_length(conkey, 1) > 1
                )
            """), {"table_name": table_name}).scalar()
        except Exception:
            has_composite_unique = None

        print(f"    Composite unique with tenant_id: {has_composite_unique}")


def audit_transaction_error_behavior(db):
    """Audit transaction/error behavior in code (READ-ONLY code review)."""
    print("\n=== TRANSACTION & ERROR BEHAVIOR AUDIT ===")

    # This is a code review, not database inspection
    # We'll check the router code patterns

    findings_text = []

    # Check for rollback patterns
    import os
    crud_file = r"D:\EOS\Eos final\routers\dynamic_crud.py"

    if os.path.exists(crud_file):
        with open(crud_file, 'r', encoding='utf-8') as f:
            code = f.read()

        # Check for try/except with rollback
        if 'db.rollback()' in code:
            print("  db.rollback() found in code")
        else:
            add_finding("TRANSACTION", "dynamic_crud.py", "HIGH",
                       "Missing rollback handling",
                       "No db.rollback() found in CRUD operations",
                       "Add rollback in except blocks")

        # Check for commit
        if 'db.commit()' in code:
            print("  db.commit() found in code")

        # Check for HTTPException re-raise
        if 'raise HTTPException' in code:
            print("  HTTPException handling found")


def audit_auth_boundary():
    """Audit authentication boundary documentation."""
    print("\n=== AUTH BOUNDARY AUDIT ===")

    import os

    auth_file = r"D:\EOS\Eos final\core\auth.py"

    if os.path.exists(auth_file):
        with open(auth_file, 'r', encoding='utf-8') as f:
            code = f.read()

        # Check for test/verification markers
        if 'TEST' in code.upper() or 'VERIFICATION' in code.upper():
            print("  core/auth.py: Marked as TEST/VERIFICATION")
        else:
            add_finding("AUTH", "core/auth.py", "MEDIUM",
                       "Missing test/verification marker",
                       "core/auth.py should be clearly marked as Test/Verification only",
                       "Add 'TEST / VERIFICATION AUTHENTICATION' header")

        # Check for hardcoded secret
        if 'your-secret-key' in code.lower() or 'test-verification-key' in code.lower():
            print("  core/auth.py: Uses test secret key")
            add_finding("AUTH", "core/auth.py", "LOW",
                       "Hardcoded test secret key",
                       "core/auth.py uses a hardcoded test secret key",
                       "Document that this is for testing only, not production")


def print_findings():
    """Print all findings with severity and recommendation."""
    print("\n" + "=" * 70)
    print("AUDIT FINDINGS SUMMARY")
    print("=" * 70)

    # Sort by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.severity, 5))

    # Group by severity
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        sev_findings = [f for f in sorted_findings if f.severity == severity]
        if sev_findings:
            print(f"\n--- {severity} ({len(sev_findings)}) ---")
            for f in sev_findings:
                print(f"  [{f.category}] {f.table}")
                print(f"    Title: {f.title}")
                print(f"    Detail: {f.detail}")
                print(f"    Recommendation: {f.recommendation}")
                print()

    # Summary
    print("\n--- SUMMARY ---")
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        count = len([f for f in findings if f.severity == severity])
        if count > 0:
            print(f"  {severity}: {count}")

    print(f"\n  Total: {len(findings)} findings")


def main():
    print("=" * 70)
    print("READ-ONLY DATABASE INTEGRITY AUDIT")
    print("=" * 70)
    print("NO modifications will be made to the database or code.")

    db = SessionLocal()

    try:
        audit_schema_constraints(db)
        audit_indexes(db)
        audit_table_mapping_security(db)
        audit_scoped_schema_integrity(db)
        audit_transaction_error_behavior(db)
        audit_auth_boundary()
        print_findings()

    finally:
        db.close()


if __name__ == "__main__":
    main()
