import os
import logging
import httpx
from dotenv import load_dotenv
from fastmcp.exceptions import ToolError

load_dotenv()

logger = logging.getLogger(__name__)
BASE_URL = "https://api.safetyculture.io"
TIMEOUT = httpx.Timeout(30.0)


def get_headers() -> dict:
    token = os.environ.get("SAFETYCULTURE_API_TOKEN")
    if not token:
        raise ToolError("SAFETYCULTURE_API_TOKEN is not set. Configure it in Horizon secrets or your .env file.")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code == 401:
        raise ToolError("Invalid or expired SAFETYCULTURE_API_TOKEN. Check your .env file.")
    if resp.status_code == 404:
        raise ToolError(f"Resource not found: {resp.url}")
    if resp.status_code == 429:
        raise ToolError("SafetyCulture rate limit exceeded. Retry after the reset window.")
    if resp.status_code >= 500:
        raise ToolError(f"SafetyCulture server error ({resp.status_code}). Try again later.")
    resp.raise_for_status()


def handle_request_error(e: Exception, context: str) -> None:
    if isinstance(e, httpx.TimeoutException):
        logger.warning("SafetyCulture API timeout: %s", context)
        raise ToolError(f"Request timed out calling SafetyCulture ({context}). Try again.")
    if isinstance(e, httpx.RequestError):
        logger.error("SafetyCulture API network error: %s — %s", context, e)
        raise ToolError(f"Network error calling SafetyCulture ({context}): {e}")
    raise e
