import pytest
from unittest.mock import AsyncMock, MagicMock
from salt_mcp.tools.discovery import create_discovery_tools
from salt_mcp.tools.keys import create_key_tools

@pytest.fixture
def mock_context():
    adapter = MagicMock()
    adapter.cmd = AsyncMock()
    adapter.list_keys = AsyncMock()
    adapter.manage_key = AsyncMock()

    guard = MagicMock()
    guard.check_operation_allowed.return_value = (True, "")
    guard.check_target.return_value = (True, "")
    guard.check_key_action.return_value = (True, "")

    audit = MagicMock()
    guard.audit = audit

    return adapter, guard, audit

@pytest.mark.asyncio
async def test_salt_ping(mock_context):
    adapter, guard, audit = mock_context
    adapter.cmd.return_value = {"web1": True, "web2": True}

    tools = create_discovery_tools(adapter, guard)
    res = await tools["salt_ping"](tgt="*")

    assert res == {"web1": True, "web2": True}
    adapter.cmd.assert_called_once_with(tgt="*", fun="test.ping", tgt_type="glob", timeout=60)
    audit.log_event.assert_called()

@pytest.mark.asyncio
async def test_salt_get_grains(mock_context):
    adapter, guard, audit = mock_context
    adapter.cmd.return_value = {"web1": {"os": "Ubuntu", "osrelease": "22.04"}}

    tools = create_discovery_tools(adapter, guard)
    res = await tools["salt_get_grains"](tgt="web1", item="os")

    assert res == {"web1": {"os": "Ubuntu", "osrelease": "22.04"}}
    adapter.cmd.assert_called_once_with(tgt="web1", fun="grains.item", arg=["os"], tgt_type="glob", timeout=60)

@pytest.mark.asyncio
async def test_salt_get_pillar(mock_context):
    adapter, guard, audit = mock_context
    adapter.cmd.return_value = {"web1": {"port": 80}}

    tools = create_discovery_tools(adapter, guard)
    res = await tools["salt_get_pillar"](tgt="web1", item="port")

    assert res == {"web1": {"port": 80}}
    adapter.cmd.assert_called_once_with(tgt="web1", fun="pillar.item", arg=["port"], tgt_type="glob", timeout=60)

@pytest.mark.asyncio
async def test_salt_list_keys(mock_context):
    adapter, guard, audit = mock_context
    adapter.list_keys.return_value = {"minions": ["web1"]}

    tools = create_key_tools(adapter, guard)
    res = await tools["salt_list_keys"]()

    assert res == {"minions": ["web1"]}

@pytest.mark.asyncio
async def test_salt_manage_key_denied(mock_context):
    adapter, guard, audit = mock_context
    guard.check_key_action.return_value = (False, "Phải có confirm=True")

    tools = create_key_tools(adapter, guard)
    res = await tools["salt_manage_key"](action="delete", match="web1", confirm=False)

    assert "error" in res
    assert "confirm=True" in res["error"]
    adapter.manage_key.assert_not_called()
