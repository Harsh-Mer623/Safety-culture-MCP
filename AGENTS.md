# SafetyCulture MCP Server — Agent Instructions

## What You Are Building
A production-grade MCP server for SafetyCulture using FastMCP, Pydantic v2, and httpx.
Target deployment: Prefect Horizon.

---

## Step 0 — Read These Before Writing Any Code

Fetch both URLs at session start. Do not rely on training data for either.

```
https://gofastmcp.com/llms.txt                   → FastMCP patterns, tools, deployment
https://developer.safetyculture.com/llms.txt      → SafetyCulture API endpoints, schemas, auth
```

---

## When You Are Stuck or Uncertain

**Do not guess. Do one of these instead:**

1. Search the web: `"FastMCP [problem] June 2026"` or `"SafetyCulture API [endpoint] example"`
2. Fetch the relevant doc page from `developer.safetyculture.com/reference`
3. Ask a clarifying question before proceeding

Never invent an API endpoint. If you cannot verify it, stop and ask.

---

## Tech Stack

| Layer | Tool |
|---|---|
| MCP framework | FastMCP (latest) |
| HTTP client | httpx (async) |
| Validation | Pydantic v2 |
| Python | 3.12+ |
| Package manager | uv (mandatory — FastMCP requires it internally) |
| Deployment | Prefect Horizon |

---

## Required Versions

| Tool | Required Version | Notes |
|---|---|---|
| Python | 3.12.x | 3.10–3.13 supported; 3.12 is most tested with FastMCP |
| FastMCP | 3.4.2 | Latest stable (June 6 2026). Do NOT use 3.4.0/3.4.1 betas |
| MCP SDK | 1.27.2 | Installed automatically by FastMCP |
| httpx | >=0.27.0 | Async support required |
| pydantic | >=2.0.0 | v1 is incompatible |
| pip | latest | Upgrade pip first before installing anything |

---

## Environment Setup

Use Python's built-in `venv` + `pip`. No uv required.

**Important pip gotcha from official FastMCP docs:** Never run `pip install -U fastmcp` to upgrade from an older version — it can corrupt the install. Always use `pip install --force-reinstall fastmcp==3.4.2` if upgrading. For fresh installs (which this is), plain pip works fine.

```bash
# Step 1 — Check Python version (must be 3.12.x)
python3 --version
# If not 3.12, download from https://python.org/downloads and install manually

# Step 2 — Create virtual environment
python3.12 -m venv .venv

# Step 3 — Activate virtual environment
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

# Step 4 — Upgrade pip first (mandatory)
pip install --upgrade pip

# Step 5 — Install pinned dependencies
pip install "fastmcp==3.4.2" "httpx>=0.27.0" "pydantic>=2.0.0" python-dotenv

# Step 6 — Verify all versions
fastmcp version
# Expected output:
# FastMCP version: 3.4.2
# MCP version:     1.27.2
# Python version:  3.12.x

pip show fastmcp httpx pydantic
```

`requirements.txt` must include:
```
fastmcp==3.4.2
httpx>=0.27.0
pydantic>=2.0.0
python-dotenv
```

`pyproject.toml` must include:
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

To add packages: always `pip install <package>` inside the activated venv, then add to `requirements.txt`.

---

## Project Structure

```
safetyculture-mcp/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .env                          # gitignored
├── .env.example                  # committed, no real values
├── src/
│   └── safetyculture_mcp/
│       ├── __init__.py
│       ├── server.py             # FastMCP app entry point
│       ├── client.py             # httpx SafetyCulture API client + auth
│       ├── tools/
│       │   ├── inspections.py
│       │   ├── actions.py
│       │   ├── templates.py
│       │   └── users.py
│       └── models/
│           └── schemas.py        # Pydantic v2 models
└── tests/
    └── test_tools.py
```

---

## Auth

SafetyCulture uses Bearer token auth. Always load from environment.

```python
# client.py
import os
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.environ["SAFETYCULTURE_API_TOKEN"]
BASE_URL = "https://api.safetyculture.io"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}
```

`.env.example` (commit this, never `.env`):
```
SAFETYCULTURE_API_TOKEN=your_token_here
```

---

## Tool Writing Rules

- Every `@mcp.tool` must have a `description=` — the AI uses this to pick which tool to call
- Use Pydantic v2 models for all inputs and outputs — no raw dicts
- Use `async` httpx for all API calls
- Handle errors explicitly: 401, 404, 429, 5xx
- Use `mcp.tool` for anything that reads or writes data. Use `mcp.resource` only for static/config data

### ✅ Correct Pattern

```python
from fastmcp import FastMCP
import httpx
from pydantic import BaseModel
from .client import BASE_URL, HEADERS

mcp = FastMCP(name="SafetyCulture MCP")

class Inspection(BaseModel):
    id: str
    name: str
    status: str

@mcp.tool(description="List inspections for the authenticated SafetyCulture account")
async def list_inspections(limit: int = 20) -> list[Inspection]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/audits/search",
            headers=HEADERS,
            params={"limit": limit}
        )
        resp.raise_for_status()
        return [Inspection(**i) for i in resp.json().get("audits", [])]
```

### ❌ Avoid These

```python
# No description on tool — agent won't know when to call it
@mcp.tool
async def list_inspections(): ...

# Raw dict return — not validated
return resp.json()

# Requests library — use httpx async only
import requests

# Hardcoded token
HEADERS = {"Authorization": "Bearer abc123"}

# Invented endpoint not in SafetyCulture docs
resp = await client.get(f"{BASE_URL}/inspections/list")
```

---

## Build Order

Build one step at a time. Test before moving to the next.

1. `client.py` — verify auth with one raw httpx call: `GET /feed/v2/accounts/me`
2. `tools/inspections.py` — list + get inspection
3. `tools/templates.py` — list templates
4. `tools/actions.py` — list + create action
5. `tools/users.py` — list users
6. `server.py` — import all tools, expose `mcp.run()`
7. Test all tools with `fastmcp inspect`
8. Deploy to Prefect Horizon

---

## Testing Each Tool

After each tool file, run:
```bash
fastmcp inspect src/safetyculture_mcp/server.py
```
This opens a browser UI. Call the tool manually. Confirm real API response before continuing.

For a single tool file (faster):
```bash
uv run python -c "from src.safetyculture_mcp.tools.inspections import *"
```

---

## Permissions

### Do without asking
- Read any file
- Run `fastmcp inspect` on a single file
- Run a single test: `uv run pytest tests/test_tools.py::test_list_inspections`

### Ask before doing
- `uv add` any new package
- Delete any file
- `git push` or `git commit`
- Run full test suite
- Deploy to Prefect Horizon

---

## Troubleshooting

| Problem | Fix |
|---|---|
| 401 Unauthorized | Check `.env` has correct `SAFETYCULTURE_API_TOKEN` |
| Endpoint 404 | Verify endpoint at `developer.safetyculture.com/reference` — do not guess |
| `fastmcp inspect` not found | Run `uv add fastmcp` and ensure venv is active |
| Pydantic validation error | Check field names against actual API response JSON |
| `uv` not found | Re-run install command, restart terminal |

If none of these fix it: search web for `"FastMCP [error] June 2026"` before asking.

---

## Definition of Done

- [ ] Auth loads from `.env` only — no hardcoded tokens anywhere
- [ ] All tools return Pydantic-validated responses
- [ ] Error handling covers 401, 404, 429, 5xx
- [ ] `fastmcp inspect` passes for all tools with real API responses
- [ ] `.env.example` committed with placeholder values
- [ ] README includes setup steps + Claude Desktop config example
- [ ] Deployed and live on Prefect Horizon