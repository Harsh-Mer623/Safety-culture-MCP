import json

from fastmcp import FastMCP, Context
from safetyculture_mcp.action_config import DEFAULT_ACTION_PRIORITIES, DEFAULT_ACTION_STATUSES
from safetyculture_mcp.tools.sites import list_sites

mcp = FastMCP(name="OrgConfig")


@mcp.resource(
    "safetyculture://org/statuses",
    name="ActionStatuses",
    description="Standard action status IDs and keys for the authenticated organisation.",
    mime_type="application/json",
)
async def org_action_statuses(ctx: Context) -> str:
    return json.dumps(DEFAULT_ACTION_STATUSES)


@mcp.resource(
    "safetyculture://org/priorities",
    name="ActionPriorities",
    description="Standard action priority IDs and labels for the authenticated organisation.",
    mime_type="application/json",
)
async def org_action_priorities(ctx: Context) -> str:
    return json.dumps(DEFAULT_ACTION_PRIORITIES)


@mcp.resource(
    "safetyculture://org/sites",
    name="OrgSites",
    description="Location-level sites in the authenticated organisation (first page, up to 100).",
    mime_type="application/json",
)
async def org_sites(ctx: Context) -> str:
    page = await list_sites(ctx, page_size=100, only_leaf_nodes=True, with_ancestors=True)
    payload = [
        {
            "id": s.folder.id,
            "name": s.folder.name,
            "meta_label": s.folder.meta_label,
            "ancestors": [{"id": a.id, "name": a.name} for a in s.ancestors],
        }
        for s in page.sites
    ]
    return json.dumps(payload)
