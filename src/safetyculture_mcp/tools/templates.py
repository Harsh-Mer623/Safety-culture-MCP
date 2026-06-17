from fastmcp import FastMCP, Context
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import Template, TemplateDefinition, TemplateDetail

mcp = FastMCP(name="Templates")


@mcp.tool(description=(
    "List inspection templates for the authenticated SafetyCulture account. "
    "limit caps the number of results returned (default 20, no pagination support). "
    "archived defaults to false — set true to include archived templates. "
    "Returns template_id, name, description, created_at, modified_at, and archived status "
    "for each template — use template_id with list_inspections(template_ids=[...]) to filter "
    "inspections to a specific template."
))
async def list_templates(
    ctx: Context,
    limit: int = 20,
    archived: bool = False,
) -> list[Template]:
    resp = await request(
        "GET", "/templates/search",
        headers=get_headers(ctx),
        params={"limit": limit, "archived": archived},
        tool="list_templates",
    )
    raise_for_status(resp)
    return [Template(**t) for t in resp.json().get("templates", [])]


@mcp.tool(description=(
    "Get metadata for a single template by template_id (from list_templates). "
    "Returns template_id, name, description, created_at, modified_at, and archived status."
))
async def get_template(ctx: Context, template_id: str) -> TemplateDetail:
    resp = await request(
        "GET", f"/templates/v1/templates/{template_id}",
        headers=get_headers(ctx),
        tool="get_template",
    )
    raise_for_status(resp)
    data = resp.json()
    tmpl = data.get("template", data)
    return TemplateDetail(
        template_id=tmpl.get("template_id", tmpl.get("id", template_id)),
        name=tmpl.get("name"),
        description=tmpl.get("description"),
        created_at=tmpl.get("created_at"),
        modified_at=tmpl.get("modified_at"),
        archived=tmpl.get("archived", False),
    )


@mcp.tool(description=(
    "Get the structural definition of a template — item hierarchy, item types, and response sets. "
    "Use this before create_inspection or update_inspection to discover item_id values for pre-filling answers. "
    "For table items, child item_ids are the column field_ids required by table line operations."
))
async def get_template_definition(ctx: Context, template_id: str) -> TemplateDefinition:
    resp = await request(
        "GET", f"/templates/integration/v1/templates/{template_id}/definition",
        headers=get_headers(ctx),
        tool="get_template_definition",
    )
    raise_for_status(resp)
    data = resp.json()
    definition = data.get("definition", data)
    return TemplateDefinition(
        template_id=definition.get("template_id", template_id),
        name=definition.get("name"),
        items=definition.get("items", []),
    )
