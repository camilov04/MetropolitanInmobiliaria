from datetime import datetime
from pathlib import Path
import shutil

from app import app
from app.models import DocumentoArrendamiento, Imagen, Inmueble, db
from sqlalchemy import inspect, text


def get_table_names():
    return set(inspect(db.engine).get_table_names())


def count_rows(table_name):
    tables = get_table_names()
    if table_name not in tables:
        return 0
    return db.session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0


def create_table_if_missing(model, table_name):
    tables = get_table_names()
    if table_name in tables:
        print(f"La tabla '{table_name}' ya existe.")
        return

    print(f"La tabla '{table_name}' no existe. Creandola sin tocar las tablas existentes...")
    model.__table__.create(bind=db.engine, checkfirst=True)
    print(f"Tabla '{table_name}' creada correctamente.")


def backup_sqlite_database():
    database_path = getattr(db.engine.url, "database", None)
    print(f"Base de datos activa: {db.engine.url}")

    if db.engine.url.drivername != "sqlite" or not database_path:
        return

    db_path = Path(database_path)
    if not db_path.exists():
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.stem}.backup_{timestamp}{db_path.suffix}")
    shutil.copy2(db_path, backup_path)
    print(f"Backup SQLite creado: {backup_path}")


def add_column_if_missing(table_name, column_name, sql_definition):
    inspector = inspect(db.engine)
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}

    if column_name in existing_columns:
        print(f"La columna '{column_name}' ya existe en '{table_name}'.")
        return

    print(f"Agregando columna faltante '{column_name}' en '{table_name}'...")
    db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_definition}"))
    print(f"Columna '{column_name}' añadida correctamente.")


INMUEBLE_COLUMNS = {
    "orden": "INTEGER DEFAULT 0",
    "ubicacion": "VARCHAR(255)",
    "latitud": "VARCHAR(50)",
    "longitud": "VARCHAR(50)",
    "comision_porcentaje": "FLOAT DEFAULT 0",
    "estado": "VARCHAR(20) DEFAULT 'disponible'",
    "estado_detalle": "VARCHAR(50)",
    "arrendatario_nombre": "VARCHAR(120)",
    "arrendatario_tipo_doc": "VARCHAR(30)",
    "arrendatario_num_doc": "VARCHAR(50)",
    "arrendatario_telefono": "VARCHAR(50)",
    "arrendatario_telefono_secundario": "VARCHAR(50)",
    "arrendatario_correo": "VARCHAR(120)",
    "arrendatario_fecha_pago": "DATE",
    "arrendatario_descripcion": "TEXT",
    "propietario_nombre": "VARCHAR(120)",
    "propietario_cedula": "VARCHAR(50)",
    "propietario_telefono": "VARCHAR(50)",
    "propietario_telefono_secundario": "VARCHAR(50)",
    "propietario_correo": "VARCHAR(120)",
    "plan_activo": "BOOLEAN DEFAULT 0",
    "estado_pago": "VARCHAR(20) DEFAULT 'Pendiente'",
    "prioridad": "INTEGER DEFAULT 0",
    "destacado": "BOOLEAN DEFAULT 0",
}


with app.app_context():
    backup_sqlite_database()

    inmuebles_antes = count_rows("inmueble")
    print(f"Inmuebles antes del ajuste: {inmuebles_antes}")

    create_table_if_missing(Inmueble, "inmueble")

    for column_name, sql_definition in INMUEBLE_COLUMNS.items():
        add_column_if_missing("inmueble", column_name, sql_definition)

    create_table_if_missing(Imagen, "inmueble_imagen")
    create_table_if_missing(DocumentoArrendamiento, "documento_arrendamiento")

    db.session.commit()

    inmuebles_despues = count_rows("inmueble")
    print(f"Inmuebles despues del ajuste: {inmuebles_despues}")

    if inmuebles_antes != inmuebles_despues:
        raise RuntimeError(
            "El conteo de inmuebles cambio durante add_cols.py. "
            "El script es aditivo y no deberia alterar registros existentes."
        )

    print("Esquema verificado correctamente sin modificar la cantidad de inmuebles.")
