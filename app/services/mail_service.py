import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")


def send_property_request_email(nombre, telefono, correo, titulo, descripcion, plan, enlaces, logger=None):
    try:
        remitente = EMAIL_USER
        password = EMAIL_PASSWORD

        if not remitente or not password:
            if logger:
                logger.warning("Email no configurado: faltan EMAIL_USER o EMAIL_PASSWORD")
            return False

        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = "🏠¡Nueva solicitud de inmueble!🏢"
        mensaje["From"] = remitente
        mensaje["To"] = f"{remitente}, {correo}"

        imagenes_html = "".join(
            f'''<div style="margin-bottom:10px;"><img src="{url}" style="width:300px; border-radius:8px;"></div>'''
            for url in enlaces
        )

        html = f"""
    <html>
    <body style="font-family: Arial; background:#f4f4f4; padding:20px;">
        <div style="max-width:600px; margin:auto; background:white; padding:20px; border-radius:10px;">
            <h2 style="color:#333;">Nueva solicitud de inmueble</h2>
            <p><b>Nombre:</b> {nombre}</p>
            <p><b>Teléfono:</b> {telefono}</p>
            <p><b>Correo:</b> {correo}</p>
            <hr>
            <p><b>Título:</b> {titulo}</p>
            <p><b>Descripción:</b><br>{descripcion}</p>
            <hr>
            <h3>Imágenes:</h3>
            {imagenes_html}
            <hr>
            <p><b>Plan:</b> {plan}</p>
            <hr>
            <a href="mailto:{correo}" style="background:#f5c542; padding:10px 15px;">
            Contactar cliente
            </a>
        </div>
    </body>
    </html>
    """

        mensaje.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remitente, password)
            server.sendmail(remitente, [remitente, correo], mensaje.as_string())

        return True
    except Exception:
        if logger:
            logger.exception("Error enviando correo de solicitud de inmueble")
        return False
