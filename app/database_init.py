from pathlib import Path

import pyodbc
from fastapi import HTTPException, status

from app.config import CREATE_ACCESS_DB_IF_MISSING
from app.database import (
    access_connection,
    quote_access_identifier,
    resolve_database_path,
    table_exists,
)


ORGANIZATIONS_TABLE = "organizations"
MY_TENDERS_TABLE = "my_tenders"
APPLICANT_AUTHORITIES_TABLE = "applicant_authorities"
CREDENTIALS_TABLE = "credentials"
ORGANIZATIONS_IDENTIFICATION_NUMBER_INDEX = "ux_organizations_identification_number"
MY_TENDERS_CONTRACTING_AUTHORITY_FK = "fk_my_tenders_contracting_authority"
APPLICANT_AUTHORITIES_ORGANIZATION_FK = "fk_applicant_authorities_organization"
APPLICANT_AUTHORITIES_MY_TENDER_FK = "fk_applicant_authorities_my_tender"
APPLICANT_AUTHORITIES_UNIQUE_INDEX = "ux_applicant_authorities_tender_organization"
CREDENTIALS_USERNAME_INDEX = "ux_credentials_username"


def ensure_access_database_file() -> None:
    database_path = resolve_database_path()
    if database_path.exists():
        return

    if not CREATE_ACCESS_DB_IF_MISSING:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Access database file was not found: {database_path}",
        )

def ensure_organizations_table() -> None:
    if table_exists(ORGANIZATIONS_TABLE):
        ensure_organizations_timestamp_columns()
        ensure_organizations_index()
        return

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            CREATE TABLE {quote_access_identifier(ORGANIZATIONS_TABLE)} (
                [id] COUNTER PRIMARY KEY,
                [identification_number] INTEGER,
                [name] LONGTEXT,
                [tax_identification_number] TEXT(20),
                [full_address] LONGTEXT,
                [city] LONGTEXT,
                [street] LONGTEXT,
                [street_number] LONGTEXT,
                [state] LONGTEXT,
                [postal_code] TEXT(20),
                [created_at] DATETIME,
                [updated_at] DATETIME
            )
            """
        )
        create_organizations_index(cursor)
        connection.commit()


def ensure_organizations_timestamp_columns() -> None:
    columns = {
        row.column_name.lower()
        for row in get_table_columns(ORGANIZATIONS_TABLE)
    }

    with access_connection() as connection:
        cursor = connection.cursor()
        if "created_at" not in columns:
            cursor.execute(
                f"""
                ALTER TABLE {quote_access_identifier(ORGANIZATIONS_TABLE)}
                ADD COLUMN [created_at] DATETIME
                """
            )
        if "updated_at" not in columns:
            cursor.execute(
                f"""
                ALTER TABLE {quote_access_identifier(ORGANIZATIONS_TABLE)}
                ADD COLUMN [updated_at] DATETIME
                """
            )
        connection.commit()

def ensure_organizations_index() -> None:
    if organizations_index_exists(ORGANIZATIONS_IDENTIFICATION_NUMBER_INDEX):
        return

    with access_connection() as connection:
        cursor = connection.cursor()
        create_organizations_index(cursor)
        connection.commit()


def create_organizations_index(cursor) -> None:
    cursor.execute(
        f"""
        CREATE UNIQUE INDEX {quote_access_identifier(ORGANIZATIONS_IDENTIFICATION_NUMBER_INDEX)}
        ON {quote_access_identifier(ORGANIZATIONS_TABLE)} ([identification_number])
        """
    )

def ensure_my_tenders_table() -> None:
    if table_exists(MY_TENDERS_TABLE):
        ensure_my_tenders_columns()
        ensure_my_tenders_foreign_keys()
        return

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            CREATE TABLE {quote_access_identifier(MY_TENDERS_TABLE)} (
                [id] COUNTER PRIMARY KEY,
                [item_number] LONGTEXT,
                [item_nested_number] LONGTEXT,
                [tender_number] LONGTEXT,
                [tender_type] LONGTEXT,
                [contracting_authority_id] INTEGER,
                [created_at] DATETIME,
                [updated_at] DATETIME
            )
            """
        )
        create_my_tenders_contracting_authority_foreign_key(cursor)
        connection.commit()


def ensure_applicant_authorities_table() -> None:
    if table_exists(APPLICANT_AUTHORITIES_TABLE):
        ensure_applicant_authorities_constraints()
        return

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            CREATE TABLE {quote_access_identifier(APPLICANT_AUTHORITIES_TABLE)} (
                [id] COUNTER PRIMARY KEY,
                [my_tender_id] INTEGER,
                [organization_id] INTEGER,
                [created_at] DATETIME,
                [updated_at] DATETIME
            )
            """
        )
        create_applicant_authorities_unique_index(cursor)
        create_applicant_authorities_organization_foreign_key(cursor)
        create_applicant_authorities_my_tender_foreign_key(cursor)
        connection.commit()


def ensure_applicant_authorities_constraints() -> None:
    with access_connection() as connection:
        cursor = connection.cursor()
        try_create_constraint(cursor, create_applicant_authorities_unique_index)
        try_create_constraint(cursor, create_applicant_authorities_organization_foreign_key)
        try_create_constraint(cursor, create_applicant_authorities_my_tender_foreign_key)
        connection.commit()


def ensure_credentials_table() -> None:
    if table_exists(CREDENTIALS_TABLE):
        ensure_credentials_index()
        return

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            CREATE TABLE {quote_access_identifier(CREDENTIALS_TABLE)} (
                [id] COUNTER PRIMARY KEY,
                [username] TEXT(255),
                [password_hash] LONGTEXT,
                [created_at] DATETIME,
                [updated_at] DATETIME
            )
            """
        )
        create_credentials_username_index(cursor)
        connection.commit()


def ensure_credentials_index() -> None:
    with access_connection() as connection:
        cursor = connection.cursor()
        try_create_constraint(cursor, create_credentials_username_index)
        connection.commit()


def create_credentials_username_index(cursor) -> None:
    cursor.execute(
        f"""
        CREATE UNIQUE INDEX {quote_access_identifier(CREDENTIALS_USERNAME_INDEX)}
        ON {quote_access_identifier(CREDENTIALS_TABLE)} ([username])
        """
    )


def create_applicant_authorities_unique_index(cursor) -> None:
    cursor.execute(
        f"""
        CREATE UNIQUE INDEX {quote_access_identifier(APPLICANT_AUTHORITIES_UNIQUE_INDEX)}
        ON {quote_access_identifier(APPLICANT_AUTHORITIES_TABLE)} ([my_tender_id], [organization_id])
        """
    )


def create_applicant_authorities_organization_foreign_key(cursor) -> None:
    cursor.execute(
        f"""
        ALTER TABLE {quote_access_identifier(APPLICANT_AUTHORITIES_TABLE)}
        ADD CONSTRAINT {quote_access_identifier(APPLICANT_AUTHORITIES_ORGANIZATION_FK)}
        FOREIGN KEY ([organization_id])
        REFERENCES {quote_access_identifier(ORGANIZATIONS_TABLE)} ([id])
        """
    )


def create_applicant_authorities_my_tender_foreign_key(cursor) -> None:
    cursor.execute(
        f"""
        ALTER TABLE {quote_access_identifier(APPLICANT_AUTHORITIES_TABLE)}
        ADD CONSTRAINT {quote_access_identifier(APPLICANT_AUTHORITIES_MY_TENDER_FK)}
        FOREIGN KEY ([my_tender_id])
        REFERENCES {quote_access_identifier(MY_TENDERS_TABLE)} ([id])
        """
    )


def ensure_my_tenders_columns() -> None:
    columns = {
        row.column_name.lower()
        for row in get_table_columns(MY_TENDERS_TABLE)
    }

    with access_connection() as connection:
        cursor = connection.cursor()
        if "contracting_authority_id" not in columns:
            cursor.execute(
                f"""
                ALTER TABLE {quote_access_identifier(MY_TENDERS_TABLE)}
                ADD COLUMN [contracting_authority_id] INTEGER
                """
            )
        connection.commit()


def ensure_my_tenders_foreign_keys() -> None:
    with access_connection() as connection:
        cursor = connection.cursor()
        try_create_constraint(cursor, create_my_tenders_contracting_authority_foreign_key)
        connection.commit()


def create_my_tenders_contracting_authority_foreign_key(cursor) -> None:
    cursor.execute(
        f"""
        ALTER TABLE {quote_access_identifier(MY_TENDERS_TABLE)}
        ADD CONSTRAINT {quote_access_identifier(MY_TENDERS_CONTRACTING_AUTHORITY_FK)}
        FOREIGN KEY ([contracting_authority_id])
        REFERENCES {quote_access_identifier(ORGANIZATIONS_TABLE)} ([id])
        """
    )

def organizations_index_exists(index_name: str) -> bool:
    with access_connection() as connection:
        cursor = connection.cursor()
        statistics = cursor.statistics(table=ORGANIZATIONS_TABLE, unique=True)
        return any(
            row.index_name and row.index_name.lower() == index_name.lower()
            for row in statistics
        )


def get_table_columns(table_name: str):
    with access_connection() as connection:
        cursor = connection.cursor()
        return list(cursor.columns(table=table_name))


def is_existing_constraint_error(exc: pyodbc.Error) -> bool:
    message = str(exc).lower()
    return (
        "already exists" in message
        or "duplicate" in message
        or MY_TENDERS_CONTRACTING_AUTHORITY_FK.lower() in message
        or APPLICANT_AUTHORITIES_ORGANIZATION_FK.lower() in message
        or APPLICANT_AUTHORITIES_MY_TENDER_FK.lower() in message
        or APPLICANT_AUTHORITIES_UNIQUE_INDEX.lower() in message
        or CREDENTIALS_USERNAME_INDEX.lower() in message
    )


def try_create_constraint(cursor, create_constraint) -> None:
    try:
        create_constraint(cursor)
    except pyodbc.Error as exc:
        if not is_existing_constraint_error(exc):
            raise
