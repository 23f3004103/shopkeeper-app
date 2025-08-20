from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
from os import makedirs
from os.path import exists

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if not exists(app.instance_path):
        makedirs(app.instance_path)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth import auth_bp
    from .inventory import inventory_bp
    from .sales import sales_bp
    from .payments import payments_bp
    from .reports import reports_bp
    from .alerts import alerts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(sales_bp, url_prefix="/sales")
    app.register_blueprint(payments_bp, url_prefix="/payments")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(alerts_bp, url_prefix="/alerts")

    @app.route("/")
    def index():
        from flask import redirect, url_for
        return redirect(url_for("reports.dashboard"))

    return app
