import os
from functools import wraps

from flask import redirect, session, url_for


ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap


def is_valid_admin_login(username, password):
    return username == ADMIN_USER and password == ADMIN_PASSWORD
