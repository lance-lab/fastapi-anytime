import base64
import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from fastapi import HTTPException, status

from app.config import SQLITE_DB_PATH, SQLITE_DB_PATH_ENV


def resolve_database_path() -> Path:
    configured_path = os.getenv(SQLITE_DB_PATH_ENV, SQLITE_DB_PATH)
    if not configured_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Set {SQLITE_DB_PATH_ENV} to the path of your SQLite database file.",
        )

    return Path(configured_path).expanduser()


def get_database_path() -> Path:
    database_path = resolve_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return database_path


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    try:
        connection = sqlite3.connect(get_database_path())
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not connect to SQLite database: {exc}",
        ) from exc

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def quote_sqlite_identifier(identifier: str) -> str:
    return f'"{identifier.replace(chr(34), chr(34) + chr(34))}"'


def list_user_tables() -> list[str]:
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
                AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

    return [row["name"] for row in rows]


def table_exists(table_name: str) -> bool:
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
                AND lower(name) = lower(?)
            """,
            (table_name,),
        ).fetchone()

    return row is not None


def ensure_table_exists(table_name: str) -> None:
    if not table_exists(table_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table not found: {table_name}",
        )


def read_table_rows(table_name: str, limit: int = 100) -> list[dict[str, Any]]:
    ensure_table_exists(table_name)

    with database_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM {quote_sqlite_identifier(table_name)} LIMIT ?",
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def create_row(table_name: str, values: dict[str, Any]) -> int:
    columns = list(values)
    column_sql = ", ".join(quote_sqlite_identifier(column) for column in columns)
    placeholder_sql = ", ".join("?" for _ in columns)

    with database_connection() as connection:
        cursor = connection.execute(
            f"""
            INSERT INTO {quote_sqlite_identifier(table_name)}
                ({column_sql})
            VALUES ({placeholder_sql})
            """,
            tuple(values.values()),
        )
        connection.commit()
        return cursor.lastrowid


def create_organization(organization: dict[str, Any]) -> dict[str, Any]:
    ensure_table_exists("organizations")
    created_id = create_row("organizations", organization)

    return {"id": created_id, **organization}


def create_my_tender(my_tender: dict[str, Any]) -> dict[str, Any]:
    ensure_table_exists("my_tenders")
    created_id = create_row("my_tenders", my_tender)

    return {"id": created_id, **my_tender}


def read_my_tender(tender_id: int) -> dict[str, Any]:
    ensure_table_exists("my_tenders")
    ensure_table_exists("organizations")

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                mt.id AS tender_id,
                mt.item_number AS tender_item_number,
                mt.item_nested_number AS tender_item_nested_number,
                mt.tender_number AS tender_tender_number,
                mt.tender_type AS tender_tender_type,
                mt.contracting_authority_id AS tender_contracting_authority_id,
                mt.created_at AS tender_created_at,
                mt.updated_at AS tender_updated_at,
                o.id AS organization_id,
                o.identification_number AS organization_identification_number,
                o.name AS organization_name,
                o.tax_identification_number AS organization_tax_identification_number,
                o.full_address AS organization_full_address,
                o.city AS organization_city,
                o.street AS organization_street,
                o.street_number AS organization_street_number,
                o.state AS organization_state,
                o.postal_code AS organization_postal_code,
                o.created_at AS organization_created_at,
                o.updated_at AS organization_updated_at
            FROM my_tenders AS mt
            LEFT JOIN organizations AS o
                ON mt.contracting_authority_id = o.id
            WHERE mt.id = ?
            """,
            (tender_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"My tender not found: {tender_id}",
        )

    values = dict(row)
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

    try:
        created_id = create_row(
            "credentials",
            {"username": username, "password_hash": password_hash},
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Credential already exists for username: {username}",
        ) from exc

    return {"id": created_id, "username": username}


def list_credentials() -> dict[str, str]:
    ensure_table_exists("credentials")

    with database_connection() as connection:
        rows = connection.execute(
            "SELECT username, password_hash FROM credentials"
        ).fetchall()

    return {row["username"]: row["password_hash"] for row in rows}


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
