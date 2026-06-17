import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from safetyculture_mcp.client import BASE_URL, get_headers, raise_for_status
from fastmcp.exceptions import ToolError
from safetyculture_mcp.models.schemas import (
    InspectionSummary, InspectionDetail,
    Template,
    ActionTask, ActionStatus, ActionPriority, Action, CreatedAction,
    User,
)
from safetyculture_mcp.tools.inspections import list_inspections, get_inspection
from safetyculture_mcp.tools.templates import list_templates
from safetyculture_mcp.tools.actions import list_actions, get_action, create_action
from safetyculture_mcp.tools.users import list_users, search_users_by_email


# ── helpers ──────────────────────────────────────────────────────────────────

def make_resp(status: int, body: dict) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body
    r.url = "http://mock"
    return r


def mock_client(resp: MagicMock) -> MagicMock:
    c = AsyncMock()
    c.get = AsyncMock(return_value=resp)
    c.post = AsyncMock(return_value=resp)
    c.__aenter__ = AsyncMock(return_value=c)
    c.__aexit__ = AsyncMock(return_value=None)
    return c


def make_ctx(token: str = "test_token") -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.request.headers.get = MagicMock(return_value=token)
    return ctx


# ── client ────────────────────────────────────────────────────────────────────

def test_client_base_url():
    assert BASE_URL == "https://api.safetyculture.io"


def test_client_headers_authorization():
    assert get_headers()["Authorization"].startswith("Bearer ")


def test_client_headers_content_type():
    assert get_headers()["Content-Type"] == "application/json"


def test_client_headers_from_ctx():
    ctx = make_ctx("ctx_token")
    h = get_headers(ctx)
    assert h["Authorization"] == "Bearer ctx_token"


def test_client_headers_missing_token_raises():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("SAFETYCULTURE_API_TOKEN", None)
        ctx = MagicMock()
        ctx.request_context.request.headers.get = MagicMock(return_value=None)
        with pytest.raises(ToolError, match="token not provided"):
            get_headers(ctx)


def test_raise_for_status_401():
    resp = httpx.Response(401, request=httpx.Request("GET", "http://t"))
    with pytest.raises(ToolError, match="Invalid or expired"):
        raise_for_status(resp)


def test_raise_for_status_404():
    resp = httpx.Response(404, request=httpx.Request("GET", "http://t"))
    with pytest.raises(ToolError, match="not found"):
        raise_for_status(resp)


def test_raise_for_status_429():
    resp = httpx.Response(429, request=httpx.Request("GET", "http://t"))
    with pytest.raises(ToolError, match="rate limit"):
        raise_for_status(resp)


def test_raise_for_status_500():
    resp = httpx.Response(500, request=httpx.Request("GET", "http://t"))
    with pytest.raises(ToolError, match="server error"):
        raise_for_status(resp)


def test_raise_for_status_200_no_raise():
    resp = httpx.Response(200, request=httpx.Request("GET", "http://t"))
    raise_for_status(resp)


# ── schemas ───────────────────────────────────────────────────────────────────

def test_inspection_summary_defaults():
    s = InspectionSummary(audit_id="a1")
    assert s.audit_id == "a1"
    assert s.template_id is None


def test_inspection_detail_defaults():
    d = InspectionDetail(id="i1")
    assert d.is_marked_as_complete is False


def test_template_defaults():
    t = Template(template_id="t1")
    assert t.name is None


def test_action_wraps_task():
    a = Action(task=ActionTask(task_id="t1"))
    assert a.task.task_id == "t1"


def test_action_status_is_object():
    status = ActionStatus(status_id="s1", key="TO_DO", label="To Do", display_order=1)
    task = ActionTask(task_id="t1", status=status)
    assert task.status.key == "TO_DO"


def test_action_ignores_extra_fields():
    a = Action(task=ActionTask(task_id="t1", unknown_field="ignored"))
    assert a.task.task_id == "t1"


def test_inspection_summary_ignores_extra():
    s = InspectionSummary(audit_id="a1", unexpected="value")
    assert s.audit_id == "a1"


def test_created_action():
    ca = CreatedAction(action_id="ca1")
    assert ca.action_id == "ca1"


def test_user_defaults():
    u = User(id="u1", email="a@b.com")
    assert u.active is True
    assert u.firstname is None


# ── inspections ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_inspections_returns_summaries():
    resp = make_resp(200, {"audits": [{"audit_id": "a1", "template_id": "t1"}]})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_inspections(ctx)
    assert len(result) == 1
    assert result[0].audit_id == "a1"


@pytest.mark.asyncio
async def test_list_inspections_empty():
    resp = make_resp(200, {"audits": []})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_inspections(ctx)
    assert result == []


@pytest.mark.asyncio
async def test_list_inspections_401():
    resp = make_resp(401, {})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client(resp)):
        with pytest.raises(ToolError, match="Invalid or expired"):
            await list_inspections(ctx)


@pytest.mark.asyncio
async def test_get_inspection_returns_detail():
    resp = make_resp(200, {"inspection": {"id": "i1", "title": "Safety Check", "is_marked_as_complete": True}})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await get_inspection(ctx, "i1")
    assert result.id == "i1"
    assert result.title == "Safety Check"
    assert result.is_marked_as_complete is True


@pytest.mark.asyncio
async def test_get_inspection_404():
    resp = make_resp(404, {})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client(resp)):
        with pytest.raises(ToolError, match="not found"):
            await get_inspection(ctx, "bad")


# ── templates ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_templates_returns_list():
    resp = make_resp(200, {"templates": [{"template_id": "t1", "name": "Daily Check"}]})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.templates.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_templates(ctx)
    assert len(result) == 1
    assert result[0].name == "Daily Check"


@pytest.mark.asyncio
async def test_list_templates_empty():
    resp = make_resp(200, {"templates": []})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.templates.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_templates(ctx)
    assert result == []


@pytest.mark.asyncio
async def test_list_templates_429():
    resp = make_resp(429, {})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.templates.httpx.AsyncClient", return_value=mock_client(resp)):
        with pytest.raises(ToolError, match="rate limit"):
            await list_templates(ctx)


# ── actions ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_actions_returns_actions():
    resp = make_resp(200, {"actions": [{"task": {"task_id": "t1", "title": "Fix hazard", "status": {"key": "TO_DO", "label": "To Do"}}}]})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_actions(ctx)
    assert len(result) == 1
    assert result[0].task.task_id == "t1"


@pytest.mark.asyncio
async def test_list_actions_empty():
    resp = make_resp(200, {"actions": []})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_actions(ctx)
    assert result == []


@pytest.mark.asyncio
async def test_list_actions_500():
    resp = make_resp(500, {})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client(resp)):
        with pytest.raises(ToolError, match="server error"):
            await list_actions(ctx)


@pytest.mark.asyncio
async def test_get_action_returns_action():
    resp = make_resp(200, {"action": {"task": {"task_id": "t1", "title": "Fix hazard", "status": {"key": "TO_DO", "label": "To Do"}}}})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await get_action(ctx, "t1")
    assert result.task.task_id == "t1"


@pytest.mark.asyncio
async def test_create_action_returns_id():
    resp = make_resp(200, {"action_id": "new1"})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await create_action(ctx, title="Fix guard rail", description="North entrance")
    assert result.action_id == "new1"


# ── users ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_returns_users():
    resp = make_resp(200, {"data": [{"id": "u1", "email": "alice@example.com", "firstname": "Alice", "active": True}]})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.users.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_users(ctx)
    assert len(result) == 1
    assert result[0].email == "alice@example.com"


@pytest.mark.asyncio
async def test_list_users_empty():
    resp = make_resp(200, {"data": []})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.users.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_users(ctx)
    assert result == []


@pytest.mark.asyncio
async def test_search_users_by_email():
    resp = make_resp(200, {"users": [{"id": "u2", "email": "bob@example.com", "active": True}]})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.users.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await search_users_by_email(ctx, ["bob@example.com"])
    assert result[0].email == "bob@example.com"


# ── server composition ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_server_exposes_all_tools():
    from safetyculture_mcp.server import mcp
    from fastmcp import FastMCP
    assert isinstance(mcp, FastMCP)
    expected = [
        "list_inspections", "get_inspection",
        "list_templates",
        "list_actions", "get_action", "create_action",
        "list_users", "search_users_by_email",
    ]
    for name in expected:
        tool = await mcp.get_tool(name)
        assert tool is not None, f"Tool '{name}' not found on server"
