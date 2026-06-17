from fastmcp import FastMCP, Context
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import Group, GroupUser, GroupUsersPage

mcp = FastMCP(name="Groups")


@mcp.tool(description=(
    "List all groups in the SafetyCulture organisation. "
    "Returns each group's id and name. Requires Platform management: Groups permission."
))
async def list_groups(ctx: Context) -> list[Group]:
    resp = await request(
        "GET", "/groups",
        headers=get_headers(ctx),
        tool="list_groups",
    )
    raise_for_status(resp)
    return [Group(**g) for g in resp.json().get("groups", [])]


@mcp.tool(description=(
    "List users in a SafetyCulture group by group_id (from list_groups). "
    "Supports pagination via limit and offset. "
    "Filter by status: active or inactive."
))
async def list_users_in_group(
    ctx: Context,
    group_id: str,
    limit: int = 200,
    offset: int = 0,
    status: list[str] | None = None,
) -> GroupUsersPage:
    params: dict = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status

    resp = await request(
        "GET", f"/groups/{group_id}/users",
        headers=get_headers(ctx),
        params=params,
        tool="list_users_in_group",
    )
    raise_for_status(resp)
    data = resp.json()
    users = [
        GroupUser(
            user_id=u.get("user_id", u.get("id", "")),
            email=u.get("email"),
            firstname=u.get("firstname"),
            lastname=u.get("lastname"),
            status=u.get("status"),
        )
        for u in data.get("users", [])
    ]
    return GroupUsersPage(
        users=users,
        total=data.get("total"),
        offset=data.get("offset"),
        limit=data.get("limit"),
    )
