from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class InspectionSummary(_Base):
    audit_id: str
    template_id: str | None = None
    modified_at: str | None = None


class InspectionDetail(_Base):
    id: str
    template_id: str | None = None
    title: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    is_marked_as_complete: bool = False


class Template(_Base):
    template_id: str
    name: str | None = None
    modified_at: str | None = None
    created_at: str | None = None


class ActionStatus(_Base):
    status_id: str | None = None
    key: str | None = None
    label: str | None = None
    display_order: int | None = None


class ActionPriority(_Base):
    priority_id: str | None = None
    label: str | None = None


class ActionTask(_Base):
    task_id: str
    title: str | None = None
    description: str | None = None
    due_at: str | None = None
    status: ActionStatus | None = None
    priority: ActionPriority | None = None


class Action(_Base):
    task: ActionTask


class CreatedAction(_Base):
    action_id: str


class User(_Base):
    id: str
    email: str
    firstname: str | None = None
    lastname: str | None = None
    active: bool = True
