from datetime import datetime

from .mail_service import send_property_request_email
from ..models import Inmueble
from sqlalchemy import cast, String


ARRIENDO_OCULTO_STATES = ("pendiente", "arrendado", "no_disponible")


def is_arrendado_state(estado):
    return (estado or "").strip().lower() in {"arrendado", "no_disponible"}


def parse_percentage_value(raw_value):
    raw_value = (raw_value or "").strip().replace("%", "").replace(",", ".")
    if not raw_value:
        return 0.0
    return float(raw_value)


def sync_image_priority(images):
    ordered_images = sorted(
        images,
        key=lambda image: ((image.orden if image.orden is not None else 999999), image.id or 0),
    )

    for index, image in enumerate(ordered_images):
        image.orden = index
        image.principal = index == 0


def get_admin_inmuebles_return_target(raw_target, url_builder):
    target = (raw_target or "").strip()
    if target.startswith("/admin/inmuebles"):
        return target
    return url_builder("admin_inmuebles")


def get_dashboard_metrics():
    total_inmuebles = Inmueble.query.count()
    total_venta = Inmueble.query.filter_by(tipo_negocio="Venta", estado="disponible").count()
    total_arriendo = Inmueble.query.filter(
        Inmueble.tipo_negocio == "Arriendo",
        Inmueble.estado == "disponible",
    ).count()
    total_arrendados = Inmueble.query.filter(Inmueble.estado.in_(["arrendado", "no_disponible"])).count()
    total_pendientes = Inmueble.query.filter_by(estado="pendiente").count()
    inmuebles_arrendados = Inmueble.query.filter(Inmueble.estado.in_(["arrendado", "no_disponible"])).all()
    total_finanzas_arrendados = sum((inmueble.precio or 0) for inmueble in inmuebles_arrendados)
    total_comision_arrendados = sum(
        (inmueble.precio or 0) * ((inmueble.comision_porcentaje or 0) / 100)
        for inmueble in inmuebles_arrendados
    )

    return {
        "total_inmuebles": total_inmuebles,
        "total_venta": total_venta,
        "total_arriendo": total_arriendo,
        "total_arrendados": total_arrendados,
        "total_pendientes": total_pendientes,
        "total_finanzas_arrendados": total_finanzas_arrendados,
        "total_comision_arrendados": total_comision_arrendados,
    }


def get_public_listing_context(municipio_filtro, tipo_filtro, tipo_negocio_filtro, orden_filtro, page, per_page=9):
    query = Inmueble.query.filter(Inmueble.estado == "disponible")

    if municipio_filtro:
        query = query.filter(Inmueble.municipio == municipio_filtro)
    if tipo_filtro:
        query = query.filter(Inmueble.tipo == tipo_filtro)
    if tipo_negocio_filtro:
        query = query.filter(Inmueble.tipo_negocio == tipo_negocio_filtro)

    if orden_filtro == "precio_asc":
        query = query.order_by(Inmueble.precio.asc())
    elif orden_filtro == "precio_desc":
        query = query.order_by(Inmueble.precio.desc())
    else:
        query = query.order_by(Inmueble.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    municipios = [
        row[0]
        for row in Inmueble.query.with_entities(Inmueble.municipio)
        .filter(Inmueble.municipio.isnot(None))
        .distinct()
        .order_by(Inmueble.municipio)
        .all()
    ]

    return {
        "inmuebles": pagination.items,
        "municipios": municipios,
        "pagination": pagination,
    }


def get_admin_listing_context(page, id_filtro, solo_destacados=False, estado_filtro=None, per_page=8):
    
    query = Inmueble.query
    if id_filtro:
        query = query.filter(Inmueble.id == id_filtro)
    if solo_destacados:
        query = query.filter(Inmueble.plan == "Destacado")
    if estado_filtro:
        if estado_filtro == "arrendado":
            query = query.filter(Inmueble.estado.in_(["arrendado", "no_disponible"]))
        else:
            query = query.filter(Inmueble.estado == estado_filtro)
    query = query.order_by(Inmueble.id.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "inmuebles": pagination.items,
        "pagination": pagination,
        "id_filtro": id_filtro,
        "solo_destacados": solo_destacados,
        "estado_filtro": estado_filtro,
    }


def build_export_sheets(inmuebles):
    venta = [i for i in inmuebles if (i.tipo_negocio or "").lower() == "venta"]
    arriendo = [i for i in inmuebles if (i.tipo_negocio or "").lower() == "arriendo" and (i.estado or "").lower() == "disponible"]
    arrendado = [i for i in inmuebles if is_arrendado_state(i.estado)]
    pendientes = [i for i in inmuebles if (i.estado or "").lower() == "pendiente"]

    def to_dicts(lista):
        campos = [c.name for c in Inmueble.__table__.columns]
        return [{campo: getattr(i, campo) for campo in campos} for i in lista]

    return {
        "Venta": to_dicts(venta),
        "Arriendo": to_dicts(arriendo),
        "Arrendado": to_dicts(arrendado),
        "Pendientes": to_dicts(pendientes),
    }


def parse_date_or_none(raw_value, fmt="%Y-%m-%d"):
    if not raw_value:
        return None
    try:
        return datetime.strptime(raw_value, fmt).date()
    except Exception:
        return None


def send_property_request(*args, logger=None, **kwargs):
    return send_property_request_email(*args, logger=logger, **kwargs)
