from typing import Literal

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from safetyculture_mcp.action_config import (
    DEFAULT_ACTION_PRIORITIES,
    DEFAULT_ACTION_STATUSES,
    build_assignee_filter,
    build_status_filter,
)
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import (
    Action,
    ActionLabel,
    ActionPriorityInfo,
    ActionStatusInfo,
    ActionsPage,
    AddCommentResult,
    CreatedAction,
    DeleteActionResult,
    UpdateActionResult,
)

mcp = FastMCP(name="Actions")

SortField = Literal["PRIORITY", "DATE_DUE", "CREATED_AT", "MODIFIED_AT"]
SortDirection = Literal["ASC", "DESC"]
StatusKey = Literal["TO_DO", "IN_PROGRESS", "COMPLETE", "CANT_DO"]


def _parse_actions_page(data: dict) -> ActionsPage:
    return ActionsPage(
        actions=[Action(**a) for a in data.get("actions", [])],
        next_page_token=data.get("next_page_token") or None,
        total_count=data.get("total_count"),
    )


@mcp.tool(description=(
    "List the standard action status values for SafetyCulture (status_id, key, label, is_complete). "
    "Use status_key with list_actions/list_all_actions filters, and status_id with create_action/update_action. "
    "Labels may be customised per organisation but IDs are typically the documented defaults."
))
async def list_action_statuses(ctx: Context) -> list[ActionStatusInfo]:
    return [ActionStatusInfo(**s) for s in DEFAULT_ACTION_STATUSES]


@mcp.tool(description=(
    "List the standard action priority values (priority_id and label). "
    "Use priority_id with create_action and update_action."
))
async def list_action_priorities(ctx: Context) -> list[ActionPriorityInfo]:
    return [ActionPriorityInfo(**p) for p in DEFAULT_ACTION_PRIORITIES]


@mcp.tool(description=(
    "List all action labels configured in the organisation. "
    "Returns label_id and label_name for each label."
))
async def list_action_labels(ctx: Context) -> list[ActionLabel]:
    resp = await request(
        "GET", "/tasks/v1/customer_configuration/action_labels",
        headers=get_headers(ctx),
        tool="list_action_labels",
    )
    raise_for_status(resp)
    return [ActionLabel(**lbl) for lbl in resp.json().get("labels", [])]


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
    status_key: StatusKey | None = None,
    sort_field: SortField = "CREATED_AT",
    sort_direction: SortDirection = "DESC",
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
        task_filters.append(build_assignee_filter(assignee_id))
    if status_key:
        task_filters.append(build_status_filter(status_key))
    if task_filters:
        body["task_filters"] = task_filters

    resp = await request(
        "POST", "/tasks/v1/actions/list",
        headers=get_headers(ctx),
        json=body,
        tool="list_actions",
    )
    raise_for_status(resp)
    return _parse_actions_page(resp.json())


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
    "Call list_action_priorities and list_action_statuses for valid priority_id and status_id values."
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
        body["collaborators"] = [
            {
                "collaborator_id": assignee_id,
                "collaborator_type": "USER",
                "assigned_role": "ASSIGNEE",
            }
        ]

    resp = await request(
        "POST", "/tasks/v1/actions",
        headers=get_headers(ctx),
        json=body,
        tool="create_action",
    )
    raise_for_status(resp)
    data = resp.json()
    action_id = data.get("action_id") or data.get("task_id") or data.get("id")
    if not action_id:
        raise ToolError("Create action succeeded but response contained no action_id.")
    return CreatedAction(action_id=action_id)


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
    status_key: StatusKey | None = None,
    sort_field: SortField = "CREATED_AT",
    sort_direction: SortDirection = "DESC",
    max_pages: int = 50,
) -> ActionsPage:
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
            task_filters.append(build_assignee_filter(assignee_id))
        if status_key:
            task_filters.append(build_status_filter(status_key))
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
    "Only the fields you provide are updated — omitted fields are left unchanged. "
    "Call list_action_statuses and list_action_priorities for valid status_id and priority_id values. "
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


@mcp.tool(description=(
    "Delete one or more SafetyCulture actions by task_id (bulk delete). "
    "Pass a single ID or multiple IDs in action_ids."
))
async def delete_action(ctx: Context, action_ids: list[str]) -> DeleteActionResult:
    if not action_ids:
        raise ToolError("action_ids must contain at least one action ID.")
    resp = await request(
        "POST", "/tasks/v1/actions/delete",
        headers=get_headers(ctx),
        json={"ids": action_ids},
        tool="delete_action",
    )
    raise_for_status(resp)
    return DeleteActionResult(deleted_ids=action_ids)


@mcp.tool(description=(
    "Add a comment to an action's timeline. "
    "task_id is the action's task_id from list_actions/get_action."
))
async def add_action_comment(
    ctx: Context,
    action_id: str,
    comment: str,
) -> AddCommentResult:
    resp = await request(
        "POST", "/tasks/v1/timeline/comments",
        headers=get_headers(ctx),
        json={"task_id": action_id, "comment": comment},
        tool="add_action_comment",
    )
    raise_for_status(resp)
    return AddCommentResult(task_id=action_id, comment=comment)
