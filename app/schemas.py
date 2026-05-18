from typing import Optional

from pydantic import BaseModel, Field


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
