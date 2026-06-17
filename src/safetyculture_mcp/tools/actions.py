from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import Action, ActionsPage, CreatedAction, UpdateActionResult

mcp = FastMCP(name="Actions")


@mcp.tool(description=(
    "List actions for the authenticated SafetyCulture account. "
    "Filter by assignee_id (user ID) to get actions for a specific person. "
    "Filter by status_key (TO_DO, IN_PROGRESS, DONE). "
    "Supports pagination via page_token returned in next_page_token. "
    "Sort by PRIORITY, DATE_DUE, CREATED_AT, or MODIFIED_AT."
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
        task_filters.append({"type": "STATUS", "status_key": status_key})
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
    "Get full details for a single SafetyCulture action by ID. "
    "Returns title, description, status, priority, assignees (collaborators), due date, site, and inspection link."
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
    "Optionally assign to a user by providing assignee_id (user ID). "
    "due_at must be ISO 8601 format e.g. 2026-12-31T09:00:00Z. "
    "priority_id and status_id can be obtained from your organisation's action settings."
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
    "Fetch ALL actions for the account by auto-paginating through every page "
    "(up to max_pages × 100 actions). Useful for bulk exports or full-account audits. "
    "Supports the same assignee_id and status_key filters as list_actions. "
    "Returns an ActionsPage with total_count equal to the number of actions fetched."
))
async def list_all_actions(
    ctx: Context,
    assignee_id: str | None = None,
    status_key: str | None = None,
    sort_field: str = "CREATED_AT",
    sort_direction: str = "DESC",
    max_pages: int = 50,
) -> ActionsPage:
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
            task_filters.append({"type": "STATUS", "status_key": status_key})
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
    "Update one or more fields on an existing SafetyCulture action. "
    "Only the fields you provide will be updated — omitted fields are left unchanged. "
    "status_id: use a known UUID (To Do: 17e793a1-26a3-4ecd-99ca-f38ecc6eaa2e, "
    "In Progress: 20ce0cb1-387a-47d4-8c34-bc6fd3be0e27, "
    "Complete: 7223d809-553e-4714-a038-62dc98f3fbf3, "
    "Can't Do: 06308884-41c2-4ee0-9da7-5676647d3d75). "
    "assignee_ids: full replacement — send all desired assignee user IDs at once. "
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
