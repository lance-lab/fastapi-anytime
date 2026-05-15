from pathlib import Path

from fastapi import HTTPException, status

from app.config import CREATE_ACCESS_DB_IF_MISSING
from app.database import (
    access_connection,
    quote_access_identifier,
    resolve_database_path,
    table_exists,
)


ORGANIZATIONS_TABLE = "organizacie"
DIC_COLUMN = "dic"


def ensure_access_database_file() -> None:
    database_path = resolve_database_path()
    if database_path.exists():
        return

    if not CREATE_ACCESS_DB_IF_MISSING:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Access database file was not found: {database_path}",
        )

    create_access_database(database_path)


def create_access_database(database_path: Path) -> None:
    if database_path.suffix.lower() != ".accdb":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Automatic Access database creation supports only .accdb files.",
        )

    try:
        import win32com.client

        database_path.parent.mkdir(parents=True, exist_ok=True)
        catalog = win32com.client.Dispatch("ADOX.Catalog")
        catalog.Create(
            f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={database_path};"
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Install pywin32 to create missing .accdb files automatically.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create Access database file: {exc}",
        ) from exc


def ensure_organizations_table() -> None:
    if table_exists(ORGANIZATIONS_TABLE):
        ensure_organizations_columns()
        return

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            CREATE TABLE {quote_access_identifier(ORGANIZATIONS_TABLE)} (
                [id] COUNTER PRIMARY KEY,
                [ico] INTEGER,
                [dic] INTEGER,
                [meno] LONGTEXT
            )
            """
        )
        connection.commit()


def ensure_organizations_columns() -> None:
    if organizations_column_exists(DIC_COLUMN):
        return

    with access_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            ALTER TABLE {quote_access_identifier(ORGANIZATIONS_TABLE)}
            ADD COLUMN {quote_access_identifier(DIC_COLUMN)} INTEGER
            """
        )
        connection.commit()


def organizations_column_exists(column_name: str) -> bool:
    with access_connection() as connection:
        cursor = connection.cursor()
        columns = cursor.columns(
            table=ORGANIZATIONS_TABLE,
            column=column_name,
        )
        return any(row.column_name.lower() == column_name.lower() for row in columns)
