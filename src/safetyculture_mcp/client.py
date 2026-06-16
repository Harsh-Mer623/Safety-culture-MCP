import os
import httpx
from dotenv import load_dotenv
from fastmcp.exceptions import ToolError

load_dotenv()

API_TOKEN = os.environ["SAFETYCULTURE_API_TOKEN"]
BASE_URL = "https://api.safetyculture.io"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}


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
