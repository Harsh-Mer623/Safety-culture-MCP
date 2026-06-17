from fastmcp import FastMCP, Context
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import Template

mcp = FastMCP(name="Templates")


@mcp.tool(description=(
    "List templates for the authenticated SafetyCulture account. "
    "Returns template_id, name, description, created_at, modified_at, and archived status."
))
async def list_templates(
    ctx: Context,
    limit: int = 20,
    archived: bool = False,
) -> list[Template]:
    resp = await request(
        "GET", "/templates/search",
        headers=get_headers(ctx),
        params={"limit": limit, "archived": archived},
        tool="list_templates",
    )
    raise_for_status(resp)
    return [Template(**t) for t in resp.json().get("templates", [])]
