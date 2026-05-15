import os


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


ACCESS_DB_PATH = r"C:\Users\lenor\Documents\anytime-db.accdb"
ACCESS_DB_PATH_ENV = "ACCESS_DB_PATH"
CREATE_ACCESS_DB_IF_MISSING = env_bool("CREATE_ACCESS_DB_IF_MISSING", True)
RUN_DATABASE_INIT = env_bool("RUN_DATABASE_INIT", True)
ACCESS_ODBC_DRIVER_ENV = "ACCESS_ODBC_DRIVER"
DEFAULT_ACCESS_ODBC_DRIVER = "Microsoft Access Driver (*.mdb, *.accdb)"
