from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from sqlalchemy import func
from .models import Item, Sale, SaleItem
from . import db
from datetime import datetime, timedelta
import io, csv

reports_bp = Blueprint("reports", __name__, template_folder="templates")

@reports_bp.route("/dashboard")
@login_required
def dashboard():
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    sales_24h = db.session.query(func.coalesce(func.sum(Sale.total), 0)).filter(Sale.created_at >= day_ago).scalar() or 0
    sales_7d = db.session.query(func.coalesce(func.sum(Sale.total), 0)).filter(Sale.created_at >= week_ago).scalar() or 0
    top_items = db.session.query(SaleItem.item_id, func.sum(SaleItem.qty).label("qty")) \
        .group_by(SaleItem.item_id).order_by(func.sum(SaleItem.qty).desc()).limit(5).all()
    top_items_detail = [(Item.query.get(iid), qty) for iid, qty in top_items]
    low_stock = Item.query.filter(Item.stock_qty <= Item.min_qty).count()
    return render_template("dashboard.html",
                           sales_24h=sales_24h, sales_7d=sales_7d, top_items=top_items_detail, low_stock=low_stock)

@reports_bp.route("/export/sales")
@login_required
def export_sales():
    start = request.args.get("start")
    end = request.args.get("end")
    q = Sale.query
    if start:
        q = q.filter(Sale.created_at >= datetime.fromisoformat(start))
    if end:
        q = q.filter(Sale.created_at <= datetime.fromisoformat(end))
    sales = q.order_by(Sale.created_at).all()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["invoice_no", "customer_name", "method", "subtotal", "tax",
                "discount", "total", "paid", "change", "created_at"])
    for s in sales:
        w.writerow([s.invoice_no, s.customer_name or "", s.payment_method, s.subtotal,
                    s.tax, s.discount, s.total, s.paid_amount, s.change_due, s.created_at.isoformat()])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv",
                     as_attachment=True, download_name="sales.csv")
