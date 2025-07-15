from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ComparisonRequest(BaseModel):
    url1: str = Field(..., example="http://example.com/api1")
    url2: str = Field(..., example="http://example.com/api2")
    method: str = Field("get", example="get")
    url1_params: Optional[str] = Field(None, example='{"param1": "value1"}')
    url2_params: Optional[str] = Field(None, example='{"param2": "value2"}')


class ComparisonResult(BaseModel):
    status: str
    diff_summary: str
    metrics: str
    tibco_response: str
    python_response: str


class ComparisonHistoryItem(BaseModel):
    id: int
    created_at: datetime
    metrics: str
    differences: str
    tibco_response: Optional[str]
    python_response: Optional[str]

    class Config:
        orm_mode = True  # allow ORM objects to be parsed correctly
