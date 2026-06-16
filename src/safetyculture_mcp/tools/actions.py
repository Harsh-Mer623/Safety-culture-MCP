import httpx
from fastmcp import FastMCP, Context
from safetyculture_mcp.client import BASE_URL, TIMEOUT, get_headers, raise_for_status, handle_request_error
from safetyculture_mcp.models.schemas import Action, CreatedAction

mcp = FastMCP(name="Actions")


@mcp.tool(description="List actions for the authenticated SafetyCulture account")
async def list_actions(ctx: Context, page_size: int = 20) -> list[Action]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/tasks/v1/actions/list",
                headers=get_headers(ctx),
                json={"page_size": page_size},
            )
    except Exception as e:
        handle_request_error(e, "list_actions")
    raise_for_status(resp)
    return [Action(**a) for a in resp.json().get("actions", [])]


@mcp.tool(description="Get full details for a single SafetyCulture action by ID")
async def get_action(ctx: Context, action_id: str) -> Action:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/tasks/v1/actions/{action_id}",
                headers=get_headers(ctx),
            )
    except Exception as e:
        handle_request_error(e, "get_action")
    raise_for_status(resp)
    return Action(**resp.json()["action"])


@mcp.tool(description="Create a new action in the authenticated SafetyCulture account")
async def create_action(
    ctx: Context,
    title: str,
    description: str = "",
    due_at: str | None = None,
) -> CreatedAction:
    body: dict = {"title": title, "description": description}
    if due_at is not None:
        body["due_at"] = due_at
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/tasks/v1/actions",
                headers=get_headers(ctx),
                json=body,
            )
    except Exception as e:
        handle_request_error(e, "create_action")
    raise_for_status(resp)
    return CreatedAction(**resp.json())
