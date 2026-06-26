from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..auth import is_valid_admin_login


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "POST":
        usuario = (request.form.get("usuario") or "").strip()
        contrasena = (request.form.get("contrasena") or "").strip()

        if is_valid_admin_login(usuario, contrasena):
            session["usuario"] = "admin"
            return redirect(url_for("panel_admin"))

        flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html")


@auth_bp.route("/logout", endpoint="logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))
