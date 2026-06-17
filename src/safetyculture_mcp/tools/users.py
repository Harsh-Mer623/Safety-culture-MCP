from fastmcp import FastMCP, Context
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import User

mcp = FastMCP(name="Users")


@mcp.tool(description=(
    "List all users in the SafetyCulture organisation. No filtering, sorting, or pagination "
    "parameters — returns every user in a single response, which may be slow or memory-heavy "
    "for very large organisations. To look up one specific person, prefer search_users_by_email "
    "(if you know their email) or get_user (if you already have their user ID, e.g. a "
    "collaborator_id from an action)."
))
async def list_users(ctx: Context) -> list[User]:
    resp = await request(
        "GET", "/feed/users",
        headers=get_headers(ctx),
        tool="list_users",
    )
    raise_for_status(resp)
    return [User(**u) for u in resp.json().get("data", [])]


@mcp.tool(description=(
    "Search for SafetyCulture users by exact email address. Pass one or more addresses in "
    "emails — addresses with no matching user are simply omitted from the results (no error). "
    "Returns each matched user's id, email, firstname, lastname, active, and role."
))
async def search_users_by_email(ctx: Context, emails: list[str]) -> list[User]:
    resp = await request(
        "POST", "/users/search",
        headers=get_headers(ctx),
        json={"email": emails},
        tool="search_users_by_email",
    )
    raise_for_status(resp)
    return [User(**u) for u in resp.json().get("users", [])]


@mcp.tool(description=(
    "Get full details (email, firstname, lastname) for a single user by their user ID. "
    "Useful for resolving a collaborator_id from an action's collaborators list — "
    "the nested user object on actions only includes firstname/lastname, not id or email."
))
async def get_user(ctx: Context, user_id: str) -> User:
    resp = await request(
        "GET", f"/users/{user_id}",
        headers=get_headers(ctx),
        tool="get_user",
    )
    raise_for_status(resp)
    return User(**resp.json())
