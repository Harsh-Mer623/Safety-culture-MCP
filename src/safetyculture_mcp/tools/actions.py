from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import Action, ActionsPage, CreatedAction, UpdateActionResult

mcp = FastMCP(name="Actions")


# Fixed: the SafetyCulture STATUS task_filter requires status_id (a UUID), not the
# human-readable status_key string — sending status_key caused a 400 Bad Request.
# These UUIDs were confirmed against this org's live action responses (status objects
# always include both status_id and key). They follow SafetyCulture's standard 4-status
# default workflow, but orgs CAN define custom statuses with different IDs — if a
# status_key isn't in this map, the filter is rejected with a clear error rather than
# silently sending a malformed request to the API.
_STATUS_KEY_TO_ID = {
    "TO_DO": "17e793a1-26a3-4ecd-99ca-f38ecc6eaa2e",
    "IN_PROGRESS": "20ce0cb1-387a-47d4-8c34-bc6fd3be0e27",
    "COMPLETE": "7223d809-553e-4714-a038-62dc98f3fbf3",
    "CANT_DO": "06308884-41c2-4ee0-9da7-5676647d3d75",
}


def _status_filter(status_key: str) -> dict:
    status_id = _STATUS_KEY_TO_ID.get(status_key.upper())
    if status_id is None:
        raise ToolError(
            f"Unknown status_key '{status_key}'. Valid values: {', '.join(_STATUS_KEY_TO_ID)}. "
            "If your organisation uses custom statuses, call get_action on a known action "
            "and read its status.status_id/status.key to find the right value."
        )
    return {"type": "STATUS", "status_id": status_id}


@mcp.tool(description=(
    "List actions for the authenticated SafetyCulture account, newest first by default. "
    "Filter by assignee_id (a user's ID, e.g. from search_users_by_email or get_user) to see "
    "only actions assigned to that person. Filter by status_key — one of TO_DO, IN_PROGRESS, "
    "COMPLETE, CANT_DO — to see actions in a specific state. "
    "Returns at most page_size actions (default 20, max 100); if next_page_token is non-null "
    "in the result, more actions exist — call again with page_token set to fetch the next page, "
    "or use list_all_actions to fetch every page automatically. "
    "Sort with sort_field (PRIORITY, DATE_DUE, CREATED_AT, MODIFIED_AT) and sort_direction (ASC/DESC)."
))
async def list_actions(
    ctx: Context,
    page_size: int = 20,
    page_token: str | None = None,
    assignee_id: str | None = None,
    status_key: str | None = None,
    sort_field: str = "CREATED_AT",
    sort_direction: str = "DESC",
) -> ActionsPage:
    body: dict = {
        "page_size": page_size,
        "sort_field": sort_field,
        "sort_direction": sort_direction,
    }
    if page_token:
        body["page_token"] = page_token

    task_filters = []
    if assignee_id:
        task_filters.append({"type": "COLLABORATOR", "collaborator_id": assignee_id})
    if status_key:
        task_filters.append(_status_filter(status_key))  # Fixed: send status_id, not status_key
    if task_filters:
        body["task_filters"] = task_filters

    resp = await request(
        "POST", "/tasks/v1/actions/list",
        headers=get_headers(ctx),
        json=body,
        tool="list_actions",
    )
    raise_for_status(resp)
    data = resp.json()
    return ActionsPage(
        actions=[Action(**a) for a in data.get("actions", [])],
        next_page_token=data.get("next_page_token"),
        total_count=data.get("total_count"),
    )


@mcp.tool(description=(
    "Get full details for a single SafetyCulture action by its task_id (from list_actions/list_all_actions). "
    "Returns title, description, status (key + UUID), priority, due date, site_id, inspection_id, and "
    "collaborators. Note: each collaborator's nested user object only includes firstname/lastname — "
    "use get_user with the collaborator_id to resolve their email."
))
async def get_action(ctx: Context, action_id: str) -> Action:
    resp = await request(
        "GET", f"/tasks/v1/actions/{action_id}",
        headers=get_headers(ctx),
        tool="get_action",
    )
    raise_for_status(resp)
    data = resp.json()
    return Action(**data.get("action", data))


@mcp.tool(description=(
    "Create a new action in the authenticated SafetyCulture account. "
    "title is required; description, due_at, assignee_id, priority_id, status_id, site_id, "
    "and inspection_id are all optional. "
    "Optionally assign to a user by providing assignee_id (a user ID from search_users_by_email "
    "or get_user — not an email address). "
    "due_at must be ISO 8601 format e.g. 2026-12-31T09:00:00Z. "
    "priority_id and status_id are org-specific UUIDs — to find valid values, call list_actions "
    "or get_action on an existing action and read its priority/status objects; new actions "
    "default to your organisation's default status if status_id is omitted."
))
async def create_action(
    ctx: Context,
    title: str,
    description: str = "",
    due_at: str | None = None,
    assignee_id: str | None = None,
    priority_id: str | None = None,
    status_id: str | None = None,
    site_id: str | None = None,
    inspection_id: str | None = None,
) -> CreatedAction:
    body: dict = {"title": title, "description": description}
    if due_at:
        body["due_at"] = due_at
    if priority_id:
        body["priority_id"] = priority_id
    if status_id:
        body["status_id"] = status_id
    if site_id:
        body["site_id"] = site_id
    if inspection_id:
        body["inspection_id"] = inspection_id
    if assignee_id:
        body["collaborators"] = [{"collaborator_id": assignee_id, "role_id": "ASSIGNEE"}]

    resp = await request(
        "POST", "/tasks/v1/actions",
        headers=get_headers(ctx),
        json=body,
        tool="create_action",
    )
    raise_for_status(resp)
    return CreatedAction(**resp.json())


@mcp.tool(description=(
    "Fetch ALL actions matching the given filters by auto-paginating through every page — "
    "use this instead of list_actions whenever you need a complete count or full export rather "
    "than just the first page. Internally requests 100 actions per page and follows "
    "next_page_token until the API reports no more pages, up to a hard cap of max_pages "
    "(default 50, server-enforced max 100 — i.e. up to 10,000 actions total). "
    "Supports the same assignee_id and status_key filters as list_actions (status_key one of "
    "TO_DO, IN_PROGRESS, COMPLETE, CANT_DO). "
    "Returns an ActionsPage with total_count equal to the number of actions actually fetched "
    "(not the org-wide total) and next_page_token always null."
))
async def list_all_actions(
    ctx: Context,
    assignee_id: str | None = None,
    status_key: str | None = None,
    sort_field: str = "CREATED_AT",
    sort_direction: str = "DESC",
    max_pages: int = 50,
) -> ActionsPage:
    # Fixed: hard server-side cap prevents callers from accumulating unbounded memory.
    # At 100 pages × 100 actions each = max 10,000 Action objects. Without this cap,
    # a caller passing max_pages=500 could exhaust MCP process memory on large orgs.
    max_pages = min(max_pages, 100)
    hdrs = get_headers(ctx)
    all_actions: list[Action] = []
    page_token: str | None = None

    for _ in range(max_pages):
        body: dict = {
            "page_size": 100,
            "sort_field": sort_field,
            "sort_direction": sort_direction,
            "without_count": True,
        }
        if page_token:
            body["page_token"] = page_token

        task_filters = []
        if assignee_id:
            task_filters.append({"type": "COLLABORATOR", "collaborator_id": assignee_id})
        if status_key:
            task_filters.append(_status_filter(status_key))  # Fixed: send status_id, not status_key
        if task_filters:
            body["task_filters"] = task_filters

        resp = await request(
            "POST", "/tasks/v1/actions/list",
            headers=hdrs,
            json=body,
            tool="list_all_actions",
        )
        raise_for_status(resp)
        data = resp.json()
        batch = data.get("actions", [])
        all_actions.extend(Action(**a) for a in batch)
        page_token = data.get("next_page_token") or None
        if not page_token or not batch:
            break

    return ActionsPage(actions=all_actions, total_count=len(all_actions))


@mcp.tool(description=(
    "Update one or more fields on an existing SafetyCulture action (identified by action_id, "
    "i.e. its task_id from list_actions/get_action). At least one optional field must be provided. "
    "Only the fields you provide are updated — omitted fields are left unchanged; each provided "
    "field is sent as its own API request, so a partial failure may leave some fields updated "
    "and others not (updated_fields in the result shows what succeeded before any error). "
    "status_id: this org's standard status UUIDs are TO_DO=17e793a1-26a3-4ecd-99ca-f38ecc6eaa2e, "
    "IN_PROGRESS=20ce0cb1-387a-47d4-8c34-bc6fd3be0e27, COMPLETE=7223d809-553e-4714-a038-62dc98f3fbf3, "
    "CANT_DO=06308884-41c2-4ee0-9da7-5676647d3d75 — confirm against get_action if your org uses "
    "custom statuses, since these IDs are not guaranteed across organisations. "
    "assignee_ids: full replacement — send all desired assignee user IDs at once, not just the ones changing. "
    "due_at: ISO 8601 e.g. 2026-12-31T09:00:00Z. Pass empty string to clear the due date."
))
async def update_action(
    ctx: Context,
    action_id: str,
    title: str | None = None,
    description: str | None = None,
    due_at: str | None = None,
    status_id: str | None = None,
    priority_id: str | None = None,
    assignee_ids: list[str] | None = None,
) -> UpdateActionResult:
    if all(f is None for f in [title, description, due_at, status_id, priority_id, assignee_ids]):
        raise ToolError("No fields provided to update. Specify at least one field.")

    hdrs = get_headers(ctx)
    base = f"/tasks/v1/actions/{action_id}"
    updated: list[str] = []

    async def _put(sub_path: str, body: dict, field: str) -> None:
        resp = await request("PUT", f"{base}/{sub_path}", headers=hdrs, json=body, tool=f"update_action_{field}")
        raise_for_status(resp)
        updated.append(field)

    if title is not None:
        await _put("title", {"title": title}, "title")
    if description is not None:
        await _put("description", {"description": description}, "description")
    if due_at is not None:
        # empty string clears the due date; a datetime string sets it
        body = {"due_at": due_at} if due_at else {}
        await _put("due_at", body, "due_at")
    if status_id is not None:
        await _put("status", {"status_id": status_id}, "status")
    if priority_id is not None:
        await _put("priority", {"priority_id": priority_id}, "priority")
    if assignee_ids is not None:
        assignees = [
            {"collaborator_id": uid, "collaborator_type": "USER", "assigned_role": "ASSIGNEE"}
            for uid in assignee_ids
        ]
        await _put("assignees", {"assignees": assignees}, "assignees")

    return UpdateActionResult(action_id=action_id, updated_fields=updated)
