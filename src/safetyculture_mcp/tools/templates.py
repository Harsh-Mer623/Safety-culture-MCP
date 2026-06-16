import httpx
from fastmcp import FastMCP
from safetyculture_mcp.client import BASE_URL, TIMEOUT, get_headers, raise_for_status, handle_request_error
from safetyculture_mcp.models.schemas import Template

mcp = FastMCP(name="Templates")


@mcp.tool(description="List templates for the authenticated SafetyCulture account")
async def list_templates(
    limit: int = 20,
    archived: bool = False,
) -> list[Template]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/templates/search",
                headers=get_headers(),
                params={"limit": limit, "archived": archived},
            )
    except Exception as e:
        handle_request_error(e, "list_templates")
    raise_for_status(resp)
    return [Template(**t) for t in resp.json().get("templates", [])]
