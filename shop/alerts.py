from flask import Blueprint, render_template
from flask_login import login_required
from datetime import date, timedelta
from .models import Item, CreditAccount, Alert
from . import db

alerts_bp = Blueprint("alerts", __name__, template_folder="templates")

def recalc_alerts_all():
    # Clear unresolved auto alerts
    Alert.query.filter(Alert.is_resolved == False).delete()
    db.session.commit()

    # Low stock
    low_items = Item.query.filter(Item.stock_qty <= Item.min_qty).all()
    for it in low_items:
        msg = f"Low stock: {it.name} (qty {it.stock_qty})"
        db.session.add(Alert(type="low_stock", message=msg, severity="warning", item_id=it.id))

    # Expiry soon: within 14 days by default
    from config import Config
    soon_days = Config.EXPIRY_SOON_DAYS
    soon = date.today() + timedelta(days=soon_days)
    exp_items = Item.query.filter(Item.expiry_date != None, Item.expiry_date <= soon).all()
    for it in exp_items:
        msg = f"Expiry soon: {it.name} ({it.expiry_date})"
        db.session.add(Alert(type="expiry", message=msg, severity="danger",
                             item_id=it.id, due_date=it.expiry_date))

    # Credit overdue: outstanding > 0
    accts = CreditAccount.query.filter(CreditAccount.outstanding > 0).all()
    for a in accts:
        msg = f"Credit outstanding: {a.customer_name} (Rs {a.outstanding})"
        db.session.add(Alert(type="credit_overdue", message=msg, severity="warning", account_id=a.id))

    db.session.commit()

@alerts_bp.route("/")
@login_required
def alerts_page():
    recalc_alerts_all()
    alerts = Alert.query.order_by(Alert.severity.desc(), Alert.created_at.desc()).all()
    return render_template("alerts/alerts.html", alerts=alerts)
