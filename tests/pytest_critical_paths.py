from decimal import Decimal

import pytest
from fastapi import HTTPException

from core.accounting_engine import AccountingEngine
from core.auth import _authorize_user
from core.industry_security import FieldSecurity
from core.validation_engine import InputValidator


class FakeResult:
    def __init__(self, rows=None, rowcount=0):
        self.rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class AccountingDB:
    def __init__(self, results):
        self.results = list(results)
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params or {}))
        return self.results.pop(0) if self.results else FakeResult()

    def commit(self):
        pass

    def rollback(self):
        pass

    def flush(self):
        pass


def _compact(sql):
    return sql.replace(" ", "")


def test_account_creation_is_tenant_and_company_scoped():
    db = AccountingDB([FakeResult([('tenant-a',)]), FakeResult([])])
    account_id = AccountingEngine(db).create_account(
        tenant_id='tenant-a', company_id='company-a', code='1000',
        name_en='Cash', account_type='asset'
    )
    assert account_id
    assert 'tenant_id=:tid' in _compact(db.statements[1][0])
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


def test_account_creation_rejects_invalid_account_type_without_db_write():
    db = AccountingDB([])
    assert AccountingEngine(db).create_account(
        tenant_id='tenant-a', company_id='company-a', code='1000',
        name_en='Cash', account_type='not-an-account-type'
    ) is None
    assert db.statements == []


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


def test_journal_post_validates_all_accounts_before_any_gl_update():
    db = AccountingDB([
        FakeResult([('je-1', 'draft', 'company-a')]),
        FakeResult([
            ('l1', 'cash', Decimal('100.00'), Decimal('0')),
            ('l2', 'foreign-sales', Decimal('0'), Decimal('100.00')),
        ]),
        FakeResult([('company-a',)]),
        FakeResult([('company-b',)]),
    ])
    with pytest.raises(HTTPException) as exc:
        AccountingEngine(db).post_journal_entry('je-1', 'tenant-a')
    assert exc.value.status_code == 403
    assert not any('UPDATE dbp_accounts' in sql for sql, _ in db.statements)


def test_add_journal_line_rejects_account_from_another_company():
    db = AccountingDB([
        FakeResult([('company-a',)]),
        FakeResult([('company-b',)]),
    ])
    with pytest.raises(HTTPException) as exc:
        AccountingEngine(db).add_journal_line(
            journal_entry_id='je-1', account_id='account-b', tenant_id='tenant-a', debit=10
        )
    assert exc.value.status_code == 403
    assert not any('INSERT INTO dbp_journal_lines' in sql for sql, _ in db.statements)


def test_add_journal_line_rejects_negative_or_zero_amounts_without_db_access():
    for debit, credit in [(-1, 0), (0, -1), (0, 0)]:
        db = AccountingDB([])
        assert AccountingEngine(db).add_journal_line(
            journal_entry_id='je-1', account_id='account-a', tenant_id='tenant-a',
            debit=debit, credit=credit
        ) is None
        assert db.statements == []


def test_journal_post_updates_only_tenant_and_company_scoped_gl():
    db = AccountingDB([
        FakeResult([('je-1', 'draft', 'company-a')]),
        FakeResult([
            ('l1', 'cash', Decimal('100.00'), Decimal('0')),
            ('l2', 'sales', Decimal('0'), Decimal('100.00')),
        ]),
        FakeResult([('company-a',)]),
        FakeResult([('company-a',)]),
        FakeResult(rowcount=1), FakeResult(rowcount=1), FakeResult(rowcount=1),
    ])
    result = AccountingEngine(db).post_journal_entry('je-1', 'tenant-a')
    assert result['success'] is True
    assert result['total_debit'] == 100.0
    assert result['total_credit'] == 100.0
    assert all(
        'tenant_id=:t' in _compact(sql) and 'company_id=:cid' in _compact(sql)
        for sql, _ in db.statements if 'UPDATE dbp_accounts' in sql
    )
    assert any(
        "status='posted'" in _compact(sql)
        and 'tenant_id=:t' in _compact(sql)
        and 'company_id=:cid' in _compact(sql)
        for sql, _ in db.statements
    )


def test_journal_post_rejects_non_draft_without_gl_update():
    db = AccountingDB([FakeResult([('je-1', 'posted', 'company-a')])])
    result = AccountingEngine(db).post_journal_entry('je-1', 'tenant-a')
    assert result['success'] is False
    assert 'Cannot post entry' in result['error']
    assert not any('UPDATE dbp_accounts' in sql for sql, _ in db.statements)


@pytest.mark.asyncio
async def test_authorization_rejects_missing_user():
    with pytest.raises(HTTPException) as exc:
        _authorize_user(None, 'accounting', 'read')
    assert exc.value.status_code == 401
