from app.database import database_connection, get_database_path


ORGANIZATIONS_TABLE = "organizacie"
MY_TENDERS_TABLE = "moje_tendre"
APPLICANT_AUTHORITIES_TABLE = "uchadzaci"
CREDENTIALS_TABLE = "credentials"


def ensure_database_file() -> None:
    get_database_path()


def ensure_organizations_table() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS organizacie (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ico INTEGER NOT NULL,
                meno TEXT NOT NULL,
                dic TEXT,
                plna_adresa TEXT,
                mesto TEXT,
                ulica TEXT,
                cislo_domu TEXT,
                stat TEXT,
                psc TEXT,
                statutarny_organ TEXT,
                statutarny_organ_funkcia TEXT,
                vytvorene TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatovane TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_organizations_ico
            ON organizacie (ico)
            """
        )
        connection.commit()


def ensure_my_tenders_table() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS moje_tendre (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cislo_opatrenia TEXT NOT NULL,
                cislo_podopatrenia TEXT NOT NULL,
                cislo_vyzvy TEXT NOT NULL,
                druh_zakazky TEXT NOT NULL,
                nazov_zakazky TEXT,
                nazov_projektu TEXT,
                kod_projektu TEXT,
                predmet_zakazky TEXT,
                rozdelenie_zakazky TEXT,
                obstaravatel INTEGER NOT NULL,
                lehota_na_predkladanie_ponuk DATETIME,
                datum_otvorenia_a_vyhodnotenia_ponuk DATETIME,
                datum_podpisu_vyzvy DATE,
                datum_podpisu_zaznam DATE,
                datum_podpisu_splnomocnenia DATE,
                vytvorene TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatovane TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (obstaravatel)
                    REFERENCES organizacie (id)
            )
            """
        )
        connection.commit()


def ensure_applicant_authorities_table() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS uchadzaci (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                moj_tender_id INTEGER NOT NULL,
                organizacia_id INTEGER NOT NULL,
                vytvorene TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatovane TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (moj_tender_id)
                    REFERENCES moje_tendre (id),
                FOREIGN KEY (organizacia_id)
                    REFERENCES organizacie (id)
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_applicant_authorities_tender_organization
            ON uchadzaci (moj_tender_id, organizacia_id)
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
                vytvorene TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatovane TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
