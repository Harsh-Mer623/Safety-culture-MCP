from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    action_id: str

    @model_validator(mode="before")
    @classmethod
    def _normalize_action_id(cls, data: object) -> object:
        if isinstance(data, dict) and not data.get("action_id"):
            alt = data.get("task_id") or data.get("id")
            if alt:
                return {**data, "action_id": alt}
        return data


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
    id: str
    email: str
    firstname: str | None = None
    lastname: str | None = None
    active: bool = True
    role: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_user_id(cls, data: object) -> object:
        if isinstance(data, dict) and not data.get("id") and data.get("user_id"):
            return {**data, "id": data["user_id"]}
        return data


# ── Action configuration ──────────────────────────────────────────────────────

class ActionStatusInfo(_Base):
    status_id: str
    key: str | None = None
    label: str | None = None
    is_complete: bool = False


class ActionPriorityInfo(_Base):
    priority_id: str
    label: str | None = None


class ActionLabel(_Base):
    label_id: str
    label_name: str | None = None


class DeleteActionResult(_Base):
    deleted_ids: list[str]


class AddCommentResult(_Base):
    task_id: str
    comment: str


# ── Sites (directory folders) ─────────────────────────────────────────────────

class Site(_Base):
    id: str
    name: str | None = None
    meta_label: str | None = None
    org_id: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    members_count: int | None = None
    deleted: bool = False


class SiteWithAncestors(_Base):
    folder: Site
    ancestors: list[Site] = []
    members_count: int | None = None
    has_children: bool | None = None


class SitesPage(_Base):
    sites: list[SiteWithAncestors] = []
    next_page_token: str | None = None
    total_count: int | None = None


class SiteDetail(_Base):
    folder: Site
    ancestors: list[Site] = []
    member_count: int | None = None


# ── Groups ────────────────────────────────────────────────────────────────────

class Group(_Base):
    id: str
    name: str | None = None


class GroupUser(_Base):
    user_id: str
    email: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    status: str | None = None


class GroupUsersPage(_Base):
    users: list[GroupUser] = []
    total: int | None = None
    offset: int | None = None
    limit: int | None = None


# ── Composite query results ─────────────────────────────────────────────────────

class UserActionSummary(_Base):
    user_id: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    email: str | None = None
    action_count: int = 0
    action_ids: list[str] = Field(default_factory=list)


# ── Inspections (extended) ────────────────────────────────────────────────────

class InspectionIdentity(_Base):
    inspection_id: str
    organisation_id: str | None = None


class CreatedInspection(_Base):
    inspection_id: str
    organisation_id: str | None = None


class InspectionAnswer(_Base):
    question_id: str | None = None
    modified_at: str | None = None
    # Type-specific answer payloads — extra fields ignored at parse time
    text_answer: dict | None = None
    question_answer: dict | None = None
    checkbox_answer: dict | None = None
    list_answer: dict | None = None
    datetime_answer: dict | None = None
    media_answer: dict | None = None
    site_answer: dict | None = None
    table_answer: dict | None = None


class InspectionExportResult(_Base):
    url: str | None = None
    status: str | None = None


class InspectionMutationResult(_Base):
    inspection_id: str


# ── Templates (extended) ────────────────────────────────────────────────────────

class TemplateDetail(_Base):
    template_id: str | None = None
    name: str | None = None
    description: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    archived: bool = False


class TemplateDefinition(_Base):
    """Structural template definition — only known fields are modelled; extras ignored."""
    template_id: str | None = None
    name: str | None = None
    items: list[dict] = []
