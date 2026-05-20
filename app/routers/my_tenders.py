from fastapi import APIRouter

from app.database import (
    MY_TENDERS_TABLE,
    create_additional_attribute,
    create_my_tender,
    create_tender_applicant,
    read_my_tender,
    read_table_rows,
    replace_additional_attributes,
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
    payload = my_tender.model_dump()
    tender_attributes = payload.pop("DalsieAtributy")
    applicants = payload.pop("Uchadzaci")

    tender_data = payload
    created_my_tender = create_my_tender(tender_data)
    tender_id = created_my_tender["Id"]

    for additional_attribute in tender_attributes:
        create_additional_attribute(
            {**additional_attribute, "MojTenderId": tender_id}
        )

    for applicant in applicants:
        organization_id = applicant["Organizacia"]["Id"]
        applicant_id = create_tender_applicant(tender_id, organization_id)
        for additional_attribute in applicant["DalsieAtributy"]:
            create_additional_attribute(
                {**additional_attribute, "UchadzacId": applicant_id}
            )

    created_my_tender_details = read_my_tender(tender_id)
    return MyTenderDetailsResponse.model_validate(created_my_tender_details)


@router.patch("/{tender_id}")
def patch_my_tender(tender_id: int, my_tender: MyTenderUpdate) -> MyTenderDetailsResponse:
    update_data = my_tender.model_dump(exclude_unset=True)
    applicants = update_data.pop("Uchadzaci", None)
    tender_attributes = update_data.pop("DalsieAtributy", None)

    update_my_tender(tender_id, update_data)
    if tender_attributes is not None:
        replace_additional_attributes(
            tender_attributes,
            moj_tender_id=tender_id,
        )
    if applicants is not None:
        replace_tender_applicants(tender_id, applicants)

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
