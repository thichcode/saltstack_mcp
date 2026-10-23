from __future__ import annotations

from typing import Optional
from mcp.server.fastmcp import FastMCP

from salt_mcp.config import SaltMcpConfig, load_config
from salt_mcp.audit import AuditLogger
from salt_mcp.safety import SafetyGuard
from salt_mcp.salt_adapter import SaltAdapter
from salt_mcp.tools.discovery import create_discovery_tools
from salt_mcp.tools.keys import create_key_tools
from salt_mcp.tools.execution import create_execution_tools
from salt_mcp.tools.state import create_state_tools
from salt_mcp.tools.jobs import create_job_tools
from salt_mcp.tools.schedule import create_schedule_tools


def create_server(
    config: Optional[SaltMcpConfig] = None,
    adapter: Optional[SaltAdapter] = None,
) -> FastMCP:
    """Builds and configures the SaltStack FastMCP Server."""
    cfg = config or load_config()
    audit = AuditLogger(log_file=cfg.audit.log_file, enabled=cfg.audit.enabled)
    guard = SafetyGuard(config=cfg, audit=audit)
    salt_adapter = adapter or SaltAdapter()

    mcp = FastMCP(
        name="salt-mcp",
        instructions="SaltStack Master MCP Server for querying, automating, and safely managing Salt infrastructure.",
    )

    # Register all tools
    all_tool_factories = [
        create_discovery_tools,
        create_key_tools,
        create_execution_tools,
        create_state_tools,
        create_job_tools,
        create_schedule_tools,
    ]

    for factory in all_tool_factories:
        tools = factory(salt_adapter, guard)
        for tool_name, tool_fn in tools.items():
            mcp.add_tool(tool_fn, name=tool_name)

    return mcp
