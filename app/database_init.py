from app.database import database_connection, get_database_path


ORGANIZATIONS_TABLE = "organizations"
MY_TENDERS_TABLE = "my_tenders"
APPLICANT_AUTHORITIES_TABLE = "applicant_authorities"
CREDENTIALS_TABLE = "credentials"


def ensure_database_file() -> None:
    get_database_path()


def ensure_organizations_table() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identification_number INTEGER NOT NULL,
                name TEXT NOT NULL,
                tax_identification_number TEXT,
                full_address TEXT,
                city TEXT,
                street TEXT,
                street_number TEXT,
                state TEXT,
                postal_code TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_organizations_identification_number
            ON organizations (identification_number)
            """
        )
        connection.commit()


def ensure_my_tenders_table() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS my_tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_number TEXT NOT NULL,
                item_nested_number TEXT NOT NULL,
                tender_number TEXT NOT NULL,
                tender_type TEXT NOT NULL,
                contracting_authority_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contracting_authority_id)
                    REFERENCES organizations (id)
            )
            """
        )
        connection.commit()


def ensure_applicant_authorities_table() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS applicant_authorities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                my_tender_id INTEGER NOT NULL,
                organization_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (my_tender_id)
                    REFERENCES my_tenders (id),
                FOREIGN KEY (organization_id)
                    REFERENCES organizations (id)
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_applicant_authorities_tender_organization
            ON applicant_authorities (my_tender_id, organization_id)
            """
        )
        connection.commit()


def ensure_credentials_table() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_credentials_username
            ON credentials (username)
            """
        )
        connection.commit()
