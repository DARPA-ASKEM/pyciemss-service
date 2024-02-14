from __future__ import annotations

from typing import ClassVar, Dict
from pydantic import BaseModel, Field


class Timespan(BaseModel):
    start: float = Field(..., example=0)
    end: float = Field(..., example=90)


class ModelConfig(BaseModel):
    id: str = Field(..., example="cd339570-047d-11ee-be55")
    solution_mappings: dict[str, str] = Field(
        ...,
        example={"Infected": "Cases", "Hospitalizations": "hospitalized_population"},
    )
    weight: float = Field(..., example="cd339570-047d-11ee-be55")


class Dataset(BaseModel):
    id: str = Field(None, example="cd339570-047d-11ee-be55")
    filename: str = Field(None, example="dataset.csv")
    mappings: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Mappings from the dataset column names to "
            "the model names they should be replaced with."
        ),
        example={"postive_tests": "infected"},
    )


class InterventionObject(BaseModel):
    timestep: float
    name: str
    value: float


class InterventionSelection(BaseModel):
    timestep: float
    name: str


class QuantityOfInterest(BaseModel):
    function: str
    state: str
    arg: int  # TODO: Make this a list of args?


class OperationRequest(BaseModel):
    pyciemss_lib_function: ClassVar[str] = ""
    engine: str = Field("ciemss", example="ciemss")
    user_id: str = Field("not_provided", example="not_provided")

    def gen_pyciemss_args(self, job_id):
        raise NotImplementedError("PyCIEMSS cannot handle this operation")

    def run_sciml_operation(self, job_id, julia_context):
        raise NotImplementedError("SciML cannot handle this operation")

    # @field_validator("engine")
    # def must_be_ciemss(cls, engine_choice):
    #     if engine_choice != "ciemss":
    #         raise ValueError("The chosen engine is NOT 'ciemss'")
    #     return engine_choice
