import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pyodbc
from fastapi import HTTPException, status

from app.config import (
    ACCESS_DB_PATH,
    ACCESS_DB_PATH_ENV,
    ACCESS_ODBC_DRIVER_ENV,
    DEFAULT_ACCESS_ODBC_DRIVER,
)


def resolve_database_path() -> Path:
    configured_path = os.getenv(ACCESS_DB_PATH_ENV, ACCESS_DB_PATH)
    if not configured_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Set {ACCESS_DB_PATH_ENV} to the path of your .accdb or .mdb file.",
        )

    return Path(configured_path).expanduser()


def get_database_path() -> Path:
    database_path = resolve_database_path()
    if not database_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Access database file was not found: {database_path}",
        )

    return database_path


def build_connection_string(database_path: Path) -> str:
    driver = os.getenv(ACCESS_ODBC_DRIVER_ENV, DEFAULT_ACCESS_ODBC_DRIVER)
    return f"DRIVER={{{driver}}};DBQ={database_path};"


@contextmanager
def access_connection() -> Iterator[pyodbc.Connection]:
    try:
        connection = pyodbc.connect(build_connection_string(get_database_path()))
    except pyodbc.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not connect to Access database: {exc}",
        ) from exc

    try:
        yield connection
    finally:
        connection.close()


def list_user_tables() -> list[str]:
    with access_connection() as connection:
        cursor = connection.cursor()
        tables = [
            row.table_name
            for row in cursor.tables(tableType="TABLE")
            if not row.table_name.startswith("MSys")
        ]
    return sorted(tables)


def table_exists(table_name: str) -> bool:
    return table_name.lower() in {table.lower() for table in list_user_tables()}


def ensure_table_exists(table_name: str) -> None:
    if not table_exists(table_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table not found: {table_name}",
        )


def quote_access_identifier(identifier: str) -> str:
    return f"[{identifier.replace(']', ']]')}]"


def read_table_rows(table_name: str, limit: int = 100) -> list[dict[str, Any]]:
    ensure_table_exists(table_name)

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(f"SELECT TOP {limit} * FROM {quote_access_identifier(table_name)}")
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]
