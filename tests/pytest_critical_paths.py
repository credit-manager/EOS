"""Focused pytest coverage for critical accounting and authorization paths."""
from decimal import Decimal

import pytest
from fastapi import HTTPException

from core.accounting_engine import AccountingEngine
from core.auth import require_permission
from core.security import FieldSecurity, InputValidator


class FakeResult:
    def __init__(self, rows=None, rowcount=1):
        self.rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def scalar(self):
        return self.rows[0][0] if self.rows else None


class AccountingDB:
    def __init__(self, responses):
        self.responses = list(responses)
        self.statements = []

    def execute(self, statement, params=None):
        self.statements.append((str(statement), params or {}))
        return self.responses.pop(0) if self.responses else FakeResult()

    def flush(self):
        pass


def test_account_creation_is_tenant_and_company_scoped():
    db = AccountingDB([FakeResult([('tenant-a',)]), FakeResult([])])
    account_id = AccountingEngine(db).create_account(
        tenant_id='tenant-a', company_id='company-a', code='1000',
        name_en='Cash', account_type='asset'
    )
    assert account_id
    assert 'tenant_id = :tid' in db.statements[1][0]
    assert db.statements[1][1]['tid'] == 'tenant-a'
    assert db.statements[1][1]['cid'] == 'company-a'


def test_account_creation_rejects_foreign_company():
    db = AccountingDB([FakeResult([('tenant-b',)])])
    with pytest.raises(HTTPException) as exc:
        AccountingEngine(db).create_account(
            tenant_id='tenant-a', company_id='company-b', code='1000',
            name_en='Cash', account_type='asset'
        )
    assert exc.value.status_code == 403


def test_journal_post_rejects_unbalanced_entry_without_gl_update():
    db = AccountingDB([
        FakeResult([('je-1', 'draft', 'company-a')]),
        FakeResult([
            ('l1', 'cash', Decimal('100.00'), Decimal('0')),
            ('l2', 'sales', Decimal('0'), Decimal('99.00')),
        ]),
    ])
    result = AccountingEngine(db).post_journal_entry('je-1', 'tenant-a')
    assert result['success'] is False
    assert 'not balanced' in result['error']
    assert not any('UPDATE dbp_accounts' in sql for sql, _ in db.statements)


def test_journal_post_updates_only_tenant_scoped_gl():
    db = AccountingDB([
        FakeResult([('je-1', 'draft', 'company-a')]),
        FakeResult([
            ('l1', 'cash', Decimal('100.00'), Decimal('0')),
            ('l2', 'sales', Decimal('0'), Decimal('100.00')),
        ]),
        FakeResult(rowcount=1), FakeResult(rowcount=1), FakeResult(rowcount=1),
    ])
    result = AccountingEngine(db).post_journal_entry('je-1', 'tenant-a')
    assert result['success'] is True
    assert result['total_debit'] == 100.0
    assert result['total_credit'] == 100.0
    assert any('UPDATE dbp_accounts' in sql and 'tenant_id = :t' in sql for sql, _ in db.statements)
    assert any("status='posted'" in sql and 'tenant_id = :t' in sql for sql, _ in db.statements)


@pytest.mark.asyncio
async def test_authorization_requires_authentication():
    with pytest.raises(HTTPException) as exc:
        await require_permission('accounting', 'read')(None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_authorization_denies_missing_permission():
    with pytest.raises(HTTPException) as exc:
        await require_permission('accounting', 'delete')({'permissions': [], 'roles': ['user']})
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_authorization_allows_exact_permission():
    assert await require_permission('accounting', 'read')({'permissions': ['accounting:read'], 'roles': ['user']}) is None


@pytest.mark.asyncio
async def test_authorization_wildcard_allows_access():
    assert await require_permission('accounting', 'delete')({'permissions': ['*:*'], 'roles': []}) is None


def test_field_security_blocks_unauthorized_write():
    payload, blocked = FieldSecurity.filter_writable_columns(
        {'amount': 10, 'approved': True},
        {'approved': {'writable_roles': ['accounting:approve']}},
        ['accounting:read'],
    )
    assert payload == {'amount': 10}
    assert blocked == ['approved']


def test_input_validation_rejects_invalid_enum_and_range():
    errors = InputValidator.validate_record(
        {'status': 'invalid', 'amount': -1},
        [
            {'code': 'status', 'field_type': 'string', 'is_required': True, 'enum_values': ['draft', 'posted']},
            {'code': 'amount', 'field_type': 'number', 'is_required': True, 'ui_config': {'min': 0}},
        ],
    )
    assert any('status' in e for e in errors)
    assert any('amount' in e for e in errors)


def test_input_validation_accepts_valid_record():
    assert InputValidator.validate_record(
        {'status': 'posted', 'amount': 100},
        [
            {'code': 'status', 'field_type': 'string', 'is_required': True, 'enum_values': ['draft', 'posted']},
            {'code': 'amount', 'field_type': 'number', 'is_required': True, 'ui_config': {'min': 0}},
        ],
    ) == []
