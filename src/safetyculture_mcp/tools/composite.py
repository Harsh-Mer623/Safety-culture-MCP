from typing import Literal

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from safetyculture_mcp.action_config import build_assignee_filter, build_status_filter
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import Action, ActionsPage, UserActionSummary
from safetyculture_mcp.tools.actions import list_all_actions
from safetyculture_mcp.tools.users import search_users_by_email

mcp = FastMCP(name="Composite")

StatusKey = Literal["TO_DO", "IN_PROGRESS", "COMPLETE", "CANT_DO"]


def _collaborator_name(collab: dict) -> tuple[str | None, str | None, str | None]:
    """Return (collaborator_id, firstname, lastname) for a USER assignee."""
    if collab.get("collaborator_type") != "USER":
        return None, None, None
    cid = collab.get("collaborator_id")
    user = collab.get("user") or {}
    return cid, user.get("firstname"), user.get("lastname")


@mcp.tool(description=(
    "List users who have action items assigned to them with a given status (default TO_DO). "
    "Returns each user's name, collaborator_id, and how many matching actions they have. "
    "This is a composite tool — use it instead of manually joining list_actions with user lookups. "
    "status_key: one of TO_DO, IN_PROGRESS, COMPLETE, CANT_DO."
))
async def list_users_with_actions(
    ctx: Context,
    status_key: StatusKey = "TO_DO",
    max_pages: int = 50,
) -> list[UserActionSummary]:
    page = await list_all_actions(ctx, status_key=status_key, max_pages=max_pages)

    # Aggregate by USER assignee collaborator_id (plain dicts — avoid mutating Pydantic models)
    by_user: dict[str, dict] = {}
    for action in page.actions:
        task = action.task
        status = task.status
        if status and status.key and status.key != status_key:
            continue
        for collab in task.collaborators:
            cid, first, last = _collaborator_name(
                collab.model_dump() if hasattr(collab, "model_dump") else collab
            )
            if not cid:
                continue
            if cid not in by_user:
                by_user[cid] = {
                    "user_id": cid,
                    "firstname": first,
                    "lastname": last,
                    "action_ids": [],
                }
            entry = by_user[cid]
            entry["action_ids"].append(task.task_id)
            if first and not entry["firstname"]:
                entry["firstname"] = first
            if last and not entry["lastname"]:
                entry["lastname"] = last

    summaries = [
        UserActionSummary(
            user_id=e["user_id"],
            firstname=e["firstname"],
            lastname=e["lastname"],
            action_count=len(e["action_ids"]),
            action_ids=e["action_ids"],
        )
        for e in by_user.values()
    ]
    return sorted(summaries, key=lambda u: (-u.action_count, u.lastname or ""))


@mcp.tool(description=(
    "Search actions assigned to a user by their email address. "
    "Resolves the email to a user ID, then lists actions filtered to that assignee. "
    "Optionally filter by status_key (TO_DO, IN_PROGRESS, COMPLETE, CANT_DO). "
    "Returns a paginated ActionsPage (first page only — use page_token for more)."
))
async def search_actions_by_assignee_email(
    ctx: Context,
    email: str,
    status_key: StatusKey | None = None,
    page_size: int = 50,
    page_token: str | None = None,
) -> ActionsPage:
    users = await search_users_by_email(ctx, [email])
    if not users:
        raise ToolError(f"No user found with email '{email}'.")

    assignee_id = users[0].id
    body: dict = {
        "page_size": page_size,
        "sort_field": "CREATED_AT",
        "sort_direction": "DESC",
    }
    if page_token:
        body["page_token"] = page_token

    task_filters = [build_assignee_filter(assignee_id)]
    if status_key:
        task_filters.append(build_status_filter(status_key))
    body["task_filters"] = task_filters

    resp = await request(
        "POST", "/tasks/v1/actions/list",
        headers=get_headers(ctx),
        json=body,
        tool="search_actions_by_assignee_email",
    )
    raise_for_status(resp)
    data = resp.json()
    return ActionsPage(
        actions=[Action(**a) for a in data.get("actions", [])],
        next_page_token=data.get("next_page_token") or None,
        total_count=data.get("total_count"),
    )
