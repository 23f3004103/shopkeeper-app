from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from decimal import Decimal
from .models import CreditAccount, CreditTxn
from . import db

payments_bp = Blueprint("payments", __name__, template_folder="templates")

@payments_bp.route("/credit")
@login_required
def credit_accounts():
    q = request.args.get("q", "").strip()
    accts = CreditAccount.query
    if q:
        accts = accts.filter(CreditAccount.customer_name.ilike(f"%{q}%"))
    accts = accts.order_by(CreditAccount.customer_name).all()
    return render_template("payments/credit_accounts.html", accounts=accts)

@payments_bp.route("/credit/<int:acct_id>", methods=["GET", "POST"])
@login_required
def account_detail(acct_id):
    acct = CreditAccount.query.get_or_404(acct_id)
    if request.method == "POST":
        amount = Decimal(request.form.get("amount", "0") or "0")
        notes = request.form.get("notes") or "Payment"
        if amount > 0:
            txn = CreditTxn(account_id=acct.id, type="payment", amount=amount, notes=notes)
            db.session.add(txn)
            acct.outstanding = Decimal(acct.outstanding) - amount
            db.session.commit()
            flash("Payment recorded", "success")
            return redirect(url_for("payments.account_detail", acct_id=acct.id))
    txns = acct.txns
    return render_template("payments/account_detail.html", acct=acct, txns=txns)
