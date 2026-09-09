"""
Bank Reconciliation API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import SessionLocal
from core.auth import get_current_user
from core.reconciliation_engine import BankReconciliationEngine

router = APIRouter(prefix="/bank-reconciliation", tags=["Bank Reconciliation"])


class BankAccountCreate(BaseModel):
    account_name: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    iban: Optional[str] = None
    currency: Optional[str] = "SAR"
    opening_balance: Optional[float] = 0


class StatementImport(BaseModel):
    bank_account_id: str
    statement_date: str
    opening_balance: float
    closing_balance: float
    lines: List[dict]


class ManualMatch(BaseModel):
    line_id: str
    transaction_id: str


@router.get("/accounts")
async def list_accounts(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = BankReconciliationEngine(db).list_bank_accounts(user["tenant_id"])
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.post("/accounts")
async def create_account(body: BankAccountCreate, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = BankReconciliationEngine(db).create_bank_account(
            user["tenant_id"], body.account_name, body.bank_name,
            body.account_number, body.iban, body.currency, body.opening_balance
        )
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/import")
async def import_statement(body: StatementImport, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = BankReconciliationEngine(db).import_statement(
            user["tenant_id"], body.bank_account_id, body.statement_date,
            body.opening_balance, body.closing_balance, body.lines
        )
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/statements")
async def list_statements(bank_account_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = BankReconciliationEngine(db).list_statements(user["tenant_id"], bank_account_id)
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.get("/statements/{statement_id}/lines")
async def get_statement_lines(statement_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = BankReconciliationEngine(db).get_statement_lines(statement_id)
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.post("/statements/{statement_id}/auto-match")
async def auto_match(statement_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = BankReconciliationEngine(db).auto_match(user["tenant_id"], statement_id)
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/manual-match")
async def manual_match(body: ManualMatch, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = BankReconciliationEngine(db).manual_match(user["tenant_id"], body.line_id, body.transaction_id)
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/unreconcile/{line_id}")
async def unreconcile(line_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = BankReconciliationEngine(db).unreconcile(user["tenant_id"], line_id)
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/status/{bank_account_id}")
async def reconciliation_status(bank_account_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = BankReconciliationEngine(db).get_reconciliation_status(user["tenant_id"], bank_account_id)
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.get("/unmatched/{bank_account_id}")
async def unmatched_lines(bank_account_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = BankReconciliationEngine(db).get_unmatched_lines(user["tenant_id"], bank_account_id)
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()
