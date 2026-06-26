# Backend Setup

## Variables de entorno

El proyecto soporta estas variables en `.env`:

- `SECRET_KEY`
- `ENV`
- `FLASK_DEBUG`
- `DATABASE_URL`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_HOST`
- `MYSQL_DATABASE`
- `ADMIN_USER`
- `ADMIN_PASSWORD`
- `EMAIL_USER`
- `EMAIL_PASSWORD`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `PREFERRED_HOST`
- `CANONICAL_BASE_URL`
- `REDIRECT_APEX_TO_WWW`

## Base de datos

- En local, si no hay `DATABASE_URL`, usa `sqlite:///inmuebles.db`.
- En cualquier entorno, si existe `DATABASE_URL`, se usa esa URL.
- Si no existe `DATABASE_URL` pero están completos `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST` y `MYSQL_DATABASE`, la app arma la conexión MySQL automáticamente.
- `add_cols.py` aplica columnas faltantes de forma idempotente para el esquema legado.
- La app ya está preparada para usar Flask-Migrate en cambios futuros de esquema.

## Ejecución

1. Activar el entorno virtual.
2. Configurar `.env` a partir de `.env.example`.
3. Ejecutar `python run.py`.

## Dominio canónico (www)

- Valor recomendado para producción:
	- `PREFERRED_HOST=www.metropolitaninmobiliaria.co`
	- `CANONICAL_BASE_URL=https://www.metropolitaninmobiliaria.co`
	- `REDIRECT_APEX_TO_WWW=1`
- La app inyecta `canonical_url` en templates y agrega redirección 301 de `metropolitaninmobiliaria.co` hacia `www.metropolitaninmobiliaria.co` cuando la petición llega al backend.
- Si el dominio raíz no resuelve o no apunta al servidor de la app, la redirección no se puede ejecutar; ese caso se corrige en DNS/proxy.

## Migraciones recomendadas

Cuando quieras dejar atrás `add_cols.py`, el flujo recomendado es:

1. `flask --app run.py db init`
2. `flask --app run.py db migrate -m "descripcion del cambio"`
3. `flask --app run.py db upgrade`

## Baseline actual

- Se creó una revisión base vacía: `cc74351769d3`.
- Esa revisión no crea ni borra tablas; sirve para empezar a versionar la base actual sin perder datos.

## PythonAnywhere sin borrar datos

Si tu base de datos en PythonAnywhere ya tiene inmuebles cargados y coincide con el esquema actual, no debes correr una migración que intente reconstruir tablas. El flujo seguro es:

1. Hacer backup de la base.
2. Subir el código nuevo al servidor.
3. Configurar variables de entorno y entorno virtual.
4. Verificar la conexión activa con:

```bash
python -c "from app import app; print(app.config['SQLALCHEMY_DATABASE_URI'])"
```

Ese valor no debe ser `sqlite:///inmuebles.db` en producción. Si aparece SQLite, faltan `DATABASE_URL` o las variables `MYSQL_*`.
5. Ejecutar `flask --app run.py db stamp cc74351769d3`

Ese comando le dice a Alembic: "esta base ya está en esta versión". No elimina datos ni recrea tablas.

Después de ese paso, los siguientes cambios ya sí se manejan así:

1. Cambiar modelos.
2. Ejecutar `flask --app run.py db migrate -m "descripcion del cambio"`
3. Ejecutar `flask --app run.py db upgrade`

Con eso futuras columnas o cambios de esquema se aplican incrementalmente sobre la base existente.

## Próximo paso recomendado

El siguiente salto natural es migrar de `add_cols.py` a un flujo versionado con Alembic o Flask-Migrate.
