import logging
import os

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
from safetyculture_mcp.tools.inspections import mcp as inspections_mcp
from safetyculture_mcp.tools.actions import mcp as actions_mcp
from safetyculture_mcp.tools.templates import mcp as templates_mcp
from safetyculture_mcp.tools.users import mcp as users_mcp
from safetyculture_mcp.tools.health import mcp as health_mcp

mcp = FastMCP(name="SafetyCulture MCP")

mcp.mount(inspections_mcp)
mcp.mount(actions_mcp)
mcp.mount(templates_mcp)
mcp.mount(users_mcp)
mcp.mount(health_mcp)

if __name__ == "__main__":
    mcp.run()
