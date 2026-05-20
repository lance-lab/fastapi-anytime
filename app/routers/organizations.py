from fastapi import APIRouter

from app.database import (
    ORGANIZATIONS_TABLE,
    create_organization,
    read_organization,
    read_table_rows,
    translate_to_api_fields,
)
from app.schemas import OrganizationCreate, OrganizationResponse


router = APIRouter(prefix="/api/organizacie", tags=["organizacie"])


@router.post("", status_code=201)
def add_organization(organization: OrganizationCreate) -> OrganizationResponse:
    created_organization = create_organization(organization.model_dump())
    return OrganizationResponse.model_validate(created_organization)


@router.get("")
def list_organizations() -> dict[str, list[dict[str, object]]]:
    rows = read_table_rows(ORGANIZATIONS_TABLE)
    organizations = [
        OrganizationResponse.model_validate(
            translate_to_api_fields(ORGANIZATIONS_TABLE, row)
        ).model_dump()
        for row in rows
    ]
    return {"organizacie": organizations}

@router.get("/{organization_id}")
def get_organization(organization_id: int) -> OrganizationResponse:
    organization = read_organization(organization_id)
    return OrganizationResponse.model_validate(organization)
