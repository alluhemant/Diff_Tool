# app/api/endpoints/compare.py

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import json
from app.services.http_client import fetch_data
from app.data.db import DBHandler
from app.data.cache import get_cached_db_handler
from app.core.compare import compare_responses
from app.models import ComparisonRequest, ComparisonResult, ComparisonHistoryItem
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/compare", response_model=ComparisonResult)
async def compare_endpoint(
        url1: str = Query(...),
        url2: str = Query(...),
        method: str = Query("get"),
        url1_params: Optional[str] = Query(None),
        url2_params: Optional[str] = Query(None)
):
    try:
        params1 = json.loads(url1_params) if url1_params else {}
        params2 = json.loads(url2_params) if url2_params else {}

        res1 = await fetch_data(method, url1, params=params1)
        res2 = await fetch_data(method, url2, params=params2)

        resp1_text = res1.text
        resp2_text = res2.text

        diff, metrics = compare_responses(resp1_text, resp2_text)
        db = get_cached_db_handler()
        db.insert_comparison(resp1_text, resp2_text, diff, metrics)

        return {
            "status": "success",
            "diff_summary": diff[:500],
            "metrics": metrics,
            "tibco_response": resp1_text,
            "python_response": resp2_text,
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in URL parameters")
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=502, detail=f"HTTP error: {str(re)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/history", response_model=List[ComparisonHistoryItem])
def get_history(limit: int = Query(10, ge=1, le=100)):
    try:
        db_handler = DBHandler()
        results = db_handler.fetch_all_differences(limit=limit)
        if not results:
            raise HTTPException(status_code=404, detail="No comparison history found.")

        # Map ORM objects to Pydantic models explicitly
        response = []
        for r in results:
            response.append(
                ComparisonHistoryItem(
                    id=r.id,
                    created_at=r.created_at,
                    metrics=r.metrics,
                    differences=r.differences[:500],
                    tibco_response=r.tibco_response,
                    python_response=r.python_response
                )
            )
        return response
    except Exception as e:
        logger.exception("Failed to fetch comparison history")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


@router.get("/latest", response_model=ComparisonHistoryItem)
def get_latest():
    try:
        # db = get_cached_db_handler()
        records = DBHandler().fetch_all_differences(limit=1)
        if not records:
            raise HTTPException(status_code=404, detail="No latest comparison available.")
        latest = records[0]
        return ComparisonHistoryItem(
            id=latest.id,
            created_at=latest.created_at,
            metrics=latest.metrics,
            differences=latest.differences[:500],
            tibco_response=latest.tibco_response,
            python_response=latest.python_response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest comparison: {str(e)}")
