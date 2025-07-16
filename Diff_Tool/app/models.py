from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class HTTPMethod(str, Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class ComparisonRequest(BaseModel):
    # This model is created for:- Request model for API comparison.
    url1: HttpUrl = Field(...,
                          example="http://example.com/api1",
                          description="First URL to compare")
    url2: HttpUrl = Field(...,
                          example="http://example.com/api2",
                          description="Second URL to compare")
    method: HTTPMethod = Field(HTTPMethod.GET,
                               example="get",
                               description="HTTP method to use for the request")
    url1_params: Optional[Dict[str, Any]] = Field(None,
                                                  example={"param1": "value1"},
                                                  description="Query parameters for URL1")
    url2_params: Optional[Dict[str, Any]] = Field(None,
                                                  example={"param2": "value2"},
                                                  description="Query parameters for URL2")
    body1: Optional[str] = Field(None,
                                 example='{"key": "value"}',
                                 description="Request body for URL1 (if method supports it)")
    body2: Optional[str] = Field(None,
                                 example='{"key": "value"}',
                                 description="Request body for URL2 (if method supports it)")


class ComparisonResult(BaseModel):
    # creating this model for comparison results.
    status: str = Field(...,
                        example="success",
                        description="Comparison status (success/failed)")
    diff_summary: str = Field(...,
                              example="3 differences found",
                              description="Summary of differences")
    metrics: Dict[str, Any] = Field(...,
                                    example={"response_time_diff": 0.15},
                                    description="Performance metrics")
    tibco_response: str = Field(...,
                                example='{"result": "data"}',
                                description="Raw response from TIBCO endpoint")
    python_response: str = Field(...,
                                 example='{"result": "data"}',
                                 description="Raw response from Python endpoint")
    content_type1: Optional[str] = Field(None,
                                         example="application/json",
                                         description="Content-Type header from URL1")
    content_type2: Optional[str] = Field(None,
                                         example="application/json",
                                         description="Content-Type header from URL2")


class ComparisonHistoryItem(BaseModel):
    # Model for historical comparison records.

    id: int
    created_at: datetime
    metrics: Union[Dict[str, Any], str]  # Accepts both types dict and string.
    differences: str
    tibco_response: Optional[str]
    python_response: Optional[str]
    content_type1: Optional[str]
    content_type2: Optional[str]

    class Config:
        json_encoders = {
            # Handle datetime serialization
            datetime: lambda v: v.isoformat() if v else None,
            # Handle metrics whether they're dict or string
            dict: lambda v: v,
            str: lambda v: v
        }
        from_attributes = True
