# app/services/http_client.py
import httpx
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


async def fetch_data(
        method: str,
        url: str,
        params: dict = None,
        json: Optional[dict] = None,
        data: Optional[str] = None,
        headers: Optional[dict] = None,  # These are the explicitly passed headers
        auth_config: Optional[Dict] = None,
) -> httpx.Response:
    try:
        # Define default headers, including a common User-Agent
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",  # Ensure this is broad enough to accept JSON/XML
            # Other headers like 'Accept-Encoding' are handled automatically by httpx
        }

        # Merge explicitly passed headers with default headers.
        # Explicit headers will override defaults if there's a conflict.
        if headers:
            combined_headers = {**default_headers, **headers}
        else:
            combined_headers = default_headers

        # ---THIS LOGIC BLOCK TO HANDLE AUTH ---
        auth = None
        if auth_config:
            auth_type = auth_config.get("auth_type")
            if auth_type == "basic" and auth_config.get("basic"):
                basic_conf = auth_config["basic"]
                auth = httpx.BasicAuth(basic_conf.get("username"), basic_conf.get("password"))
            elif auth_type == "bearer" and auth_config.get("bearer"):
                bearer_conf = auth_config["bearer"]
                token = bearer_conf.get("token")
                if token:
                    combined_headers["Authorization"] = f"Bearer {token}"
            # --- END OF AUTH LOGIC BLOCK ---

        async with httpx.AsyncClient(timeout=30.0, headers=combined_headers) as client:  # MODIFIED THIS LINE
            # Create a request object to inspect all headers (including defaults)
            if method.lower() == "get":
                request_obj = client.build_request(method, url, params=params)  # headers are now part of AsyncClient
            elif method.lower() == "post":
                request_obj = client.build_request(method, url, params=params, json=json,
                                                   data=data)  # headers are now part of AsyncClient
            else:
                raise ValueError("Unsupported HTTP method")

            # Log the full details of the request that will be sent
            logger.info(f"Preparing to send Request:")
            logger.info(f"  Method: {request_obj.method}")
            logger.info(f"  URL: {request_obj.url}")
            logger.info(f"  Headers: {dict(request_obj.headers)}")
            logger.info(
                f"  Body (first 200 chars): {request_obj.content.decode(errors='ignore')[:200] if request_obj.content else 'None'}")

            # Now actually sending the request
            response = await client.send(request_obj, auth=auth)

            logger.info(f"Received Response Status: {response.status_code} for URL: {url}")
            logger.debug(f"Received Response Headers: {response.headers}")
            logger.debug(f"Received Response Body Preview: {response.text[:200]}...")

        response.raise_for_status()
        return response
    except httpx.HTTPError as e:
        logger.error(f"HTTP request failed for {url}: {e}")
        raise RuntimeError(f"HTTP request failed: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in fetch_data for {url}: {e}")
        raise
