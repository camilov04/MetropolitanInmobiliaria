import os
from pathlib import Path


DEFAULT_PREFERRED_HOST = "www.metropolitaninmobiliaria.co"
BASE_DIR = Path(__file__).resolve().parent


def build_sqlite_uri(path_value):
    sqlite_path = Path(path_value).expanduser()
    if not sqlite_path.is_absolute():
        sqlite_path = BASE_DIR / sqlite_path

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{sqlite_path.as_posix()}"


def build_database_uri():
    explicit_database_url = os.getenv("DATABASE_URL", "").strip()
    if explicit_database_url:
        return explicit_database_url

    sqlite_db_path = os.getenv("SQLITE_DB_PATH", "").strip()
    if sqlite_db_path:
        return build_sqlite_uri(sqlite_db_path)

    mysql_user = os.getenv("MYSQL_USER", "").strip()
    mysql_password = os.getenv("MYSQL_PASSWORD", "").strip()
    mysql_host = os.getenv("MYSQL_HOST", "").strip()
    mysql_database = os.getenv("MYSQL_DATABASE", "").strip()

    if all([mysql_user, mysql_password, mysql_host, mysql_database]):
        return f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_database}?charset=utf8mb4"

    return build_sqlite_uri("instance/inmuebles.db")


def build_preferred_host():
    return os.getenv("PREFERRED_HOST", DEFAULT_PREFERRED_HOST).strip().lower()


def build_canonical_base_url(preferred_host):
    explicit_canonical_base_url = os.getenv("CANONICAL_BASE_URL", "").strip().rstrip("/")
    if explicit_canonical_base_url:
        return explicit_canonical_base_url

    return f"https://{preferred_host}"


def env_flag(name, default="0"):
    return os.getenv(name, default).strip() == "1"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "mi_clave_super_secreta_123")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    DEBUG = env_flag("FLASK_DEBUG")
    PREFERRED_HOST = build_preferred_host()
    CANONICAL_BASE_URL = build_canonical_base_url(PREFERRED_HOST)
    REDIRECT_APEX_TO_WWW = env_flag("REDIRECT_APEX_TO_WWW", "1")
    PREFERRED_URL_SCHEME = "https"

    # ==============================
    # FACTURACIÓN ELECTRÓNICA DIAN
    # ==============================
    DIAN_ENV = os.getenv("DIAN_ENV", "sandbox").strip().lower()  # sandbox | production
    DIAN_SOFTWARE_ID = os.getenv("DIAN_SOFTWARE_ID", "").strip()
    DIAN_SOFTWARE_PIN = os.getenv("DIAN_SOFTWARE_PIN", "").strip()
    DIAN_TEST_SET_ID = os.getenv("DIAN_TEST_SET_ID", "").strip()
    DIAN_ENDPOINT_URL = os.getenv("DIAN_ENDPOINT_URL", "").strip() or (
        "https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc"
        if DIAN_ENV == "sandbox"
        else "https://vpfe.dian.gov.co/WcfDianCustomerServices.svc"
    )
