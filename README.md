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
| `get_user` | Get user details by ID |
| `whoami` | Return the authenticated user's profile |

### Action configuration
| Tool | Description |
|---|---|
| `list_action_statuses` | List standard action status IDs and keys |
| `list_action_priorities` | List standard action priority IDs |
| `list_action_labels` | List org action labels |
| `delete_action` | Bulk-delete actions by ID |
| `add_action_comment` | Add a timeline comment to an action |

### Sites & groups
| Tool | Description |
|---|---|
| `list_sites` | List location-level sites (paginated) |
| `search_sites` | Search sites by name |
| `get_site` | Get site details with ancestors |
| `list_groups` | List all groups |
| `list_users_in_group` | List users in a group |

### Inspections (extended)
| Tool | Description |
|---|---|
| `create_inspection` | Create inspection from template |
| `get_inspection_answers` | Get all Q&A responses |
| `update_inspection` | Update inspection item values |
| `complete_inspection` | Mark inspection complete |
| `archive_inspection` | Archive an inspection |
| `restore_inspection` | Restore archived inspection |
| `export_inspection_pdf` | Export inspection to PDF/Word |

### Templates (extended)
| Tool | Description |
|---|---|
| `get_template` | Get single template metadata |
| `get_template_definition` | Get template structure for prefilling |

### Composite queries
| Tool | Description |
|---|---|
| `list_users_with_actions` | Users with actions in a given status |
| `search_actions_by_assignee_email` | Actions for a user by email |

### MCP resources
| URI | Description |
|---|---|
| `safetyculture://org/statuses` | Action status reference |
| `safetyculture://org/priorities` | Action priority reference |
| `safetyculture://org/sites` | Org sites (first page) |

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
