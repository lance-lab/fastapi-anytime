from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Query

from app.config import RUN_DATABASE_INIT
from app.database import list_user_tables, read_table_rows
from app.database_init import ensure_access_database_file, ensure_organizations_table


TABLE_NAME_TRANSLATIONS = {
    "organizations": "organizacie",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if RUN_DATABASE_INIT:
        ensure_access_database_file()
        ensure_organizations_table()
    yield


app = FastAPI(title="Access Database API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tables")
def tables() -> dict[str, list[str]]:
    return {"tables": list_user_tables()}


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
