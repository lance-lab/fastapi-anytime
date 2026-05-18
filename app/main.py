from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel, Field

from app.auth import load_credentials_cache, require_basic_auth
from app.config import RUN_DATABASE_INIT
from app.database import (
    create_credential,
    create_my_tender,
    create_organization,
    list_user_tables,
    read_my_tender,
    read_table_rows,
)
from app.database_init import (
    ensure_applicant_authorities_table,
    ensure_credentials_table,
    ensure_database_file,
    ensure_my_tenders_table,
    ensure_organizations_table,
)


TABLE_NAME_TRANSLATIONS = {
    "organizations": "organizations",
    "my-tenders": "my_tenders",
}


class OrganizationCreate(BaseModel):
    identification_number: int
    name: str = Field(min_length=1)
    tax_identification_number: Optional[str] = Field(default=None, max_length=20)
    full_address: Optional[str] = None
    city: Optional[str] = None
    street: Optional[str] = None
    street_number: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = Field(default=None, max_length=20)


class MyTenderCreate(BaseModel):
    item_number: str = Field(min_length=1)
    item_nested_number: str = Field(min_length=1)
    tender_number: str = Field(min_length=1)
    tender_type: str = Field(min_length=1)
    contracting_authority_id: int


class CredentialCreate(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tables")
def tables() -> dict[str, list[str]]:
    return {"tables": list_user_tables()}


@app.post("/organizations", status_code=201)
def add_organization(organization: OrganizationCreate) -> dict[str, object]:
    return create_organization(organization.model_dump())


@app.post("/my-tenders", status_code=201)
def add_my_tender(my_tender: MyTenderCreate) -> dict[str, object]:
    return create_my_tender(my_tender.model_dump())


@app.get("/my-tenders/{tender_id}")
def get_my_tender(tender_id: int) -> dict[str, object]:
    return read_my_tender(tender_id)


@app.post("/credentials", status_code=201)
def add_credential(credential: CredentialCreate) -> dict[str, object]:
    created_credential = create_credential(
        username=credential.username,
        password=credential.password,
    )
    load_credentials_cache()
    return created_credential


@app.get("/tables/{table_name}/rows")
def table_rows(
    table_name: str,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> dict[str, object]:
    resolved_table_name = TABLE_NAME_TRANSLATIONS.get(table_name, table_name)
    rows = read_table_rows(resolved_table_name, limit)
    return {
        "table": resolved_table_name,
        "requested_table": table_name,
        "count": len(rows),
        "rows": rows,
    }
