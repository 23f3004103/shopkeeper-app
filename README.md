# Shopkeeper App

Quick start:
1. python -m venv .venv && source .venv/bin/activate
2. pip install -r requirements.txt
3. flask --app manage.py db-init
4. flask --app app.py run

Deploy on PythonAnywhere:
- Create a new web app (Flask).
- Upload this folder.
- Point WSGI to wsgi.py.
- Create a virtualenv and pip install -r requirements.txt.
- Set env variables in Web tab: SECRET_KEY, TIMEZONE.
- Reload app.
