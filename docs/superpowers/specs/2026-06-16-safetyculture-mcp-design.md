# SafetyCulture MCP Server — Design Spec

**Date:** 2026-06-16  
**Status:** Approved  
**Stack:** FastMCP 3.4.2 · httpx async · Pydantic v2 · Python 3.12 · pip + venv  
**Target deployment:** Prefect Horizon

---

## 1. Goal

Build a production-grade MCP server that exposes SafetyCulture's REST API as callable tools for LLM clients (Claude Desktop, Claude Code, Cursor, etc.). The server must handle auth, validation, and error cases cleanly, and be deployable to Prefect Horizon with a single GitHub push.

---

## 2. Architecture

```
server.py (FastMCP entry point)
  └── mounts:
      ├── tools/inspections.py  (FastMCP sub-app)
      ├── tools/templates.py    (FastMCP sub-app)
      ├── tools/actions.py      (FastMCP sub-app)
      └── tools/users.py        (FastMCP sub-app)
              ↓ all import from
          client.py             (BASE_URL, HEADERS, raise_for_status)
          models/schemas.py     (Pydantic v2 models)
              ↓ HTTP calls to
          api.safetyculture.io
```

Each tool module creates its own `FastMCP` sub-app. `server.py` mounts all sub-apps onto the root app using `main.mount(child)`. This avoids circular imports, keeps domains isolated, and lets FastMCP propagate tools dynamically to the parent.

---

## 3. Project Structure

```
safetyculture-mcp/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env                          # gitignored
├── .env.example                  # committed, placeholder values only
├── src/
│   └── safetyculture_mcp/
│       ├── __init__.py
│       ├── server.py             # root FastMCP app, mounts sub-apps, entry point
│       ├── client.py             # BASE_URL, HEADERS, raise_for_status helper
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── inspections.py    # FastMCP sub-app with inspection tools
│       │   ├── actions.py        # FastMCP sub-app with action tools
│       │   ├── templates.py      # FastMCP sub-app with template tools
│       │   └── users.py          # FastMCP sub-app with user tools
│       └── models/
│           ├── __init__.py
│           └── schemas.py        # all Pydantic v2 models
└── tests/
    └── test_tools.py
```

---

## 4. Authentication

SafetyCulture uses Bearer token auth. The token is loaded once at module import from `.env`:

```python
# client.py
import os
import httpx
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.environ["SAFETYCULTURE_API_TOKEN"]
BASE_URL = "https://api.safetyculture.io"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}
```

**Auth verification (build step 1):** `GET /feed/v2/accounts/me` — confirms the token is valid before writing any tool.

`.env.example` (committed, no real values):
```
SAFETYCULTURE_API_TOKEN=your_token_here
```

---

## 5. Error Handling

A shared helper in `client.py` maps HTTP status codes to descriptive errors. FastMCP tools raise `ToolError` (from `fastmcp.exceptions`) so the error message reaches the LLM client without exposing raw HTTP details:

```python
from fastmcp.exceptions import ToolError

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

All tool functions wrap their httpx calls in try/except and call `raise_for_status(resp)` before parsing JSON.

---

## 6. Pydantic Models (schemas.py)

All models use Pydantic v2. Optional fields default to `None` to handle API responses where fields may be absent.

```python
from pydantic import BaseModel

# --- Inspections ---
class InspectionSummary(BaseModel):
    audit_id: str
    template_id: str | None = None
    modified_at: str | None = None

class InspectionPermissions(BaseModel):
    canView: bool = False
    canEdit: bool = False
    canDelete: bool = False

class InspectionDetail(BaseModel):
    id: str
    template_id: str | None = None
    title: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    is_marked_as_complete: bool = False

# --- Templates ---
class Template(BaseModel):
    template_id: str
    name: str | None = None
    modified_at: str | None = None
    created_at: str | None = None

# --- Actions ---
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

# --- Users ---
class User(BaseModel):
    id: str
    email: str
    firstname: str | None = None
    lastname: str | None = None
    active: bool = True
```

---

## 7. Tool Modules

Each module creates a `FastMCP` sub-app and registers `@mcp.tool` functions on it. Descriptions are set via the `description=` decorator argument (not docstrings) per AGENTS.md convention.

### 7.1 tools/inspections.py

**Endpoints used:**
- `GET /audits/search` — params: `limit` (int), `archived` (bool), `completed` (bool)
- `GET /inspections/v1/inspections/{id}`

**Tools:**
| Tool | Description |
|---|---|
| `list_inspections(limit, archived, completed)` | List inspections for the authenticated account |
| `get_inspection(inspection_id)` | Get full detail for a single inspection by ID |

**API note:** `/audits/search` returns `{"count": int, "total": int, "audits": [...]}`. Each audit in the list is an `InspectionSummary`. `get_inspection` returns `{"inspection": {...}}` mapped to `InspectionDetail`.

### 7.2 tools/templates.py

**Endpoints used:**
- `GET /templates/search` — params: `limit` (int), `archived` (bool)

**Tools:**
| Tool | Description |
|---|---|
| `list_templates(limit, archived)` | List templates for the authenticated account |

**API note:** Returns `{"count": int, "total": int, "templates": [...]}`.

### 7.3 tools/actions.py

**Endpoints used:**
- `POST /tasks/v1/actions/list` — body: `{"page_size": int, "task_filters": []}`
- `GET /tasks/v1/actions/{id}`
- `POST /tasks/v1/actions` — body: `{"title": str, "description": str, "due_at": str, "collaborators": [...]}`

**Important:** List actions is a `POST` endpoint, not `GET`. Using `GET` returns 404.

**Tools:**
| Tool | Description |
|---|---|
| `list_actions(page_size)` | List actions for the authenticated account |
| `get_action(action_id)` | Get full detail for a single action by ID |
| `create_action(title, description, due_at)` | Create a new action |

**API note:** List response is `{"actions": [{task, custom_field_and_values, type}], "next_page_token": str}`. Create returns `{"action_id": str}`.

### 7.4 tools/users.py

**Endpoints used:**
- `GET /feed/users` — returns paginated feed of all users
- `POST /users/search` — body: `{"email": [str, ...]}` — search by email

**Tools:**
| Tool | Description |
|---|---|
| `list_users()` | List all users in the organisation (paginated feed) |
| `search_users_by_email(emails)` | Search for users by a list of email addresses |

---

## 8. server.py (Entry Point)

Uses FastMCP `mount()` to compose all sub-apps onto the root. This is a live connection — tools added to child apps after mounting are immediately visible through the parent:

```python
from fastmcp import FastMCP
from safetyculture_mcp.tools.inspections import mcp as inspections_mcp
from safetyculture_mcp.tools.actions import mcp as actions_mcp
from safetyculture_mcp.tools.templates import mcp as templates_mcp
from safetyculture_mcp.tools.users import mcp as users_mcp

mcp = FastMCP(name="SafetyCulture MCP")

mcp.mount(inspections_mcp)
mcp.mount(actions_mcp)
mcp.mount(templates_mcp)
mcp.mount(users_mcp)

if __name__ == "__main__":
    mcp.run()
```

**Prefect Horizon entrypoint:** `src/safetyculture_mcp/server.py:mcp`

---

## 9. FastMCP Tool Pattern

Per FastMCP 3.4.2 docs and AGENTS.md rules:

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
import httpx
from ..client import BASE_URL, HEADERS, raise_for_status
from ..models.schemas import InspectionSummary

mcp = FastMCP(name="Inspections")

@mcp.tool(description="List inspections for the authenticated SafetyCulture account")
async def list_inspections(limit: int = 20, archived: bool = False) -> list[InspectionSummary]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/audits/search",
            headers=HEADERS,
            params={"limit": limit, "archived": archived},
        )
        raise_for_status(resp)
        return [InspectionSummary(**a) for a in resp.json().get("audits", [])]
```

Rules enforced:
- All tools are `async`
- All tools have `description=` set
- All inputs/outputs use Pydantic models — no raw dicts
- httpx `AsyncClient` used as context manager per request
- `raise_for_status()` called before parsing JSON
- No hardcoded tokens

---

## 10. Build & Test Order

Per AGENTS.md build order — one step at a time, test before advancing:

1. `client.py` — verify auth: `GET /feed/v2/accounts/me`
2. `models/schemas.py` — all Pydantic models
3. `tools/inspections.py` — `list_inspections` + `get_inspection`
4. `tools/templates.py` — `list_templates`
5. `tools/actions.py` — `list_actions` + `get_action` + `create_action`
6. `tools/users.py` — `list_users` + `search_users_by_email`
7. `server.py` — mount all sub-apps
8. `fastmcp inspect src/safetyculture_mcp/server.py:mcp` — verify all tools visible
9. `tests/test_tools.py` — httpx mock transport tests
10. Deploy to Prefect Horizon

**Test command after each tool file:**
```bash
fastmcp inspect src/safetyculture_mcp/server.py
```

---

## 11. Testing

`tests/test_tools.py` uses `pytest` + `httpx.MockTransport` to stub API responses without a live token. Tests cover: happy path, 401, 404, 429, 500.

---

## 12. Prefect Horizon Deployment

Prerequisites: GitHub repo, `requirements.txt` or `pyproject.toml` present.

1. Push code to GitHub (main branch)
2. Visit [horizon.prefect.io](https://horizon.prefect.io), authenticate with GitHub
3. Grant Horizon access to the repository
4. Set **entrypoint**: `src/safetyculture_mcp/server.py:mcp`
5. Set **server name** (determines URL: `https://<name>.fastmcp.app/mcp`)
6. Click Deploy — live in ~60 seconds
7. Test via Inspector and ChatMCP on the Horizon dashboard

Horizon auto-redeploys on every push to `main`.

---

## 13. Dependencies

**requirements.txt:**
```
fastmcp==3.4.2
httpx>=0.27.0
pydantic>=2.0.0
python-dotenv
```

**pyproject.toml:**
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

---

## 14. Definition of Done

- [ ] Auth loads from `.env` only — no hardcoded tokens anywhere
- [ ] All tools return Pydantic-validated responses
- [ ] Error handling covers 401, 404, 429, 5xx via `raise_for_status()`
- [ ] `fastmcp inspect` passes for all tools with real API responses
- [ ] `.env.example` committed with placeholder values
- [ ] README includes setup steps + Claude Desktop config example
- [ ] Deployed and live on Prefect Horizon
