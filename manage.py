import click
from shop import create_app, db
from shop.models import User
from passlib.hash import bcrypt

app = create_app()

@app.cli.command("db-init")
def db_init():
    """Initialize database and create owner user."""
    db.create_all()
    if not User.query.filter_by(username="owner").first():
        pw = "Owner@123"
        user = User(username="owner", role="owner", password_hash=bcrypt.hash(pw))
        db.session.add(user)
        db.session.commit()
        click.echo(f"Owner user created: owner / {pw}")
    click.echo("DB initialized.")
