from fastapi import APIRouter, Response, status

from app.auth import credentials_cache, load_credentials_cache
from app.database import (
    create_attribute_list_item,
    create_credential,
    delete_attribute_list_item,
    list_attribute_list_items,
)
from app.schemas import (
    AttributeListCreate,
    AttributeListResponse,
    CredentialCreate,
)


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/status")
def admin_status() -> dict[str, bool]:
    credentials_configured = bool(credentials_cache)
    return {
        "initialUserRequired": not credentials_configured,
    }


@router.post("/credentials", status_code=201)
def add_credential(credential: CredentialCreate) -> dict[str, object]:
    created_credential = create_credential(
        username=credential.Username,
        password=credential.Password,
    )
    load_credentials_cache()
    return created_credential


@router.get("/zoznam-atributov")
def list_attributes() -> dict[str, list[dict[str, object]]]:
    attributes = [
        AttributeListResponse.model_validate(attribute).model_dump()
        for attribute in list_attribute_list_items()
    ]
    return {"zoznam-atributov": attributes}


@router.post("/zoznam-atributov", status_code=201)
def add_attribute(attribute: AttributeListCreate) -> AttributeListResponse:
    created_attribute = create_attribute_list_item(attribute.model_dump())
    return AttributeListResponse.model_validate(created_attribute)


@router.delete("/zoznam-atributov/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_attribute(attribute_id: int) -> Response:
    delete_attribute_list_item(attribute_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
