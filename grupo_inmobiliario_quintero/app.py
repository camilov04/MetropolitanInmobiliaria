from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

app = Flask(__name__)
app.secret_key = "clave_super_secreta"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inmuebles.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELO =================
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

    destacado = db.Column(db.Boolean, default=False)  # ⭐ NUEVO
    id = db.Column(db.Integer, primary_key=True)

    titulo = db.Column(db.String(100), nullable=False)
    tipo_negocio = db.Column(db.String(20), nullable=False)  # Venta / Arriendo
    descripcion = db.Column(db.Text, nullable=False)

    tipo = db.Column(db.String(50), nullable=False)
    municipio = db.Column(db.String(100), nullable=False)

    habitaciones = db.Column(db.Integer)
    banos = db.Column(db.Integer)
    parqueadero = db.Column(db.Boolean, default=False)

    precio = db.Column(db.Float, nullable=False)
    imagen_url = db.Column(db.String(255))

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
@app.route("/")
def home():
    destacados = Inmueble.query.filter_by(destacado=True).limit(4).all()
    return render_template("index.html", destacados=destacados)




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

    inmuebles = query.all()
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
    inmuebles = Inmueble.query.order_by(Inmueble.id.desc()).all()
    return render_template(
        "admin_inmuebles.html",
        inmuebles=inmuebles
    )

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
        destacado=True if request.form.get("destacado") else False,
        imagen_url=request.form.get("imagen_url")
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
