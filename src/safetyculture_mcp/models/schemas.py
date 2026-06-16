from pydantic import BaseModel


class InspectionSummary(BaseModel):
    audit_id: str
    template_id: str | None = None
    modified_at: str | None = None


class InspectionDetail(BaseModel):
    id: str
    template_id: str | None = None
    title: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    is_marked_as_complete: bool = False


class Template(BaseModel):
    template_id: str
    name: str | None = None
    modified_at: str | None = None
    created_at: str | None = None


class ActionTask(BaseModel):
    task_id: str
    title: str | None = None
    description: str | None = None
    due_at: str | None = None
    status: str | None = None
    priority_id: str | None = None


class Action(BaseModel):
    task: ActionTask


class CreatedAction(BaseModel):
    action_id: str


class User(BaseModel):
    id: str
    email: str
    firstname: str | None = None
    lastname: str | None = None
    active: bool = True
