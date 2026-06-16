import httpx
from fastmcp import FastMCP
from safetyculture_mcp.client import BASE_URL, HEADERS, raise_for_status
from safetyculture_mcp.models.schemas import Template

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
