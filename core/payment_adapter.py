"""
P56 Payment Provider Adapter — provider-agnostic payment interface.
Core never calls Stripe/PayPal/etc directly. All payment operations
go through this adapter. Providers can be swapped without touching core.
"""
import secrets, time, os
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text


class PaymentProvider:
    """Base class for payment providers. Override for Stripe, PayPal, etc."""

    def create_charge(self, amount: float, currency: str,
                      description: str, metadata: Dict) -> Dict[str, Any]:
        """Charge a card. Returns {success, transaction_id, receipt_url}."""
        raise NotImplementedError

    def refund(self, transaction_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Refund a transaction. Returns {success, refund_id}."""
        raise NotImplementedError

    def get_transaction(self, transaction_id: str) -> Optional[Dict]:
        """Look up a transaction. Returns {id, status, amount, receipt_url}."""
        return None


class SimulatedPaymentProvider(PaymentProvider):
    """Test provider — always succeeds. Used in test mode."""

    def create_charge(self, amount: float, currency: str,
                      description: str, metadata: Dict) -> Dict[str, Any]:
        txn_id = f"SIM-{secrets.token_hex(8).upper()}"
        return {"success": True, "transaction_id": txn_id,
                "receipt_url": f"https://sim.receipt/{txn_id}",
                "amount": amount, "currency": currency}

    def refund(self, transaction_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        return {"success": True, "refund_id": f"SIMREF-{secrets.token_hex(6).upper()}",
                "amount": amount}

    def get_transaction(self, transaction_id: str) -> Optional[Dict]:
        return {"id": transaction_id, "status": "captured", "amount": 0}


class StripeTestPaymentProvider(PaymentProvider):
    """Stripe Test Mode provider. Uses Stripe API with test secret key.
    Test card: 4242424242424242, CVC: 123, Exp: 12/28.
    """

    def __init__(self):
        self.secret_key = os.getenv("EOS_STRIPE_SECRET_KEY", "")
        self.api_base = "https://api.stripe.com/v1"

    def _headers(self):
        return {"Authorization": f"Bearer {self.secret_key}", "Content-Type": "application/x-www-form-urlencoded"}

    def create_charge(self, amount: float, currency: str,
                      description: str, metadata: Dict) -> Dict[str, Any]:
        if not self.secret_key:
            return {"success": False, "error": "Stripe secret key not configured"}
        try:
            import httpx
            data = {
                "amount": int(amount * 100),
                "currency": currency.lower(),
                "description": description,
                "metadata[tenant_id]": metadata.get("tenant_id", ""),
                "metadata[invoice_id]": metadata.get("invoice_id", ""),
            }
            r = httpx.post(f"{self.api_base}/payment_intents", headers=self._headers(), data=data, timeout=30)
            if r.status_code == 200:
                pi = r.json()
                return {"success": True, "transaction_id": pi["id"],
                        "receipt_url": pi.get("receipt_url", ""),
                        "amount": amount, "currency": currency,
                        "status": pi.get("status", "succeeded")}
            else:
                err = r.json().get("error", {}).get("message", "Stripe error")
                return {"success": False, "error": err}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def refund(self, transaction_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        if not self.secret_key:
            return {"success": False, "error": "Stripe secret key not configured"}
        try:
            import httpx
            data = {"payment_intent": transaction_id}
            if amount is not None:
                data["amount"] = int(amount * 100)
            r = httpx.post(f"{self.api_base}/refunds", headers=self._headers(), data=data, timeout=30)
            if r.status_code == 200:
                ref = r.json()
                return {"success": True, "refund_id": ref["id"], "amount": amount}
            else:
                err = r.json().get("error", {}).get("message", "Stripe refund error")
                return {"success": False, "error": err}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_transaction(self, transaction_id: str) -> Optional[Dict]:
        if not self.secret_key:
            return None
        try:
            import httpx
            r = httpx.get(f"{self.api_base}/payment_intents/{transaction_id}",
                          headers=self._headers(), timeout=30)
            if r.status_code == 200:
                pi = r.json()
                return {"id": pi["id"], "status": pi.get("status"),
                        "amount": pi.get("amount", 0) / 100}
            return None
        except Exception:
            return None


class PaymentAdapter:
    """Wraps a PaymentProvider and records all transactions in dbp_payments."""

    def __init__(self, db: Session, provider: Optional[PaymentProvider] = None):
        self.db = db
        self.provider = provider or SimulatedPaymentProvider()

    def charge(self, tenant_id: str, amount: float, currency: str,
               invoice_id: str, description: str = "",
               payment_method: str = "card") -> Dict[str, Any]:
        result = self.provider.create_charge(
            amount, currency, description or f"Invoice {invoice_id}",
            {"tenant_id": tenant_id, "invoice_id": invoice_id})

        if not result.get("success"):
            self._record(tenant_id, invoice_id, amount, currency,
                         payment_method, "failed", result.get("transaction_id"),
                         error=str(result))
            return {"success": False, "error": result.get("error", "Payment declined")}

        self._record(tenant_id, invoice_id, amount, currency,
                     payment_method, "captured", result.get("transaction_id"),
                     receipt_url=result.get("receipt_url"))
        return {"success": True, "transaction_id": result["transaction_id"],
                "receipt_url": result.get("receipt_url"),
                "amount": amount, "currency": currency}

    def refund_payment(self, transaction_id: str,
                       amount: Optional[float] = None) -> Dict[str, Any]:
        result = self.provider.refund(transaction_id, amount)
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Refund failed")}
        return {"success": True, "refund_id": result["refund_id"], "amount": amount}

    def get_status(self, tenant_id: str, invoice_id: str) -> Optional[Dict]:
        row = self.db.execute(text(
            "SELECT id, amount, currency, status, transaction_id "
            "FROM dbp_payments WHERE tenant_id = :t AND invoice_id = :iid "
            "ORDER BY created_at DESC LIMIT 1"
        ), {"t": tenant_id, "iid": invoice_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "amount": float(row[1]), "currency": row[2],
                "status": row[3], "transaction_id": row[4]}

    def _record(self, tenant_id: str, invoice_id: str, amount: float,
                currency: str, payment_method: str, status: str,
                transaction_id: Optional[str], receipt_url: Optional[str] = None,
                error: Optional[str] = None):
        rid = secrets.token_hex(8)
        self.db.execute(text(
            "INSERT INTO dbp_payments "
            "(tenant_id, invoice_id, amount, currency, payment_method, status, "
            "transaction_id, receipt_url, error_message) "
            "VALUES (:t, :iid, :amt, :cur, :pm, :st, :txn, :rc, :err)"
        ), {"t": tenant_id, "iid": invoice_id, "amt": amount, "cur": currency,
            "pm": payment_method, "st": status, "txn": transaction_id,
            "rc": receipt_url, "err": error})
        self.db.flush()


def get_payment_adapter(db: Session) -> PaymentAdapter:
    """Factory — returns the correct adapter based on EOS_PAYMENT_MODE."""
    mode = os.getenv("EOS_PAYMENT_MODE", "test").lower()
    if mode == "stripe":
        return PaymentAdapter(db, StripeTestPaymentProvider())
    return PaymentAdapter(db, SimulatedPaymentProvider())
