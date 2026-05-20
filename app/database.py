import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from fastapi import HTTPException, status

from app.auth import hash_password
from app.config import SQLITE_DB_PATH, SQLITE_DB_PATH_ENV


ORGANIZATIONS_TABLE = "organizacie"
MY_TENDERS_TABLE = "moje_tendre"
APPLICANT_AUTHORITIES_TABLE = "uchadzaci"
ATTRIBUTE_LIST_TABLE = "zoznam_atributov"
ADDITIONAL_ATTRIBUTES_TABLE = "dalsie_atributy"
CREDENTIALS_TABLE = "credentials"

DB_COLUMN_TRANSLATIONS = {
    ORGANIZATIONS_TABLE: {
        "Id": "id",
        "Ico": "ico",
        "Meno": "meno",
        "Dic": "dic",
        "PlnaAdresa": "plna_adresa",
        "Mesto": "mesto",
        "Ulica": "ulica",
        "CisloDomu": "cislo_domu",
        "Stat": "stat",
        "Psc": "psc",
        "StatutarnyOrgan": "statutarny_organ",
        "StatutarnyOrganFunkcia": "statutarny_organ_funkcia",
        "Vytvorene": "vytvorene",
        "Updatovane": "updatovane",
    },
    MY_TENDERS_TABLE: {
        "Id": "id",
        "CisloOpatrenia": "cislo_opatrenia",
        "CisloPodopatrenia": "cislo_podopatrenia",
        "CisloVyzvy": "cislo_vyzvy",
        "DruhZakazky": "druh_zakazky",
        "NazovZakazky": "nazov_zakazky",
        "NazovProjektu": "nazov_projektu",
        "KodProjektu": "kod_projektu",
        "PredmetZakazky": "predmet_zakazky",
        "RozdelenieZakazky": "rozdelenie_zakazky",
        "ObstaravatelId": "obstaravatel",
        "LehotaNaPredkladaniePonuk": "lehota_na_predkladanie_ponuk",
        "DatumOtvoreniaAVyhodnoteniaPonuk": "datum_otvorenia_a_vyhodnotenia_ponuk",
        "DatumPodpisuVyzvy": "datum_podpisu_vyzvy",
        "DatumPodpisuZaznam": "datum_podpisu_zaznam",
        "DatumPodpisuSplnomocnenia": "datum_podpisu_splnomocnenia",
        "Vytvorene": "vytvorene",
        "Updatovane": "updatovane",
    },
    CREDENTIALS_TABLE: {
        "Username": "username",
        "PasswordHash": "password_hash",
    },
    APPLICANT_AUTHORITIES_TABLE: {
        "Id": "id",
        "MojTenderId": "moj_tender_id",
        "OrganizaciaId": "organizacia_id",
    },
    ATTRIBUTE_LIST_TABLE: {
        "Id": "id",
        "Nazov": "nazov",
        "Vytvorene": "vytvorene",
        "Updatovane": "updatovane",
    },
    ADDITIONAL_ATTRIBUTES_TABLE: {
        "Id": "id",
        "Nazov": "nazov",
        "Hodnota": "hodnota",
        "MojTenderId": "moj_tender_id",
        "UchadzacId": "uchadzac_id",
        "Vytvorene": "vytvorene",
        "Updatovane": "updatovane",
    },
}

API_FIELD_TRANSLATIONS = {
    table_name: {
        db_column: api_field
        for api_field, db_column in column_translations.items()
    }
    for table_name, column_translations in DB_COLUMN_TRANSLATIONS.items()
}


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


def read_table_row_by_id(table_name: str, row_id: int) -> dict[str, Any]:
    ensure_table_exists(table_name)

    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT *
            FROM {quote_sqlite_identifier(table_name)}
            WHERE id = ?
            """,
            (row_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{table_name} row not found: {row_id}",
        )

    return dict(row)


def translate_to_db_columns(table_name: str, values: dict[str, Any]) -> dict[str, Any]:
    column_translations = DB_COLUMN_TRANSLATIONS.get(table_name, {})
    return {
        column_translations.get(column, column): value
        for column, value in values.items()
    }


def translate_to_api_fields(table_name: str, values: dict[str, Any]) -> dict[str, Any]:
    field_translations = API_FIELD_TRANSLATIONS.get(table_name, {})
    return {
        field_translations.get(column, column): value
        for column, value in values.items()
    }


def create_row(table_name: str, values: dict[str, Any]) -> int:
    db_values = translate_to_db_columns(table_name, values)
    columns = list(db_values)
    column_sql = ", ".join(quote_sqlite_identifier(column) for column in columns)
    placeholder_sql = ", ".join("?" for _ in columns)

    try:
        with database_connection() as connection:
            cursor = connection.execute(
                f"""
                INSERT INTO {quote_sqlite_identifier(table_name)}
                    ({column_sql})
                VALUES ({placeholder_sql})
                """,
                tuple(db_values.values()),
            )
            connection.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise constraint_error_response(table_name, exc) from exc


def delete_row(table_name: str, row_id: int) -> None:
    read_table_row_by_id(table_name, row_id)

    try:
        with database_connection() as connection:
            connection.execute(
                f"""
                DELETE FROM {quote_sqlite_identifier(table_name)}
                WHERE id = ?
                """,
                (row_id,),
            )
            connection.commit()
    except sqlite3.IntegrityError as exc:
        raise constraint_error_response(table_name, exc) from exc


def update_row(table_name: str, row_id: int, values: dict[str, Any]) -> None:
    read_table_row_by_id(table_name, row_id)
    db_values = translate_to_db_columns(table_name, values)
    if not db_values:
        return

    set_sql = ", ".join(
        f"{quote_sqlite_identifier(column)} = ?"
        for column in db_values
    )
    if "updatovane" not in db_values:
        set_sql = f"{set_sql}, updatovane = CURRENT_TIMESTAMP"

    try:
        with database_connection() as connection:
            connection.execute(
                f"""
                UPDATE {quote_sqlite_identifier(table_name)}
                SET {set_sql}
                WHERE id = ?
                """,
                (*db_values.values(), row_id),
            )
            connection.commit()
    except sqlite3.IntegrityError as exc:
        raise constraint_error_response(table_name, exc) from exc


def constraint_error_response(table_name: str, exc: sqlite3.IntegrityError) -> HTTPException:
    message = str(exc)
    lower_message = message.lower()

    if "unique constraint failed" in lower_message:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": f"{table_name} record already exists.",
                "constraint": message,
            },
        )

    if "foreign key constraint failed" in lower_message:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"{table_name} references a record that does not exist.",
                "constraint": message,
            },
        )

    if "not null constraint failed" in lower_message:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"{table_name} is missing a required value.",
                "constraint": message,
            },
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "message": f"{table_name} violates a database constraint.",
            "constraint": message,
        },
    )


def create_organization(organization: dict[str, Any]) -> dict[str, Any]:
    ensure_table_exists(ORGANIZATIONS_TABLE)
    created_id = create_row(ORGANIZATIONS_TABLE, organization)
    db_organization = read_table_row_by_id(ORGANIZATIONS_TABLE, created_id)

    return translate_to_api_fields(ORGANIZATIONS_TABLE, db_organization)


def read_organization(organization_id: int) -> dict[str, Any]:
    ensure_table_exists(ORGANIZATIONS_TABLE)
    db_organization = read_table_row_by_id(ORGANIZATIONS_TABLE, organization_id)

    return translate_to_api_fields(ORGANIZATIONS_TABLE, db_organization)


def create_attribute_list_item(attribute: dict[str, Any]) -> dict[str, Any]:
    ensure_table_exists(ATTRIBUTE_LIST_TABLE)
    created_id = create_row(ATTRIBUTE_LIST_TABLE, attribute)
    db_attribute = read_table_row_by_id(ATTRIBUTE_LIST_TABLE, created_id)

    return translate_to_api_fields(ATTRIBUTE_LIST_TABLE, db_attribute)


def list_attribute_list_items() -> list[dict[str, Any]]:
    rows = read_table_rows(ATTRIBUTE_LIST_TABLE)
    return [
        translate_to_api_fields(ATTRIBUTE_LIST_TABLE, row)
        for row in rows
    ]


def delete_attribute_list_item(attribute_id: int) -> None:
    delete_row(ATTRIBUTE_LIST_TABLE, attribute_id)


def read_tender_applicants(tender_id: int) -> list[dict[str, Any]]:
    ensure_table_exists(APPLICANT_AUTHORITIES_TABLE)
    ensure_table_exists(ORGANIZATIONS_TABLE)

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT id, organizacia_id
            FROM {quote_sqlite_identifier(APPLICANT_AUTHORITIES_TABLE)}
            WHERE moj_tender_id = ?
            ORDER BY id
            """,
            (tender_id,),
        ).fetchall()

    return [
        {
            "Id": row["id"],
            "Organizacia": read_organization(row["organizacia_id"]),
            "DalsieAtributy": read_additional_attributes(uchadzac_id=row["id"]),
        }
        for row in rows
    ]


def create_additional_attribute(additional_attribute: dict[str, Any]) -> int:
    ensure_table_exists(ADDITIONAL_ATTRIBUTES_TABLE)
    return create_row(ADDITIONAL_ATTRIBUTES_TABLE, additional_attribute)


def read_additional_attributes(
    *,
    moj_tender_id: int | None = None,
    uchadzac_id: int | None = None,
) -> list[dict[str, Any]]:
    ensure_table_exists(ADDITIONAL_ATTRIBUTES_TABLE)

    if (moj_tender_id is None) == (uchadzac_id is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one additional attribute parent.",
        )

    parent_column = "moj_tender_id" if moj_tender_id is not None else "uchadzac_id"
    parent_id = moj_tender_id if moj_tender_id is not None else uchadzac_id

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM {quote_sqlite_identifier(ADDITIONAL_ATTRIBUTES_TABLE)}
            WHERE {quote_sqlite_identifier(parent_column)} = ?
            ORDER BY id
            """,
            (parent_id,),
        ).fetchall()

    return [
        translate_to_api_fields(ADDITIONAL_ATTRIBUTES_TABLE, dict(row))
        for row in rows
    ]


def replace_additional_attributes(
    additional_attributes: list[dict[str, Any]],
    *,
    moj_tender_id: int | None = None,
    uchadzac_id: int | None = None,
) -> None:
    ensure_table_exists(ADDITIONAL_ATTRIBUTES_TABLE)

    if (moj_tender_id is None) == (uchadzac_id is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one additional attribute parent.",
        )

    parent_column = "moj_tender_id" if moj_tender_id is not None else "uchadzac_id"
    parent_key = "MojTenderId" if moj_tender_id is not None else "UchadzacId"
    parent_id = moj_tender_id if moj_tender_id is not None else uchadzac_id

    try:
        with database_connection() as connection:
            connection.execute(
                f"""
                DELETE FROM {quote_sqlite_identifier(ADDITIONAL_ATTRIBUTES_TABLE)}
                WHERE {quote_sqlite_identifier(parent_column)} = ?
                """,
                (parent_id,),
            )
            for additional_attribute in additional_attributes:
                values = translate_to_db_columns(
                    ADDITIONAL_ATTRIBUTES_TABLE,
                    {**additional_attribute, parent_key: parent_id},
                )
                connection.execute(
                    f"""
                    INSERT INTO {quote_sqlite_identifier(ADDITIONAL_ATTRIBUTES_TABLE)}
                        ({", ".join(quote_sqlite_identifier(column) for column in values)})
                    VALUES ({", ".join("?" for _ in values)})
                    """,
                    tuple(values.values()),
                )
            connection.commit()
    except sqlite3.IntegrityError as exc:
        raise constraint_error_response(ADDITIONAL_ATTRIBUTES_TABLE, exc) from exc


def create_my_tender(my_tender: dict[str, Any]) -> dict[str, Any]:
    ensure_table_exists(MY_TENDERS_TABLE)
    created_id = create_row(MY_TENDERS_TABLE, my_tender)
    db_my_tender = read_table_row_by_id(MY_TENDERS_TABLE, created_id)

    return translate_to_api_fields(MY_TENDERS_TABLE, db_my_tender)


def update_my_tender(tender_id: int, my_tender: dict[str, Any]) -> dict[str, Any]:
    update_row(MY_TENDERS_TABLE, tender_id, my_tender)
    db_my_tender = read_table_row_by_id(MY_TENDERS_TABLE, tender_id)

    return translate_to_api_fields(MY_TENDERS_TABLE, db_my_tender)


def read_my_tender(tender_id: int) -> dict[str, Any]:
    ensure_table_exists(MY_TENDERS_TABLE)
    db_my_tender = read_table_row_by_id(MY_TENDERS_TABLE, tender_id)
    my_tender = translate_to_api_fields(MY_TENDERS_TABLE, db_my_tender)
    my_tender["Obstaravatel"] = read_organization(my_tender["ObstaravatelId"])
    my_tender["Uchadzaci"] = read_tender_applicants(tender_id)
    my_tender["DalsieAtributy"] = read_additional_attributes(moj_tender_id=tender_id)

    return my_tender

def create_tender_applicant(tender_id: int, organization_id: int) -> int:
    ensure_table_exists(APPLICANT_AUTHORITIES_TABLE)
    return create_row(
        APPLICANT_AUTHORITIES_TABLE,
        {"MojTenderId": tender_id, "OrganizaciaId": organization_id},
    )


def replace_tender_applicants(tender_id: int, applicants: list[dict[str, Any]]) -> None:
    read_table_row_by_id(MY_TENDERS_TABLE, tender_id)
    ensure_table_exists(APPLICANT_AUTHORITIES_TABLE)
    ensure_table_exists(ADDITIONAL_ATTRIBUTES_TABLE)

    try:
        with database_connection() as connection:
            connection.execute(
                f"""
                DELETE FROM {quote_sqlite_identifier(ADDITIONAL_ATTRIBUTES_TABLE)}
                WHERE uchadzac_id IN (
                    SELECT id
                    FROM {quote_sqlite_identifier(APPLICANT_AUTHORITIES_TABLE)}
                    WHERE moj_tender_id = ?
                )
                """,
                (tender_id,),
            )
            connection.execute(
                f"""
                DELETE FROM {quote_sqlite_identifier(APPLICANT_AUTHORITIES_TABLE)}
                WHERE moj_tender_id = ?
                """,
                (tender_id,),
            )
            for applicant in applicants:
                organization_id = applicant["Organizacia"]["Id"]
                cursor = connection.execute(
                    f"""
                    INSERT INTO {quote_sqlite_identifier(APPLICANT_AUTHORITIES_TABLE)}
                        (moj_tender_id, organizacia_id)
                    VALUES (?, ?)
                    """,
                    (tender_id, organization_id),
                )
                applicant_id = cursor.lastrowid
                for additional_attribute in applicant.get("DalsieAtributy", []):
                    values = translate_to_db_columns(
                        ADDITIONAL_ATTRIBUTES_TABLE,
                        {**additional_attribute, "UchadzacId": applicant_id},
                    )
                    connection.execute(
                        f"""
                        INSERT INTO {quote_sqlite_identifier(ADDITIONAL_ATTRIBUTES_TABLE)}
                            ({", ".join(quote_sqlite_identifier(column) for column in values)})
                        VALUES ({", ".join("?" for _ in values)})
                        """,
                        tuple(values.values()),
                    )
            connection.commit()
    except sqlite3.IntegrityError as exc:
        raise constraint_error_response(APPLICANT_AUTHORITIES_TABLE, exc) from exc


def create_credential(username: str, password: str) -> dict[str, Any]:
    ensure_table_exists("credentials")
    password_hash = hash_password(password)

    created_id = create_row(
        "credentials",
        {"username": username, "password_hash": password_hash},
    )

    return {"id": created_id, "username": username}


def list_credentials() -> dict[str, str]:
    ensure_table_exists("credentials")

    with database_connection() as connection:
        rows = connection.execute(
            "SELECT username, password_hash FROM credentials"
        ).fetchall()

    return {row["username"]: row["password_hash"] for row in rows}

