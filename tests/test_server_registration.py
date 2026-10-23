import pytest
from salt_mcp.server import create_server

@pytest.mark.asyncio
async def test_fastmcp_server_tools_registered():
    mcp = create_server()
    # List tools from FastMCP instance
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]

    expected_tools = [
        "salt_ping",
        "salt_get_grains",
        "salt_get_pillar",
        "salt_list_keys",
        "salt_manage_key",
        "salt_run_command",
        "salt_run_module",
        "salt_apply_state",
        "salt_list_jobs",
        "salt_get_job",
        "salt_manage_schedule",
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names, f"Tool '{tool_name}' is not registered in FastMCP server"
