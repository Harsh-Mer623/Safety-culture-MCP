# SafetyCulture MCP Server

A FastMCP 3.4.2 server exposing SafetyCulture inspections, actions, templates, and users as MCP tools.

## Setup

```powershell
# Activate venv
.venv\Scripts\Activate.ps1

# Install deps
pip install -r requirements.txt
pip install -e .

# Configure
cp .env.example .env
# Edit .env: set SAFETYCULTURE_API_TOKEN=your_token_here
```

## Verify auth

```powershell
python -c "
import asyncio, httpx
async def check():
    async with httpx.AsyncClient() as c:
        r = await c.get(
            'https://api.safetyculture.io/accounts/user/v1/user:WhoAmI',
            headers={'Authorization': 'Bearer YOUR_TOKEN'}
        )
        print(r.status_code, r.json())
asyncio.run(check())
"
```

## Run tests

```powershell
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Inspect tools locally

```powershell
fastmcp inspect src/safetyculture_mcp/server.py:mcp
```

## Available Tools

| Tool | Description |
|---|---|
| `list_inspections` | List inspections (limit, archived, completed) |
| `get_inspection` | Get inspection detail by ID |
| `list_templates` | List templates (limit, archived) |
| `list_actions` | List actions (page_size) |
| `get_action` | Get action detail by ID |
| `create_action` | Create a new action (title, description, due_at) |
| `list_all_actions` | Auto-paginate all actions (up to max_pages × 100, server cap 100 pages) |
| `update_action` | Update fields on an existing action (title, description, status, due_at, assignees) |
| `list_users` | List all users in the organisation |
| `search_users_by_email` | Search users by email addresses |
| `whoami` | Return the authenticated user's profile |

## Claude Desktop config

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

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

1. Push repo to GitHub
2. Go to [horizon.prefect.io](https://horizon.prefect.io) → authenticate with GitHub
3. Select your repo, set entrypoint: `src/safetyculture_mcp/server.py:mcp`
4. Click Deploy — live at `https://<name>.fastmcp.app/mcp` in ~60s

Auto-redeploys on every push to `main`.
