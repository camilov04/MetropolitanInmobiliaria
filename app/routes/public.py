
from datetime import datetime
from flask import Blueprint, abort, render_template, request
from ..models import Imagen, Inmueble
from ..services.property_service import get_dashboard_metrics, get_public_listing_context

public_bp = Blueprint("public", __name__)

@public_bp.route("/privacidad", endpoint="privacidad")
def privacidad():
    return render_template("privacidad.html")


@public_bp.route("/arriendo", endpoint="arriendo")
def arriendo():
    return render_template("arriendo.html")


@public_bp.route("/venta", endpoint="venta")
def venta():
    return render_template("venta.html")


@public_bp.route("/avaluo", endpoint="avaluo")
def avaluo():
    return render_template("avaluo.html")


@public_bp.route("/", endpoint="home")
def home():
    ahora = datetime.utcnow()
    destacados = Inmueble.query.filter(
        Inmueble.plan_activo == True,
        Inmueble.plan == "Destacado",
        Inmueble.plan_vencimiento > ahora,
        Inmueble.estado == "disponible",
    ).limit(4).all()
    return render_template("index.html", destacados=destacados)


@public_bp.route("/inmuebles", endpoint="mostrar_inmuebles")
def mostrar_inmuebles():
    listing_context = get_public_listing_context(
        municipio_filtro=(request.args.get("municipio") or "").strip(),
        tipo_filtro=(request.args.get("tipo") or "").strip(),
        tipo_negocio_filtro=(request.args.get("tipo_negocio") or "").strip(),
        orden_filtro=(request.args.get("orden") or "").strip(),
        page=request.args.get("page", 1, type=int),
    )
    return render_template("inmuebles.html", **listing_context)


@public_bp.route("/detalle_inmueble/<int:inmueble_id>", endpoint="detalle_inmueble")
def detalle_inmueble(inmueble_id):
    inmueble = Inmueble.query.get_or_404(inmueble_id)
    if inmueble.estado != "disponible":
        abort(404)
    imagenes = Imagen.query.filter_by(inmueble_id=inmueble.id).order_by(Imagen.orden).all()
    return render_template("detalle_inmueble.html", inmueble=inmueble, imagenes=imagenes)
