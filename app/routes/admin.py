import io
from datetime import datetime, timedelta, date
import mimetypes
import os
from urllib.parse import quote

import pandas as pd
import requests
from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, send_file, stream_with_context, url_for

from ..auth import login_required
from ..models import ContratoArriendo, DocumentoArrendamiento, FacturaElectronica, Gasto, Imagen, Ingreso, Inmueble, OtroIngreso, PagoArriendo, db
from ..services.einvoice_service import generate_signed_invoice_envelope
from ..services.dian_client import DianClient
from ..services.property_service import (
    build_export_sheets,
    get_admin_inmuebles_return_target,
    get_admin_listing_context,
    get_dashboard_metrics,
    is_arrendado_state,
    parse_date_or_none,
    parse_percentage_value,
    sync_image_priority,
)
from ..services_cloudinary import delete_image_by_url, upload_document, upload_image
from ..validators import clean_text, missing_required_fields, parse_boolean_choice, parse_price_value


admin_bp = Blueprint("admin", __name__)


def _assign_owner_fields(inmueble, values):
    inmueble.propietario_nombre = clean_text(values.get("propietario_nombre")) or None
    inmueble.propietario_cedula = clean_text(values.get("propietario_cedula")) or None
    inmueble.propietario_telefono = clean_text(values.get("propietario_telefono")) or None
    inmueble.propietario_telefono_secundario = clean_text(values.get("propietario_telefono_secundario")) or None
    inmueble.propietario_correo = clean_text(values.get("propietario_correo")) or None


def _clear_arrendatario_data(inmueble):
    inmueble.arrendatario_nombre = None
    inmueble.arrendatario_tipo_doc = None
    inmueble.arrendatario_num_doc = None
    inmueble.arrendatario_telefono = None
    inmueble.arrendatario_telefono_secundario = None
    inmueble.arrendatario_correo = None
    inmueble.arrendatario_fecha_pago = None
    inmueble.arrendatario_descripcion = None


def _deactivate_active_contract(inmueble_id):
    contrato_activo = ContratoArriendo.query.filter_by(inmueble_id=inmueble_id, activo=True).first()
    if contrato_activo:
        contrato_activo.activo = False
    return contrato_activo


def _assign_contact_fields(inmueble, values):
    inmueble.arrendatario_nombre = clean_text(values.get("arrendatario_nombre")) or None
    inmueble.arrendatario_tipo_doc = clean_text(values.get("arrendatario_tipo_doc")) or None
    inmueble.arrendatario_num_doc = clean_text(values.get("arrendatario_num_doc")) or None
    inmueble.arrendatario_telefono = clean_text(values.get("arrendatario_telefono")) or None
    inmueble.arrendatario_telefono_secundario = clean_text(values.get("arrendatario_telefono_secundario")) or None
    inmueble.arrendatario_correo = clean_text(values.get("arrendatario_correo")) or None
    inmueble.arrendatario_descripcion = clean_text(values.get("arrendatario_descripcion")) or None


def _parse_contract_payment_date(raw_value):
    return parse_date_or_none(raw_value)


def _compute_fecha_limite(fecha_pago):
    if not fecha_pago:
        return None
    return fecha_pago + timedelta(days=5)


@admin_bp.route("/admin/exportar_excel", endpoint="exportar_excel")
@login_required
def exportar_excel():
    inmuebles = Inmueble.query.all()
    sheets = build_export_sheets(inmuebles)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="metropolitan_inmobiliaria.xlsx",
    )


@admin_bp.route("/admin/arrendamiento/<int:id>", methods=["GET", "POST"], endpoint="detalle_arrendamiento")
@login_required
def detalle_arrendamiento(id):
    inmueble = Inmueble.query.get_or_404(id)
    contrato = ContratoArriendo.query.filter_by(inmueble_id=inmueble.id, activo=True).first()
    documentos = contrato.documentos if contrato else []
    if request.method == "POST":
        inmueble.estado = "disponible"
        inmueble.estado_detalle = None
        _clear_arrendatario_data(inmueble)
        _deactivate_active_contract(inmueble.id)
        db.session.commit()
        flash("El inmueble ahora está disponible nuevamente.", "success")
        return redirect(url_for("admin_inmuebles"))
    return render_template("detalle_arrendamiento.html", inmueble=inmueble, contrato=contrato, documentos=documentos)


def _proxy_remote_document(remote_url, filename, inline=True):
    guessed_mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    disposition = "inline" if inline else "attachment"
    safe_filename = quote(filename, safe="._-()")
    content_disposition = f"{disposition}; filename*=UTF-8''{safe_filename}"

    remote = requests.get(remote_url, stream=True, timeout=30)
    remote.raise_for_status()

    return Response(
        stream_with_context(remote.iter_content(chunk_size=8192)),
        headers={
            "Content-Type": remote.headers.get("Content-Type") or guessed_mime,
            "Content-Disposition": content_disposition,
        },
    )


@admin_bp.route("/admin/documento/<int:doc_id>/preview", endpoint="admin_preview_documento")
@login_required
def admin_preview_documento(doc_id):
    doc = DocumentoArrendamiento.query.get_or_404(doc_id)
    filename = doc.display_filename
    ext = (doc.formato or os.path.splitext(filename)[1].lstrip(".") or "").lower()

    # Browsers don't render Office documents; use Microsoft's online viewer in the iframe.
    if ext in {"doc", "docx", "ppt", "pptx", "xls", "xlsx"}:
        src = quote(doc.url, safe="")
        return redirect(f"https://view.officeapps.live.com/op/embed.aspx?src={src}")

    # PDFs and other formats: stream inline so the iframe renders instead of downloading.
    return _proxy_remote_document(doc.url, filename=filename, inline=True)


@admin_bp.route("/admin/documento/<int:doc_id>/download", endpoint="admin_download_documento")
@login_required
def admin_download_documento(doc_id):
    doc = DocumentoArrendamiento.query.get_or_404(doc_id)
    return _proxy_remote_document(doc.url, filename=doc.display_filename, inline=False)


@admin_bp.route("/admin/arrendar/<int:id>", methods=["GET", "POST"], endpoint="arrendar_inmueble")
@login_required
def arrendar_inmueble(id):
    inmueble = Inmueble.query.get_or_404(id)
    contrato = ContratoArriendo.query.filter_by(inmueble_id=inmueble.id, activo=True).first()
    estado_objetivo = clean_text(request.values.get("estado")) or ("arrendado" if is_arrendado_state(inmueble.estado) else "pendiente")
    if estado_objetivo not in {"pendiente", "arrendado"}:
        estado_objetivo = "pendiente"
    if request.method == "POST":
        _assign_contact_fields(inmueble, request.form)
        inmueble.estado = estado_objetivo
        inmueble.estado_detalle = clean_text(request.form.get("arrendatario_descripcion")) if estado_objetivo == "pendiente" else None

        if estado_objetivo == "pendiente":
            inmueble.arrendatario_fecha_pago = None
            _deactivate_active_contract(inmueble.id)
            db.session.commit()
            flash("Prospecto guardado y estado actualizado a pendiente.", "success")
            return redirect(url_for("admin_inmuebles", estado="pendiente"))

        fecha_inicio_contrato = parse_date_or_none(request.form.get("fecha_inicio_contrato"))
        fecha_pago = _parse_contract_payment_date(request.form.get("arrendatario_fecha_pago"))
        canon = float(request.form.get("canon") or 0)
        vigencia = max(1, min(12, int(request.form.get("vigencia_contrato") or 12)))
        fecha_limite = _compute_fecha_limite(fecha_pago)

        inmueble.arrendatario_fecha_pago = fecha_pago
        inmueble.estado_detalle = None
        contrato = ContratoArriendo.query.filter_by(inmueble_id=inmueble.id, activo=True).first()
        if contrato is None:
            contrato = ContratoArriendo(inmueble_id=inmueble.id, activo=True)
        contrato.fecha_inicio_contrato = fecha_inicio_contrato or date.today()
        contrato.fecha_pago = fecha_pago
        contrato.fecha_limite = fecha_limite
        contrato.vigencia_contrato = vigencia
        contrato.nombre = inmueble.arrendatario_nombre or "Sin nombre"
        contrato.nit = inmueble.arrendatario_num_doc
        contrato.celular = inmueble.arrendatario_telefono
        contrato.correo = inmueble.arrendatario_correo
        contrato.canon = canon
        contrato.direccion = inmueble.ubicacion
        contrato.propietario = inmueble.propietario_nombre
        contrato.comision = (canon or 0) * ((inmueble.comision_porcentaje or 0) / 100)
        contrato.estado_pago_inquilino = "Pendiente"
        contrato.dias_mora = 0
        contrato.mes = request.form.get("mes") or ""
        db.session.add(contrato)
        db.session.flush()

        archivos = [archivo for archivo in request.files.getlist("documentos") if archivo and archivo.filename]
        for archivo in archivos:
            uploaded = upload_document(archivo)
            db.session.add(
                DocumentoArrendamiento(
                    contrato_id=contrato.id,
                    nombre=uploaded["original_filename"],
                    url=uploaded["secure_url"],
                    resource_type=uploaded["resource_type"],
                    formato=uploaded.get("format"),
                )
            )

        db.session.commit()
        flash("Inmueble actualizado como arrendado con informacion del inquilino y contrato.", "success")
        return redirect(url_for("detalle_arrendamiento", id=inmueble.id))
    return render_template("form_arrendatario.html", inmueble=inmueble, contrato=contrato, estado_objetivo=estado_objetivo)


@admin_bp.route("/admin/cambiar_estado/<int:id>", methods=["POST"], endpoint="cambiar_estado")
@login_required
def cambiar_estado(id):
    inmueble = Inmueble.query.get_or_404(id)
    nuevo_estado = clean_text(request.form.get("estado"))
    estado_anterior = inmueble.estado

    estados_validos = ["disponible", "pendiente", "arrendado"]
    if nuevo_estado not in estados_validos:
        flash("Estado no válido", "error")
        return redirect(url_for("admin_inmuebles"))

    if nuevo_estado in {"pendiente", "arrendado"}:
        return redirect(url_for("arrendar_inmueble", id=inmueble.id, estado=nuevo_estado))

    inmueble.estado = nuevo_estado
    inmueble.estado_detalle = None

    if nuevo_estado == "disponible":
        _clear_arrendatario_data(inmueble)
        if is_arrendado_state(estado_anterior):
            _deactivate_active_contract(inmueble.id)

    db.session.commit()
    flash(f"Estado actualizado a {nuevo_estado}", "success")
    return redirect(url_for("admin_inmuebles"))


@admin_bp.route("/admin", endpoint="panel_admin")
@login_required
def panel_admin():
    return render_template("admin.html", **get_dashboard_metrics())


def _build_fe_payload_from_inmueble(inmueble, contrato):
    hoy = datetime.utcnow().date().isoformat()
    nombre_cliente = None
    nit_cliente = None
    descripcion_item = "Servicio de administración inmobiliaria"

    if contrato:
        nombre_cliente = contrato.nombre or inmueble.arrendatario_nombre or inmueble.titulo
        nit_cliente = contrato.nit or inmueble.arrendatario_num_doc or "222222222"
        descripcion_item = f"Facturación arriendo inmueble #{inmueble.id} - {inmueble.titulo}"
        valor_total = float(contrato.canon or inmueble.precio or 0)
    else:
        nombre_cliente = inmueble.arrendatario_nombre or inmueble.titulo
        nit_cliente = inmueble.arrendatario_num_doc or "222222222"
        valor_total = float(inmueble.precio or 0)

    return {
        "numero_factura": f"FE-TEST-{inmueble.id}-{int(datetime.utcnow().timestamp())}",
        "fecha_emision": hoy,
        "cliente_nombre": nombre_cliente,
        "cliente_nit": nit_cliente,
        "valor_total": valor_total,
        "descripcion_item": descripcion_item,
    }


@admin_bp.route("/admin/facturacion", endpoint="facturacion")
@login_required
def facturacion():
    q = (request.args.get("q") or "").strip()
    query = Inmueble.query

    if q:
        if q.isdigit():
            query = query.filter(
                (Inmueble.id == int(q))
                | (Inmueble.titulo.ilike(f"%{q}%"))
                | (Inmueble.ubicacion.ilike(f"%{q}%"))
            )
        else:
            query = query.filter(
                (Inmueble.titulo.ilike(f"%{q}%"))
                | (Inmueble.ubicacion.ilike(f"%{q}%"))
            )

    inmuebles = query.order_by(Inmueble.id.desc()).limit(100).all()
    return render_template("facturacion.html", inmuebles=inmuebles, q=q)


def _calcular_estado_pago_contrato(contrato):
    if not contrato:
        return "Pendiente", 0

    hoy = date.today()
    if contrato.fecha_limite:
        dias_mora = (hoy - contrato.fecha_limite).days
        if dias_mora > 0:
            return "Vencido", dias_mora

    if (contrato.pago or 0) >= (contrato.canon or 0) and (contrato.canon or 0) > 0:
        return "Pagado", 0

    return "Pendiente", 0


def _parse_mes_anio():
    hoy = datetime.utcnow()
    mes = request.args.get("mes", type=int) or hoy.month
    anio = request.args.get("anio", type=int) or hoy.year
    mes = max(1, min(12, mes))
    return mes, anio


def _month_name(num):
    nombres = [
        "Ene", "Feb", "Mar", "Abr", "May", "Jun",
        "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
    ]
    return nombres[num - 1]


@admin_bp.route("/admin/estadisticas", endpoint="estadisticas")
@login_required
def estadisticas():
    mes, anio = _parse_mes_anio()
    return render_template("estadisticas.html", mes=mes, anio=anio)


@admin_bp.route("/admin/api/estadisticas/estado-pagos", endpoint="api_estadisticas_estado_pagos")
@login_required
def api_estadisticas_estado_pagos():
    mes, anio = _parse_mes_anio()
    pagos = PagoArriendo.query.filter(
        db.extract("month", PagoArriendo.fecha_pago) == mes,
        db.extract("year", PagoArriendo.fecha_pago) == anio,
    ).all()

    conteo = {"Pagado": 0, "Pendiente": 0, "Vencido": 0}
    for p in pagos:
        estado = (p.estado or "Pendiente").capitalize()
        if estado not in conteo:
            estado = "Pendiente"
        conteo[estado] += 1

    return {
        "labels": list(conteo.keys()),
        "values": list(conteo.values()),
        "mes": mes,
        "anio": anio,
    }


@admin_bp.route("/admin/api/estadisticas/recaudado", endpoint="api_estadisticas_recaudado")
@login_required
def api_estadisticas_recaudado():
    anio = request.args.get("anio", type=int) or datetime.utcnow().year
    labels = []
    values = []

    for mes in range(1, 13):
        total = db.session.query(db.func.coalesce(db.func.sum(PagoArriendo.valor_pagado), 0)).filter(
            db.extract("month", PagoArriendo.fecha_pago) == mes,
            db.extract("year", PagoArriendo.fecha_pago) == anio,
        ).scalar() or 0
        labels.append(_month_name(mes))
        values.append(float(total))

    return {"labels": labels, "values": values, "anio": anio}


@admin_bp.route("/admin/api/estadisticas/dias-mora", endpoint="api_estadisticas_dias_mora")
@login_required
def api_estadisticas_dias_mora():
    mes, anio = _parse_mes_anio()
    contratos = ContratoArriendo.query.filter_by(activo=True).all()

    labels = []
    values = []
    for c in contratos:
        if not c.fecha_limite:
            continue
        if c.fecha_limite.month != mes or c.fecha_limite.year != anio:
            continue
        labels.append(c.nombre or f"Contrato {c.id}")
        values.append(int(c.dias_mora or 0))

    return {"labels": labels, "values": values, "mes": mes, "anio": anio}


@admin_bp.route("/admin/api/estadisticas/ingresos-gastos", endpoint="api_estadisticas_ingresos_gastos")
@login_required
def api_estadisticas_ingresos_gastos():
    mes, anio = _parse_mes_anio()

    ingresos_arriendo = db.session.query(db.func.coalesce(db.func.sum(PagoArriendo.valor_pagado), 0)).filter(
        db.extract("month", PagoArriendo.fecha_pago) == mes,
        db.extract("year", PagoArriendo.fecha_pago) == anio,
    ).scalar() or 0

    ingresos_base = db.session.query(db.func.coalesce(db.func.sum(Ingreso.valor), 0)).filter(
        db.extract("month", Ingreso.fecha) == mes,
        db.extract("year", Ingreso.fecha) == anio,
    ).scalar() or 0

    otros_ingresos = db.session.query(db.func.coalesce(db.func.sum(OtroIngreso.valor), 0)).filter(
        db.extract("month", OtroIngreso.fecha) == mes,
        db.extract("year", OtroIngreso.fecha) == anio,
    ).scalar() or 0

    gastos = db.session.query(db.func.coalesce(db.func.sum(Gasto.valor), 0)).filter(
        db.extract("month", Gasto.fecha) == mes,
        db.extract("year", Gasto.fecha) == anio,
    ).scalar() or 0

    total_ingresos = float(ingresos_arriendo or 0) + float(ingresos_base or 0) + float(otros_ingresos or 0)

    return {
        "labels": ["Ingresos", "Gastos"],
        "values": [total_ingresos, float(gastos or 0)],
        "mes": mes,
        "anio": anio,
    }


@admin_bp.route("/admin/api/estadisticas/gastos-porcentaje", endpoint="api_estadisticas_gastos_porcentaje")
@login_required
def api_estadisticas_gastos_porcentaje():
    mes, anio = _parse_mes_anio()
    rows = db.session.query(
        Gasto.categoria,
        db.func.coalesce(db.func.sum(Gasto.valor), 0),
    ).filter(
        db.extract("month", Gasto.fecha) == mes,
        db.extract("year", Gasto.fecha) == anio,
    ).group_by(Gasto.categoria).all()

    labels = [r[0] or "Sin categoría" for r in rows]
    values = [float(r[1] or 0) for r in rows]

    return {"labels": labels, "values": values, "mes": mes, "anio": anio}


@admin_bp.route("/admin/facturacion/<int:inmueble_id>", methods=["GET", "POST"], endpoint="detalle_facturacion")
@login_required
def detalle_facturacion(inmueble_id):
    inmueble = Inmueble.query.get_or_404(inmueble_id)
    contrato = ContratoArriendo.query.filter_by(inmueble_id=inmueble.id, activo=True).first()
    pagos = []

    if request.method == "POST":
        accion = (request.form.get("accion") or "").strip()

        if accion == "guardar_contrato":
            try:
                fecha_inicio_raw = request.form.get("fecha_inicio_contrato")
                fecha_pago_raw = request.form.get("fecha_pago")
                fecha_limite_raw = request.form.get("fecha_limite")

                if not fecha_inicio_raw:
                    flash("La fecha de inicio de contrato es obligatoria.", "error")
                    return redirect(url_for("detalle_facturacion", inmueble_id=inmueble.id))

                if contrato is None:
                    contrato = ContratoArriendo(inmueble_id=inmueble.id, activo=True)

                contrato.incremento = float(request.form.get("incremento") or 0)
                contrato.fecha_inicio_contrato = parse_date_or_none(fecha_inicio_raw)
                contrato.vigencia_contrato = int(request.form.get("vigencia_contrato") or 12)
                contrato.mes = clean_text(request.form.get("mes"))
                contrato.fecha_pago = parse_date_or_none(fecha_pago_raw)
                contrato.nombre = clean_text(request.form.get("nombre")) or (inmueble.arrendatario_nombre or "Sin nombre")
                contrato.nit = clean_text(request.form.get("nit"))
                contrato.celular = clean_text(request.form.get("celular"))
                contrato.direccion = clean_text(request.form.get("direccion")) or inmueble.ubicacion
                contrato.direccion2 = clean_text(request.form.get("direccion2"))
                contrato.correo = clean_text(request.form.get("correo")) or inmueble.arrendatario_correo
                contrato.canon = float(request.form.get("canon") or 0)
                contrato.estado_pago_inquilino = clean_text(request.form.get("estado_pago_inquilino")) or "Pendiente"
                contrato.fecha_limite = parse_date_or_none(fecha_limite_raw)
                contrato.dias_mora = int(request.form.get("dias_mora") or 0)
                contrato.pago = float(request.form.get("pago") or 0)
                contrato.propietario = clean_text(request.form.get("propietario"))
                contrato.comision = float(request.form.get("comision") or 0)
                contrato.pago_adicional = float(request.form.get("pago_adicional") or 0)
                contrato.reintegro = float(request.form.get("reintegro") or 0)
                contrato.pago_propietario = float(request.form.get("pago_propietario") or 0)
                contrato.estado_pago_propietario = clean_text(request.form.get("estado_pago_propietario")) or "Pendiente"

                estado_calc, mora_calc = _calcular_estado_pago_contrato(contrato)
                contrato.estado_pago_inquilino = estado_calc
                contrato.dias_mora = mora_calc

                db.session.add(contrato)
                db.session.commit()
                flash("Contrato de facturación guardado correctamente.", "success")
            except Exception as exc:
                db.session.rollback()
                current_app.logger.exception("Error guardando contrato de facturación")
                flash(f"Error guardando contrato: {str(exc)}", "error")

            return redirect(url_for("detalle_facturacion", inmueble_id=inmueble.id))

        if accion == "registrar_pago":
            try:
                if contrato is None:
                    flash("Primero debes guardar el contrato.", "error")
                    return redirect(url_for("detalle_facturacion", inmueble_id=inmueble.id))

                fecha_pago = parse_date_or_none(request.form.get("pago_fecha"))
                mes = clean_text(request.form.get("pago_mes"))
                anio = int(request.form.get("pago_anio") or datetime.utcnow().year)
                valor = float(request.form.get("pago_valor") or 0)
                estado = clean_text(request.form.get("pago_estado")) or "Pendiente"
                observacion = clean_text(request.form.get("pago_observacion"))

                if not fecha_pago or not mes:
                    flash("Debes completar fecha y mes del pago.", "error")
                    return redirect(url_for("detalle_facturacion", inmueble_id=inmueble.id))

                pago = PagoArriendo(
                    contrato_id=contrato.id,
                    fecha_pago=fecha_pago,
                    valor_pagado=valor,
                    mes_correspondiente=mes,
                    anio_correspondiente=anio,
                    estado=estado,
                    observacion=observacion,
                )
                db.session.add(pago)

                contrato.pago = (contrato.pago or 0) + valor
                estado_calc, mora_calc = _calcular_estado_pago_contrato(contrato)
                contrato.estado_pago_inquilino = estado_calc
                contrato.dias_mora = mora_calc

                db.session.commit()
                flash("Pago registrado correctamente.", "success")
            except Exception as exc:
                db.session.rollback()
                current_app.logger.exception("Error registrando pago")
                flash(f"Error registrando pago: {str(exc)}", "error")

            return redirect(url_for("detalle_facturacion", inmueble_id=inmueble.id))

    if contrato is not None:
        pagos = PagoArriendo.query.filter_by(contrato_id=contrato.id).order_by(PagoArriendo.fecha_pago.desc()).all()

    return render_template(
        "detalle_facturacion.html",
        inmueble=inmueble,
        contrato=contrato,
        pagos=pagos,
    )


@admin_bp.route(
    "/admin/facturacion/<int:inmueble_id>/generar-fe-prueba",
    methods=["POST"],
    endpoint="generar_fe_prueba",
)
@login_required
def generar_fe_prueba(inmueble_id):
    inmueble = Inmueble.query.get_or_404(inmueble_id)
    contrato = ContratoArriendo.query.filter_by(inmueble_id=inmueble.id, activo=True).first()

    payload = _build_fe_payload_from_inmueble(inmueble, contrato)
    software_pin = current_app.config.get("DIAN_SOFTWARE_PIN", "")
    dian_env = current_app.config.get("DIAN_ENV", "sandbox")
    payload["dian_env"] = dian_env

    fe_result = generate_signed_invoice_envelope(payload, software_pin=software_pin)
    if not fe_result.get("ok"):
        return {"ok": False, "errors": fe_result.get("errors", ["No se pudo generar FE"])}, 400

    dian_client = DianClient(
        endpoint_url=current_app.config.get("DIAN_ENDPOINT_URL", ""),
        environment=dian_env,
    )
    dian_response = dian_client.submit_invoice(fe_result["dian_envelope"])

    try:
        factura = FacturaElectronica(
            numero_factura=payload["numero_factura"],
            contrato_id=contrato.id if contrato else None,
            cliente_nombre=payload.get("cliente_nombre"),
            cliente_nit=payload.get("cliente_nit"),
            valor_total=float(payload.get("valor_total") or 0),
            valor_arriendo=float(contrato.canon or 0) if contrato else float(inmueble.precio or 0),
            valor_comision=float(contrato.comision or 0) if contrato else 0.0,
            otros_valores=float(contrato.pago_adicional or 0) if contrato else 0.0,
            fecha_emision=parse_date_or_none(payload.get("fecha_emision")),
            estado_dian="recibida" if dian_response.get("ok") else "error",
            cufe=fe_result.get("signature_stub"),
            xml_firmado=fe_result.get("signed_xml"),
            observacion=dian_response.get("message"),
        )
        db.session.add(factura)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error guardando traza de factura electrónica de prueba")
        return {"ok": False, "errors": [f"Error guardando traza FE: {str(exc)}"]}, 500

    return {
        "ok": True,
        "invoice_number": payload["numero_factura"],
        "signature_stub": fe_result.get("signature_stub"),
        "dian_response": dian_response,
    }


@admin_bp.route("/admin/inmuebles", strict_slashes=False, endpoint="admin_inmuebles")
@login_required
def admin_inmuebles():
    error_admin_inmuebles = None
    id_filtro = request.args.get("id", type=int)
    solo_destacados = request.args.get("destacados", type=int) == 1
    estado_filtro = request.args.get("estado", type=str)

    try:
        listing_context = get_admin_listing_context(
            page=request.args.get("page", 1, type=int),
            id_filtro=id_filtro,
            solo_destacados=solo_destacados,
            estado_filtro=estado_filtro,
        )
    except Exception as exc:
        current_app.logger.exception("Error obteniendo inmuebles del panel admin")
        error_admin_inmuebles = str(exc)
        listing_context = {
            "inmuebles": [],
            "pagination": type("obj", (object,), {"pages": 0, "page": 1, "has_prev": False, "has_next": False, "prev_num": 1, "next_num": 1})(),
            "id_filtro": id_filtro,
            "solo_destacados": solo_destacados,
            "estado_filtro": estado_filtro,
        }

    return render_template("admin_inmuebles.html", **listing_context, error_admin_inmuebles=error_admin_inmuebles)


@admin_bp.route("/admin/activar_plan/<int:id>", methods=["POST"], endpoint="activar_plan")
@login_required
def activar_plan(id):
    inmueble = Inmueble.query.get_or_404(id)
    plan = clean_text(request.form.get("plan")) or "Basico"
    dias = {"Basico": 30, "Premium": 30, "Destacado": 30}.get(plan, 30)
    inmueble.plan = plan
    inmueble.plan_activo = True
    inmueble.plan_vencimiento = datetime.utcnow() + timedelta(days=dias)
    db.session.commit()
    return redirect(url_for("admin_inmuebles"))


@admin_bp.route("/admin/desactivar_plan/<int:id>", methods=["POST"], endpoint="desactivar_plan")
@login_required
def desactivar_plan(id):
    inmueble = Inmueble.query.get_or_404(id)
    inmueble.plan = None
    inmueble.plan_activo = False
    inmueble.plan_vencimiento = None
    db.session.commit()
    return redirect(url_for("admin_inmuebles"))


@admin_bp.route("/admin/inmuebles/nuevo", endpoint="nuevo_inmueble")
@login_required
def nuevo_inmueble():
    return render_template(
        "admin_nuevo_inmueble.html",
        return_target=get_admin_inmuebles_return_target(request.args.get("next"), url_for),
    )


@admin_bp.route("/agregar_inmueble", methods=["POST"], endpoint="agregar_inmueble")
@login_required
def agregar_inmueble():
    try:
        return_target = get_admin_inmuebles_return_target(request.form.get("next"), url_for)
        required_fields = missing_required_fields(
            request.form,
            ["titulo", "tipo_negocio", "descripcion", "tipo", "municipio", "precio"],
        )
        if required_fields:
            flash("Faltan campos obligatorios para crear el inmueble", "error")
            return redirect(url_for("nuevo_inmueble", next=return_target))

        nuevo = Inmueble(
            titulo=clean_text(request.form.get("titulo")),
            tipo_negocio=clean_text(request.form.get("tipo_negocio")),
            ubicacion=clean_text(request.form.get("ubicacion")) or None,
            latitud=request.form.get("latitud") or None,
            longitud=request.form.get("longitud") or None,
            descripcion=clean_text(request.form.get("descripcion")),
            tipo=clean_text(request.form.get("tipo")),
            municipio=clean_text(request.form.get("municipio")),
            habitaciones=request.form.get("habitaciones") or None,
            banos=request.form.get("banos") or None,
            parqueadero=parse_boolean_choice(request.form.get("parqueadero")),
            destacado=parse_boolean_choice(request.form.get("destacado")),
            precio=parse_price_value(request.form.get("precio")),
            comision_porcentaje=parse_percentage_value(request.form.get("comision_porcentaje")),
            plan="Basico",
            estado_pago="pendiente",
            prioridad=0,
        )
        _assign_owner_fields(nuevo, request.form)
        db.session.add(nuevo)
        db.session.commit()

        imagenes = [imagen for imagen in request.files.getlist("imagenes") if imagen and imagen.filename != ""]
        for index, imagen in enumerate(imagenes):
            try:
                url = upload_image(imagen)
                db.session.add(
                    Imagen(
                        url=url,
                        orden=index,
                        principal=index == 0,
                        inmueble_id=nuevo.id,
                    )
                )
            except Exception as exc:
                current_app.logger.exception("Error subiendo imagen a Cloudinary al crear inmueble")
                flash(f"Error al subir imagen: {str(exc)}", "error")

        db.session.commit()
        flash("Inmueble creado correctamente", "success")
        return redirect(return_target)
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error creando inmueble")
        flash(f"Error al crear inmueble: {str(exc)}", "error")
        return redirect(url_for("nuevo_inmueble", next=get_admin_inmuebles_return_target(request.form.get("next"), url_for)))


@admin_bp.route("/admin/eliminar_imagen/<int:id>", methods=["POST"], endpoint="eliminar_imagen")
@login_required
def eliminar_imagen(id):
    inmueble_id = None
    try:
        imagen = Imagen.query.get_or_404(id)
        inmueble_id = imagen.inmueble_id
        remote_deleted = delete_image_by_url(imagen.url)
        db.session.delete(imagen)
        imagenes_restantes = Imagen.query.filter_by(inmueble_id=inmueble_id).all()
        sync_image_priority(imagenes_restantes)
        db.session.commit()
        if remote_deleted:
            flash("✅ Imagen eliminada correctamente", "success")
        else:
            flash("⚠️ La imagen se eliminó del sistema, pero no se pudo confirmar el borrado en Cloudinary.", "warning")
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error eliminando imagen")
        flash(f"❌ Error al eliminar imagen: {str(exc)}", "error")

    return redirect(url_for("editar_inmueble", id=inmueble_id))


@admin_bp.route("/editar/<int:id>", methods=["GET", "POST"], endpoint="editar_inmueble")
@login_required
def editar_inmueble(id):
    inmueble = Inmueble.query.get_or_404(id)
    inmueble.imagenes = Imagen.query.filter_by(inmueble_id=inmueble.id).order_by(Imagen.orden).all()
    contrato = ContratoArriendo.query.filter_by(inmueble_id=inmueble.id, activo=True).first()
    documentos = contrato.documentos if contrato else []

    if request.method == "POST":
        try:
            titulo = clean_text(request.form.get("titulo"))
            tipo_negocio = clean_text(request.form.get("tipo_negocio"))
            ubicacion = clean_text(request.form.get("ubicacion")) or None
            descripcion = clean_text(request.form.get("descripcion"))
            tipo = clean_text(request.form.get("tipo"))
            municipio = clean_text(request.form.get("municipio"))
            required_fields = missing_required_fields(
                request.form,
                ["titulo", "tipo_negocio", "descripcion", "tipo", "municipio", "precio"],
            )
            if required_fields:
                flash("❌ Todos los campos obligatorios deben estar completos", "error")
                return render_template("editar.html", inmueble=inmueble, contrato=contrato, documentos=documentos)

            inmueble.titulo = titulo
            inmueble.tipo_negocio = tipo_negocio
            inmueble.ubicacion = ubicacion
            inmueble.latitud = request.form.get("latitud") or None
            inmueble.longitud = request.form.get("longitud") or None
            inmueble.descripcion = descripcion
            inmueble.tipo = tipo
            inmueble.municipio = municipio
            inmueble.precio = parse_price_value(request.form.get("precio"))
            inmueble.comision_porcentaje = parse_percentage_value(request.form.get("comision_porcentaje"))
            inmueble.habitaciones = request.form.get("habitaciones") or None
            inmueble.banos = request.form.get("banos") or None
            inmueble.parqueadero = parse_boolean_choice(request.form.get("parqueadero"))
            inmueble.destacado = parse_boolean_choice(request.form.get("destacado"))
            _assign_owner_fields(inmueble, request.form)
            plan = clean_text(request.form.get("plan"))
            if plan:
                inmueble.plan = plan
                inmueble.plan_activo = True
                if not inmueble.plan_vencimiento:
                    inmueble.plan_vencimiento = datetime.utcnow() + timedelta(days=30)
            else:
                inmueble.plan = None
                inmueble.plan_activo = False
                inmueble.plan_vencimiento = None
            principal_source = request.form.get("principal_source", "")

            imagenes = [imagen for imagen in request.files.getlist("imagenes") if imagen and imagen.filename != ""]
            imagenes_creadas = []

            if principal_source == "new" and imagenes:
                sync_image_priority(inmueble.imagenes)
                total_nuevas = len(imagenes)
                for imagen_existente in inmueble.imagenes:
                    imagen_existente.orden = (imagen_existente.orden or 0) + total_nuevas
                    imagen_existente.principal = False
                for index, imagen in enumerate(imagenes):
                    try:
                        url = upload_image(imagen)
                        nueva_imagen = Imagen(url=url, orden=index, principal=index == 0, inmueble_id=inmueble.id)
                        db.session.add(nueva_imagen)
                        imagenes_creadas.append(nueva_imagen)
                    except Exception as exc:
                        flash(f"❌ Error al subir imagen: {str(exc)}", "error")
            elif imagenes:
                sync_image_priority(inmueble.imagenes)
                ultimo_orden = max([imagen.orden for imagen in inmueble.imagenes], default=-1)
                for index, imagen in enumerate(imagenes, start=1):
                    try:
                        url = upload_image(imagen)
                        nueva_imagen = Imagen(url=url, orden=ultimo_orden + index, principal=False, inmueble_id=inmueble.id)
                        db.session.add(nueva_imagen)
                        imagenes_creadas.append(nueva_imagen)
                    except Exception as exc:
                        flash(f"❌ Error al subir imagen: {str(exc)}", "error")

            sync_image_priority(list(inmueble.imagenes) + imagenes_creadas)
            db.session.commit()
            flash("✅ Inmueble actualizado correctamente", "success")
            return redirect(url_for("editar_inmueble", id=inmueble.id))
        except Exception as exc:
            db.session.rollback()
            current_app.logger.exception("Error editando inmueble")
            flash(f"❌ Error al editar inmueble: {str(exc)}", "error")
            return render_template("editar.html", inmueble=inmueble, contrato=contrato, documentos=documentos)

    return render_template("editar.html", inmueble=inmueble, contrato=contrato, documentos=documentos)


@admin_bp.route("/admin/reordenar_imagenes", methods=["POST"], endpoint="reordenar_imagenes")
@login_required
def reordenar_imagenes():
    data = request.get_json()
    imagenes_actualizadas = []

    for item in data["orden"]:
        imagen = Imagen.query.get(item["id"])
        if imagen:
            imagen.orden = item["posicion"]
            imagenes_actualizadas.append(imagen)

    sync_image_priority(imagenes_actualizadas)
    db.session.commit()
    return {"status": "ok"}


@admin_bp.route("/eliminar_inmueble/<int:id>", methods=["POST"], endpoint="eliminar_inmueble")
@login_required
def eliminar_inmueble(id):
    return_target = get_admin_inmuebles_return_target(request.form.get("next"), url_for)
    try:
        inmueble = Inmueble.query.get_or_404(id)
        imagenes = Imagen.query.filter_by(inmueble_id=id).all()
        imagenes_no_eliminadas = []

        for imagen in imagenes:
            try:
                remote_deleted = delete_image_by_url(imagen.url)
            except Exception:
                current_app.logger.exception("Error eliminando imagen remota en Cloudinary")
                remote_deleted = False

            if not remote_deleted:
                imagenes_no_eliminadas.append(imagen.url)
            db.session.delete(imagen)

        db.session.delete(inmueble)
        db.session.commit()
        if imagenes_no_eliminadas:
            flash("⚠️ El inmueble se eliminó, pero una o más imágenes no se pudieron borrar en Cloudinary.", "warning")
        else:
            flash("Inmueble eliminado correctamente", "success")
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Error eliminando inmueble")
        flash(f"Error al eliminar inmueble: {str(exc)}", "error")

    return redirect(return_target)
