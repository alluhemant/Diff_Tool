# app/api/service/http_client.py
import httpx
from typing import Optional


"""
fetch_data() — async GET/POST call with support for params, body (JSON/XML), headers.
"""


async def fetch_data(
        method: str,
        url: str,
        params: dict = None,
        json: Optional[dict] = None,
        data: Optional[str] = None,
        headers: Optional[dict] = None
) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method.lower() == "get":
                response = await client.get(url, params=params, headers=headers)
            elif method.lower() == "post":
                response = await client.post(url, params=params, json=json, data=data, headers=headers)
            else:
                raise ValueError("Unsupported HTTP method")
        response.raise_for_status()
        return response
    except httpx.HTTPError as e:
        raise RuntimeError(f"HTTP request failed: {e}")
