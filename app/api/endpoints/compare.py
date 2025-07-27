import json
import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool

from app.services.http_client import fetch_data
# UPDATED: Removed parse_body_content from this import
from app.core.compare import compare_responses
from app.data import db as db_ops
from app.data.db import get_db
from app.models import ApiCompareRequest, ComparisonResult, ComparisonHistoryItem

logger = logging.getLogger(__name__)
router = APIRouter()


def parse_body_content(body: Optional[str]):
    """Parses a raw string body to determine its content and type."""
    if not body or not body.strip():
        return None, None
    try:
        return json.loads(body), 'application/json'
    except json.JSONDecodeError:
        try:
            # A simple check for XML
            ET.fromstring(body)
            return body, 'application/xml'
        except ET.ParseError:
            return body, 'text/plain'


@router.post("/compare", response_model=ComparisonResult)
async def compare_endpoint(
        request: ApiCompareRequest,
        db: Session = Depends(get_db)
):
    try:
        # Prepare data for the Source API call
        body1_content, body1_type = parse_body_content(request.source_body)
        data1 = {
            'json': body1_content if body1_type == 'application/json' else None,
            'data': body1_content if body1_type in ('application/xml', 'text/plain') else None
        }

        # Prepare headers for Source API call if a raw string body (XML/text) is being sent via POST
        headers1 = {'Content-Type': body1_type} if request.method.lower() == "post" and body1_type in (
            'application/xml', 'text/plain') else None

        # Prepare data for the Target API call
        body2_content, body2_type = parse_body_content(request.target_body)
        data2 = {
            'json': body2_content if body2_type == 'application/json' else None,
            'data': body2_content if body2_type in ('application/xml', 'text/plain') else None
        }

        # Prepare headers for Target API call if a raw string body (XML/text) is being sent via POST
        headers2 = {'Content-Type': body2_type} if request.method.lower() == "post" and body2_type in (
            'application/xml', 'text/plain') else None

        # Fetch data concurrently using the data from the request model
        res1_task = fetch_data(
            request.method,
            str(request.source_url),
            params=request.source_params or {},
            headers=headers1,  # Pass the prepared headers
            # --- PASS SOURCE AUTH ---
            auth_config=request.source_auth.model_dump() if request.source_auth else None,
            **data1
        )
        res2_task = fetch_data(
            request.method,
            str(request.target_url),
            params=request.target_params or {},
            headers=headers2,  # Pass the prepared headers
            # --- PASS TARGET AUTH ---
            auth_config=request.target_auth.model_dump() if request.target_auth else None,
            **data2
        )
        res1, res2 = await asyncio.gather(res1_task, res2_task)

        resp1_text = res1.text
        resp2_text = res2.text

        if not resp1_text or not resp2_text:
            raise HTTPException(status_code=502, detail="One or both URLs returned empty response")

        diff, metrics = compare_responses(resp1_text, resp2_text)

        await run_in_threadpool(
            db_ops.insert_comparison,
            db=db,
            tibco=resp1_text,
            python=resp2_text,
            diff=diff,
            metrics=json.dumps(metrics),
            content_type1=res1.headers.get('Content-Type'),
            content_type2=res2.headers.get('Content-Type')
        )

        return ComparisonResult(
            status="success",
            diff_summary=diff[:500],
            metrics=metrics,
            source_response=resp1_text,
            target_response=resp2_text,
            content_type1=res1.headers.get('Content-Type'),
            content_type2=res2.headers.get('Content-Type')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Comparison failed")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/history", response_model=List[ComparisonHistoryItem])
def get_history(limit: int = 10, db: Session = Depends(get_db)):
    """
    Retrieves a list of the last N comparison records from the database.
    """
    history = db_ops.fetch_all_differences(db=db, limit=limit)
    if history is None:
        # If the database operation fails, return an empty list to match the response model
        return []
    return history


@router.get("/latest", response_model=ComparisonHistoryItem)
def get_latest(db: Session = Depends(get_db)):
    """
    Retrieves the single most recent comparison record from the database.
    """
    latest = db_ops.fetch_latest_comparison(db=db)
    if not latest:
        # If no records are found, return a 404 error
        raise HTTPException(status_code=404, detail="No comparisons found in history")
    return latest
