import logging
import os
from contextlib import asynccontextmanager

from safetyculture_mcp.logging_config import configure_logging

configure_logging()

_log = logging.getLogger(__name__)

# Warn early so misconfiguration surfaces before the first tool call rather
# than producing a cryptic error mid-conversation.
if not os.environ.get("SAFETYCULTURE_API_TOKEN"):
    _log.warning(
        "startup_token_missing",
        extra={
            "detail": (
                "SAFETYCULTURE_API_TOKEN is not set. "
                "Tools will work only if callers pass the x-safetyculture-token header."
            )
        },
    )

from fastmcp import FastMCP
from safetyculture_mcp.client import aclose_http_client
from safetyculture_mcp.tools.inspections import mcp as inspections_mcp
from safetyculture_mcp.tools.actions import mcp as actions_mcp
from safetyculture_mcp.tools.templates import mcp as templates_mcp
from safetyculture_mcp.tools.users import mcp as users_mcp
from safetyculture_mcp.tools.health import mcp as health_mcp
from safetyculture_mcp.tools.sites import mcp as sites_mcp
from safetyculture_mcp.tools.groups import mcp as groups_mcp
from safetyculture_mcp.tools.composite import mcp as composite_mcp
from safetyculture_mcp.resources.org_config import mcp as org_config_mcp


# Fixed: replaced atexit-based shutdown with FastMCP lifespan so aclose() runs
# in a live async context — atexit fired outside the event loop on Python 3.12+.
@asynccontextmanager
async def _sc_lifespan(server):
    yield
    await aclose_http_client()


mcp = FastMCP(name="SafetyCulture MCP", lifespan=_sc_lifespan)

mcp.mount(inspections_mcp)
mcp.mount(actions_mcp)
mcp.mount(templates_mcp)
mcp.mount(users_mcp)
mcp.mount(health_mcp)
mcp.mount(sites_mcp)
mcp.mount(groups_mcp)
mcp.mount(composite_mcp)
mcp.mount(org_config_mcp)

if __name__ == "__main__":
    mcp.run()
