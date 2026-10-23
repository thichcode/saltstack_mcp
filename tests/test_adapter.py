import pytest
from unittest.mock import MagicMock
from salt_mcp.salt_adapter import SaltAdapter

@pytest.mark.asyncio
async def test_salt_adapter_cmd_execution():
    mock_local = MagicMock()
    mock_local.cmd.return_value = {"minion1": True, "minion2": True}

    adapter = SaltAdapter(local_client=mock_local)
    result = await adapter.cmd(tgt="*", fun="test.ping")

    assert result == {"minion1": True, "minion2": True}
    mock_local.cmd.assert_called_once_with("*", "test.ping", arg=None, kwarg=None, tgt_type="glob", timeout=60)

@pytest.mark.asyncio
async def test_salt_adapter_list_keys():
    mock_key = MagicMock()
    mock_key.list_keys.return_value = {
        "minions": ["web1", "web2"],
        "minions_pre": ["pending1"],
        "minions_rejected": [],
        "minions_denied": []
    }

    adapter = SaltAdapter(key_client=mock_key)
    result = await adapter.list_keys()

    assert "minions" in result
    assert result["minions"] == ["web1", "web2"]
    mock_key.list_keys.assert_called_once()

@pytest.mark.asyncio
async def test_salt_adapter_manage_key():
    mock_key = MagicMock()
    mock_key.accept.return_value = True

    adapter = SaltAdapter(key_client=mock_key)
    result = await adapter.manage_key(action="accept", match="pending1")

    assert result == {"success": True, "action": "accept", "match": "pending1"}
    mock_key.accept.assert_called_once_with(match="pending1")

@pytest.mark.asyncio
async def test_salt_adapter_runner_job():
    mock_runner = MagicMock()
    mock_runner.cmd.return_value = {"jid": "20261023150000"}

    adapter = SaltAdapter(runner_client=mock_runner)
    result = await adapter.run_job(fun="jobs.lookup_jid", kwarg={"jid": "20261023150000"})

    assert result == {"jid": "20261023150000"}
    mock_runner.cmd.assert_called_once_with("jobs.lookup_jid", kwarg={"jid": "20261023150000"})
