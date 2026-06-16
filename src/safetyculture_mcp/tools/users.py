import httpx
from fastmcp import FastMCP
from safetyculture_mcp.client import BASE_URL, HEADERS, raise_for_status
from safetyculture_mcp.models.schemas import User

mcp = FastMCP(name="Users")


@mcp.tool(description="List all users in the SafetyCulture organisation")
async def list_users() -> list[User]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/feed/users",
            headers=HEADERS,
        )
    raise_for_status(resp)
    return [User(**u) for u in resp.json().get("data", [])]


@mcp.tool(description="Search for SafetyCulture users by a list of email addresses")
async def search_users_by_email(emails: list[str]) -> list[User]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/users/search",
            headers=HEADERS,
            json={"email": emails},
        )
    raise_for_status(resp)
    return [User(**u) for u in resp.json().get("users", [])]
