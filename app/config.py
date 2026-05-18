import os


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


SQLITE_DB_PATH = os.path.join("data", "database.sqlite3")
SQLITE_DB_PATH_ENV = "SQLITE_DB_PATH"
RUN_DATABASE_INIT = env_bool("RUN_DATABASE_INIT", True)
