from fastmcp import FastMCP
from safetyculture_mcp.tools.inspections import mcp as inspections_mcp
from safetyculture_mcp.tools.actions import mcp as actions_mcp
from safetyculture_mcp.tools.templates import mcp as templates_mcp
from safetyculture_mcp.tools.users import mcp as users_mcp

mcp = FastMCP(name="SafetyCulture MCP")

mcp.mount(inspections_mcp)
mcp.mount(actions_mcp)
mcp.mount(templates_mcp)
mcp.mount(users_mcp)

if __name__ == "__main__":
    mcp.run()
