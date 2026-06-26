from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()



class Inmueble(db.Model):
    __tablename__ = "inmueble"

    id = db.Column(db.Integer, primary_key=True)

    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer, default=0)
    tipo_negocio = db.Column(db.String(20))  # Venta / Arriendo
    tipo = db.Column(db.String(50))  # Casa / Apartamento / Lote
    municipio = db.Column(db.String(100))
    ubicacion = db.Column(db.String(255), nullable=True)
    latitud = db.Column(db.String(50), nullable=True)
    longitud = db.Column(db.String(50), nullable=True)

    habitaciones = db.Column(db.Integer)
    banos = db.Column(db.Integer)
    parqueadero = db.Column(db.Boolean, default=False)

    precio = db.Column(db.Float)
    comision_porcentaje = db.Column(db.Float, default=0.0)

    # ===== ESTADO Y ARRENDATARIO =====
    # Estados: disponible, pendiente, no_disponible
    estado = db.Column(db.String(20), default="disponible")
    estado_detalle = db.Column(db.String(50), nullable=True)  # Sub-estado cuando es pendiente
    arrendatario_nombre = db.Column(db.String(120), nullable=True)
    arrendatario_tipo_doc = db.Column(db.String(30), nullable=True)
    arrendatario_num_doc = db.Column(db.String(50), nullable=True)
    arrendatario_telefono = db.Column(db.String(50), nullable=True)
    arrendatario_telefono_secundario = db.Column(db.String(50), nullable=True)
    arrendatario_correo = db.Column(db.String(120), nullable=True)
    arrendatario_fecha_pago = db.Column(db.Date, nullable=True)
    arrendatario_descripcion = db.Column(db.Text, nullable=True)
    propietario_nombre = db.Column(db.String(120), nullable=True)
    propietario_cedula = db.Column(db.String(50), nullable=True)
    propietario_telefono = db.Column(db.String(50), nullable=True)
    propietario_telefono_secundario = db.Column(db.String(50), nullable=True)
    propietario_correo = db.Column(db.String(120), nullable=True)

    # ===== PLANES =====
    plan = db.Column(db.String(20))
    plan_activo = db.Column(db.Boolean, default=False)
    plan_vencimiento = db.Column(db.DateTime)
    estado_pago = db.Column(db.String(20), default="Pendiente")

    # ===== PRIORIDAD =====
    prioridad = db.Column(db.Integer, default=0)

    # ===== DESTACADO =====
    destacado = db.Column(db.Boolean, default=False)

    # ===== RELACIÓN CON IMÁGENES =====
    imagenes = db.relationship(
        "Imagen",
        backref="inmueble",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="Imagen.orden"
    )


class Imagen(db.Model):
    __tablename__ = "inmueble_imagen"

    id = db.Column(db.Integer, primary_key=True)

    url = db.Column(db.String(500))
    orden = db.Column(db.Integer)
    principal = db.Column(db.Boolean, default=False)

    inmueble_id = db.Column(
        db.Integer,
        db.ForeignKey("inmueble.id"),
        nullable=False
    )


# ============================================================
# MODELOS DE FACTURACIÓN Y CONTABILIDAD
# ============================================================

class ContratoArriendo(db.Model):
    __tablename__ = "contrato_arriendo"

    id = db.Column(db.Integer, primary_key=True)
    inmueble_id = db.Column(db.Integer, db.ForeignKey("inmueble.id"), nullable=False)
    incremento = db.Column(db.Float, default=0.0)  # % de incremento anual
    fecha_inicio_contrato = db.Column(db.Date, nullable=False)
    vigencia_contrato = db.Column(db.Integer, default=12)  # meses
    mes = db.Column(db.String(20), nullable=True)  # mes actual de facturación
    fecha_pago = db.Column(db.Date, nullable=True)  # fecha de pago mensual
    nombre = db.Column(db.String(120), nullable=False)
    nit = db.Column(db.String(50), nullable=True)
    celular = db.Column(db.String(50), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    direccion2 = db.Column(db.String(255), nullable=True)
    correo = db.Column(db.String(120), nullable=True)
    canon = db.Column(db.Float, default=0.0)  # valor del arriendo
    estado_pago_inquilino = db.Column(db.String(20), default="Pendiente")  # Pagado, Pendiente, Vencido
    fecha_limite = db.Column(db.Date, nullable=True)
    dias_mora = db.Column(db.Integer, default=0)
    pago = db.Column(db.Float, default=0.0)  # valor pagado
    propietario = db.Column(db.String(120), nullable=True)
    comision = db.Column(db.Float, default=0.0)  # ingreso para la inmobiliaria
    pago_adicional = db.Column(db.Float, default=0.0)
    reintegro = db.Column(db.Float, default=0.0)
    pago_propietario = db.Column(db.Float, default=0.0)
    estado_pago_propietario = db.Column(db.String(20), default="Pendiente")
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inmueble = db.relationship("Inmueble", backref="contratos")
    pagos = db.relationship("PagoArriendo", backref="contrato", cascade="all, delete-orphan", lazy=True)


class PagoArriendo(db.Model):
    __tablename__ = "pago_arriendo"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey("contrato_arriendo.id"), nullable=False)
    fecha_pago = db.Column(db.Date, nullable=False)
    valor_pagado = db.Column(db.Float, default=0.0)
    mes_correspondiente = db.Column(db.String(20), nullable=False)
    anio_correspondiente = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20), default="Pendiente")  # Pagado, Pendiente, Vencido
    observacion = db.Column(db.Text, nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


class DocumentoArrendamiento(db.Model):
    __tablename__ = "documento_arrendamiento"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey("contrato_arriendo.id"), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    resource_type = db.Column(db.String(20), default="raw")
    formato = db.Column(db.String(20), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    contrato = db.relationship("ContratoArriendo", backref=db.backref("documentos", cascade="all, delete-orphan", lazy=True))

    @property
    def display_filename(self):
        """Best-effort filename for download/labels, keeping extension when known."""
        name = (self.nombre or "documento").strip()
        fmt = (self.formato or "").strip().lower()
        if fmt and not name.lower().endswith(f".{fmt}"):
            name = f"{name}.{fmt}"
        return name


class Ingreso(db.Model):
    __tablename__ = "ingreso"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    propiedad_id = db.Column(db.Integer, db.ForeignKey("inmueble.id"), nullable=True)
    cliente = db.Column(db.String(120), nullable=True)
    valor = db.Column(db.Float, default=0.0)
    estado = db.Column(db.String(20), default="Pendiente")
    observacion = db.Column(db.Text, nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    propiedad = db.relationship("Inmueble", backref="ingresos")


class OtroIngreso(db.Model):
    __tablename__ = "otro_ingreso"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # Venta / Comisión
    cliente = db.Column(db.String(120), nullable=True)
    propiedad = db.Column(db.String(200), nullable=True)
    valor = db.Column(db.Float, default=0.0)
    estado = db.Column(db.String(20), default="Pendiente")
    observacion = db.Column(db.Text, nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


class Gasto(db.Model):
    __tablename__ = "gasto"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    valor = db.Column(db.Float, default=0.0)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


class FacturaElectronica(db.Model):
    __tablename__ = "factura_electronica"

    id = db.Column(db.Integer, primary_key=True)
    numero_factura = db.Column(db.String(50), unique=True, nullable=False)
    contrato_id = db.Column(db.Integer, db.ForeignKey("contrato_arriendo.id"), nullable=True)
    cliente_nombre = db.Column(db.String(120), nullable=False)
    cliente_nit = db.Column(db.String(50), nullable=True)
    cliente_correo = db.Column(db.String(120), nullable=True)
    valor_total = db.Column(db.Float, default=0.0)
    valor_arriendo = db.Column(db.Float, default=0.0)
    valor_comision = db.Column(db.Float, default=0.0)
    otros_valores = db.Column(db.Float, default=0.0)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    estado_dian = db.Column(db.String(20), default="Pendiente")  # Pendiente, Enviada, Aceptada, Rechazada
    cufe = db.Column(db.String(100), nullable=True)  # Código único de factura electrónica
    xml_firmado = db.Column(db.Text, nullable=True)
    pdf_url = db.Column(db.String(500), nullable=True)
    observacion = db.Column(db.Text, nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
