from fastmcp import FastMCP, Context
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import WhoAmIResponse

mcp = FastMCP(name="Health")


@mcp.tool(description=(
    "Verify that the SafetyCulture API token is valid and return the authenticated user's details. "
    "Useful for confirming your token works before running other tools. "
    "Returns user id, name, email, role, and organisation_id."
))
async def whoami(ctx: Context) -> WhoAmIResponse:
    resp = await request(
        "GET", "/accounts/user/v1/user:WhoAmI",
        headers=get_headers(ctx),
        tool="whoami",
    )
    raise_for_status(resp)
    return WhoAmIResponse(**resp.json())
