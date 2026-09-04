"""P26 Sales & Invoicing Engine — tenant/company scoped."""
import uuid
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session

class SalesEngine:
    STATUSES_QUOTE={"draft","sent","accepted","rejected","converted"}
    STATUSES_ORDER={"draft","confirmed","partially_delivered","delivered","closed","cancelled"}
    def __init__(self,db:Session):self.db=db

    def _verify_company(self,tenant_id,company_id):
        if not self.db.execute(text("SELECT id FROM dbp_companies WHERE id=:cid AND tenant_id=:tid"),{"cid":company_id,"tid":tenant_id}).fetchone():
            raise ValueError("Company does not belong to tenant")
    def _verify_customer(self,tenant_id,company_id,customer_id):
        if not self.db.execute(text("SELECT id FROM dbp_customers WHERE id=:id AND tenant_id=:tid AND company_id=:cid"),{"id":customer_id,"tid":tenant_id,"cid":company_id}).fetchone():
            raise ValueError("Customer does not belong to tenant/company")

    def create_customer(self,tenant_id,company_id,name,**kw):
        self._verify_company(tenant_id,company_id); cid=str(uuid.uuid4()); code=self._next_code(company_id,"CUS",tenant_id)
        self.db.execute(text("INSERT INTO dbp_customers (id,tenant_id,company_id,code,name,contact_name,email,phone,address,tax_number,payment_terms,credit_limit,currency_code) VALUES (:id,:tid,:cid,:code,:name,:cn,:email,:phone,:addr,:tax,:pt,:cl,:cc)"),{"id":cid,"tid":tenant_id,"cid":company_id,"code":code,"name":name,"cn":kw.get("contact_name"),"email":kw.get("email"),"phone":kw.get("phone"),"addr":kw.get("address"),"tax":kw.get("tax_number"),"pt":kw.get("payment_terms","net30"),"cl":kw.get("credit_limit",0),"cc":kw.get("currency_code","SAR")});self.db.flush();return cid
    def list_customers(self,company_id,tenant_id=None):
        if not tenant_id:return []
        rows=self.db.execute(text("SELECT id,code,name,contact_name,email,phone,payment_terms,credit_limit,is_active FROM dbp_customers WHERE company_id=:cid AND tenant_id=:tid ORDER BY name"),{"cid":company_id,"tid":tenant_id}).fetchall()
        return [{"id":r[0],"code":r[1],"name":r[2],"contact_name":r[3],"email":r[4],"phone":r[5],"payment_terms":r[6],"credit_limit":float(r[7]) if r[7] is not None else 0,"is_active":bool(r[8])} for r in rows]

    def create_quotation(self,tenant_id,company_id,customer_id,quote_date,lines,**kw):
        self._verify_company(tenant_id,company_id);self._verify_customer(tenant_id,company_id,customer_id);qid=str(uuid.uuid4());qnum=self._next_code(company_id,"QT",tenant_id);total,tax=self._calc_totals(lines)
        self.db.execute(text("INSERT INTO dbp_sales_quotations (id,tenant_id,company_id,quote_number,customer_id,quote_date,valid_until,total_amount,tax_amount,currency_code,notes,created_by) VALUES (:id,:tid,:cid,:qn,:custid,:qd,:vu,:ta,:tx,:cc,:notes,:cb)"),{"id":qid,"tid":tenant_id,"cid":company_id,"qn":qnum,"custid":customer_id,"qd":quote_date,"vu":kw.get("valid_until"),"ta":total,"tx":tax,"cc":kw.get("currency_code","SAR"),"notes":kw.get("notes"),"cb":kw.get("created_by")});self._insert_lines("dbp_sales_quotation_lines",tenant_id,"quote_id",qid,lines);self.db.flush();return qid
    def convert_quotation_to_order(self,quote_id,tenant_id,company_id,created_by=None):
        self._verify_company(tenant_id,company_id);q=self.db.execute(text("SELECT id,status,customer_id,quote_date,total_amount,tax_amount,currency_code,notes FROM dbp_sales_quotations WHERE id=:qid AND tenant_id=:tid AND company_id=:cid"),{"qid":quote_id,"tid":tenant_id,"cid":company_id}).fetchone()
        if not q:return {"success":False,"error":"Quotation not found"}
        if q[1]=="converted":return {"success":False,"error":"Quotation already converted"}
        self._verify_customer(tenant_id,company_id,q[2]); rows=self.db.execute(text("SELECT item_id,description,quantity,unit_price,tax_rate,tax_amount FROM dbp_sales_quotation_lines WHERE quote_id=:qid AND tenant_id=:tid ORDER BY line_number"),{"qid":quote_id,"tid":tenant_id}).fetchall();lines=[{"item_id":r[0],"description":r[1],"quantity":float(r[2]),"unit_price":float(r[3]),"tax_rate":float(r[4] or 0),"tax_amount":float(r[5]) if r[5] is not None else None} for r in rows];total,tax=self._calc_totals(lines);oid=self._insert_sales_order(tenant_id,company_id,q[2],str(q[3]),total,tax,q[6],q[7],created_by);self._insert_lines("dbp_sales_order_lines",tenant_id,"order_id",oid,lines);self.db.execute(text("UPDATE dbp_sales_orders SET quotation_id=:qid WHERE id=:oid AND tenant_id=:tid AND company_id=:cid"),{"qid":quote_id,"oid":oid,"tid":tenant_id,"cid":company_id});self.db.execute(text("UPDATE dbp_sales_quotations SET status='converted' WHERE id=:qid AND tenant_id=:tid AND company_id=:cid"),{"qid":quote_id,"tid":tenant_id,"cid":company_id});self.db.flush();return {"success":True,"order_id":oid}

    def create_sales_order(self,tenant_id,company_id,customer_id,order_date,lines,**kw):
        self._verify_company(tenant_id,company_id);self._verify_customer(tenant_id,company_id,customer_id);oid=self._insert_sales_order(tenant_id,company_id,customer_id,order_date,*self._calc_totals(lines),kw.get("currency_code","SAR"),kw.get("notes"),kw.get("created_by"));self._insert_lines("dbp_sales_order_lines",tenant_id,"order_id",oid,lines);self.db.flush();return oid
    def get_sales_order(self,order_id,tenant_id=None):
        if not tenant_id:return None
        row=self.db.execute(text("SELECT o.id,o.order_number,o.customer_id,c.name,o.quotation_id,o.order_date,o.status,o.total_amount,o.tax_amount,o.currency_code,o.notes FROM dbp_sales_orders o LEFT JOIN dbp_customers c ON o.customer_id=c.id AND c.tenant_id=o.tenant_id WHERE o.id=:oid AND o.tenant_id=:tid"),{"oid":order_id,"tid":tenant_id}).fetchone()
        if not row:return None
        lines=self.db.execute(text("SELECT l.id,l.line_number,l.item_id,l.description,l.quantity,l.unit_price,l.line_total,l.quantity_delivered,l.tax_rate,l.tax_amount FROM dbp_sales_order_lines l WHERE l.order_id=:oid AND l.tenant_id=:tid ORDER BY l.line_number"),{"oid":order_id,"tid":tenant_id}).fetchall();return {"id":row[0],"order_number":row[1],"customer_id":row[2],"customer_name":row[3],"quotation_id":row[4],"order_date":str(row[5]) if row[5] else None,"status":row[6],"total_amount":float(row[7] or 0),"tax_amount":float(row[8] or 0),"currency_code":row[9],"notes":row[10],"lines":[{"id":l[0],"line_number":l[1],"item_id":l[2],"description":l[3],"quantity":float(l[4]),"unit_price":float(l[5]),"line_total":float(l[6]),"quantity_delivered":float(l[7] or 0),"tax_rate":float(l[8] or 0),"tax_amount":float(l[9] or 0)} for l in lines]}
    def list_sales_orders(self,company_id,status=None,tenant_id=None):
        if not tenant_id:return []
        conditions=["o.company_id=:cid","o.tenant_id=:tid"];p={"cid":company_id,"tid":tenant_id}
        if status:conditions.append("o.status=:st");p["st"]=status
        rows=self.db.execute(text(f"SELECT o.id,o.order_number,c.name,o.order_date,o.status,o.total_amount,o.currency_code FROM dbp_sales_orders o LEFT JOIN dbp_customers c ON o.customer_id=c.id AND c.tenant_id=o.tenant_id WHERE {' AND '.join(conditions)} ORDER BY o.order_date DESC"),p).fetchall();return [{"id":r[0],"order_number":r[1],"customer_name":r[2],"order_date":str(r[3]) if r[3] else None,"status":r[4],"total_amount":float(r[5] or 0),"currency_code":r[6]} for r in rows]

    def create_invoice(self,tenant_id,company_id,customer_id,invoice_date,lines,**kw):
        self._verify_company(tenant_id,company_id);self._verify_customer(tenant_id,company_id,customer_id);iid=str(uuid.uuid4());num=self._next_code(company_id,"INV",tenant_id);total,tax=self._calc_totals(lines);self.db.execute(text("INSERT INTO dbp_sales_invoices (id,tenant_id,company_id,invoice_number,customer_id,order_id,invoice_date,due_date,total_amount,tax_amount,paid_amount,currency_code,notes,created_by) VALUES (:id,:tid,:cid,:in,:custid,:oid,:idate,:dd,:ta,:tx,0,:cc,:notes,:cb)"),{"id":iid,"tid":tenant_id,"cid":company_id,"in":num,"custid":customer_id,"oid":kw.get("order_id"),"idate":invoice_date,"dd":kw.get("due_date"),"ta":total,"tx":tax,"cc":kw.get("currency_code","SAR"),"notes":kw.get("notes"),"cb":kw.get("created_by")});self._insert_lines("dbp_sales_invoice_lines",tenant_id,"invoice_id",iid,lines);self.db.flush();return iid
    def get_invoice(self,invoice_id,tenant_id=None):
        if not tenant_id:return None
        row=self.db.execute(text("SELECT i.id,i.invoice_number,i.customer_id,c.name,i.order_id,i.invoice_date,i.due_date,i.status,i.total_amount,i.tax_amount,i.paid_amount,i.currency_code,i.notes FROM dbp_sales_invoices i LEFT JOIN dbp_customers c ON i.customer_id=c.id AND c.tenant_id=i.tenant_id WHERE i.id=:iid AND i.tenant_id=:tid"),{"iid":invoice_id,"tid":tenant_id}).fetchone()
        if not row:return None
        lines=self.db.execute(text("SELECT l.id,l.line_number,l.item_id,l.description,l.quantity,l.unit_price,l.line_total,l.tax_rate,l.tax_amount FROM dbp_sales_invoice_lines l WHERE l.invoice_id=:iid AND l.tenant_id=:tid ORDER BY l.line_number"),{"iid":invoice_id,"tid":tenant_id}).fetchall();return {"id":row[0],"invoice_number":row[1],"customer_id":row[2],"customer_name":row[3],"order_id":row[4],"invoice_date":str(row[5]) if row[5] else None,"due_date":str(row[6]) if row[6] else None,"status":row[7],"total_amount":float(row[8] or 0),"tax_amount":float(row[9] or 0),"paid_amount":float(row[10] or 0),"currency_code":row[11],"notes":row[12],"lines":[{"id":l[0],"line_number":l[1],"item_id":l[2],"description":l[3],"quantity":float(l[4]),"unit_price":float(l[5]),"line_total":float(l[6]),"tax_rate":float(l[7] or 0),"tax_amount":float(l[8] or 0)} for l in lines]}
    def list_invoices(self,company_id,status=None,tenant_id=None):
        if not tenant_id:return []
        conditions=["i.company_id=:cid","i.tenant_id=:tid"];p={"cid":company_id,"tid":tenant_id}
        if status:conditions.append("i.status=:st");p["st"]=status
        rows=self.db.execute(text(f"SELECT i.id,i.invoice_number,c.name,i.invoice_date,i.due_date,i.status,i.total_amount,i.tax_amount,i.paid_amount,i.currency_code FROM dbp_sales_invoices i LEFT JOIN dbp_customers c ON i.customer_id=c.id AND c.tenant_id=i.tenant_id WHERE {' AND '.join(conditions)} ORDER BY i.invoice_date DESC"),p).fetchall();return [{"id":r[0],"invoice_number":r[1],"customer_name":r[2],"invoice_date":str(r[3]) if r[3] else None,"due_date":str(r[4]) if r[4] else None,"status":r[5],"total_amount":float(r[6] or 0),"tax_amount":float(r[7] or 0),"paid_amount":float(r[8] or 0),"currency_code":r[9]} for r in rows]
    def record_payment(self,invoice_id,amount,payment_date,tenant_id=None,**kw):
        if not tenant_id:return {"success":False,"error":"Tenant required"}
        row=self.db.execute(text("SELECT total_amount,tax_amount,paid_amount,status FROM dbp_sales_invoices WHERE id=:iid AND tenant_id=:tid"),{"iid":invoice_id,"tid":tenant_id}).fetchone()
        if not row:return {"success":False,"error":"Invoice not found"}
        if row[3]=="cancelled":return {"success":False,"error":"Cannot record payment on a cancelled invoice"}
        if amount<=0:return {"success":False,"error":"Payment amount must be positive"}
        total=float(row[0] or 0)+float(row[1] or 0);paid=float(row[2] or 0);balance=total-paid
        if round(amount,4)>round(balance,4):return {"success":False,"error":f"Payment {amount} exceeds remaining balance {balance}"}
        new_paid=paid+amount;status="paid" if round(new_paid,4)>=round(total,4) else "partial";self.db.execute(text("UPDATE dbp_sales_invoices SET paid_amount=:pa,status=:st WHERE id=:iid AND tenant_id=:tid"),{"pa":new_paid,"st":status,"iid":invoice_id,"tid":tenant_id});self.db.flush();return {"success":True,"paid_amount":new_paid,"status":status}

    def _calc_totals(self,lines):
        total=sum(float(l.get("quantity",0))*float(l.get("unit_price",0)) for l in lines);tax=sum(float(l["tax_amount"]) if l.get("tax_amount") is not None else float(l.get("quantity",0))*float(l.get("unit_price",0))*float(l.get("tax_rate",0) or 0)/100 for l in lines);return total,tax
    def _insert_lines(self,table,tenant_id,fk_col,fk_id,lines):
        delivered=table=="dbp_sales_order_lines";cols=f"id,tenant_id,{fk_col},line_number,item_id,description,quantity,unit_price,line_total,tax_rate,tax_amount";vals=":id,:tid,:fkid,:ln,:iid,:desc,:qty,:up,:lt,:tr,:txa"; 
        if delivered:cols+=",quantity_delivered";vals+=",:qd"
        for i,line in enumerate(lines,1):
            lt=float(line.get("quantity",0))*float(line.get("unit_price",0));p={"id":str(uuid.uuid4()),"tid":tenant_id,"fkid":fk_id,"ln":i,"iid":line.get("item_id"),"desc":line.get("description"),"qty":line.get("quantity",0),"up":line.get("unit_price",0),"lt":lt,"tr":line.get("tax_rate",0),"txa":line.get("tax_amount") if line.get("tax_amount") is not None else lt*float(line.get("tax_rate",0) or 0)/100};
            if delivered:p["qd"]=line.get("quantity_delivered",0)
            self.db.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({vals})"),p)
    def _insert_sales_order(self,tenant_id,company_id,customer_id,order_date,total,tax,currency,notes,created_by):
        self._verify_company(tenant_id,company_id);self._verify_customer(tenant_id,company_id,customer_id);oid=str(uuid.uuid4());code=self._next_code(company_id,"SO",tenant_id);self.db.execute(text("INSERT INTO dbp_sales_orders (id,tenant_id,company_id,order_number,customer_id,order_date,total_amount,tax_amount,currency_code,notes,created_by) VALUES (:id,:tid,:cid,:on,:custid,:od,:ta,:tx,:cc,:notes,:cb)"),{"id":oid,"tid":tenant_id,"cid":company_id,"on":code,"custid":customer_id,"od":order_date,"ta":total,"tx":tax,"cc":currency,"notes":notes,"cb":created_by});return oid
    def _next_code(self,company_id,prefix,tenant_id):
        table,col={"CUS":("dbp_customers","code"),"QT":("dbp_sales_quotations","quote_number"),"SO":("dbp_sales_orders","order_number"),"INV":("dbp_sales_invoices","invoice_number")}[prefix];rows=self.db.execute(text(f"SELECT {col} FROM {table} WHERE company_id=:cid AND tenant_id=:tid AND {col} LIKE :pre"),{"cid":company_id,"tid":tenant_id,"pre":f"{prefix}-%"}).fetchall();num=0
        for r in rows:
            try:num=max(num,int(str(r[0]).rsplit("-",1)[1]))
            except (ValueError,IndexError):pass
        return f"{prefix}-{num+1:06d}"
