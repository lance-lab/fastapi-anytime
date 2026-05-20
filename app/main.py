from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Query

from app.auth import load_credentials_cache, require_basic_auth
from app.config import RUN_DATABASE_INIT
from app.database import (
    create_credential,
    read_table_rows,
)
from app.database_init import (
    ensure_applicant_authorities_table,
    ensure_credentials_table,
    ensure_database_file,
    ensure_my_tenders_table,
    ensure_organizations_table,
)
from app.routers import my_tenders, organizations
from app.schemas import CredentialCreate


TABLE_NAME_TRANSLATIONS = {
    "organizations": "organizacie",
    "organizacie": "organizacie",
    "my-tenders": "moje_tendre",
    "moje-tendre": "moje_tendre",
    "moje_tendre": "moje_tendre",
    "applicant-authorities": "uchadzaci",
    "uchadzaci": "uchadzaci",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if RUN_DATABASE_INIT:
        ensure_database_file()
        ensure_organizations_table()
        ensure_my_tenders_table()
        ensure_applicant_authorities_table()
        ensure_credentials_table()
    load_credentials_cache()
    yield


app = FastAPI(
    title="SQLite Database API",
    lifespan=lifespan,
    dependencies=[Depends(require_basic_auth)],
)
app.include_router(organizations.router)
app.include_router(my_tenders.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/credentials", status_code=201)
def add_credential(credential: CredentialCreate) -> dict[str, object]:
    created_credential = create_credential(
        username=credential.Username,
        password=credential.Password,
    )
    load_credentials_cache()
    return created_credential
