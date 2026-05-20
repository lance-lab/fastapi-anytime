from fastapi import APIRouter

from app.database import (
    MY_TENDERS_TABLE,
    create_my_tender,
    create_tender_applicant,
    read_my_tender,
    read_table_rows,
    replace_tender_applicants,
    translate_to_api_fields,
    update_my_tender,
)

from app.schemas import (
    MyTenderCreate,
    MyTenderDetailsResponse,
    MyTendersResponse,
    MyTenderUpdate,
)


router = APIRouter(prefix="/api/moje-tendre", tags=["moje-tendre"])


@router.post("", status_code=201)
def add_my_tender(my_tender: MyTenderCreate) -> MyTenderDetailsResponse:
    tender_data = my_tender.model_dump(exclude={"Uchadzaci"})
    created_my_tender = create_my_tender(tender_data)
    tender_id = created_my_tender["Id"]

    for applicant in my_tender.Uchadzaci:
        organization_id = applicant["Organizacia"]["Id"]
        create_tender_applicant(tender_id, organization_id)

    created_my_tender_details = read_my_tender(tender_id)
    return MyTenderDetailsResponse.model_validate(created_my_tender_details)


@router.patch("/{tender_id}")
def patch_my_tender(tender_id: int, my_tender: MyTenderUpdate) -> MyTenderDetailsResponse:
    update_data = my_tender.model_dump(exclude_unset=True)
    applicants = update_data.pop("Uchadzaci", None)

    update_my_tender(tender_id, update_data)
    if applicants is not None:
        organization_ids = [
            applicant["Organizacia"]["Id"]
            for applicant in applicants
        ]
        replace_tender_applicants(tender_id, organization_ids)

    updated_my_tender = read_my_tender(tender_id)
    return MyTenderDetailsResponse.model_validate(updated_my_tender)


@router.get("")
def list_my_tenders() -> dict[str, list[dict[str, object]]]:
    rows = read_table_rows(MY_TENDERS_TABLE)
    my_tenders = [
        MyTendersResponse.model_validate(
            translate_to_api_fields(MY_TENDERS_TABLE, row)
        ).model_dump()
        for row in rows
    ]
    return {"moje-tendre": my_tenders}


@router.get("/{tender_id}")
def get_my_tender(tender_id: int) -> MyTenderDetailsResponse:
    my_tender = read_my_tender(tender_id)
    return MyTenderDetailsResponse.model_validate(my_tender)
