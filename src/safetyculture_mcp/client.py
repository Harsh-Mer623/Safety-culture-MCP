import asyncio
import atexit
import logging
import os
import time
import uuid

import httpx
from dotenv import load_dotenv
from fastmcp import Context
from fastmcp.exceptions import ToolError
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://api.safetyculture.io"

_TIMEOUT = httpx.Timeout(30.0)
_LIMITS = httpx.Limits(
    max_keepalive_connections=10,
    max_connections=20,
    keepalive_expiry=30,
)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3

# ── Shared connection pool ────────────────────────────────────────────────────

_http_client: httpx.AsyncClient | None = None


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=_TIMEOUT,
        limits=_LIMITS,
    )


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = _build_client()
    return _http_client


def _shutdown_client() -> None:
    global _http_client
    if _http_client and not _http_client.is_closed:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_http_client.aclose())
            else:
                loop.run_until_complete(_http_client.aclose())
        except Exception:
            pass


atexit.register(_shutdown_client)

# ── Auth ──────────────────────────────────────────────────────────────────────


def get_headers(ctx: Context | None = None) -> dict:
    token = None
    incoming_request_id = None
    if ctx is not None:
        try:
            hdrs = ctx.request_context.request.headers
            token = hdrs.get("x-safetyculture-token")
            incoming_request_id = hdrs.get("x-request-id")
        except (AttributeError, KeyError):
            pass
    if not token:
        token = os.environ.get("SAFETYCULTURE_API_TOKEN")
    if not token:
        raise ToolError(
            "SafetyCulture API token not provided. "
            "Pass it via the x-safetyculture-token header or set SAFETYCULTURE_API_TOKEN."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        # Propagate the caller's trace ID or generate one so every outbound
        # call is linkable end-to-end without the tool needing to think about it.
        "x-request-id": incoming_request_id or str(uuid.uuid4()),
    }


# ── Error mapping ─────────────────────────────────────────────────────────────


def raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code == 401:
        raise ToolError("Invalid or expired SafetyCulture API token.")
    if resp.status_code == 404:
        raise ToolError(f"Resource not found: {resp.url}")
    if resp.status_code == 429:
        raise ToolError("SafetyCulture rate limit exceeded. Retry after the reset window.")
    if resp.status_code >= 500:
        raise ToolError(f"SafetyCulture server error ({resp.status_code}). Try again later.")
    resp.raise_for_status()


# ── Retry + pooling + structured-logging request helper ───────────────────────


async def request(
    method: str,
    path: str,
    *,
    headers: dict,
    tool: str,
    params: dict | None = None,
    json: dict | None = None,
) -> httpx.Response:
    """
    Central HTTP helper providing:
    - shared connection pool — no new TCP handshake per tool call
    - automatic retry (up to 3x) on network errors and 429/5xx
      with exponential back-off + jitter; Retry-After header respected
    - structured JSON log lines per request (tool, method, status_code,
      duration_ms, request_id) for log-aggregator ingestion
    """
    # Re-use the trace ID already embedded in headers by get_headers(), or
    # generate a fallback so logging always has a correlation ID.
    request_id = headers.get("x-request-id") or str(uuid.uuid4())
    client = get_http_client()
    resp: httpx.Response | None = None

    async def _do() -> httpx.Response:
        nonlocal resp
        t0 = time.monotonic()
        logger.debug(
            "api_request_start",
            extra={"tool": tool, "method": method, "path": path, "request_id": request_id},
        )
        r = await client.request(method, path, headers=headers, params=params, json=json)
        duration_ms = round((time.monotonic() - t0) * 1000, 1)
        logger.info(
            "api_request_complete",
            extra={
                "tool": tool,
                "method": method,
                "path": path,
                "status_code": r.status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
            },
        )
        resp = r
        return r

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(_MAX_ATTEMPTS),
            wait=wait_exponential_jitter(initial=1, max=30, jitter=2),
            retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        ):
            with attempt:
                r = await _do()
                if r.status_code in _RETRYABLE_STATUS:
                    retry_after = r.headers.get("Retry-After")
                    if retry_after:
                        wait_secs = min(float(retry_after), 60.0)
                        logger.warning(
                            "retry_after_header",
                            extra={
                                "tool": tool,
                                "wait_secs": wait_secs,
                                "request_id": request_id,
                            },
                        )
                        await asyncio.sleep(wait_secs)
                    raise httpx.HTTPStatusError(
                        f"Retryable status {r.status_code}",
                        request=r.request,
                        response=r,
                    )

    except httpx.HTTPStatusError:
        # Retries exhausted on 429/5xx — fall through;
        # caller calls raise_for_status() which converts to ToolError
        pass
    except httpx.TimeoutException:
        logger.warning(
            "api_timeout",
            extra={"tool": tool, "path": path, "request_id": request_id},
        )
        raise ToolError(f"Request timed out calling SafetyCulture ({tool}). Try again.")
    except httpx.RequestError as e:
        logger.error(
            "api_network_error",
            extra={"tool": tool, "path": path, "error": str(e), "request_id": request_id},
        )
        raise ToolError(f"Network error calling SafetyCulture ({tool}): {e}")

    return resp  # type: ignore[return-value]
