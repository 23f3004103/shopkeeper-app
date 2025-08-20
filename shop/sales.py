from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import Item, Sale, SaleItem, StockMovement, CreditAccount, CreditTxn, OnlinePayment
from . import db
from sqlalchemy import func
from datetime import datetime
from decimal import Decimal

sales_bp = Blueprint("sales", __name__, template_folder="templates")

def next_invoice_no():
    # Simple incremental invoice number YYYYMMDD-XXXX
    today = datetime.utcnow().strftime("%Y%m%d")
    last = db.session.query(func.max(Sale.invoice_no)).filter(Sale.invoice_no.like(f"{today}-%")).scalar()
    if not last:
        return f"{today}-0001"
    seq = int(last.split("-")[1]) + 1
    return f"{today}-{seq:04d}"

@sales_bp.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
    if request.method == "POST":
        # collect and combine SKU quantities into a map to avoid duplicate lines
        sku_map = {}
        subtotal = Decimal("0")
        discount = Decimal(request.form.get("discount", "0") or "0")
        payment_method = request.form.get("payment_method")
        customer_name = request.form.get("customer_name") or None
        paid_amount = Decimal(request.form.get("paid_amount", "0") or "0")
        provider = request.form.get("provider") or None
        reference = request.form.get("reference") or None

        for key in request.form:
            if key.startswith("sku_"):
                sku = key.split("_", 1)[1]
                try:
                    qty = Decimal(request.form.get(f"qty_{sku}", "0") or "0")
                except:
                    qty = Decimal("0")
                if qty <= 0:
                    continue
                item = Item.query.filter_by(sku=sku).first()
                if not item:
                    continue
                if sku in sku_map:
                    sku_map[sku]['qty'] += qty
                else:
                    sku_map[sku] = {'item': item, 'qty': qty, 'price': Decimal(item.sale_price), 'tax': Decimal(item.tax_rate)}

        # convert map to list for further processing
        items = []
        for sku, v in sku_map.items():
            items.append((v['item'], v['qty'], v['price'], v['tax']))
            subtotal += v['price'] * v['qty']

        tax = sum((price*qty)*(taxrate/Decimal("100")) for (item, qty, price, taxrate) in items)
        total = subtotal + tax - discount
        change_due = Decimal("0")

        # validate stock availability before creating the sale
        insufficient = []
        for (item, qty, price, taxrate) in items:
            try:
                available = Decimal(item.stock_qty or 0)
            except:
                available = Decimal(0)
            if qty > available:
                insufficient.append((item.sku, item.name, float(available), float(qty)))
        if insufficient:
            msgs = [f"{s[0]} ({s[1]}): available {s[2]}, requested {s[3]}" for s in insufficient]
            flash("Insufficient stock for: " + "; ".join(msgs), "danger")
            return redirect(url_for("sales.cart"))

        sale = Sale(
            invoice_no=next_invoice_no(),
            customer_name=customer_name,
            payment_method=payment_method,
            subtotal=subtotal, tax=tax, discount=discount, total=total,
            paid_amount=paid_amount, change_due=Decimal("0"),
            created_by=getattr(current_user, "id", None)
        )
        db.session.add(sale)
        db.session.flush()
        try:
            for (item, qty, price, taxrate) in items:
                si = SaleItem(sale_id=sale.id, item_id=item.id, qty=qty,
                              unit_price=price, tax_rate=taxrate,
                              line_total=(price*qty)*(1+taxrate/Decimal("100")))
                db.session.add(si)
                # decrement stock
                item.stock_qty = Decimal(item.stock_qty or 0) - qty
                mv = StockMovement(item_id=item.id, type="sale", qty_change=-qty,
                                   unit_cost=item.cost_price, reason=f"Sale {sale.invoice_no}")
                db.session.add(mv)
        except Exception:
            db.session.rollback()
            flash("Error processing sale", "danger")
            return redirect(url_for("sales.cart"))

        if payment_method == "cash":
            change_due = paid_amount - total if paid_amount > total else Decimal("0")
            sale.change_due = change_due
        elif payment_method == "online":
            op = OnlinePayment(sale_id=sale.id, provider=provider or "unknown",
                               reference=reference or "", amount=total, status="captured")
            db.session.add(op)
            sale.paid_amount = total
        elif payment_method == "credit":
            cust = customer_name or "Walk-in"
            acct = CreditAccount.query.filter_by(customer_name=cust).first()
            if not acct:
                acct = CreditAccount(customer_name=cust, outstanding=0)
                db.session.add(acct)
                db.session.flush()
            txn = CreditTxn(account_id=acct.id, sale_id=sale.id, type="debit",
                            amount=total, notes=f"Invoice {sale.invoice_no}")
            db.session.add(txn)
            acct.outstanding = Decimal(acct.outstanding) + total
            sale.paid_amount = Decimal("0")
        else:
            flash("Invalid payment method", "danger")
            db.session.rollback()
            return redirect(url_for("sales.cart"))

        db.session.commit()
        flash(f"Sale completed: {sale.invoice_no}", "success")
        return redirect(url_for("sales.cart"))

    q = request.args.get("q", "").strip()
    items = []
    if q:
        items = Item.query.filter((Item.name.ilike(f"%{q}%")) | (Item.sku.ilike(f"%{q}%"))).order_by(Item.name).limit(20).all()
    return render_template("sales/cart.html", items=items)

@sales_bp.route("/quick", methods=["GET", "POST"])
@login_required
def quick_sell():
    if request.method == "POST":
        sku = request.form.get("sku", "").strip()
        qty = Decimal(request.form.get("qty", "1") or "1")
        method = request.form.get("payment_method", "cash")
        request.form = request.form.copy()
        request.form[f"sku_{sku}"] = "on"
        request.form[f"qty_{sku}"] = str(qty)
        request.form["payment_method"] = method
        request.form["paid_amount"] = request.form.get("paid_amount", "0")
        return cart()
    return render_template("sales/quick_sell.html")

@sales_bp.route("/receipt/<int:sale_id>")
@login_required
def receipt(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    items = sale.items
    return render_template("sales/receipt.html", sale=sale, items=items)

@sales_bp.route("/list")
@login_required
def sales_list():
    sales = Sale.query.order_by(Sale.created_at.desc()).limit(200).all()
    return render_template("sales/sales_list.html", sales=sales)

@sales_bp.route("/<int:sale_id>")
@login_required
def sale_detail(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template("sales/sale_detail.html", sale=sale)
