# app/api/endpoints/compare.py
from fastapi import APIRouter, Query, HTTPException, Request, Body
from typing import Optional, List
import json
import xml.etree.ElementTree as ET
from app.services.http_client import fetch_data
from app.data.db import DBHandler
from app.data.cache import get_cached_db_handler
from app.core.compare import compare_responses
from app.models import ComparisonRequest, ComparisonResult, ComparisonHistoryItem
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

"""
POST /compare — accepts URLs + optional bodies → fetches → compares → stores.
GET /latest — fetch latest comparison from DB.
GET /history — fetches last n comparisons.

models(Pydantic) are used to define the schema of request bodies.
Define a model by subclassing BaseModel from Pydantic.
FastAPI automatically:			
    Parses the incoming JSON request body.
    Validates the data according to the model.
    Converts types as per type hints.
    If validation fails, FastAPI returns a 422 error with details.
"""


def is_valid_xml(xml_string):
    try:
        ET.fromstring(xml_string)
        return True
    except ET.ParseError:
        return False


def parse_body_content(body: Optional[str]):
    if not body or not body.strip():
        return None, None

    try:
        return json.loads(body), 'application/json'
    except json.JSONDecodeError:
        if is_valid_xml(body):
            return body, 'application/xml'
        return body, 'text/plain'


@router.post("/compare", response_model=ComparisonResult)
async def compare_endpoint(
        # request: Request,
        url1: str = Query(...),
        url2: str = Query(...),
        method: str = Query("get"),
        url1_params: Optional[str] = Query(None),
        url2_params: Optional[str] = Query(None),
        body1: Optional[str] = Query(None),
        body2: Optional[str] = Query(None)
):
    try:
        params1 = json.loads(url1_params) if url1_params else {}
        params2 = json.loads(url2_params) if url2_params else {}

        body1_content, body1_type = parse_body_content(body1)
        body2_content, body2_type = parse_body_content(body2)

        def prepare_request_data(content, content_type):
            return {
                'json': content if content_type == 'application/json' else None,
                'data': content if content_type in ('application/xml', 'text/plain') else None
            }

        data1 = prepare_request_data(body1_content, body1_type)
        data2 = prepare_request_data(body2_content, body2_type)

        res1 = await fetch_data(method, url1, params=params1, **data1)
        res2 = await fetch_data(method, url2, params=params2, **data2)

        resp1_text = res1.text
        resp2_text = res2.text

        if not resp1_text or not resp2_text:
            raise HTTPException(
                status_code=502,
                detail="One or both URLs returned empty response"
            )

        diff, metrics = compare_responses(resp1_text, resp2_text)

        db = get_cached_db_handler()
        db.insert_comparison(
            resp1_text,
            resp2_text,
            diff,
            json.dumps(metrics),
            content_type1=res1.headers.get('Content-Type'),
            content_type2=res2.headers.get('Content-Type')
        )

        return ComparisonResult(
            status="success",
            diff_summary=diff[:500],
            metrics=metrics,
            tibco_response=resp1_text,
            python_response=resp2_text,
            content_type1=res1.headers.get('Content-Type'),
            content_type2=res2.headers.get('Content-Type')
        )

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in parameters")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Comparison failed")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/compare/body", response_model=ComparisonResult)
async def compare_body_endpoint(
        request: Request,
        body1: str = Body(...),
        body2: str = Body(...)
):
    try:
        # Trying to determine the content types.
        body1_content, body1_type = parse_body_content(body1)
        body2_content, body2_type = parse_body_content(body2)

        # converting the bodies to strings for comparison
        resp1_text = body1
        resp2_text = body2

        if not resp1_text or not resp2_text:
            raise HTTPException(
                status_code=400,
                detail="One or both bodies are empty"
            )

        diff, metrics = compare_responses(resp1_text, resp2_text)

        db = get_cached_db_handler()
        db.insert_comparison(resp1_text, resp2_text, diff, json.dumps(metrics), content_type1=body1_type, content_type2=body2_type)

        return ComparisonResult(
            status="success",
            diff_summary=diff[:500],
            metrics=metrics,
            tibco_response=resp1_text,
            python_response=resp2_text,
            content_type1=body1_type,
            content_type2=body2_type
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Body comparison failed")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/history", response_model=List[ComparisonHistoryItem])
def get_history(limit: int = Query(10, ge=1, le=100)):
    try:
        db_handler = DBHandler()
        results = db_handler.fetch_all_differences(limit=limit)
        if not results:
            return []  # Returns an empty list instead of error if no results

        # Map ORM objects to Pydantic models explicitly
        response = []
        for r in results:
            metrics = r.metrics
            if isinstance(metrics, str):
                try:
                    metrics = json.loads(metrics)
                except json.JSONDecodeError:
                    metrics = {"raw_metrics": metrics}

            response.append(
                ComparisonHistoryItem(
                    id=r.id,
                    created_at=r.created_at,
                    metrics=r.metrics,
                    differences=r.differences[:500] if r.differences else "",
                    tibco_response=r.tibco_response,
                    python_response=r.python_response,
                    content_type1=r.content_type1,
                    content_type2=r.content_type2
                )
            )
        return response
    except Exception as e:
        logger.exception("Failed to fetch comparison history")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch history: {str(e)}"
        )


@router.get("/latest", response_model=ComparisonHistoryItem)
def get_latest():
    try:
        db_handler = DBHandler()
        latest = db_handler.fetch_latest_comparison()

        if not latest:
            raise HTTPException(
                status_code=404,
                detail="No comparisons available in database"
            )

        # ensuring that the metrics is properly formatted.
        metrics = latest.metrics
        if isinstance(metrics, str):
            try:
                metrics = json.loads(metrics)
            except json.JSONDecodeError:
                metrics = {"raw_metrics": metrics}

        return ComparisonHistoryItem(
            id=latest.id,
            created_at=latest.created_at,
            metrics=metrics,
            differences=latest.differences[:500] if latest.differences else "",
            tibco_response=latest.tibco_response,
            python_response=latest.python_response,
            content_type1=latest.content_type1,
            content_type2=latest.content_type2
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch latest comparison")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch latest comparison: {str(e)}"
        )
