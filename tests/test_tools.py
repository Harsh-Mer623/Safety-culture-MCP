import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from safetyculture_mcp.client import BASE_URL, get_headers, raise_for_status
from fastmcp.exceptions import ToolError
from safetyculture_mcp.models.schemas import (
    InspectionSummary, InspectionDetail,
    Template,
    ActionTask, Action, CreatedAction,
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


# ── client ────────────────────────────────────────────────────────────────────

def test_client_base_url():
    assert BASE_URL == "https://api.safetyculture.io"


def test_client_headers_authorization():
    assert get_headers()["Authorization"].startswith("Bearer ")


def test_client_headers_content_type():
    assert get_headers()["Content-Type"] == "application/json"


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
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_inspections()
    assert len(result) == 1
    assert result[0].audit_id == "a1"


@pytest.mark.asyncio
async def test_list_inspections_empty():
    resp = make_resp(200, {"audits": []})
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_inspections()
    assert result == []


@pytest.mark.asyncio
async def test_list_inspections_401():
    resp = make_resp(401, {})
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client(resp)):
        with pytest.raises(ToolError, match="Invalid or expired"):
            await list_inspections()


@pytest.mark.asyncio
async def test_get_inspection_returns_detail():
    resp = make_resp(200, {"inspection": {"id": "i1", "title": "Safety Check", "is_marked_as_complete": True}})
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await get_inspection("i1")
    assert result.id == "i1"
    assert result.title == "Safety Check"
    assert result.is_marked_as_complete is True


@pytest.mark.asyncio
async def test_get_inspection_404():
    resp = make_resp(404, {})
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client(resp)):
        with pytest.raises(ToolError, match="not found"):
            await get_inspection("bad")


# ── templates ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_templates_returns_list():
    resp = make_resp(200, {"templates": [{"template_id": "t1", "name": "Daily Check"}]})
    with patch("safetyculture_mcp.tools.templates.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_templates()
    assert len(result) == 1
    assert result[0].name == "Daily Check"


@pytest.mark.asyncio
async def test_list_templates_empty():
    resp = make_resp(200, {"templates": []})
    with patch("safetyculture_mcp.tools.templates.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_templates()
    assert result == []


@pytest.mark.asyncio
async def test_list_templates_429():
    resp = make_resp(429, {})
    with patch("safetyculture_mcp.tools.templates.httpx.AsyncClient", return_value=mock_client(resp)):
        with pytest.raises(ToolError, match="rate limit"):
            await list_templates()


# ── actions ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_actions_returns_actions():
    resp = make_resp(200, {"actions": [{"task": {"task_id": "t1", "title": "Fix hazard", "status": "open"}}]})
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_actions()
    assert len(result) == 1
    assert result[0].task.task_id == "t1"


@pytest.mark.asyncio
async def test_list_actions_empty():
    resp = make_resp(200, {"actions": []})
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_actions()
    assert result == []


@pytest.mark.asyncio
async def test_list_actions_500():
    resp = make_resp(500, {})
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client(resp)):
        with pytest.raises(ToolError, match="server error"):
            await list_actions()


@pytest.mark.asyncio
async def test_get_action_returns_action():
    resp = make_resp(200, {"action": {"task": {"task_id": "t1", "title": "Fix hazard", "status": "open"}}})
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await get_action("t1")
    assert result.task.task_id == "t1"


@pytest.mark.asyncio
async def test_create_action_returns_id():
    resp = make_resp(200, {"action_id": "new1"})
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await create_action(title="Fix guard rail", description="North entrance")
    assert result.action_id == "new1"


# ── users ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_returns_users():
    resp = make_resp(200, {"data": [{"id": "u1", "email": "alice@example.com", "firstname": "Alice", "active": True}]})
    with patch("safetyculture_mcp.tools.users.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_users()
    assert len(result) == 1
    assert result[0].email == "alice@example.com"


@pytest.mark.asyncio
async def test_list_users_empty():
    resp = make_resp(200, {"data": []})
    with patch("safetyculture_mcp.tools.users.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await list_users()
    assert result == []


@pytest.mark.asyncio
async def test_search_users_by_email():
    resp = make_resp(200, {"users": [{"id": "u2", "email": "bob@example.com", "active": True}]})
    with patch("safetyculture_mcp.tools.users.httpx.AsyncClient", return_value=mock_client(resp)):
        result = await search_users_by_email(["bob@example.com"])
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
