from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask import session, redirect, url_for

from models import Session, User, Transaction

class AdminModelView(ModelView):
    def is_accessible(self):
        return session.get("logged_in", False)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login"))

admin = Admin(name="My Admin")

def init_admin(app):
    admin.init_app(app)
    admin.add_view(AdminModelView(User, Session))
    admin.add_view(AdminModelView(Transaction, Session))