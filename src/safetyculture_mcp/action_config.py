"""Action status/priority constants and task-filter builders.

Status and priority UUIDs are documented defaults from:
https://developer.safetyculture.com/reference/actions.md

Organisations may customise status labels but typically keep the same IDs.
Call list_action_statuses or get_action on a known action to confirm IDs.
"""

from fastmcp.exceptions import ToolError

# Documented default action statuses (key → status_id)
DEFAULT_ACTION_STATUSES: list[dict[str, str | int | bool]] = [
    {
        "status_id": "17e793a1-26a3-4ecd-99ca-f38ecc6eaa2e",
        "key": "TO_DO",
        "label": "To do",
        "is_complete": False,
    },
    {
        "status_id": "20ce0cb1-387a-47d4-8c34-bc6fd3be0e27",
        "key": "IN_PROGRESS",
        "label": "In progress",
        "is_complete": False,
    },
    {
        "status_id": "7223d809-553e-4714-a038-62dc98f3fbf3",
        "key": "COMPLETE",
        "label": "Complete",
        "is_complete": True,
    },
    {
        "status_id": "06308884-41c2-4ee0-9da7-5676647d3d75",
        "key": "CANT_DO",
        "label": "Can't do",
        "is_complete": True,
    },
]

# Documented default action priorities (priority_id → label)
DEFAULT_ACTION_PRIORITIES: list[dict[str, str]] = [
    {"priority_id": "58941717-817f-4c7c-a6f6-5cd05e2bbfde", "label": "None"},
    {"priority_id": "16ba4717-adc9-4d48-bf7c-044cfe0d2727", "label": "Low"},
    {"priority_id": "ce87c58a-eeb2-4fde-9dc4-c6e85f1f4055", "label": "Medium"},
    {"priority_id": "02eb40c1-4f46-40c5-be16-d32941c96ec9", "label": "High"},
]

_STATUS_KEY_TO_ID = {s["key"]: s["status_id"] for s in DEFAULT_ACTION_STATUSES}


def resolve_status_id(status_key: str) -> str:
    status_id = _STATUS_KEY_TO_ID.get(status_key.upper())
    if status_id is None:
        valid = ", ".join(_STATUS_KEY_TO_ID)
        raise ToolError(
            f"Unknown status_key '{status_key}'. Valid values: {valid}. "
            "Call list_action_statuses for IDs, or get_action on a known action."
        )
    return status_id


def build_status_filter(status_key: str) -> dict:
    """Build a TaskFilter object for POST /tasks/v1/actions/list."""
    return {"status_id": {"value": [resolve_status_id(status_key)]}}


def build_assignee_filter(assignee_id: str) -> dict:
    """Build a TaskFilter object filtering by USER assignee."""
    return {
        "collaborator": {
            "value": [
                {
                    "collaborator_id": assignee_id,
                    "collaborator_type": "USER",
                    "assigned_role": "ASSIGNEE",
                }
            ]
        }
    }
