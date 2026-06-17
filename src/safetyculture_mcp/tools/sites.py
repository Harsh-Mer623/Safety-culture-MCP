from fastmcp import FastMCP, Context
from safetyculture_mcp.client import get_headers, raise_for_status, request
from safetyculture_mcp.models.schemas import Site, SiteDetail, SiteWithAncestors, SitesPage

mcp = FastMCP(name="Sites")


def _parse_folder(raw: dict) -> Site:
    return Site(**raw)


def _parse_folder_with_ancestors(entry: dict) -> SiteWithAncestors:
    folder = entry.get("folder", entry)
    ancestors = [_parse_folder(a) for a in entry.get("ancestors", [])]
    return SiteWithAncestors(
        folder=_parse_folder(folder),
        ancestors=ancestors,
        members_count=entry.get("members_count"),
        has_children=entry.get("has_children"),
    )


@mcp.tool(description=(
    "List sites (location folders) in the SafetyCulture organisation. "
    "Returns site id, name, meta_label (e.g. location, area, region), and optional ancestor hierarchy. "
    "Use page_token from the result to fetch subsequent pages. "
    "Set only_leaf_nodes=true (default) to return only location-level sites."
))
async def list_sites(
    ctx: Context,
    page_size: int = 100,
    page_token: str | None = None,
    only_leaf_nodes: bool = True,
    with_ancestors: bool = True,
) -> SitesPage:
    params: dict = {
        "page_size": page_size,
        "only_leaf_nodes": only_leaf_nodes,
        "with_ancestors": with_ancestors,
        "domain": "site",
    }
    if page_token:
        params["page_token"] = page_token

    resp = await request(
        "GET", "/directory/v1/folders",
        headers=get_headers(ctx),
        params=params,
        tool="list_sites",
    )
    raise_for_status(resp)
    data = resp.json()

    ancestor_entries = data.get("folders_with_ancestors")
    if with_ancestors and ancestor_entries:
        sites = [_parse_folder_with_ancestors(f) for f in ancestor_entries]
    else:
        raw_folders = data.get("folders", [])
        if with_ancestors and raw_folders and isinstance(raw_folders[0], dict) and "folder" in raw_folders[0]:
            sites = [_parse_folder_with_ancestors(f) for f in raw_folders]
        else:
            sites = [
                SiteWithAncestors(folder=_parse_folder(f), ancestors=[])
                for f in raw_folders
            ]

    return SitesPage(
        sites=sites,
        next_page_token=data.get("next_page_token") or None,
        total_count=None,
    )


@mcp.tool(description=(
    "Search sites (folders) by name or partial name. "
    "Returns matching sites with optional ancestor hierarchy. "
    "Set only_leaf_nodes=true to restrict to location-level sites only."
))
async def search_sites(
    ctx: Context,
    query: str,
    limit: int = 50,
    page_token: str | None = None,
    only_leaf_nodes: bool = True,
) -> SitesPage:
    body: dict = {
        "query": query,
        "limit": limit,
        "only_leaf_nodes": only_leaf_nodes,
        "domain": "site",
    }
    if page_token:
        body["page_token"] = page_token

    resp = await request(
        "POST", "/directory/v1/folders/search",
        headers=get_headers(ctx),
        json=body,
        tool="search_sites",
    )
    raise_for_status(resp)
    data = resp.json()
    sites = [_parse_folder_with_ancestors(f) for f in data.get("folders", [])]
    return SitesPage(
        sites=sites,
        next_page_token=data.get("next_page_token") or None,
        total_count=data.get("folder_count"),
    )


@mcp.tool(description=(
    "Get full details for a single site (folder) by its ID, including optional ancestor hierarchy."
))
async def get_site(
    ctx: Context,
    site_id: str,
    with_ancestors: bool = True,
) -> SiteDetail:
    resp = await request(
        "GET", f"/directory/v1/folder/{site_id}",
        headers=get_headers(ctx),
        params={"with_ancestors": with_ancestors},
        tool="get_site",
    )
    raise_for_status(resp)
    data = resp.json()
    folder = data.get("folder", data)
    ancestors = [_parse_folder(a) for a in data.get("ancestors", [])]
    return SiteDetail(
        folder=_parse_folder(folder),
        ancestors=ancestors,
        member_count=data.get("member_count"),
    )
