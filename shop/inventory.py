from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from .models import Item, StockMovement
from . import db
from datetime import date
import io, csv

inventory_bp = Blueprint("inventory", __name__, template_folder="templates")

def can_edit_cost():
    return getattr(current_user, "role", "") == "owner"

@inventory_bp.route("/")
@login_required
def list_items():
    q = request.args.get("q", "").strip()
    items = Item.query
    if q:
        items = items.filter((Item.name.ilike(f"%{q}%")) | (Item.sku.ilike(f"%{q}%")))
    items = items.order_by(Item.name).all()
    return render_template("inventory/list.html", items=items, can_edit_cost=can_edit_cost())

@inventory_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_item():
    from .forms import ItemForm
    form = ItemForm()
    if form.validate_on_submit():
        item = Item(
            sku=form.sku.data, name=form.name.data, category=form.category.data,
            unit=form.unit.data, cost_price=form.cost_price.data or 0,
            sale_price=form.sale_price.data or 0, tax_rate=form.tax_rate.data or 0,
            stock_qty=form.stock_qty.data or 0, min_qty=form.min_qty.data or 0,
            expiry_date=form.expiry_date.data, supplier=form.supplier.data, notes=form.notes.data
        )
        db.session.add(item)
        if item.stock_qty and item.stock_qty > 0:
            m = StockMovement(item=item, type="adjustment", qty_change=item.stock_qty, unit_cost=item.cost_price, reason="Initial stock")
            db.session.add(m)
        db.session.commit()
        flash("Item created", "success")
        return redirect(url_for("inventory.list_items"))
    return render_template("inventory/create.html", form=form)

@inventory_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    from .forms import ItemForm
    item = Item.query.get_or_404(item_id)
    form = ItemForm(obj=item)
    if not can_edit_cost():
        del form.cost_price
    if form.validate_on_submit():
        item.sku = form.sku.data
        item.name = form.name.data
        item.category = form.category.data
        item.unit = form.unit.data
        if can_edit_cost():
            item.cost_price = form.cost_price.data or 0
        item.sale_price = form.sale_price.data or 0
        item.tax_rate = form.tax_rate.data or 0
        item.stock_qty = form.stock_qty.data or 0
        item.min_qty = form.min_qty.data or 0
        item.expiry_date = form.expiry_date.data
        item.supplier = form.supplier.data
        item.notes = form.notes.data
        db.session.commit()
        flash("Item updated", "success")
        return redirect(url_for("inventory.list_items"))
    return render_template("inventory/edit.html", form=form, item=item)

@inventory_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_items():
    from .forms import UploadForm
    form = UploadForm()
    if form.validate_on_submit() and form.file.data:
        stream = io.StringIO(form.file.data.stream.read().decode("utf-8"))
        reader = csv.DictReader(stream)
        count = 0
        for row in reader:
            sku = row.get("sku", "").strip()
            if not sku:
                continue
            item = Item.query.filter_by(sku=sku).first()
            if not item:
                item = Item(sku=sku, name=row.get("name", "").strip())
                db.session.add(item)
            item.category = row.get("category") or None
            item.unit = row.get("unit") or "pcs"
            item.cost_price = float(row.get("cost_price") or 0)
            item.sale_price = float(row.get("sale_price") or 0)
            item.tax_rate = float(row.get("tax_rate") or 0)
            item.stock_qty = float(row.get("stock_qty") or 0)
            item.min_qty = float(row.get("min_qty") or 0)
            exp = (row.get("expiry_date") or "").strip()
            if exp:
                try:
                    item.expiry_date = date.fromisoformat(exp)
                except:
                    pass
            item.supplier = row.get("supplier") or None
            item.notes = row.get("notes") or None
            count += 1
        db.session.commit()
        flash(f"Imported {count} rows", "success")
        return redirect(url_for("inventory.list_items"))
    return render_template("inventory/import.html", form=form)

@inventory_bp.route("/export")
@login_required
def export_items():
    items = Item.query.order_by(Item.name).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["sku", "name", "category", "unit", "cost_price", "sale_price", "tax_rate", "stock_qty", "min_qty", "expiry_date", "supplier", "notes"])
    for it in items:
        writer.writerow([it.sku, it.name, it.category or "", it.unit, it.cost_price, it.sale_price, it.tax_rate, it.stock_qty, it.min_qty, it.expiry_date or "", it.supplier or "", (it.notes or "").replace("\n"," ")])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="inventory.csv")


@inventory_bp.route('/items')
@login_required
def items_api():
    """Return JSON list of items for typeahead/autocomplete.
    Query param: q (partial sku or name)
    Returns up to 50 matches with fields: sku, name, sale_price, tax_rate, stock_qty
    """
    q = request.args.get('q', '').strip()
    items_q = Item.query
    if q:
        items_q = items_q.filter((Item.name.ilike(f"%{q}%")) | (Item.sku.ilike(f"%{q}%")))
    items = items_q.order_by(Item.name).limit(50).all()
    out = []
    for it in items:
        out.append({
            'sku': it.sku,
            'name': it.name,
            'supplier': it.supplier or '',
            'sale_price': float(it.sale_price or 0),
            'tax_rate': float(it.tax_rate or 0),
            'stock_qty': float(it.stock_qty or 0),
        })
    return jsonify(out)

@inventory_bp.route('/items/delete', methods=['POST'])
@login_required
def delete_items():
    from flask import request, jsonify
    try:
        data = request.get_json()
        ids = data.get('ids', [])
        # Only delete if owner or whoever is allowed
        if getattr(current_user, "role", "") != "owner":
            return jsonify({"error": "Not allowed"}), 403
        for iid in ids:
            item = Item.query.get(iid)
            if item:
                db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
