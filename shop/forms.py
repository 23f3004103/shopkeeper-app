from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, SelectField, TextAreaField, DateField, FileField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=64)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class ItemForm(FlaskForm):
    sku = StringField("SKU", validators=[DataRequired(), Length(max=64)])
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    category = StringField("Category", validators=[Optional(), Length(max=100)])
    unit = StringField("Unit", validators=[Optional(), Length(max=32)])
    cost_price = DecimalField("Cost Price", places=2, validators=[Optional(), NumberRange(min=0)])
    sale_price = DecimalField("Sale Price", places=2, validators=[Optional(), NumberRange(min=0)])
    tax_rate = DecimalField("Tax %", places=2, validators=[Optional(), NumberRange(min=0, max=100)])
    stock_qty = DecimalField("Stock Qty", places=2, validators=[Optional(), NumberRange(min=0)])
    min_qty = DecimalField("Min Qty", places=2, validators=[Optional(), NumberRange(min=0)])
    expiry_date = DateField("Expiry Date", validators=[Optional()])
    supplier = StringField("Supplier", validators=[Optional(), Length(max=200)])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save")

class UploadForm(FlaskForm):
    file = FileField("CSV File")
    submit = SubmitField("Upload")
