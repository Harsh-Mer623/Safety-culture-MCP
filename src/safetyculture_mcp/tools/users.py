import httpx
from fastmcp import FastMCP, Context
from safetyculture_mcp.client import BASE_URL, TIMEOUT, get_headers, raise_for_status, handle_request_error
from safetyculture_mcp.models.schemas import User

mcp = FastMCP(name="Users")


@mcp.tool(description="List all users in the SafetyCulture organisation")
async def list_users(ctx: Context) -> list[User]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/feed/users",
                headers=get_headers(ctx),
            )
    except Exception as e:
        handle_request_error(e, "list_users")
    raise_for_status(resp)
    return [User(**u) for u in resp.json().get("data", [])]


@mcp.tool(description="Search for SafetyCulture users by a list of email addresses")
async def search_users_by_email(ctx: Context, emails: list[str]) -> list[User]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/users/search",
                headers=get_headers(ctx),
                json={"email": emails},
            )
    except Exception as e:
        handle_request_error(e, "search_users_by_email")
    raise_for_status(resp)
    return [User(**u) for u in resp.json().get("users", [])]
