from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class AuthType(str, Enum):
    NO_AUTH = "no_auth"
    BASIC = "basic"
    BEARER = "bearer"


class BasicAuthConfig(BaseModel):
    username: str = ""
    password: str = ""


class BearerConfig(BaseModel):
    token: str = ""


class AuthConfig(BaseModel):
    auth_type: AuthType = AuthType.NO_AUTH
    basic: Optional[BasicAuthConfig] = None
    bearer: Optional[BearerConfig] = None


class HTTPMethod(str, Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class ApiCompareRequest(BaseModel):
    method: str = "get"
    source_url: HttpUrl
    target_url: HttpUrl
    source_params: Optional[Dict[str, Any]] = None
    target_params: Optional[Dict[str, Any]] = None
    source_body: Optional[str] = None
    target_body: Optional[str] = None
    source_auth: Optional[AuthConfig] = None
    target_auth: Optional[AuthConfig] = None


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
    status: str = Field(..., description="Comparison status")
    diff_summary: str = Field(..., description="Summary of differences")
    metrics: Dict[str, Any] = Field(..., description="Performance metrics")
    # UPDATED these two lines
    source_response: str = Field(..., description="Raw response from the source endpoint")
    target_response: str = Field(..., description="Raw response from the target endpoint")
    content_type1: Optional[str] = Field(None, description="Content-Type header from Source")
    content_type2: Optional[str] = Field(None, description="Content-Type header from Target")


class ComparisonHistoryItem(BaseModel):
    id: int
    created_at: datetime
    metrics: Union[Dict[str, Any], str]
    differences: str
    # UPDATED these field names to match the database columns
    tibco_response: Optional[str]
    python_response: Optional[str]
    content_type1: Optional[str]
    content_type2: Optional[str]

    class Config:
        from_attributes = True  # Changed from orm_mode=True for Pydantic v2
