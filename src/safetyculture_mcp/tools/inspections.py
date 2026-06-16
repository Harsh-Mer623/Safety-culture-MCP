import httpx
from fastmcp import FastMCP
from safetyculture_mcp.client import BASE_URL, HEADERS, raise_for_status
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
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/audits/search",
            headers=HEADERS,
            params=params,
        )
    raise_for_status(resp)
    return [InspectionSummary(**a) for a in resp.json().get("audits", [])]


@mcp.tool(description="Get full details for a single SafetyCulture inspection by ID")
async def get_inspection(inspection_id: str) -> InspectionDetail:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/inspections/v1/inspections/{inspection_id}",
            headers=HEADERS,
        )
    raise_for_status(resp)
    return InspectionDetail(**resp.json()["inspection"])
