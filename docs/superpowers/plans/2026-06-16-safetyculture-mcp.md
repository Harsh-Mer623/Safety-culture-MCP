# SafetyCulture MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade FastMCP server exposing SafetyCulture inspections, actions, templates, and users as typed MCP tools, deployable to Prefect Horizon.

**Architecture:** Each domain (inspections, actions, templates, users) lives in its own `FastMCP` sub-app. `server.py` mounts all sub-apps onto a root `FastMCP` instance. A shared `client.py` holds auth config and a `raise_for_status` error helper used by all tool modules.

**Tech Stack:** FastMCP 3.4.2 · httpx async · Pydantic v2 · Python 3.12 · pip + venv · pytest + pytest-asyncio

---

## File Map

| File | Role |
|---|---|
| `pyproject.toml` | Package metadata, requires-python, deps |
| `requirements.txt` | Pinned runtime deps |
| `requirements-dev.txt` | Test-only deps (pytest, pytest-asyncio) |
| `.env.example` | Placeholder env vars, committed |
| `.gitignore` | Ignore `.env`, `.venv`, `__pycache__`, `.pytest_cache` |
| `src/safetyculture_mcp/__init__.py` | Package marker |
| `src/safetyculture_mcp/client.py` | BASE_URL, HEADERS, raise_for_status |
| `src/safetyculture_mcp/models/__init__.py` | Package marker |
| `src/safetyculture_mcp/models/schemas.py` | All Pydantic v2 models |
| `src/safetyculture_mcp/tools/__init__.py` | Package marker |
| `src/safetyculture_mcp/tools/inspections.py` | FastMCP sub-app: list_inspections, get_inspection |
| `src/safetyculture_mcp/tools/templates.py` | FastMCP sub-app: list_templates |
| `src/safetyculture_mcp/tools/actions.py` | FastMCP sub-app: list_actions, get_action, create_action |
| `src/safetyculture_mcp/tools/users.py` | FastMCP sub-app: list_users, search_users_by_email |
| `src/safetyculture_mcp/server.py` | Root FastMCP app, mounts all sub-apps, entry point |
| `tests/conftest.py` | Sets SAFETYCULTURE_API_TOKEN env var before imports |
| `tests/test_tools.py` | All unit tests with mocked httpx |
| `README.md` | Setup steps + Claude Desktop config example |

---

## Task 1: Project scaffold and dependency installation

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/safetyculture_mcp/__init__.py`
- Create: `src/safetyculture_mcp/models/__init__.py`
- Create: `src/safetyculture_mcp/tools/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "safetyculture-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastmcp==3.4.2",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "python-dotenv",
]
```

- [ ] **Step 2: Create requirements.txt**

```
fastmcp==3.4.2
httpx>=0.27.0
pydantic>=2.0.0
python-dotenv
```

- [ ] **Step 3: Create requirements-dev.txt**

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 4: Create .env.example**

```
SAFETYCULTURE_API_TOKEN=your_token_here
```

- [ ] **Step 5: Create .gitignore**

```
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
```

- [ ] **Step 6: Create all empty package markers**

Create these four empty files (each completely empty):
- `src/safetyculture_mcp/__init__.py`
- `src/safetyculture_mcp/models/__init__.py`
- `src/safetyculture_mcp/tools/__init__.py`
- `tests/__init__.py`

- [ ] **Step 7: Create tests/conftest.py**

This file runs before any test imports, ensuring the env var exists so `client.py` doesn't crash at import time:

```python
import os
os.environ.setdefault("SAFETYCULTURE_API_TOKEN", "test_token_for_testing")
```

- [ ] **Step 8: Activate the venv and install all dependencies**

Run in the project root (Windows PowerShell):
```powershell
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
```

- [ ] **Step 9: Verify FastMCP installed correctly**

```powershell
fastmcp version
```

Expected output (all three lines):
```
FastMCP version: 3.4.2
MCP version:     1.27.2
Python version:  3.12.x
```

- [ ] **Step 10: Commit scaffold**

```bash
git init
git add pyproject.toml requirements.txt requirements-dev.txt .env.example .gitignore src/ tests/
git commit -m "chore: scaffold safetyculture-mcp project structure"
```

---

## Task 2: client.py — auth config and error helper

**Files:**
- Create: `src/safetyculture_mcp/client.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_tools.py` (create it now):

```python
import pytest
from safetyculture_mcp.client import BASE_URL, HEADERS, raise_for_status
import httpx
from fastmcp.exceptions import ToolError


def test_client_base_url():
    assert BASE_URL == "https://api.safetyculture.io"


def test_client_headers_has_authorization():
    assert "Authorization" in HEADERS
    assert HEADERS["Authorization"].startswith("Bearer ")


def test_client_headers_has_content_type():
    assert HEADERS["Content-Type"] == "application/json"


def test_raise_for_status_401():
    resp = httpx.Response(401, request=httpx.Request("GET", "http://test"))
    with pytest.raises(ToolError, match="Invalid or expired"):
        raise_for_status(resp)


def test_raise_for_status_404():
    resp = httpx.Response(404, request=httpx.Request("GET", "http://test"))
    with pytest.raises(ToolError, match="not found"):
        raise_for_status(resp)


def test_raise_for_status_429():
    resp = httpx.Response(429, request=httpx.Request("GET", "http://test"))
    with pytest.raises(ToolError, match="rate limit"):
        raise_for_status(resp)


def test_raise_for_status_500():
    resp = httpx.Response(500, request=httpx.Request("GET", "http://test"))
    with pytest.raises(ToolError, match="server error"):
        raise_for_status(resp)


def test_raise_for_status_200_does_not_raise():
    resp = httpx.Response(200, request=httpx.Request("GET", "http://test"))
    raise_for_status(resp)  # should not raise
```

- [ ] **Step 2: Run tests to confirm they fail**

```powershell
pytest tests/test_tools.py -v -k "test_client"
```

Expected: `FAILED` / `ImportError` — `client.py` doesn't exist yet.

- [ ] **Step 3: Create src/safetyculture_mcp/client.py**

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```powershell
pytest tests/test_tools.py -v -k "test_client"
```

Expected: All 8 tests `PASSED`.

- [ ] **Step 5: Manual auth verification (requires real .env)**

Copy `.env.example` to `.env` and set your real token, then run:

```powershell
python -c "
import asyncio, httpx
from safetyculture_mcp.client import BASE_URL, HEADERS

async def check():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f'{BASE_URL}/feed/v2/accounts/me', headers=HEADERS)
        print(resp.status_code, resp.json())

asyncio.run(check())
"
```

Expected: `200` and a JSON object with your account details. If you see `401`, the token in `.env` is wrong.

- [ ] **Step 6: Commit**

```bash
git add src/safetyculture_mcp/client.py tests/test_tools.py tests/conftest.py
git commit -m "feat: add client auth config and error helper"
```

---

## Task 3: schemas.py — Pydantic v2 models

**Files:**
- Create: `src/safetyculture_mcp/models/schemas.py`

- [ ] **Step 1: Write failing tests — add to tests/test_tools.py**

```python
from safetyculture_mcp.models.schemas import (
    InspectionSummary,
    InspectionDetail,
    Template,
    ActionTask,
    Action,
    CreatedAction,
    User,
)


def test_inspection_summary_required_field():
    s = InspectionSummary(audit_id="audit_1")
    assert s.audit_id == "audit_1"
    assert s.template_id is None
    assert s.modified_at is None


def test_inspection_detail_defaults():
    d = InspectionDetail(id="insp_1")
    assert d.id == "insp_1"
    assert d.is_marked_as_complete is False
    assert d.title is None


def test_template_required_field():
    t = Template(template_id="tmpl_1")
    assert t.template_id == "tmpl_1"
    assert t.name is None


def test_action_task_required_field():
    t = ActionTask(task_id="task_1")
    assert t.task_id == "task_1"
    assert t.status is None


def test_action_wraps_task():
    a = Action(task=ActionTask(task_id="task_1"))
    assert a.task.task_id == "task_1"


def test_created_action():
    ca = CreatedAction(action_id="act_1")
    assert ca.action_id == "act_1"


def test_user_defaults():
    u = User(id="user_1", email="a@b.com")
    assert u.active is True
    assert u.firstname is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```powershell
pytest tests/test_tools.py -v -k "test_inspection or test_template or test_action or test_user or test_created"
```

Expected: `ImportError` — schemas module doesn't exist yet.

- [ ] **Step 3: Create src/safetyculture_mcp/models/schemas.py**

```python
from pydantic import BaseModel


class InspectionSummary(BaseModel):
    audit_id: str
    template_id: str | None = None
    modified_at: str | None = None


class InspectionDetail(BaseModel):
    id: str
    template_id: str | None = None
    title: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    is_marked_as_complete: bool = False


class Template(BaseModel):
    template_id: str
    name: str | None = None
    modified_at: str | None = None
    created_at: str | None = None


class ActionTask(BaseModel):
    task_id: str
    title: str | None = None
    description: str | None = None
    due_at: str | None = None
    status: str | None = None
    priority_id: str | None = None


class Action(BaseModel):
    task: ActionTask


class CreatedAction(BaseModel):
    action_id: str


class User(BaseModel):
    id: str
    email: str
    firstname: str | None = None
    lastname: str | None = None
    active: bool = True
```

- [ ] **Step 4: Run tests to confirm they pass**

```powershell
pytest tests/test_tools.py -v -k "test_inspection or test_template or test_action or test_user or test_created"
```

Expected: All 7 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add src/safetyculture_mcp/models/schemas.py tests/test_tools.py
git commit -m "feat: add pydantic v2 schemas for all domains"
```

---

## Task 4: tools/inspections.py

**Files:**
- Create: `src/safetyculture_mcp/tools/inspections.py`

- [ ] **Step 1: Write failing tests — add to tests/test_tools.py**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from safetyculture_mcp.tools.inspections import list_inspections, get_inspection


def make_mock_client(status_code: int, json_body: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body
    mock_resp.url = "http://mock"
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
async def test_list_inspections_returns_summaries():
    mock_client = make_mock_client(200, {
        "audits": [
            {"audit_id": "audit_1", "template_id": "tmpl_1", "modified_at": "2024-01-01"},
        ]
    })
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client):
        result = await list_inspections()
    assert len(result) == 1
    assert result[0].audit_id == "audit_1"
    assert result[0].template_id == "tmpl_1"


@pytest.mark.asyncio
async def test_list_inspections_empty():
    mock_client = make_mock_client(200, {"audits": []})
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client):
        result = await list_inspections()
    assert result == []


@pytest.mark.asyncio
async def test_list_inspections_401_raises_tool_error():
    from fastmcp.exceptions import ToolError
    mock_client = make_mock_client(401, {})
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ToolError, match="Invalid or expired"):
            await list_inspections()


@pytest.mark.asyncio
async def test_get_inspection_returns_detail():
    mock_client = make_mock_client(200, {
        "inspection": {
            "id": "insp_1",
            "title": "Site Safety Check",
            "template_id": "tmpl_1",
            "is_marked_as_complete": True,
        }
    })
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client):
        result = await get_inspection("insp_1")
    assert result.id == "insp_1"
    assert result.title == "Site Safety Check"
    assert result.is_marked_as_complete is True


@pytest.mark.asyncio
async def test_get_inspection_404_raises_tool_error():
    from fastmcp.exceptions import ToolError
    mock_client = make_mock_client(404, {})
    with patch("safetyculture_mcp.tools.inspections.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ToolError, match="not found"):
            await get_inspection("bad_id")
```

- [ ] **Step 2: Add pytest-asyncio config to pyproject.toml**

Add this section to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3: Run tests to confirm they fail**

```powershell
pytest tests/test_tools.py -v -k "test_list_inspections or test_get_inspection"
```

Expected: `ImportError` — tools/inspections.py doesn't exist yet.

- [ ] **Step 4: Create src/safetyculture_mcp/tools/inspections.py**

```python
import httpx
from fastmcp import FastMCP
from ..client import BASE_URL, HEADERS, raise_for_status
from ..models.schemas import InspectionSummary, InspectionDetail

mcp = FastMCP(name="Inspections")


@mcp.tool(description="List inspections for the authenticated SafetyCulture account")
async def list_inspections(
    limit: int = 20,
    archived: bool = False,
    completed: bool | None = None,
) -> list[InspectionSummary]:
    params: dict = {"limit": limit, "archived": archived}
    if completed is not None:
        params["completed"] = completed
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/audits/search",
            headers=HEADERS,
            params=params,
        )
    raise_for_status(resp)
    return [InspectionSummary(**a) for a in resp.json().get("audits", [])]


@mcp.tool(description="Get full details for a single SafetyCulture inspection by ID")
async def get_inspection(inspection_id: str) -> InspectionDetail:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/inspections/v1/inspections/{inspection_id}",
            headers=HEADERS,
        )
    raise_for_status(resp)
    return InspectionDetail(**resp.json()["inspection"])
```

- [ ] **Step 5: Run tests to confirm they pass**

```powershell
pytest tests/test_tools.py -v -k "test_list_inspections or test_get_inspection"
```

Expected: All 5 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add src/safetyculture_mcp/tools/inspections.py tests/test_tools.py pyproject.toml
git commit -m "feat: add inspections tools (list_inspections, get_inspection)"
```

---

## Task 5: tools/templates.py

**Files:**
- Create: `src/safetyculture_mcp/tools/templates.py`

- [ ] **Step 1: Write failing tests — add to tests/test_tools.py**

```python
from safetyculture_mcp.tools.templates import list_templates


@pytest.mark.asyncio
async def test_list_templates_returns_list():
    mock_client = make_mock_client(200, {
        "templates": [
            {"template_id": "tmpl_1", "name": "Daily Checklist", "modified_at": "2024-01-01"},
        ]
    })
    with patch("safetyculture_mcp.tools.templates.httpx.AsyncClient", return_value=mock_client):
        result = await list_templates()
    assert len(result) == 1
    assert result[0].template_id == "tmpl_1"
    assert result[0].name == "Daily Checklist"


@pytest.mark.asyncio
async def test_list_templates_empty():
    mock_client = make_mock_client(200, {"templates": []})
    with patch("safetyculture_mcp.tools.templates.httpx.AsyncClient", return_value=mock_client):
        result = await list_templates()
    assert result == []


@pytest.mark.asyncio
async def test_list_templates_429_raises_tool_error():
    from fastmcp.exceptions import ToolError
    mock_client = make_mock_client(429, {})
    with patch("safetyculture_mcp.tools.templates.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ToolError, match="rate limit"):
            await list_templates()
```

- [ ] **Step 2: Run tests to confirm they fail**

```powershell
pytest tests/test_tools.py -v -k "test_list_templates"
```

Expected: `ImportError` — tools/templates.py doesn't exist yet.

- [ ] **Step 3: Create src/safetyculture_mcp/tools/templates.py**

```python
import httpx
from fastmcp import FastMCP
from ..client import BASE_URL, HEADERS, raise_for_status
from ..models.schemas import Template

mcp = FastMCP(name="Templates")


@mcp.tool(description="List templates for the authenticated SafetyCulture account")
async def list_templates(
    limit: int = 20,
    archived: bool = False,
) -> list[Template]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/templates/search",
            headers=HEADERS,
            params={"limit": limit, "archived": archived},
        )
    raise_for_status(resp)
    return [Template(**t) for t in resp.json().get("templates", [])]
```

- [ ] **Step 4: Run tests to confirm they pass**

```powershell
pytest tests/test_tools.py -v -k "test_list_templates"
```

Expected: All 3 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add src/safetyculture_mcp/tools/templates.py tests/test_tools.py
git commit -m "feat: add templates tools (list_templates)"
```

---

## Task 6: tools/actions.py

**Files:**
- Create: `src/safetyculture_mcp/tools/actions.py`

- [ ] **Step 1: Write failing tests — add to tests/test_tools.py**

```python
from safetyculture_mcp.tools.actions import list_actions, get_action, create_action


def make_mock_client_post(status_code: int, json_body: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body
    mock_resp.url = "http://mock"
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
async def test_list_actions_returns_actions():
    mock_client = make_mock_client_post(200, {
        "actions": [
            {"task": {"task_id": "task_1", "title": "Fix hazard", "status": "open"}}
        ],
        "next_page_token": "",
    })
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client):
        result = await list_actions()
    assert len(result) == 1
    assert result[0].task.task_id == "task_1"
    assert result[0].task.title == "Fix hazard"


@pytest.mark.asyncio
async def test_list_actions_empty():
    mock_client = make_mock_client_post(200, {"actions": []})
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client):
        result = await list_actions()
    assert result == []


@pytest.mark.asyncio
async def test_get_action_returns_action():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "action": {"task": {"task_id": "task_1", "title": "Fix hazard", "status": "open"}},
        "read_only": False,
    }
    mock_resp.url = "http://mock"
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client):
        result = await get_action("task_1")
    assert result.task.task_id == "task_1"


@pytest.mark.asyncio
async def test_create_action_returns_id():
    mock_client = make_mock_client_post(200, {"action_id": "new_action_1"})
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client):
        result = await create_action(title="Fix guard rail", description="North entrance")
    assert result.action_id == "new_action_1"


@pytest.mark.asyncio
async def test_list_actions_500_raises_tool_error():
    from fastmcp.exceptions import ToolError
    mock_client = make_mock_client_post(500, {})
    with patch("safetyculture_mcp.tools.actions.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ToolError, match="server error"):
            await list_actions()
```

- [ ] **Step 2: Run tests to confirm they fail**

```powershell
pytest tests/test_tools.py -v -k "test_list_actions or test_get_action or test_create_action"
```

Expected: `ImportError` — tools/actions.py doesn't exist yet.

- [ ] **Step 3: Create src/safetyculture_mcp/tools/actions.py**

```python
import httpx
from fastmcp import FastMCP
from ..client import BASE_URL, HEADERS, raise_for_status
from ..models.schemas import Action, CreatedAction

mcp = FastMCP(name="Actions")


@mcp.tool(description="List actions for the authenticated SafetyCulture account")
async def list_actions(page_size: int = 20) -> list[Action]:
    # NOTE: List actions uses POST, not GET
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/tasks/v1/actions/list",
            headers=HEADERS,
            json={"page_size": page_size},
        )
    raise_for_status(resp)
    return [Action(**a) for a in resp.json().get("actions", [])]


@mcp.tool(description="Get full details for a single SafetyCulture action by ID")
async def get_action(action_id: str) -> Action:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/tasks/v1/actions/{action_id}",
            headers=HEADERS,
        )
    raise_for_status(resp)
    return Action(**resp.json()["action"])


@mcp.tool(description="Create a new action in the authenticated SafetyCulture account")
async def create_action(
    title: str,
    description: str = "",
    due_at: str | None = None,
) -> CreatedAction:
    body: dict = {"title": title, "description": description}
    if due_at is not None:
        body["due_at"] = due_at
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/tasks/v1/actions",
            headers=HEADERS,
            json=body,
        )
    raise_for_status(resp)
    return CreatedAction(**resp.json())
```

- [ ] **Step 4: Run tests to confirm they pass**

```powershell
pytest tests/test_tools.py -v -k "test_list_actions or test_get_action or test_create_action"
```

Expected: All 5 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add src/safetyculture_mcp/tools/actions.py tests/test_tools.py
git commit -m "feat: add actions tools (list_actions, get_action, create_action)"
```

---

## Task 7: tools/users.py

**Files:**
- Create: `src/safetyculture_mcp/tools/users.py`

- [ ] **Step 1: Write failing tests — add to tests/test_tools.py**

```python
from safetyculture_mcp.tools.users import list_users, search_users_by_email


@pytest.mark.asyncio
async def test_list_users_returns_users():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "user_1", "email": "alice@example.com", "firstname": "Alice", "lastname": "Smith", "active": True},
        ],
        "metadata": {"next_page": "", "remaining_records": 0},
    }
    mock_resp.url = "http://mock"
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("safetyculture_mcp.tools.users.httpx.AsyncClient", return_value=mock_client):
        result = await list_users()
    assert len(result) == 1
    assert result[0].id == "user_1"
    assert result[0].email == "alice@example.com"
    assert result[0].firstname == "Alice"


@pytest.mark.asyncio
async def test_list_users_empty():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": [], "metadata": {"next_page": "", "remaining_records": 0}}
    mock_resp.url = "http://mock"
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("safetyculture_mcp.tools.users.httpx.AsyncClient", return_value=mock_client):
        result = await list_users()
    assert result == []


@pytest.mark.asyncio
async def test_search_users_by_email_returns_users():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "users": [
            {"id": "user_2", "email": "bob@example.com", "firstname": "Bob", "lastname": "Jones", "active": True},
        ]
    }
    mock_resp.url = "http://mock"
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("safetyculture_mcp.tools.users.httpx.AsyncClient", return_value=mock_client):
        result = await search_users_by_email(["bob@example.com"])
    assert len(result) == 1
    assert result[0].email == "bob@example.com"
```

- [ ] **Step 2: Run tests to confirm they fail**

```powershell
pytest tests/test_tools.py -v -k "test_list_users or test_search_users"
```

Expected: `ImportError` — tools/users.py doesn't exist yet.

- [ ] **Step 3: Create src/safetyculture_mcp/tools/users.py**

```python
import httpx
from fastmcp import FastMCP
from ..client import BASE_URL, HEADERS, raise_for_status
from ..models.schemas import User

mcp = FastMCP(name="Users")


@mcp.tool(description="List all users in the SafetyCulture organisation")
async def list_users() -> list[User]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/feed/users",
            headers=HEADERS,
        )
    raise_for_status(resp)
    return [User(**u) for u in resp.json().get("data", [])]


@mcp.tool(description="Search for SafetyCulture users by a list of email addresses")
async def search_users_by_email(emails: list[str]) -> list[User]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/users/search",
            headers=HEADERS,
            json={"email": emails},
        )
    raise_for_status(resp)
    return [User(**u) for u in resp.json().get("users", [])]
```

- [ ] **Step 4: Run tests to confirm they pass**

```powershell
pytest tests/test_tools.py -v -k "test_list_users or test_search_users"
```

Expected: All 3 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add src/safetyculture_mcp/tools/users.py tests/test_tools.py
git commit -m "feat: add users tools (list_users, search_users_by_email)"
```

---

## Task 8: server.py — compose all sub-apps

**Files:**
- Create: `src/safetyculture_mcp/server.py`

- [ ] **Step 1: Write failing test — add to tests/test_tools.py**

```python
@pytest.mark.asyncio
async def test_server_mcp_exposes_all_tools():
    from safetyculture_mcp.server import mcp
    from fastmcp import FastMCP
    assert isinstance(mcp, FastMCP)
    assert mcp.name == "SafetyCulture MCP"
    # Verify all sub-apps are mounted by calling list_tools via the MCP protocol
    tools = await mcp.get_tools()
    tool_names = {name for name in tools}
    expected = {
        "list_inspections", "get_inspection",
        "list_templates",
        "list_actions", "get_action", "create_action",
        "list_users", "search_users_by_email",
    }
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"
```

- [ ] **Step 2: Run test to confirm it fails**

```powershell
pytest tests/test_tools.py -v -k "test_server_mcp"
```

Expected: `ImportError` — server.py doesn't exist yet.

- [ ] **Step 3: Create src/safetyculture_mcp/server.py**

```python
from fastmcp import FastMCP
from .tools.inspections import mcp as inspections_mcp
from .tools.actions import mcp as actions_mcp
from .tools.templates import mcp as templates_mcp
from .tools.users import mcp as users_mcp

mcp = FastMCP(name="SafetyCulture MCP")

mcp.mount(inspections_mcp)
mcp.mount(actions_mcp)
mcp.mount(templates_mcp)
mcp.mount(users_mcp)

if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 4: Run test to confirm it passes**

```powershell
pytest tests/test_tools.py -v -k "test_server_mcp"
```

Expected: `PASSED`.

- [ ] **Step 5: Run the full test suite**

```powershell
pytest tests/test_tools.py -v
```

Expected: All tests `PASSED`, 0 failures.

- [ ] **Step 6: Inspect with FastMCP (requires real .env)**

```powershell
fastmcp inspect src/safetyculture_mcp/server.py:mcp
```

Expected: All 9 tools listed. If a browser UI opens, manually call `list_inspections` and verify a real API response returns.

- [ ] **Step 7: Commit**

```bash
git add src/safetyculture_mcp/server.py tests/test_tools.py
git commit -m "feat: compose all sub-apps into root server"
```

---

## Task 9: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

```markdown
# SafetyCulture MCP Server

A FastMCP server that exposes SafetyCulture inspections, actions, templates, and users as MCP tools.

## Setup

### Prerequisites
- Python 3.12+
- A SafetyCulture API token ([get one here](https://app.safetyculture.com/account/api))

### Install

```bash
python3.12 -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### Configure

```bash
cp .env.example .env
# Edit .env and set SAFETYCULTURE_API_TOKEN=your_token_here
```

### Verify auth

```bash
python -c "
import asyncio, httpx
from safetyculture_mcp.client import BASE_URL, HEADERS
async def check():
    async with httpx.AsyncClient() as c:
        r = await c.get(f'{BASE_URL}/feed/v2/accounts/me', headers=HEADERS)
        print(r.status_code, r.json())
asyncio.run(check())
"
```

### Test

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Run locally

```bash
fastmcp inspect src/safetyculture_mcp/server.py:mcp
```

## Available Tools

| Tool | Description |
|---|---|
| `list_inspections` | List inspections (params: limit, archived, completed) |
| `get_inspection` | Get full inspection detail by ID |
| `list_templates` | List templates (params: limit, archived) |
| `list_actions` | List actions (params: page_size) |
| `get_action` | Get full action detail by ID |
| `create_action` | Create a new action (params: title, description, due_at) |
| `list_users` | List all users in the organisation |
| `search_users_by_email` | Search users by email addresses |

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "safetyculture": {
      "command": "fastmcp",
      "args": ["run", "C:/path/to/safetyculture-mcp/src/safetyculture_mcp/server.py:mcp"],
      "env": {
        "SAFETYCULTURE_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Deploy to Prefect Horizon

1. Push this repo to GitHub
2. Visit [horizon.prefect.io](https://horizon.prefect.io) and authenticate with GitHub
3. Select this repository
4. Set **entrypoint**: `src/safetyculture_mcp/server.py:mcp`
5. Click **Deploy** — live at `https://<your-name>.fastmcp.app/mcp` in ~60 seconds

Horizon auto-redeploys on every push to `main`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, tools reference, and Prefect Horizon deploy steps"
```

---

## Task 10: Final verification

- [ ] **Step 1: Run full test suite one last time**

```powershell
pytest tests/ -v
```

Expected: All tests `PASSED`, 0 failures, 0 errors.

- [ ] **Step 2: Verify fastmcp version**

```powershell
fastmcp version
```

Expected:
```
FastMCP version: 3.4.2
MCP version:     1.27.2
Python version:  3.12.x
```

- [ ] **Step 3: Check definition of done**

- [ ] Auth loads from `.env` only — grep confirms no hardcoded tokens: `grep -r "Bearer " src/` should only show `f"Bearer {API_TOKEN}"` in `client.py`
- [ ] All tools return Pydantic-validated responses
- [ ] Error handling covers 401, 404, 429, 5xx via `raise_for_status()`
- [ ] `fastmcp inspect` passes for all tools
- [ ] `.env.example` committed with placeholder values
- [ ] README includes setup steps + Claude Desktop config
