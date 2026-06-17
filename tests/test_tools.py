import logging
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from safetyculture_mcp.client import BASE_URL, get_headers, raise_for_status
from fastmcp.exceptions import ToolError
from safetyculture_mcp.models.schemas import (
    InspectionSummary, InspectionDetail, InspectionScore,
    Template,
    ActionTask, ActionStatus, ActionPriority, Collaborator, CollaboratorUser,
    Action, ActionsPage, CreatedAction, UpdateActionResult,
    WhoAmIResponse,
    PersonRef, SiteRef,
    User,
)
from safetyculture_mcp.tools.inspections import list_inspections, get_inspection
from safetyculture_mcp.tools.templates import list_templates
from safetyculture_mcp.tools.actions import list_actions, get_action, create_action, list_all_actions, update_action
from safetyculture_mcp.tools.users import list_users, search_users_by_email
from safetyculture_mcp.tools.health import whoami

# Shared helpers — defined in helpers.py, re-exported by conftest.py
from helpers import make_resp, mock_request, make_ctx


# ── client ────────────────────────────────────────────────────────────────────

def test_client_base_url():
    assert BASE_URL == "https://api.safetyculture.io"


def test_client_headers_authorization():
    assert get_headers()["Authorization"].startswith("Bearer ")


def test_client_headers_content_type():
    assert get_headers()["Content-Type"] == "application/json"


def test_client_headers_from_ctx():
    ctx = make_ctx("ctx_token")
    assert get_headers(ctx)["Authorization"] == "Bearer ctx_token"


def test_client_headers_include_request_id_from_ctx():
    ctx = MagicMock()
    ctx.request_context.request.headers.get = MagicMock(side_effect=lambda k, *_: {
        "x-safetyculture-token": "tok",
        "x-request-id": "trace-abc-123",
    }.get(k))
    h = get_headers(ctx)
    assert h["x-request-id"] == "trace-abc-123"


def test_client_headers_generates_request_id_when_missing():
    ctx = make_ctx("tok")
    # make_ctx returns None for x-request-id (not in headers)
    ctx.request_context.request.headers.get = MagicMock(side_effect=lambda k, *_: {
        "x-safetyculture-token": "tok",
    }.get(k))
    h = get_headers(ctx)
    assert "x-request-id" in h
    assert len(h["x-request-id"]) == 36  # UUID format


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


def test_inspection_detail_rich_fields():
    d = InspectionDetail(
        id="i1",
        title="Safety Check",
        score={"percentage": 95.5, "value": 19.0, "max_value": 20.0},
        site={"site_id": "s1", "name": "Warehouse A"},
        owner={"id": "u1", "name": "Alice"},
        assignees=[{"id": "u2", "name": "Bob"}],
        conducted_on="2026-06-17T09:00:00Z",
        duration=3600,
        status="completed",
    )
    assert d.score.percentage == 95.5
    assert d.site.name == "Warehouse A"
    assert d.owner.name == "Alice"
    assert len(d.assignees) == 1
    assert d.duration == 3600


def test_inspection_detail_defaults():
    d = InspectionDetail(id="i1")
    assert d.is_marked_as_complete is False
    assert d.assignees == []
    assert d.score is None


def test_template_defaults():
    t = Template(template_id="t1")
    assert t.name is None
    assert t.archived is False


def test_action_status_is_object():
    status = ActionStatus(status_id="s1", key="TO_DO", label="To Do", display_order=1)
    task = ActionTask(task_id="t1", status=status)
    assert task.status.key == "TO_DO"


def test_action_collaborators():
    collab = Collaborator(
        collaborator_id="c1",
        collaborator_type="USER",
        assigned_role="ASSIGNEE",
        user=CollaboratorUser(id="u1", email="a@b.com"),
    )
    task = ActionTask(task_id="t1", collaborators=[collab])
    assert task.collaborators[0].user.email == "a@b.com"


def test_action_task_new_fields():
    task = ActionTask(
        task_id="t1",
        site_id="site_1",
        inspection_id="insp_1",
        created_at="2026-01-01T00:00:00Z",
        modified_at="2026-06-01T00:00:00Z",
    )
    assert task.site_id == "site_1"
    assert task.inspection_id == "insp_1"


def test_actions_page():
    page = ActionsPage(
        actions=[Action(task=ActionTask(task_id="t1"))],
        next_page_token="tok123",
        total_count=42,
    )
    assert len(page.actions) == 1
    assert page.next_page_token == "tok123"
    assert page.total_count == 42


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
    assert u.role is None


# ── inspections ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_inspections_returns_summaries():
    resp = make_resp(200, {"audits": [{"audit_id": "a1", "template_id": "t1"}]})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.request", mock_request(resp)):
        result = await list_inspections(ctx)
    assert len(result) == 1
    assert result[0].audit_id == "a1"


@pytest.mark.asyncio
async def test_list_inspections_with_filters():
    resp = make_resp(200, {"audits": []})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.request", mock_request(resp)):
        result = await list_inspections(ctx, modified_after="2026-01-01T00:00:00Z", template_ids=["t1"])
    assert result == []


@pytest.mark.asyncio
async def test_list_inspections_empty():
    resp = make_resp(200, {"audits": []})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.request", mock_request(resp)):
        result = await list_inspections(ctx)
    assert result == []


@pytest.mark.asyncio
async def test_list_inspections_401():
    resp = make_resp(401, {})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.request", mock_request(resp)):
        with pytest.raises(ToolError, match="Invalid or expired"):
            await list_inspections(ctx)


@pytest.mark.asyncio
async def test_get_inspection_returns_detail():
    body = {
        "inspection": {
            "id": "i1",
            "title": "Safety Check",
            "is_marked_as_complete": True,
            "score": {"percentage": 95.5, "value": 19.0, "max_value": 20.0},
            "site": {"site_id": "s1", "name": "Warehouse A"},
            "conducted_on": "2026-06-17T09:00:00Z",
        }
    }
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.request", mock_request(make_resp(200, body))):
        result = await get_inspection(ctx, "i1")
    assert result.id == "i1"
    assert result.title == "Safety Check"
    assert result.is_marked_as_complete is True
    assert result.score.percentage == 95.5
    assert result.site.name == "Warehouse A"


@pytest.mark.asyncio
async def test_get_inspection_404():
    resp = make_resp(404, {})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.inspections.request", mock_request(resp)):
        with pytest.raises(ToolError, match="not found"):
            await get_inspection(ctx, "bad")


# ── templates ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_templates_returns_list():
    resp = make_resp(200, {"templates": [{"template_id": "t1", "name": "Daily Check", "archived": False}]})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.templates.request", mock_request(resp)):
        result = await list_templates(ctx)
    assert len(result) == 1
    assert result[0].name == "Daily Check"
    assert result[0].archived is False


@pytest.mark.asyncio
async def test_list_templates_empty():
    resp = make_resp(200, {"templates": []})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.templates.request", mock_request(resp)):
        result = await list_templates(ctx)
    assert result == []


@pytest.mark.asyncio
async def test_list_templates_429():
    resp = make_resp(429, {})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.templates.request", mock_request(resp)):
        with pytest.raises(ToolError, match="rate limit"):
            await list_templates(ctx)


# ── actions ───────────────────────────────────────────────────────────────────

FULL_ACTION = {
    "task": {
        "task_id": "t1",
        "title": "Fix hazard",
        "status": {"status_id": "s1", "key": "TO_DO", "label": "To Do", "display_order": 1},
        "priority": {"priority_id": "p1", "label": "High"},
        "collaborators": [
            {
                "collaborator_id": "c1",
                "collaborator_type": "USER",
                "assigned_role": "ASSIGNEE",
                "user": {"id": "u1", "email": "alice@example.com"},
            }
        ],
        "site_id": "site_1",
        "due_at": "2026-12-31T09:00:00Z",
    }
}


@pytest.mark.asyncio
async def test_list_actions_returns_page():
    body = {"actions": [FULL_ACTION], "next_page_token": "tok2", "total_count": 5}
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", mock_request(make_resp(200, body))):
        result = await list_actions(ctx)
    assert isinstance(result, ActionsPage)
    assert len(result.actions) == 1
    assert result.next_page_token == "tok2"
    assert result.total_count == 5
    assert result.actions[0].task.task_id == "t1"
    assert result.actions[0].task.status.key == "TO_DO"
    assert result.actions[0].task.collaborators[0].user.email == "alice@example.com"


@pytest.mark.asyncio
async def test_list_actions_empty():
    resp = make_resp(200, {"actions": []})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", mock_request(resp)):
        result = await list_actions(ctx)
    assert result.actions == []
    assert result.next_page_token is None


@pytest.mark.asyncio
async def test_list_actions_500():
    resp = make_resp(500, {})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", mock_request(resp)):
        with pytest.raises(ToolError, match="server error"):
            await list_actions(ctx)


@pytest.mark.asyncio
async def test_get_action_returns_full_action():
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", mock_request(make_resp(200, {"action": FULL_ACTION}))):
        result = await get_action(ctx, "t1")
    assert result.task.task_id == "t1"
    assert result.task.priority.label == "High"
    assert result.task.site_id == "site_1"
    assert result.task.collaborators[0].assigned_role == "ASSIGNEE"


@pytest.mark.asyncio
async def test_create_action_returns_id():
    resp = make_resp(200, {"action_id": "new1"})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", mock_request(resp)):
        result = await create_action(ctx, title="Fix guard rail", description="North entrance")
    assert result.action_id == "new1"


@pytest.mark.asyncio
async def test_create_action_with_assignee():
    resp = make_resp(200, {"action_id": "new2"})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", mock_request(resp)):
        result = await create_action(
            ctx,
            title="Inspect roof",
            assignee_id="user_abc",
            due_at="2026-12-31T09:00:00Z",
            priority_id="p1",
        )
    assert result.action_id == "new2"


# ── users ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_returns_users():
    body = {"data": [{"id": "u1", "email": "alice@example.com", "firstname": "Alice", "active": True}]}
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.users.request", mock_request(make_resp(200, body))):
        result = await list_users(ctx)
    assert len(result) == 1
    assert result[0].email == "alice@example.com"


@pytest.mark.asyncio
async def test_list_users_empty():
    resp = make_resp(200, {"data": []})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.users.request", mock_request(resp)):
        result = await list_users(ctx)
    assert result == []


@pytest.mark.asyncio
async def test_search_users_by_email():
    body = {"users": [{"id": "u2", "email": "bob@example.com", "active": True}]}
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.users.request", mock_request(make_resp(200, body))):
        result = await search_users_by_email(ctx, ["bob@example.com"])
    assert result[0].email == "bob@example.com"


# ── list_all_actions ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_all_actions_single_page():
    """When next_page_token is absent after first page, loop stops."""
    body = {"actions": [FULL_ACTION], "next_page_token": None}
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", mock_request(make_resp(200, body))):
        result = await list_all_actions(ctx)
    assert isinstance(result, ActionsPage)
    assert len(result.actions) == 1
    assert result.total_count == 1
    assert result.next_page_token is None


@pytest.mark.asyncio
async def test_list_all_actions_multi_page():
    """Accumulates actions across two pages; stops when token is empty on page 2."""
    page1 = make_resp(200, {"actions": [FULL_ACTION], "next_page_token": "tok_p2"})
    page2 = make_resp(200, {"actions": [FULL_ACTION], "next_page_token": ""})
    ctx = make_ctx()
    mock_req = AsyncMock(side_effect=[page1, page2])
    with patch("safetyculture_mcp.tools.actions.request", mock_req):
        result = await list_all_actions(ctx)
    assert len(result.actions) == 2
    assert result.total_count == 2
    assert mock_req.call_count == 2


@pytest.mark.asyncio
async def test_list_all_actions_stops_on_empty_batch():
    """Stops when batch is empty even if next_page_token present (API quirk guard)."""
    page1 = make_resp(200, {"actions": [FULL_ACTION], "next_page_token": "tok"})
    page2 = make_resp(200, {"actions": [], "next_page_token": "tok2"})
    ctx = make_ctx()
    mock_req = AsyncMock(side_effect=[page1, page2])
    with patch("safetyculture_mcp.tools.actions.request", mock_req):
        result = await list_all_actions(ctx)
    assert len(result.actions) == 1
    assert mock_req.call_count == 2


@pytest.mark.asyncio
async def test_list_all_actions_respects_max_pages():
    """Safety cap: stops after max_pages iterations regardless of token."""
    page = make_resp(200, {"actions": [FULL_ACTION], "next_page_token": "always_present"})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", AsyncMock(return_value=page)):
        result = await list_all_actions(ctx, max_pages=3)
    assert len(result.actions) == 3


# ── update_action ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_action_title_only():
    ok = make_resp(200, {})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", mock_request(ok)):
        result = await update_action(ctx, "a1", title="New title")
    assert result.action_id == "a1"
    assert result.updated_fields == ["title"]


@pytest.mark.asyncio
async def test_update_action_multiple_fields():
    ok = make_resp(200, {})
    ctx = make_ctx()
    call_count = 0

    async def multi_ok(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return ok

    with patch("safetyculture_mcp.tools.actions.request", side_effect=multi_ok):
        result = await update_action(
            ctx, "a1",
            title="T",
            status_id="7223d809-553e-4714-a038-62dc98f3fbf3",
            due_at="2026-12-31T09:00:00Z",
        )
    assert set(result.updated_fields) == {"title", "status", "due_at"}
    assert call_count == 3


@pytest.mark.asyncio
async def test_update_action_assignees_replacement():
    ok = make_resp(200, {})
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", mock_request(ok)):
        result = await update_action(ctx, "a1", assignee_ids=["u1", "u2"])
    assert "assignees" in result.updated_fields


@pytest.mark.asyncio
async def test_update_action_no_fields_raises():
    ctx = make_ctx()
    with pytest.raises(ToolError, match="No fields provided"):
        await update_action(ctx, "a1")


@pytest.mark.asyncio
async def test_update_action_clears_due_date():
    """Empty string for due_at sends empty body to clear the due date."""
    ok = make_resp(200, {})
    captured = {}

    async def capture(*args, **kwargs):
        captured.update(kwargs)
        return ok

    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.actions.request", side_effect=capture):
        result = await update_action(ctx, "a1", due_at="")
    assert "due_at" in result.updated_fields
    assert captured.get("json") == {}


# ── health / whoami ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_whoami_returns_user():
    body = {"user_id": "u1", "email": "alice@example.com", "firstname": "Alice", "role": "ADMIN"}
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.health.request", mock_request(make_resp(200, body))):
        result = await whoami(ctx)
    assert result.user_id == "u1"
    assert result.email == "alice@example.com"
    assert result.firstname == "Alice"


@pytest.mark.asyncio
async def test_whoami_ignores_unknown_fields():
    body = {"user_id": "u1", "email": "a@b.com", "unknown_future_field": "x"}
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.health.request", mock_request(make_resp(200, body))):
        result = await whoami(ctx)
    assert result.user_id == "u1"


@pytest.mark.asyncio
async def test_whoami_401():
    ctx = make_ctx()
    with patch("safetyculture_mcp.tools.health.request", mock_request(make_resp(401, {}))):
        with pytest.raises(ToolError, match="Invalid or expired"):
            await whoami(ctx)


# ── logging / token masking ───────────────────────────────────────────────────

def test_sensitive_filter_masks_bearer_in_message():
    from safetyculture_mcp.logging_config import _SensitiveFilter
    f = _SensitiveFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "token is Bearer abc123xyz", (), None)
    f.filter(record)
    assert "abc123xyz" not in record.msg
    assert "***REDACTED***" in record.msg


def test_sensitive_filter_masks_bearer_in_extra_field():
    from safetyculture_mcp.logging_config import _SensitiveFilter
    f = _SensitiveFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
    record.auth = "Bearer supersecrettoken"
    f.filter(record)
    assert "supersecrettoken" not in record.auth
    assert "***REDACTED***" in record.auth


def test_sensitive_filter_masks_header_dict():
    from safetyculture_mcp.logging_config import _SensitiveFilter
    f = _SensitiveFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
    record.headers = {"Authorization": "Bearer tok", "Content-Type": "application/json"}
    f.filter(record)
    assert record.headers["Authorization"] == "***REDACTED***"
    assert record.headers["Content-Type"] == "application/json"


def test_sensitive_filter_passes_safe_records():
    from safetyculture_mcp.logging_config import _SensitiveFilter
    f = _SensitiveFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "tool=whoami status=200", (), None)
    result = f.filter(record)
    assert result is True
    assert record.msg == "tool=whoami status=200"


# ── startup env var warning ───────────────────────────────────────────────────

def test_startup_warning_emitted_when_token_missing():
    import importlib
    import safetyculture_mcp.server

    # logging.getLogger returns a singleton — patching .warning here intercepts
    # the call inside server.py even after reload, because _log = getLogger(...)
    # returns the same object.
    server_logger = logging.getLogger("safetyculture_mcp.server")

    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("SAFETYCULTURE_API_TOKEN", None)
        with patch("safetyculture_mcp.server.configure_logging"):
            with patch.object(server_logger, "warning") as mock_warn:
                importlib.reload(safetyculture_mcp.server)

    mock_warn.assert_called_once()
    detail = mock_warn.call_args.kwargs.get("extra", {}).get("detail", "")
    assert "SAFETYCULTURE_API_TOKEN" in detail


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
        "list_all_actions", "update_action",
        "list_users", "search_users_by_email",
        "whoami",
    ]
    for name in expected:
        tool = await mcp.get_tool(name)
        assert tool is not None, f"Tool '{name}' not found on server"
