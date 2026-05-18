import base64
import hashlib
import os
import secrets
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


def create_organization(organization: dict[str, Any]) -> dict[str, Any]:
    table_name = "organizations"
    ensure_table_exists(table_name)
    columns = [
        "identification_number",
        "name",
        "tax_identification_number",
        "full_address",
        "city",
        "street",
        "street_number",
        "state",
        "postal_code",
    ]
    timestamp_columns = ["created_at", "updated_at"]
    all_columns = columns + timestamp_columns
    column_sql = ", ".join(quote_access_identifier(column) for column in all_columns)
    placeholders = ", ".join("?" for _ in columns)
    values = [organization.get(column) for column in columns]

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"INSERT INTO {quote_access_identifier(table_name)} ({column_sql}) VALUES ({placeholders}, Now(), Now())",
            *values,
        )
        cursor.execute("SELECT @@IDENTITY")
        created_id = cursor.fetchone()[0]
        connection.commit()

    return {"id": created_id, **organization}


def create_my_tender(my_tender: dict[str, Any]) -> dict[str, Any]:
    table_name = "my_tenders"
    ensure_table_exists(table_name)
    columns = [
        "item_number",
        "item_nested_number",
        "tender_number",
        "tender_type",
        "contracting_authority_id",
    ]
    timestamp_columns = ["created_at", "updated_at"]
    all_columns = columns + timestamp_columns
    column_sql = ", ".join(quote_access_identifier(column) for column in all_columns)
    placeholders = ", ".join("?" for _ in columns)
    values = [my_tender.get(column) for column in columns]

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"INSERT INTO {quote_access_identifier(table_name)} ({column_sql}) VALUES ({placeholders}, Now(), Now())",
            *values,
        )
        cursor.execute("SELECT @@IDENTITY")
        created_id = cursor.fetchone()[0]
        connection.commit()

    return {"id": created_id, **my_tender}


def read_my_tender(tender_id: int) -> dict[str, Any]:
    ensure_table_exists("my_tenders")
    ensure_table_exists("organizations")

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                mt.[id] AS tender_id,
                mt.[item_number] AS tender_item_number,
                mt.[item_nested_number] AS tender_item_nested_number,
                mt.[tender_number] AS tender_tender_number,
                mt.[tender_type] AS tender_tender_type,
                mt.[contracting_authority_id] AS tender_contracting_authority_id,
                mt.[created_at] AS tender_created_at,
                mt.[updated_at] AS tender_updated_at,
                o.[id] AS organization_id,
                o.[identification_number] AS organization_identification_number,
                o.[name] AS organization_name,
                o.[tax_identification_number] AS organization_tax_identification_number,
                o.[full_address] AS organization_full_address,
                o.[city] AS organization_city,
                o.[street] AS organization_street,
                o.[street_number] AS organization_street_number,
                o.[state] AS organization_state,
                o.[postal_code] AS organization_postal_code,
                o.[created_at] AS organization_created_at,
                o.[updated_at] AS organization_updated_at
            FROM [my_tenders] AS mt
            LEFT JOIN [organizations] AS o
                ON mt.[contracting_authority_id] = o.[id]
            WHERE mt.[id] = ?
            """,
            tender_id,
        )
        row = cursor.fetchone()
        columns = [column[0] for column in cursor.description]

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"My tender not found: {tender_id}",
        )

    values = dict(zip(columns, row))
    contracting_authority = None
    if values["organization_id"] is not None:
        contracting_authority = {
            "id": values["organization_id"],
            "identification_number": values["organization_identification_number"],
            "name": values["organization_name"],
            "tax_identification_number": values["organization_tax_identification_number"],
            "full_address": values["organization_full_address"],
            "city": values["organization_city"],
            "street": values["organization_street"],
            "street_number": values["organization_street_number"],
            "state": values["organization_state"],
            "postal_code": values["organization_postal_code"],
            "created_at": values["organization_created_at"],
            "updated_at": values["organization_updated_at"],
        }

    return {
        "id": values["tender_id"],
        "item_number": values["tender_item_number"],
        "item_nested_number": values["tender_item_nested_number"],
        "tender_number": values["tender_tender_number"],
        "tender_type": values["tender_tender_type"],
        "contracting_authority_id": values["tender_contracting_authority_id"],
        "contracting_authority": contracting_authority,
        "created_at": values["tender_created_at"],
        "updated_at": values["tender_updated_at"],
    }


def create_credential(username: str, password: str) -> dict[str, Any]:
    ensure_table_exists("credentials")
    password_hash = hash_password(password)

    with access_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO [credentials]
                    ([username], [password_hash], [created_at], [updated_at])
                VALUES (?, ?, Now(), Now())
                """,
                username,
                password_hash,
            )
        except pyodbc.Error as exc:
            if is_unique_constraint_error(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Credential already exists for username: {username}",
                ) from exc
            raise
        cursor.execute("SELECT @@IDENTITY")
        created_id = cursor.fetchone()[0]
        connection.commit()

    return {"id": created_id, "username": username}


def list_credentials() -> dict[str, str]:
    ensure_table_exists("credentials")

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT [username], [password_hash] FROM [credentials]")
        rows = cursor.fetchall()

    return {row.username: row.password_hash for row in rows}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 210_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_digest = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${encoded_salt}${encoded_digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_digest = password_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.b64decode(encoded_digest.encode("ascii"))
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
    except (ValueError, TypeError):
        return False

    return secrets.compare_digest(actual_digest, expected_digest)


def is_unique_constraint_error(exc: pyodbc.Error) -> bool:
    message = str(exc).lower()
    return "duplicate" in message or "unique" in message or "already exists" in message
