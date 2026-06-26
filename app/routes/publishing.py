from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from ..services.property_service import send_property_request
from ..services_cloudinary import upload_image
from ..validators import clean_text, missing_required_fields


publishing_bp = Blueprint("publishing", __name__)


def enviar_correo_solicitud(nombre, telefono, correo, titulo, descripcion, plan, enlaces):
    return send_property_request(
        nombre,
        telefono,
        correo,
        titulo,
        descripcion,
        plan,
        enlaces,
        logger=current_app.logger,
    )


@publishing_bp.route("/publicar", methods=["GET", "POST"], endpoint="publicar")
def publicar():
    if request.method == "POST":
        try:
            required_fields = missing_required_fields(
                request.form,
                ["nombre", "telefono", "correo", "titulo", "descripcion"],
            )
            if required_fields:
                flash("Completa todos los campos obligatorios para publicar", "error")
                return render_template("publicar.html")

            nombre = clean_text(request.form.get("nombre"))
            telefono = clean_text(request.form.get("telefono"))
            correo = clean_text(request.form.get("correo"))
            titulo = clean_text(request.form.get("titulo"))
            descripcion = clean_text(request.form.get("descripcion"))
            imagenes = request.files.getlist("imagenes")
            session["publicacion_temp"] = request.form.to_dict()
            plan = clean_text(request.form.get("plan_seleccionado")) or "Basico"
            enlaces = []

            for imagen in imagenes:
                if imagen and imagen.filename != "":
                    try:
                        enlaces.append(upload_image(imagen))
                    except Exception as exc:
                        current_app.logger.exception("Error subiendo imagen durante publicacion")
                        flash(f"Error al subir imagen: {str(exc)}", "error")

            enviar_correo_solicitud(nombre, telefono, correo, titulo, descripcion, plan, enlaces)
            flash("Solicitud enviada correctamente", "success")
            return redirect(url_for("home"))
        except Exception as exc:
            current_app.logger.exception("Error procesando publicacion")
            flash(f"Error al procesar solicitud: {str(exc)}", "error")

    return render_template("publicar.html")


@publishing_bp.route("/promocionar", endpoint="promocionar")
def promocionar():
    data = session.get("publicacion_temp")
    imagenes = session.get("imagenes_temp", [])

    if not data:
        return redirect(url_for("publicar"))

    return render_template("promocionar.html", data=data, imagenes=imagenes)


@publishing_bp.route("/guardar_temp", methods=["POST"], endpoint="guardar_temp")
def guardar_temp():
    try:
        imagenes = request.files.getlist("imagenes")
        urls = []

        for imagen in imagenes:
            if imagen and imagen.filename != "":
                try:
                    urls.append(upload_image(imagen))
                except Exception:
                    current_app.logger.exception("Error subiendo imagen temporal")

        session["imagenes_temp"] = urls
        session["publicacion_temp"] = request.form.to_dict()
    except Exception:
        current_app.logger.exception("Error guardando publicacion temporal")

    return "", 204


@publishing_bp.route("/confirmar_envio", methods=["POST"], endpoint="confirmar_envio")
def confirmar_envio():
    data = session.get("publicacion_temp")
    imagenes = session.get("imagenes_temp", [])

    if not data:
        return redirect(url_for("publicar"))

    try:
        plan = clean_text(request.form.get("plan")) or "Basico"
        enviar_correo_solicitud(
            data.get("nombre", ""),
            data.get("telefono", ""),
            data.get("correo", ""),
            data.get("titulo", ""),
            data.get("descripcion", ""),
            plan,
            imagenes,
        )
        session.pop("publicacion_temp", None)
        session.pop("imagenes_temp", None)
        flash("Solicitud enviada correctamente con promoción", "success")
    except Exception as exc:
        current_app.logger.exception("Error confirmando envio de publicacion")
        flash(f"Error al confirmar envío: {str(exc)}", "error")

    return redirect(url_for("home"))
