"""sme schemas"""

from pydantic import BaseModel
from app.db.models import Values
from typing import List


# pylint: disable = too-few-public-methods, unsupported-binary-operation


class SmeRequest(BaseModel):
    """
    Schema for sme
    """

    module_id: int
    heading: str
    question: str
    value: str
    selected_value: str | None = None

    class Config:
        orm_mode = True


class SmeResponse(BaseModel):
    """sme_Response _summary_

    :param _type_ BaseModel: _description_
    """

    success: bool


class ModuleResponse(BaseModel):
    """sme_Response _summary_

    :param _type_ BaseModel: _description_
    """

    success: bool
    id: int


class SmeValueResponse(BaseModel):
    sme_id: int
    value: int


class StartRequestData(BaseModel):
    question: str
    option_1: str
    option_2: str
    option_3: str
    selected_option: int | None = None


class StartupRequest(BaseModel):
    """
    Schema for sme
    """

    module_id: int
    data: list[StartRequestData]

    class Config:
        orm_mode = True


class StartupValueResponse(BaseModel):
    startup_id: int
    value: int


class StrategyValueResponse(BaseModel):
    strategy_id: int
    strategy: str


class SituationValueRequest(BaseModel):
    situation_id: int
    selected_value: int
    descriptions: str | None = None
