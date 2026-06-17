from fastmcp import FastMCP, Context
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import User

mcp = FastMCP(name="Users")


@mcp.tool(description="List all users in the SafetyCulture organisation")
async def list_users(ctx: Context) -> list[User]:
    resp = await request(
        "GET", "/feed/users",
        headers=get_headers(ctx),
        tool="list_users",
    )
    raise_for_status(resp)
    return [User(**u) for u in resp.json().get("data", [])]


@mcp.tool(description="Search for SafetyCulture users by a list of email addresses")
async def search_users_by_email(ctx: Context, emails: list[str]) -> list[User]:
    resp = await request(
        "POST", "/users/search",
        headers=get_headers(ctx),
        json={"email": emails},
        tool="search_users_by_email",
    )
    raise_for_status(resp)
    return [User(**u) for u in resp.json().get("users", [])]
