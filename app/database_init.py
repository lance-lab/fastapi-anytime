from app.database import database_connection, get_database_path


ORGANIZATIONS_TABLE = "organizacie"
MY_TENDERS_TABLE = "moje_tendre"
APPLICANT_AUTHORITIES_TABLE = "uchadzaci"
ATTRIBUTE_LIST_TABLE = "zoznam_atributov"
ADDITIONAL_ATTRIBUTES_TABLE = "dalsie_atributy"
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


def ensure_attribute_list_table() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS zoznam_atributov (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nazov TEXT NOT NULL UNIQUE,
                vytvorene TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatovane TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()


def ensure_additional_attributes_table() -> None:
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dalsie_atributy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nazov TEXT NOT NULL,
                hodnota TEXT,
                moj_tender_id INTEGER,
                uchadzac_id INTEGER,
                vytvorene TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatovane TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (
                    (moj_tender_id IS NOT NULL AND uchadzac_id IS NULL)
                    OR (moj_tender_id IS NULL AND uchadzac_id IS NOT NULL)
                ),
                FOREIGN KEY (moj_tender_id)
                    REFERENCES moje_tendre (id),
                FOREIGN KEY (uchadzac_id)
                    REFERENCES uchadzaci (id),
                FOREIGN KEY (nazov)
                    REFERENCES zoznam_atributov (nazov)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_dalsie_atributy_moj_tender
            ON dalsie_atributy (moj_tender_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_dalsie_atributy_uchadzac
            ON dalsie_atributy (uchadzac_id)
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
