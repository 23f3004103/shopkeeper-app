import os

class Config:
    # Read from environment where possible; provide safe defaults for local development
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")

    # Use an absolute path for the default sqlite DB to avoid issues with relative paths on Windows/OneDrive
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    default_sqlite = os.path.join(BASE_DIR, "instance", "shop.db")
    # Ensure slashes are normalized for the sqlite URI
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{default_sqlite.replace('\\\\','/')}")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kathmandu")
    EXPIRY_SOON_DAYS = int(os.environ.get("EXPIRY_SOON_DAYS", "14"))
    CREDIT_OVERDUE_DAYS = int(os.environ.get("CREDIT_OVERDUE_DAYS", "30"))
    DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
