"""Request/response models.

`AIExtraction` mirrors exactly what the AI part (../ai/azure_llm_agent.py) produces
and stores in Mongo under `extractedValues`:

    {
      "Customer Type": null,
      "Customer": "Air Logistics Partners FZE",
      "Operator": null,
      "Flight Type": "Cargo",
      "Purposes": "Hazardous materials transport mission",
      "Reg No": "TC-MAA",
      "ACFT Type": "A330-200F",
      "Bulk Reg No": "TC-MAB, TC-MAC",
      "Flight Schedule": { "fieldType": "table", "items": [ { Date, Flight, Departure, From, Arrival, To, Load } ] },
      "Flight Sectors":  { "fieldType": "table", "items": [ { "Sector", "Flight No.", "Country", "Permit Type" } ] }
    }
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Table(BaseModel):
    fieldType: str = "table"
    items: list[dict[str, Any]] = Field(default_factory=list)


class AIExtraction(BaseModel):
    # Part A (forms)
    customer_type: str | None = Field(default=None, alias="Customer Type")
    customer: str | None = Field(default=None, alias="Customer")
    operator: str | None = Field(default=None, alias="Operator")
    flight_type: str | None = Field(default=None, alias="Flight Type")
    purposes: str | None = Field(default=None, alias="Purposes")
    reg_no: str | None = Field(default=None, alias="Reg No")
    acft_type: str | None = Field(default=None, alias="ACFT Type")
    bulk_reg_no: str | None = Field(default=None, alias="Bulk Reg No")

    # Part B (tables)
    flight_schedule: Table | None = Field(default=None, alias="Flight Schedule")
    flight_sectors: Table | None = Field(default=None, alias="Flight Sectors")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ProcessRequest(BaseModel):
    """Body for POST /awery/process — triggered by the frontend click."""

    extracted: dict[str, Any] | None = Field(
        default=None, description="Raw AI extraction JSON (extractedValues)."
    )
    mongo_id: str | None = Field(
        default=None, description="_id of a tb_file_details doc to load `extractedValues` from."
    )
    create_customer: bool = Field(
        default=False, description="Call createCustomer before createFlight."
    )
    company_name: str | None = Field(
        default=None, description="Awery company the flight/customer belongs to (company__name)."
    )
    flight_no: str | None = Field(
        default=None, description="Override the flight_no instead of deriving it from the schedule."
    )
    unique: list[Any] | None = Field(
        default=None, description='Awery duplicate-check algorithm, e.g. [0] to skip, [1] default.'
    )
    dry_run: bool = Field(
        default=False, description="Build and return the Awery payload without sending it."
    )


class ProceedRequest(BaseModel):
    """Body for POST /files/{id}/proceed — same options as ProcessRequest minus the source."""

    create_customer: bool = False
    company_name: str | None = None
    flight_no: str | None = None
    unique: list[Any] | None = None
    dry_run: bool = False


class FileUpdate(BaseModel):
    """Body for PUT /files/{id} — the edited extraction form."""

    updatedExtractedValues: dict[str, Any]


class RpcRequest(BaseModel):
    """Body for POST /awery/rpc — thin passthrough limited to ALLOWED_METHODS."""

    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class CreateCustomerRequest(BaseModel):
    customer: dict[str, Any]
    contacts: list[dict[str, Any]] | None = None
    documents: list[dict[str, Any]] | None = None
