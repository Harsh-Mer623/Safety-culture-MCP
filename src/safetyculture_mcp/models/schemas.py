from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── Shared refs ───────────────────────────────────────────────────────────────

class PersonRef(_Base):
    id: str | None = None
    name: str | None = None
    email: str | None = None
    firstname: str | None = None
    lastname: str | None = None


class SiteRef(_Base):
    site_id: str | None = None
    name: str | None = None


# ── Inspections ───────────────────────────────────────────────────────────────

class InspectionSummary(_Base):
    audit_id: str  # UNVERIFIED: confirm field name against live API response — may be "id"
    template_id: str | None = None
    modified_at: str | None = None


class InspectionScore(_Base):
    percentage: float | None = None
    value: float | None = None
    max_value: float | None = None


class InspectionDetail(_Base):
    id: str  # UNVERIFIED: confirm field name against live API response — may be "audit_id"
    template_id: str | None = None
    title: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    conducted_on: str | None = None
    duration: int | None = None
    is_marked_as_complete: bool = False
    status: str | None = None
    score: InspectionScore | None = None
    site: SiteRef | None = None
    owner: PersonRef | None = None
    created_by: PersonRef | None = None
    assignees: list[PersonRef] = []


# ── Templates ─────────────────────────────────────────────────────────────────

class Template(_Base):
    template_id: str
    name: str | None = None
    description: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    archived: bool = False


# ── Actions ───────────────────────────────────────────────────────────────────

class ActionStatus(_Base):
    status_id: str | None = None
    key: str | None = None
    label: str | None = None
    display_order: int | None = None


class ActionPriority(_Base):
    priority_id: str | None = None
    label: str | None = None


class CollaboratorUser(_Base):
    id: str | None = None
    email: str | None = None
    firstname: str | None = None
    lastname: str | None = None


class Collaborator(_Base):
    collaborator_id: str | None = None
    collaborator_type: str | None = None
    assigned_role: str | None = None
    user: CollaboratorUser | None = None


class ActionTask(_Base):
    task_id: str  # UNVERIFIED: confirm field name against live API response
    title: str | None = None
    description: str | None = None
    due_at: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    status: ActionStatus | None = None
    priority: ActionPriority | None = None
    collaborators: list[Collaborator] = []
    site_id: str | None = None
    inspection_id: str | None = None


class Action(_Base):
    task: ActionTask


class ActionsPage(_Base):
    actions: list[Action] = []
    next_page_token: str | None = None
    total_count: int | None = None


class CreatedAction(_Base):
    action_id: str  # UNVERIFIED: confirm field name against live API response — may be "id" or "task_id"


class UpdateActionResult(_Base):
    action_id: str
    updated_fields: list[str]


# ── Health ────────────────────────────────────────────────────────────────────

class WhoAmIResponse(_Base):
    # Confirmed against live API response for a service-account token (2026-06-17).
    # For service accounts: organisation_id holds a "role_..." value, and email holds
    # a UUID placeholder instead of a real address — this is real API behavior, not a bug.
    # `id`, `active`, `role` are not present in the service-account response; kept
    # optional in case human-user tokens return a different shape.
    user_id: str | None = None
    id: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    email: str | None = None
    active: bool = True
    role: str | None = None
    organisation_id: str | None = None


# ── Users ─────────────────────────────────────────────────────────────────────

class User(_Base):
    id: str  # UNVERIFIED: confirm field name against live API response
    email: str
    firstname: str | None = None
    lastname: str | None = None
    active: bool = True
    role: str | None = None
