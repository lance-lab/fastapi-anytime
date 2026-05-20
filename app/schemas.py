from typing import Optional

from pydantic import BaseModel, Field


class OrganizationResponse(BaseModel):
    Id: int
    Ico: int
    Meno: str
    Dic: str | None = None
    PlnaAdresa: str | None = None
    Mesto: str | None = None
    Ulica: str | None = None
    CisloDomu: str | None = None
    Stat: str | None = None
    Psc: str | None = None
    StatutarnyOrgan: str | None = None
    StatutarnyOrganFunkcia: str | None = None
    Vytvorene: str
    Updatovane: str


class OrganizationCreate(BaseModel):
    Ico: int
    Meno: str = Field(min_length=1)
    Dic: Optional[str] = Field(default=None, max_length=20)
    PlnaAdresa: Optional[str] = None
    Mesto: Optional[str] = None
    Ulica: Optional[str] = None
    CisloDomu: Optional[str] = None
    Stat: Optional[str] = None
    Psc: Optional[str] = Field(default=None, max_length=20)
    StatutarnyOrgan: Optional[str] = None
    StatutarnyOrganFunkcia: Optional[str] = None


class TenderApplicant(BaseModel):
    Id: int
    Organizacia: OrganizationResponse


class MyTendersResponse(BaseModel):
    Id: int
    CisloOpatrenia: str
    CisloPodopatrenia: str
    CisloVyzvy: str
    DruhZakazky: str
    NazovZakazky: str | None = None
    NazovProjektu: str | None = None
    KodProjektu: str | None = None
    PredmetZakazky: str | None = None
    RozdelenieZakazky: str | None = None
    Obstaravatel: int
    LehotaNaPredkladaniePonuk: str | None = None
    DatumOtvoreniaAVyhodnoteniaPonuk: str | None = None
    DatumPodpisuVyzvy: str | None = None
    DatumPodpisuZaznam: str | None = None
    DatumPodpisuSplnomocnenia: str | None = None
    Vytvorene: str
    Updatovane: str


class MyTenderDetailsResponse(BaseModel):
    Id: int
    CisloOpatrenia: str
    CisloPodopatrenia: str
    CisloVyzvy: str
    DruhZakazky: str
    NazovZakazky: str | None = None
    NazovProjektu: str | None = None
    KodProjektu: str | None = None
    PredmetZakazky: str | None = None
    RozdelenieZakazky: str | None = None
    Obstaravatel: OrganizationResponse
    Uchadzaci: list[TenderApplicant]
    LehotaNaPredkladaniePonuk: str | None = None
    DatumOtvoreniaAVyhodnoteniaPonuk: str | None = None
    DatumPodpisuVyzvy: str | None = None
    DatumPodpisuZaznam: str | None = None
    DatumPodpisuSplnomocnenia: str | None = None
    Vytvorene: str
    Updatovane: str


class TenderApplicantOrganizationCreate(BaseModel):
    Id: int


class TenderApplicantCreate(BaseModel):
    Organizacia: TenderApplicantOrganizationCreate


class MyTenderCreate(BaseModel):
    CisloOpatrenia: str = Field(min_length=1)
    CisloPodopatrenia: str = Field(min_length=1)
    CisloVyzvy: str = Field(min_length=1)
    DruhZakazky: str = Field(min_length=1)
    NazovZakazky: Optional[str] = None
    NazovProjektu: Optional[str] = None
    KodProjektu: Optional[str] = None
    PredmetZakazky: Optional[str] = None
    RozdelenieZakazky: Optional[str] = None
    Obstaravatel: int
    LehotaNaPredkladaniePonuk: Optional[str] = None
    DatumOtvoreniaAVyhodnoteniaPonuk: Optional[str] = None
    DatumPodpisuVyzvy: Optional[str] = None
    DatumPodpisuZaznam: Optional[str] = None
    DatumPodpisuSplnomocnenia: Optional[str] = None
    Uchadzaci: list[TenderApplicantCreate] = Field(default_factory=list)


class MyTenderUpdate(BaseModel):
    CisloOpatrenia: Optional[str] = Field(default=None, min_length=1)
    CisloPodopatrenia: Optional[str] = Field(default=None, min_length=1)
    CisloVyzvy: Optional[str] = Field(default=None, min_length=1)
    DruhZakazky: Optional[str] = Field(default=None, min_length=1)
    NazovZakazky: Optional[str] = None
    NazovProjektu: Optional[str] = None
    KodProjektu: Optional[str] = None
    PredmetZakazky: Optional[str] = None
    RozdelenieZakazky: Optional[str] = None
    Obstaravatel: Optional[int] = None
    LehotaNaPredkladaniePonuk: Optional[str] = None
    DatumOtvoreniaAVyhodnoteniaPonuk: Optional[str] = None
    DatumPodpisuVyzvy: Optional[str] = None
    DatumPodpisuZaznam: Optional[str] = None
    DatumPodpisuSplnomocnenia: Optional[str] = None
    Uchadzaci: Optional[list[TenderApplicantCreate]] = None


class CredentialCreate(BaseModel):
    Username: str = Field(min_length=1, max_length=255)
    Password: str = Field(min_length=8)
