import httpx
from fastmcp import FastMCP
from safetyculture_mcp.client import BASE_URL, TIMEOUT, get_headers, raise_for_status, handle_request_error
from safetyculture_mcp.models.schemas import InspectionSummary, InspectionDetail

mcp = FastMCP(name="Inspections")


@mcp.tool(description="List inspections for the authenticated SafetyCulture account")
async def list_inspections(
    limit: int = 20,
    archived: bool = False,
    completed: bool | None = None,
) -> list[InspectionSummary]:
    params: dict = {"limit": limit, "archived": archived}
    if completed is not None:
        params["completed"] = completed
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/audits/search",
                headers=get_headers(),
                params=params,
            )
    except Exception as e:
        handle_request_error(e, "list_inspections")
    raise_for_status(resp)
    return [InspectionSummary(**a) for a in resp.json().get("audits", [])]


@mcp.tool(description="Get full details for a single SafetyCulture inspection by ID")
async def get_inspection(inspection_id: str) -> InspectionDetail:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/inspections/v1/inspections/{inspection_id}",
                headers=get_headers(),
            )
    except Exception as e:
        handle_request_error(e, "get_inspection")
    raise_for_status(resp)
    return InspectionDetail(**resp.json()["inspection"])
