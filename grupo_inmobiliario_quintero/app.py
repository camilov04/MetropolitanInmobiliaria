from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

app = Flask(__name__)
app.secret_key = "clave_super_secreta"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inmuebles.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELO =================
from datetime import datetime

class Inmueble(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    titulo = db.Column(db.String(100), nullable=False)
    tipo_negocio = db.Column(db.String(20), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)

    tipo = db.Column(db.String(50), nullable=False)
    municipio = db.Column(db.String(100), nullable=False)

    habitaciones = db.Column(db.Integer)
    banos = db.Column(db.Integer)
    parqueadero = db.Column(db.Boolean, default=False)

    precio = db.Column(db.Float, nullable=False)
    imagen_url = db.Column(db.String(255))

    # ===== SISTEMA PLANES =====
    plan = db.Column(db.String(20))
    plan_activo = db.Column(db.Boolean, default=False)
    plan_vencimiento = db.Column(db.DateTime)
    estado_pago = db.Column(db.String(20), default="Pendiente")

    # ===== PRIORIDAD VISUAL =====
    prioridad = db.Column(db.Integer, default=0)

    # ===== DESTACADO HOME =====
    destacado = db.Column(db.Boolean, default=False)


def verificar_planes():
    hoy = datetime.utcnow()

    inmuebles = Inmueble.query.filter(
        Inmueble.plan_activo == True,
        Inmueble.plan_vencimiento != None
    ).all()

    for i in inmuebles:
        if i.plan_vencimiento < hoy:
            i.plan_activo = False
            i.plan = None
            i.plan_vencimiento = None

    db.session.commit()


# ================= LOGIN =================
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == "admin" and request.form["contrasena"] == "1234":
            session["usuario"] = "admin"
            return redirect(url_for("panel_admin"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))

# ================= PUBLICO =================
from datetime import datetime

@app.route("/")
def home():

    ahora = datetime.utcnow()

    destacados = Inmueble.query.filter(
        Inmueble.plan_activo == True,
        Inmueble.plan == "Destacado",
        Inmueble.plan_vencimiento > ahora
    ).limit(4).all()

    return render_template(
        "index.html",
        destacados=destacados
    )


@app.route("/inmuebles")
def mostrar_inmuebles():
    query = Inmueble.query

    tipo_negocio = request.args.get("tipo_negocio")
    tipo = request.args.get("tipo")
    municipio = request.args.get("municipio")

    if tipo_negocio:
        query = query.filter_by(tipo_negocio=tipo_negocio)

    if tipo:
        query = query.filter_by(tipo=tipo)

    if tipo_negocio:
        query = query.filter(Inmueble.tipo_negocio == tipo_negocio)

    if municipio:
        query = query.filter(Inmueble.municipio.ilike(f"%{municipio}%"))

    inmuebles = query.order_by(
        db.case(
            (Inmueble.plan == "premium", 1),
            (Inmueble.plan == "destacado", 2),
            else_=3
        )
    ).all()

    return render_template("inmuebles.html", inmuebles=inmuebles)

@app.route("/inmueble/<int:inmueble_id>")
def detalle_inmueble(inmueble_id):
    inmueble = Inmueble.query.get_or_404(inmueble_id)

    imagenes = []
    if inmueble.imagen_url:
        imagenes = [img.strip() for img in inmueble.imagen_url.split(",")]

    return render_template(
        "detalle_inmueble.html",
        inmueble=inmueble,
        imagenes=imagenes
    )


# ================= ADMIN =================
@app.route("/admin")
@login_required
def panel_admin():
    total_inmuebles = Inmueble.query.count()
    total_venta = Inmueble.query.filter_by(tipo_negocio="Venta").count()
    total_arriendo = Inmueble.query.filter_by(tipo_negocio="Arriendo").count()

    return render_template(
        "admin.html",
        total_inmuebles=total_inmuebles,
        total_venta=total_venta,
        total_arriendo=total_arriendo
    )

@app.route("/admin/inmuebles")
@login_required
def admin_inmuebles():

    solo_destacados = request.args.get("destacados")

    query = Inmueble.query.order_by(Inmueble.id.desc())

    if solo_destacados == "1":
        query = query.filter_by(destacado=True)

    inmuebles = query.all()

    return render_template(
        "admin_inmuebles.html",
        inmuebles=inmuebles,
        solo_destacados=solo_destacados
    )

@app.route("/promocionar/<int:id>")
def promocionar_inmueble(id):

    inmueble = Inmueble.query.get_or_404(id)

    return render_template(
        "promocionar.html",
        inmueble=inmueble
    )

from datetime import datetime, timedelta


@app.route("/admin/activar_plan/<int:id>", methods=["POST"])
@login_required
def activar_plan(id):

    inmueble = Inmueble.query.get_or_404(id)

    plan = request.form.get("plan")

    if not plan:
        return redirect(url_for("admin_inmuebles"))

    if plan == "Basico":
        dias = 30
    elif plan == "Premium":
        dias = 60
    elif plan == "Destacado":
        dias = 90
    else:
        dias = 30

    inmueble.plan = plan
    inmueble.plan_activo = True
    inmueble.plan_vencimiento = datetime.utcnow() + timedelta(days=dias)

    db.session.commit()

    return redirect(url_for("admin_inmuebles"))


@app.route("/admin/desactivar_plan/<int:id>", methods=["POST"])
@login_required
def desactivar_plan(id):

    inmueble = Inmueble.query.get_or_404(id)

    inmueble.plan = None
    inmueble.plan_activo = False
    inmueble.plan_vencimiento = None

    db.session.commit()

    return redirect(url_for("admin_inmuebles"))




@app.route("/admin/toggle_destacado/<int:id>")
@login_required
def toggle_destacado(id):

    inmueble = Inmueble.query.get_or_404(id)

    inmueble.destacado = not inmueble.destacado

    db.session.commit()

    return redirect(request.referrer or url_for("admin_inmuebles"))


@app.route("/admin/inmuebles/nuevo")
@login_required
def nuevo_inmueble():
    return render_template("admin_nuevo_inmueble.html")


@app.route("/agregar_inmueble", methods=["POST"])
@login_required
def agregar_inmueble():
    nuevo = Inmueble(
    titulo=request.form["titulo"],
    tipo_negocio=request.form["tipo_negocio"],
    descripcion=request.form["descripcion"],
    tipo=request.form["tipo"],
    municipio=request.form["municipio"],
    habitaciones=request.form.get("habitaciones") or None,
    banos=request.form.get("banos") or None,
    parqueadero=True if request.form.get("parqueadero") == "1" else False,
    precio=float(request.form["precio"]),
    imagen_url=request.form.get("imagen_url"),

    plan="basico",
    estado_pago="pendiente",
    prioridad=0
)


    db.session.add(nuevo)
    db.session.commit()
    return redirect(url_for("panel_admin"))

@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_inmueble(id):
    inmueble = Inmueble.query.get_or_404(id)

    if request.method == "POST":
        inmueble.titulo = request.form["titulo"]
        inmueble.tipo_negocio = request.form["tipo_negocio"]
        inmueble.descripcion = request.form["descripcion"]
        inmueble.tipo = request.form["tipo"]
        inmueble.municipio = request.form["municipio"]

        inmueble.habitaciones = (
            int(request.form["habitaciones"])
            if request.form.get("habitaciones")
            else None
        )

        inmueble.banos = (
            int(request.form["banos"])
            if request.form.get("banos")
            else None
        )

        inmueble.parqueadero = (
            True if request.form.get("parqueadero") == "1" else False
        )

        inmueble.precio = float(request.form["precio"])
        inmueble.destacado = True if request.form.get("destacado") else False
        inmueble.imagen_url = request.form.get("imagen_url")

        db.session.commit()
        return redirect(url_for("panel_admin"))

    return render_template("editar.html", inmueble=inmueble)

@app.route("/eliminar_inmueble/<int:id>", methods=["POST"])
@login_required
def eliminar_inmueble(id):
    inmueble = Inmueble.query.get_or_404(id)
    db.session.delete(inmueble)
    db.session.commit()
    return redirect(url_for("panel_admin"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
