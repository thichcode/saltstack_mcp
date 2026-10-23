import pytest
from unittest.mock import AsyncMock, MagicMock
from salt_mcp.tools.execution import create_execution_tools
from salt_mcp.tools.state import create_state_tools

@pytest.fixture
def mock_context():
    adapter = MagicMock()
    adapter.cmd = AsyncMock()

    guard = MagicMock()
    guard.check_operation_allowed.return_value = (True, "")
    guard.check_target.return_value = (True, "")
    guard.check_command.return_value = (True, "")
    guard.check_state_apply.return_value = (True, "")

    audit = MagicMock()
    guard.audit = audit

    return adapter, guard, audit

@pytest.mark.asyncio
async def test_salt_run_command_success(mock_context):
    adapter, guard, audit = mock_context
    adapter.cmd.return_value = {"web1": "active (running)"}

    tools = create_execution_tools(adapter, guard)
    res = await tools["salt_run_command"](tgt="web1", command="systemctl status nginx")

    assert res == {"web1": "active (running)"}
    adapter.cmd.assert_called_once_with(tgt="web1", fun="cmd.run", arg=["systemctl status nginx"], kwarg={"cwd": ""}, tgt_type="glob", timeout=60)
    audit.log_event.assert_called()

@pytest.mark.asyncio
async def test_salt_run_command_denied(mock_context):
    adapter, guard, audit = mock_context
    guard.check_command.return_value = (False, "Lệnh chứa pattern nguy hiểm")

    tools = create_execution_tools(adapter, guard)
    res = await tools["salt_run_command"](tgt="web1", command="rm -rf /")

    assert "error" in res
    assert "nguy hiểm" in res["error"]
    adapter.cmd.assert_not_called()

@pytest.mark.asyncio
async def test_salt_run_module(mock_context):
    adapter, guard, audit = mock_context
    adapter.cmd.return_value = {"web1": True}

    tools = create_execution_tools(adapter, guard)
    res = await tools["salt_run_module"](tgt="web1", fun="service.restart", args=["nginx"])

    assert res == {"web1": True}
    adapter.cmd.assert_called_once_with(tgt="web1", fun="service.restart", arg=["nginx"], kwarg={}, tgt_type="glob", timeout=60)

@pytest.mark.asyncio
async def test_salt_apply_state_dry_run_default(mock_context):
    adapter, guard, audit = mock_context
    adapter.cmd.return_value = {"web1": {"result": True, "changes": {}}}

    tools = create_state_tools(adapter, guard)
    res = await tools["salt_apply_state"](tgt="web1", mods="nginx")

    assert res == {"web1": {"result": True, "changes": {}}}
    guard.check_state_apply.assert_called_once_with(test_mode=True, confirm_live=False)
    adapter.cmd.assert_called_once_with(tgt="web1", fun="state.apply", arg=["nginx"], kwarg={"test": True}, tgt_type="glob", timeout=300)

@pytest.mark.asyncio
async def test_salt_apply_state_live_rejected_without_confirmation(mock_context):
    adapter, guard, audit = mock_context
    guard.check_state_apply.return_value = (False, "Cần confirm_live_run=True")

    tools = create_state_tools(adapter, guard)
    res = await tools["salt_apply_state"](tgt="web1", mods="nginx", test=False, confirm_live_run=False)

    assert "error" in res
    assert "confirm_live_run=True" in res["error"]
    adapter.cmd.assert_not_called()
