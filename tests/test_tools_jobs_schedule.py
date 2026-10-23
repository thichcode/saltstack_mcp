import pytest
from unittest.mock import AsyncMock, MagicMock
from salt_mcp.tools.jobs import create_job_tools
from salt_mcp.tools.schedule import create_schedule_tools

@pytest.fixture
def mock_context():
    adapter = MagicMock()
    adapter.cmd = AsyncMock()
    adapter.run_job = AsyncMock()

    guard = MagicMock()
    guard.check_operation_allowed.return_value = (True, "")
    guard.check_target.return_value = (True, "")

    audit = MagicMock()
    guard.audit = audit

    return adapter, guard, audit

@pytest.mark.asyncio
async def test_salt_list_jobs_active(mock_context):
    adapter, guard, audit = mock_context
    adapter.run_job.return_value = {"202610231500": {"Function": "state.apply"}}

    tools = create_job_tools(adapter, guard)
    res = await tools["salt_list_jobs"](active_only=True)

    assert res == {"202610231500": {"Function": "state.apply"}}
    adapter.run_job.assert_called_once_with(fun="jobs.active", kwarg=None)

@pytest.mark.asyncio
async def test_salt_list_jobs_recent(mock_context):
    adapter, guard, audit = mock_context
    adapter.run_job.return_value = {"202610231400": {"Function": "test.ping"}}

    tools = create_job_tools(adapter, guard)
    res = await tools["salt_list_jobs"](active_only=False, limit=10)

    assert res == {"202610231400": {"Function": "test.ping"}}
    adapter.run_job.assert_called_once_with(fun="jobs.list_jobs", kwarg=None)

@pytest.mark.asyncio
async def test_salt_get_job(mock_context):
    adapter, guard, audit = mock_context
    adapter.run_job.return_value = {"web1": {"result": True}}

    tools = create_job_tools(adapter, guard)
    res = await tools["salt_get_job"](jid="20261023150000000001")

    assert res == {"web1": {"result": True}}
    adapter.run_job.assert_called_once_with(fun="jobs.lookup_jid", kwarg={"jid": "20261023150000000001"})

@pytest.mark.asyncio
async def test_salt_manage_schedule_list(mock_context):
    adapter, guard, audit = mock_context
    adapter.cmd.return_value = {"web1": {"backup_task": {"function": "state.apply"}}}

    tools = create_schedule_tools(adapter, guard)
    res = await tools["salt_manage_schedule"](tgt="web1", action="list")

    assert res == {"web1": {"backup_task": {"function": "state.apply"}}}
    adapter.cmd.assert_called_once_with(tgt="web1", fun="schedule.list", arg=None, kwarg={}, tgt_type="glob", timeout=60)

@pytest.mark.asyncio
async def test_salt_manage_schedule_add(mock_context):
    adapter, guard, audit = mock_context
    adapter.cmd.return_value = {"web1": {"complete": True}}

    tools = create_schedule_tools(adapter, guard)
    res = await tools["salt_manage_schedule"](
        tgt="web1",
        action="add",
        job_name="daily_check",
        function="test.ping",
        schedule_spec={"hours": 24}
    )

    assert res == {"web1": {"complete": True}}
    adapter.cmd.assert_called_once_with(
        tgt="web1",
        fun="schedule.add",
        arg=["daily_check"],
        kwarg={"function": "test.ping", "hours": 24},
        tgt_type="glob",
        timeout=60
    )
