import httpx
from fastmcp import FastMCP
from safetyculture_mcp.client import BASE_URL, HEADERS, raise_for_status
from safetyculture_mcp.models.schemas import Action, CreatedAction

mcp = FastMCP(name="Actions")


@mcp.tool(description="List actions for the authenticated SafetyCulture account")
async def list_actions(page_size: int = 20) -> list[Action]:
    # List actions uses POST, not GET
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
