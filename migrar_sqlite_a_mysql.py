"""Migra datos desde SQLite local a MySQL usando el esquema actual."""

import os
import sqlite3

# ===== CONFIGURACIÓN =====

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "instance", "inmuebles.db")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASS = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DATABASE", "metropolitan_db")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))

# ==========================

try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    print("❌ Instala pymysql:  pip install pymysql")
    exit(1)


def conectar_mysql():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        port=MYSQL_PORT,
        charset="utf8mb4",
        autocommit=False,
    )


def crear_tablas(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inmueble (
            id INT PRIMARY KEY,
            titulo VARCHAR(200) NOT NULL,
            descripcion TEXT NOT NULL,
            orden INT DEFAULT 0,
            tipo_negocio VARCHAR(20),
            tipo VARCHAR(50),
            municipio VARCHAR(100),
            ubicacion VARCHAR(255),
            latitud VARCHAR(50),
            longitud VARCHAR(50),
            habitaciones INT,
            banos INT,
            parqueadero TINYINT(1) DEFAULT 0,
            precio DOUBLE,
            comision_porcentaje DOUBLE DEFAULT 0,
            estado VARCHAR(20) DEFAULT 'disponible',
            arrendatario_nombre VARCHAR(120),
            arrendatario_tipo_doc VARCHAR(30),
            arrendatario_num_doc VARCHAR(50),
            arrendatario_telefono VARCHAR(50),
            arrendatario_correo VARCHAR(120),
            arrendatario_fecha_pago DATE,
            arrendatario_descripcion TEXT,
            plan VARCHAR(20),
            plan_activo TINYINT(1) DEFAULT 0,
            plan_vencimiento DATETIME,
            estado_pago VARCHAR(20) DEFAULT 'Pendiente',
            prioridad INT DEFAULT 0,
            destacado TINYINT(1) DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inmueble_imagen (
            id INT PRIMARY KEY,
            url VARCHAR(500),
            orden INT,
            principal TINYINT(1) DEFAULT 0,
            inmueble_id INT NOT NULL,
            FOREIGN KEY (inmueble_id) REFERENCES inmueble(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    print("✅ Tablas creadas en MySQL")


def migrar_datos():
    # Conectar SQLite
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ No se encontró la base SQLite en: {SQLITE_PATH}")
        print("   Ajusta la variable SQLITE_PATH al inicio del script.")
        exit(1)

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # Conectar MySQL
    mysql_conn = conectar_mysql()
    mysql_cur = mysql_conn.cursor()

    # Crear tablas
    crear_tablas(mysql_cur)
    mysql_conn.commit()

    # ----- Migrar inmuebles -----
    sqlite_cur.execute("SELECT * FROM inmueble")
    inmuebles = sqlite_cur.fetchall()

    mysql_cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    mysql_cur.execute("TRUNCATE TABLE inmueble_imagen")
    mysql_cur.execute("TRUNCATE TABLE inmueble")
    mysql_cur.execute("SET FOREIGN_KEY_CHECKS = 1")

    for row in inmuebles:
        mysql_cur.execute("""
            INSERT INTO inmueble
            (id, titulo, descripcion, orden, tipo_negocio, tipo, municipio,
             ubicacion, latitud, longitud, habitaciones, banos, parqueadero,
             precio, comision_porcentaje, estado, arrendatario_nombre,
             arrendatario_tipo_doc, arrendatario_num_doc, arrendatario_telefono,
             arrendatario_correo, arrendatario_fecha_pago, arrendatario_descripcion,
             plan, plan_activo, plan_vencimiento, estado_pago, prioridad, destacado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row["id"],
            row["titulo"],
            row["descripcion"],
            row["orden"] if "orden" in row.keys() else 0,
            row["tipo_negocio"],
            row["tipo"],
            row["municipio"],
            row["ubicacion"] if "ubicacion" in row.keys() else None,
            row["latitud"] if "latitud" in row.keys() else None,
            row["longitud"] if "longitud" in row.keys() else None,
            row["habitaciones"],
            row["banos"],
            1 if row["parqueadero"] else 0,
            row["precio"],
            row["comision_porcentaje"] if "comision_porcentaje" in row.keys() else 0,
            row["estado"] if "estado" in row.keys() else "disponible",
            row["arrendatario_nombre"] if "arrendatario_nombre" in row.keys() else None,
            row["arrendatario_tipo_doc"] if "arrendatario_tipo_doc" in row.keys() else None,
            row["arrendatario_num_doc"] if "arrendatario_num_doc" in row.keys() else None,
            row["arrendatario_telefono"] if "arrendatario_telefono" in row.keys() else None,
            row["arrendatario_correo"] if "arrendatario_correo" in row.keys() else None,
            row["arrendatario_fecha_pago"] if "arrendatario_fecha_pago" in row.keys() else None,
            row["arrendatario_descripcion"] if "arrendatario_descripcion" in row.keys() else None,
            row["plan"] if "plan" in row.keys() else None,
            1 if ("plan_activo" in row.keys() and row["plan_activo"]) else 0,
            row["plan_vencimiento"] if "plan_vencimiento" in row.keys() else None,
            row["estado_pago"] if "estado_pago" in row.keys() else "Pendiente",
            row["prioridad"] if "prioridad" in row.keys() else 0,
            1 if ("destacado" in row.keys() and row["destacado"]) else 0,
        ))

    print(f"✅ {len(inmuebles)} inmuebles migrados")

    # ----- Migrar imágenes -----
    sqlite_cur.execute("SELECT * FROM inmueble_imagen")
    imagenes = sqlite_cur.fetchall()

    for row in imagenes:
        if row["inmueble_id"] is None:
            print(f"   ⚠️  Imagen {row['id']} sin inmueble asociado, omitida")
            continue

        mysql_cur.execute("""
            INSERT INTO inmueble_imagen (id, url, orden, principal, inmueble_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            row["id"],
            row["url"],
            row["orden"],
            1 if row["principal"] else 0,
            row["inmueble_id"],
        ))

    print(f"✅ {len(imagenes)} imágenes migradas")

    # Commit y cerrar
    mysql_conn.commit()
    mysql_cur.close()
    mysql_conn.close()
    sqlite_cur.close()
    sqlite_conn.close()

    print("\n🎉 Migración completada exitosamente")
    print(f"   Base de datos MySQL: {MYSQL_DB}")


if __name__ == "__main__":
    print("🔄 Iniciando migración SQLite → MySQL...\n")
    migrar_datos()
