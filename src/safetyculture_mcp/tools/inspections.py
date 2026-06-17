from fastmcp import FastMCP, Context
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import InspectionSummary, InspectionDetail

mcp = FastMCP(name="Inspections")


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
