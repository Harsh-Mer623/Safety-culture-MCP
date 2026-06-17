"""Shared test factory functions used by test modules and conftest."""

from unittest.mock import AsyncMock, MagicMock

import httpx


def make_resp(status: int, body: dict) -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.status_code = status
    r.json.return_value = body
    r.url = "http://mock"
    r.headers = {}
    r.raise_for_status = MagicMock()
    return r


def mock_request(resp: MagicMock) -> AsyncMock:
    return AsyncMock(return_value=resp)


def make_ctx(token: str = "test_token") -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.request.headers.get = MagicMock(return_value=token)
    return ctx
