from fastmcp import FastMCP, Context
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import InspectionSummary, InspectionDetail

mcp = FastMCP(name="Inspections")


@mcp.tool(description=(
    "List inspections for the authenticated SafetyCulture account. "
    "Filter by date range, template, completion status, or archive status. "
    "Returns audit_id, template_id, and modified_at for each inspection."
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
    "Get full details for a single SafetyCulture inspection by ID. "
    "Returns title, score, site, owner, assignees, conducted_on, duration, and completion status."
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
