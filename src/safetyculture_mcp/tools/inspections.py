from typing import Any, Literal

from fastmcp import FastMCP, Context
from safetyculture_mcp.client import get_headers, raise_for_status, request, stream_json_objects
from safetyculture_mcp.models.schemas import (
    CreatedInspection,
    InspectionAnswer,
    InspectionDetail,
    InspectionExportResult,
    InspectionMutationResult,
    InspectionSummary,
)

mcp = FastMCP(name="Inspections")

ExportType = Literal["DOCUMENT_TYPE_PDF", "DOCUMENT_TYPE_WORD"]


@mcp.tool(description=(
    "List inspections (audits) for the authenticated SafetyCulture account, most recently "
    "modified first by default (order='desc'; pass 'asc' to reverse). "
    "limit caps the number of results returned (default 20) — there is no page_token; "
    "for large result sets narrow with modified_after/modified_before or template_ids instead. "
    "Filter by modified_after/modified_before (ISO 8601, e.g. 2026-01-01T00:00:00Z), "
    "template_ids (list of template_id from list_templates), completed (true/false), "
    "and archived (default false — set true to include archived inspections). "
    "Returns only summary fields per inspection (audit_id, template_id, modified_at) — "
    "call get_inspection for full details."
))
async def list_inspections(
    ctx: Context,
    limit: int = 20,
    archived: bool = False,
    completed: bool | None = None,
    modified_after: str | None = None,
    modified_before: str | None = None,
    template_ids: list[str] | None = None,
    order: str = "desc",
) -> list[InspectionSummary]:
    params: dict = {"limit": limit, "archived": archived, "order": order}
    if completed is not None:
        params["completed"] = completed
    if modified_after is not None:
        params["modified_after"] = modified_after
    if modified_before is not None:
        params["modified_before"] = modified_before
    if template_ids:
        params["template"] = template_ids

    resp = await request(
        "GET", "/audits/search",
        headers=get_headers(ctx),
        params=params,
        tool="list_inspections",
    )
    raise_for_status(resp)
    return [InspectionSummary(**a) for a in resp.json().get("audits", [])]


@mcp.tool(description=(
    "Get full details for a single SafetyCulture inspection by its audit_id "
    "(from list_inspections). Returns title, template_id, score (percentage/value/max_value), "
    "site, owner, created_by, assignees, created_at, conducted_on, duration (seconds), "
    "is_marked_as_complete, and status."
))
async def get_inspection(ctx: Context, inspection_id: str) -> InspectionDetail:
    resp = await request(
        "GET", f"/inspections/v1/inspections/{inspection_id}",
        headers=get_headers(ctx),
        tool="get_inspection",
    )
    raise_for_status(resp)
    data = resp.json()
    return InspectionDetail(**data.get("inspection", data))


@mcp.tool(description=(
    "Create a new inspection from a template_id (from list_templates). "
    "Optionally pre-fill item values via items — each item needs item_id and item_type "
    "matching the template structure (use get_template_definition to discover item_ids). "
    "Returns the new inspection_id."
))
async def create_inspection(
    ctx: Context,
    template_id: str,
    items: list[dict[str, Any]] | None = None,
) -> CreatedInspection:
    body: dict = {"template_id": template_id}
    if items:
        body["items"] = items

    resp = await request(
        "POST", "/inspections/integration/v1/inspections",
        headers=get_headers(ctx),
        json=body,
        tool="create_inspection",
    )
    raise_for_status(resp)
    data = resp.json()
    identity = data.get("inspection_identity", data)
    return CreatedInspection(
        inspection_id=identity.get("inspection_id", ""),
        organisation_id=identity.get("organisation_id"),
    )


@mcp.tool(description=(
    "Get all answers/responses for an inspection by its audit_id. "
    "Parses the SafetyCulture streaming answers API into a list of answer objects. "
    "Each answer includes question_id and type-specific answer fields "
    "(text_answer, question_answer, checkbox_answer, etc.)."
))
async def get_inspection_answers(ctx: Context, inspection_id: str) -> list[InspectionAnswer]:
    raw = await stream_json_objects(
        "GET", f"/inspections/v1/answers/{inspection_id}",
        headers=get_headers(ctx),
        tool="get_inspection_answers",
    )
    return [InspectionAnswer(**a) for a in raw]


@mcp.tool(description=(
    "Update item values on an existing inspection. "
    "Only items listed in the request are changed — omitted items are left untouched. "
    "Each item needs item_id and item_type (use get_template_definition to discover structure). "
    "See SafetyCulture InspectionItem types: TEXT, NUMBER, CHECKBOX, QUESTION, etc."
))
async def update_inspection(
    ctx: Context,
    inspection_id: str,
    items: list[dict[str, Any]],
) -> InspectionMutationResult:
    resp = await request(
        "PUT", f"/inspections/integration/v1/inspections/{inspection_id}",
        headers=get_headers(ctx),
        json={"items": items},
        tool="update_inspection",
    )
    raise_for_status(resp)
    data = resp.json()
    identity = data.get("inspection_identity", {})
    return InspectionMutationResult(
        inspection_id=identity.get("inspection_id", inspection_id),
    )


@mcp.tool(description=(
    "Mark an inspection as complete. All required template questions must be answered first — "
    "use get_inspection_answers to verify before calling. "
    "If the template has an approval page, the inspection moves to Awaiting approval instead of Complete."
))
async def complete_inspection(ctx: Context, inspection_id: str) -> InspectionMutationResult:
    resp = await request(
        "POST", f"/inspections/integration/v1/inspections/{inspection_id}/complete",
        headers=get_headers(ctx),
        json={},
        tool="complete_inspection",
    )
    raise_for_status(resp)
    data = resp.json()
    identity = data.get("inspection_identity", {})
    return InspectionMutationResult(
        inspection_id=identity.get("inspection_id", inspection_id),
    )


@mcp.tool(description=(
    "Archive an inspection by its audit_id. Archived inspections are hidden from default list_inspections "
    "results unless archived=true is passed."
))
async def archive_inspection(ctx: Context, inspection_id: str) -> InspectionMutationResult:
    resp = await request(
        "POST", f"/inspections/v1/inspections/{inspection_id}/archive",
        headers=get_headers(ctx),
        json={},
        tool="archive_inspection",
    )
    raise_for_status(resp)
    data = resp.json()
    return InspectionMutationResult(inspection_id=data.get("inspection_id", inspection_id))


@mcp.tool(description=(
    "Restore an archived inspection by its audit_id (removes archived status)."
))
async def restore_inspection(ctx: Context, inspection_id: str) -> InspectionMutationResult:
    resp = await request(
        "DELETE", f"/inspections/v1/inspections/{inspection_id}/archive",
        headers=get_headers(ctx),
        tool="restore_inspection",
    )
    raise_for_status(resp)
    data = resp.json()
    return InspectionMutationResult(inspection_id=data.get("inspection_id", inspection_id))


@mcp.tool(description=(
    "Export an inspection to PDF or Word. "
    "Returns export status and download url when status is STATUS_DONE. "
    "If status is STATUS_IN_PROGRESS, retry after a short delay. "
    "document_type: DOCUMENT_TYPE_PDF (default) or DOCUMENT_TYPE_WORD."
))
async def export_inspection_pdf(
    ctx: Context,
    inspection_id: str,
    document_type: ExportType = "DOCUMENT_TYPE_PDF",
) -> InspectionExportResult:
    body = {
        "export_data": [{"inspection_id": inspection_id}],
        "type": document_type,
    }
    resp = await request(
        "POST", "/inspection/v1/export",
        headers=get_headers(ctx),
        json=body,
        tool="export_inspection_pdf",
    )
    raise_for_status(resp)
    data = resp.json()
    return InspectionExportResult(url=data.get("url"), status=data.get("status"))
