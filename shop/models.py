from . import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timezone
from passlib.hash import bcrypt
from sqlalchemy.orm import relationship

def utcnow():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(16), default="clerk", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password):
        return bcrypt.verify(password, self.password_hash)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    unit = db.Column(db.String(32), default="pcs")
    cost_price = db.Column(db.Numeric(12,2), default=0)
    sale_price = db.Column(db.Numeric(12,2), default=0)
    tax_rate = db.Column(db.Numeric(5,2), default=0)
    stock_qty = db.Column(db.Numeric(12,2), default=0)
    min_qty = db.Column(db.Numeric(12,2), default=0)
    expiry_date = db.Column(db.Date)
    supplier = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    movements = relationship("StockMovement", backref="item", lazy="dynamic")

class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    type = db.Column(db.String(16), nullable=False)  # purchase|adjustment|sale
    qty_change = db.Column(db.Numeric(12,2), nullable=False)
    unit_cost = db.Column(db.Numeric(12,2), default=0)
    reason = db.Column(db.String(200))
    at = db.Column(db.DateTime, default=utcnow, nullable=False)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(32), unique=True, nullable=False)
    customer_name = db.Column(db.String(200))
    payment_method = db.Column(db.String(16), nullable=False)  # cash|online|credit
    subtotal = db.Column(db.Numeric(12,2), default=0)
    tax = db.Column(db.Numeric(12,2), default=0)
    discount = db.Column(db.Numeric(12,2), default=0)
    total = db.Column(db.Numeric(12,2), default=0)
    paid_amount = db.Column(db.Numeric(12,2), default=0)
    change_due = db.Column(db.Numeric(12,2), default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))

    items = relationship("SaleItem", backref="sale", cascade="all, delete-orphan")
    online_payment = relationship("OnlinePayment", backref="sale", uselist=False)

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    qty = db.Column(db.Numeric(12,2), nullable=False)
    unit_price = db.Column(db.Numeric(12,2), nullable=False)
    tax_rate = db.Column(db.Numeric(5,2), default=0)
    line_total = db.Column(db.Numeric(12,2), nullable=False)

    item = relationship("Item")

class CreditAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(32))
    email = db.Column(db.String(200))
    outstanding = db.Column(db.Numeric(12,2), default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    txns = relationship("CreditTxn", backref="account", cascade="all, delete-orphan")

class CreditTxn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("credit_account.id"), nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"))
    type = db.Column(db.String(16), nullable=False)  # debit|payment|adjustment
    amount = db.Column(db.Numeric(12,2), nullable=False)
    notes = db.Column(db.String(200))
    at = db.Column(db.DateTime, default=utcnow, nullable=False)

class OnlinePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    provider = db.Column(db.String(64))
    reference = db.Column(db.String(128))
    amount = db.Column(db.Numeric(12,2), nullable=False)
    status = db.Column(db.String(16), default="captured")
    at = db.Column(db.DateTime, default=utcnow, nullable=False)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(32), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.String(16), default="info")
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"))
    account_id = db.Column(db.Integer, db.ForeignKey("credit_account.id"))
    due_date = db.Column(db.Date)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime)
