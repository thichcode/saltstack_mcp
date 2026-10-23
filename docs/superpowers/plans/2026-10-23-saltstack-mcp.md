# SaltStack FastMCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng một Model Context Protocol (FastMCP) Server bằng Python chạy trực tiếp trên Salt Master qua `stdio`, cung cấp đầy đủ công cụ khám phá minion, quản lý key, thực thi lệnh shell, áp dụng state (có dry-run), quản lý jobs/scheduler và có hệ thống kiểm duyệt an toàn (Safety Guard) cùng Audit Log.

**Architecture:** Sử dụng thư viện `FastMCP` từ Python MCP SDK. Các tương tác với Salt Master được bọc bất đồng bộ qua `asyncio.to_thread` kết nối với `salt.client.LocalClient`, `salt.key.Key`, `salt.runner.RunnerClient`. Một lớp Safety Guard kiểm duyệt target và lệnh cấm, tự động ghi nhật ký vào `salt-mcp-audit.jsonl`.

**Tech Stack:** Python 3.10+, `mcp` (FastMCP), `pydantic`, `pyyaml`, `pytest`, `pytest-asyncio`.

**Spec:** [`docs/superpowers/specs/2026-10-23-saltstack-mcp-design.md`](file:///d:/pupeteer/ios_modify/docs/superpowers/specs/2026-10-23-saltstack-mcp-design.md)

## Global Constraints

- Chạy qua giao thức chuẩn MCP `stdio` (JSON-RPC) bằng `FastMCP`.
- Mặc định mọi thao tác `salt_apply_state` đều ở chế độ mô phỏng (`test=True`). Chạy thật bắt buộc có cờ `confirm_live_run=True`.
- Các câu lệnh shell nguy hiểm trong `cmd_denylist` và target trong `target_filters.denied` bị chặn ngay lập tức.
- Tất cả các tool call và quyết định an toàn đều được ghi vào `salt-mcp-audit.jsonl`.
- Codebase có thể chạy test độc lập mà không bắt buộc phải cài đặt Salt daemon thật (thông qua mock/adapter).

## Review Focus

1. **Lệnh shell nguy hiểm bị bypass bằng cách chèn ký tự**: Test safety guard với các biến thể như `rm -rf /`, `rm  -rf  /`, `sudo rm -rf /`.
2. **Target regex phủ định**: Minion khớp cả wildcard allow (`*`) nhưng nằm trong deny list (`prod-*`) phải luôn bị từ chối.
3. **State apply vô tình chạy live**: Gọi `salt_apply_state(test=False)` mà thiếu `confirm_live_run=True` phải báo lỗi và không thực thi.
4. **Key deletion không có xác nhận**: Gọi `salt_manage_key(action='delete')` thiếu `confirm=True` phải bị chặn.
5. **Salt Master timeout/unresponsive**: Xử lý ngoại lệ kết nối socket mượt mà và trả về thông báo lỗi chuẩn MCP thay vì crash server.

---

### Task 1: Project Scaffolding & Configuration Module

**Files:**
- Create: `pyproject.toml`
- Create: `src/salt_mcp/__init__.py`
- Create: `src/salt_mcp/config.py`
- Create: `salt_mcp_config.example.yaml`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `SaltMcpConfig` (Pydantic model), `load_config(path: Optional[str] = None) -> SaltMcpConfig`

- [ ] **Step 1: Write the failing test for configuration loading**

```python
# tests/test_config.py
import pytest
from salt_mcp.config import load_config, SaltMcpConfig

def test_load_default_config():
    config = load_config()
    assert isinstance(config, SaltMcpConfig)
    assert config.auth.mode == "safe_ops"
    assert "rm -rf /" in config.safety_rules.cmd_denylist
    assert config.safety_rules.require_dry_run_first is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'salt_mcp')

- [ ] **Step 3: Implement `pyproject.toml`, `src/salt_mcp/config.py`, and default config**

Create standard pyproject with dependencies `mcp>=1.0.0`, `pyyaml>=6.0`, `pydantic>=2.0`, and Pydantic models for `AuthConfig`, `TargetFilters`, `SafetyRules`, `SaltMcpConfig`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/salt_mcp/config.py salt_mcp_config.example.yaml tests/test_config.py
git commit -m "feat: setup project scaffolding and configuration loading"
```

---

### Task 2: Audit Logger Module

**Files:**
- Create: `src/salt_mcp/audit.py`
- Test: `tests/test_audit.py`

**Interfaces:**
- Consumes: `SaltMcpConfig`
- Produces: `AuditLogger(log_file: str)`, `log_event(tool: str, args: dict, allowed: bool, reason: str = "", result_summary: str = "") -> None`

- [ ] **Step 1: Write failing test for audit logging**

```python
# tests/test_audit.py
import json
import os
from salt_mcp.audit import AuditLogger

def test_audit_log_event(tmp_path):
    log_file = tmp_path / "test_audit.jsonl"
    logger = AuditLogger(str(log_file))
    logger.log_event("salt_ping", {"tgt": "minion1"}, allowed=True, result_summary="pong")

    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["tool"] == "salt_ping"
        assert record["allowed"] is True
        assert record["args"]["tgt"] == "minion1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_audit.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'salt_mcp.audit')

- [ ] **Step 3: Implement `AuditLogger` with thread-safe file writing**

Implement JSONL appending with ISO timestamps and error resilience.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_audit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/salt_mcp/audit.py tests/test_audit.py
git commit -m "feat: implement audit logging module"
```

---

### Task 3: Safety Guard Engine

**Files:**
- Create: `src/salt_mcp/safety.py`
- Test: `tests/test_safety.py`

**Interfaces:**
- Consumes: `SaltMcpConfig`, `AuditLogger`
- Produces: `SafetyGuard(config: SaltMcpConfig, audit: AuditLogger)`
  - `check_target(tgt: str) -> tuple[bool, str]`
  - `check_command(command: str) -> tuple[bool, str]`
  - `check_state_apply(test_mode: bool, confirm_live: bool) -> tuple[bool, str]`
  - `check_key_action(action: str, confirm: bool) -> tuple[bool, str]`

- [ ] **Step 1: Write failing tests for Safety Guard rules**

```python
# tests/test_safety.py
from salt_mcp.config import SaltMcpConfig, TargetFilters, SafetyRules, AuthConfig
from salt_mcp.safety import SafetyGuard
from salt_mcp.audit import AuditLogger

def test_safety_guard_denied_target(tmp_path):
    config = SaltMcpConfig(
        auth=AuthConfig(mode="safe_ops"),
        target_filters=TargetFilters(allowed=["dev-*"], denied=["prod-*"]),
        safety_rules=SafetyRules(cmd_denylist=["rm -rf /"])
    )
    guard = SafetyGuard(config, AuditLogger(str(tmp_path / "audit.jsonl")))
    
    ok, reason = guard.check_target("prod-server-01")
    assert ok is False
    assert "cấm tác động" in reason.lower() or "denied" in reason.lower()

    ok, _ = guard.check_target("dev-node-01")
    assert ok is True

def test_safety_guard_command_denylist(tmp_path):
    config = SaltMcpConfig()
    guard = SafetyGuard(config, AuditLogger(str(tmp_path / "audit.jsonl")))
    
    ok, _ = guard.check_command("echo hello")
    assert ok is True
    
    ok, _ = guard.check_command("rm -rf /")
    assert ok is False
    
    ok, _ = guard.check_command("sudo rm  -rf  /")
    assert ok is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_safety.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `SafetyGuard` with regex patterns and target evaluation**

Implement fnmatch/regex matching for target filters, regex pattern searching for denylists, and confirmation checking.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_safety.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/salt_mcp/safety.py tests/test_safety.py
git commit -m "feat: implement safety guard engine"
```

---

### Task 4: Async Salt Client Adapter

**Files:**
- Create: `src/salt_mcp/salt_adapter.py`
- Test: `tests/test_adapter.py`

**Interfaces:**
- Produces: `SaltAdapter(client=None, key_client=None, runner_client=None)`
  - `async cmd(tgt: str, fun: str, arg: list = None, kwarg: dict = None, tgt_type: str = "glob") -> dict`
  - `async list_keys() -> dict`
  - `async manage_key(action: str, match: str) -> dict`
  - `async run_job(fun: str, kwarg: dict = None) -> dict`

- [ ] **Step 1: Write failing test with mock Salt clients**

```python
# tests/test_adapter.py
import pytest
from unittest.mock import MagicMock
from salt_mcp.salt_adapter import SaltAdapter

@pytest.mark.asyncio
async def test_salt_adapter_cmd_execution():
    mock_local_client = MagicMock()
    mock_local_client.cmd.return_value = {"minion1": True}
    
    adapter = SaltAdapter(local_client=mock_local_client)
    res = await adapter.cmd(tgt="minion1", fun="test.ping")
    
    assert res == {"minion1": True}
    mock_local_client.cmd.assert_called_once_with("minion1", "test.ping", arg=None, kwarg=None, tgt_type="glob")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapter.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `SaltAdapter` with lazy initialization and `asyncio.to_thread`**

Implement dynamic import of `salt.client`, `salt.key`, `salt.runner` with graceful handling when salt is not installed, delegating calls to `asyncio.to_thread()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/salt_mcp/salt_adapter.py tests/test_adapter.py
git commit -m "feat: implement async salt client adapter"
```

---

### Task 5: Discovery & Minion Keys Tools

**Files:**
- Create: `src/salt_mcp/tools/__init__.py`
- Create: `src/salt_mcp/tools/discovery.py`
- Create: `src/salt_mcp/tools/keys.py`
- Test: `tests/test_tools_discovery_keys.py`

**Interfaces:**
- Consumes: `SaltAdapter`, `SafetyGuard`
- Produces:
  - `salt_ping(tgt: str = "*", tgt_type: str = "glob") -> dict`
  - `salt_get_grains(tgt: str, item: str = "", tgt_type: str = "glob") -> dict`
  - `salt_get_pillar(tgt: str, item: str = "", tgt_type: str = "glob") -> dict`
  - `salt_list_keys() -> dict`
  - `salt_manage_key(action: str, match: str, confirm: bool = False) -> dict`

- [ ] **Step 1: Write failing tests for discovery & keys tools**

```python
# tests/test_tools_discovery_keys.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from salt_mcp.tools.discovery import create_discovery_tools
from salt_mcp.tools.keys import create_key_tools

@pytest.mark.asyncio
async def test_salt_ping_tool():
    adapter = MagicMock()
    adapter.cmd = AsyncMock(return_value={"minion1": True, "minion2": True})
    guard = MagicMock()
    guard.check_target.return_value = (True, "")
    
    tools = create_discovery_tools(adapter, guard)
    result = await tools["salt_ping"](tgt="*")
    assert result == {"minion1": True, "minion2": True}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools_discovery_keys.py -v`
Expected: FAIL

- [ ] **Step 3: Implement discovery and keys tools**

Implement `salt_ping`, `salt_get_grains`, `salt_get_pillar`, `salt_list_keys`, `salt_manage_key` incorporating target check and key deletion confirmation.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools_discovery_keys.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/salt_mcp/tools/discovery.py src/salt_mcp/tools/keys.py tests/test_tools_discovery_keys.py
git commit -m "feat: implement discovery and minion keys tools"
```

---

### Task 6: Execution & State Tools

**Files:**
- Create: `src/salt_mcp/tools/execution.py`
- Create: `src/salt_mcp/tools/state.py`
- Test: `tests/test_tools_execution_state.py`

**Interfaces:**
- Consumes: `SaltAdapter`, `SafetyGuard`
- Produces:
  - `salt_run_command(tgt: str, command: str, tgt_type: str = "glob", cwd: str = "") -> dict`
  - `salt_run_module(tgt: str, fun: str, args: list = None, kwargs: dict = None, tgt_type: str = "glob") -> dict`
  - `salt_apply_state(tgt: str, mods: str = "", highstate: bool = False, test: bool = True, confirm_live_run: bool = False, tgt_type: str = "glob") -> dict`

- [ ] **Step 1: Write failing tests for command & state tools with safety checks**

```python
# tests/test_tools_execution_state.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from salt_mcp.tools.execution import create_execution_tools
from salt_mcp.tools.state import create_state_tools

@pytest.mark.asyncio
async def test_salt_apply_state_dry_run_enforced():
    adapter = MagicMock()
    adapter.cmd = AsyncMock()
    guard = MagicMock()
    guard.check_target.return_value = (True, "")
    guard.check_state_apply.return_value = (False, "Live run requires confirm_live_run=True")
    
    tools = create_state_tools(adapter, guard)
    res = await tools["salt_apply_state"](tgt="web1", mods="nginx", test=False, confirm_live_run=False)
    assert "error" in res
    assert "confirm_live_run" in res["error"]
    adapter.cmd.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools_execution_state.py -v`
Expected: FAIL

- [ ] **Step 3: Implement execution and state tools**

Wire safety checks to `cmd.run`, execution modules, `state.apply` and `state.highstate`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools_execution_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/salt_mcp/tools/execution.py src/salt_mcp/tools/state.py tests/test_tools_execution_state.py
git commit -m "feat: implement execution and state management tools"
```

---

### Task 7: Job & Scheduler Management Tools

**Files:**
- Create: `src/salt_mcp/tools/jobs.py`
- Create: `src/salt_mcp/tools/schedule.py`
- Test: `tests/test_tools_jobs_schedule.py`

**Interfaces:**
- Consumes: `SaltAdapter`, `SafetyGuard`
- Produces:
  - `salt_list_jobs(active_only: bool = False, limit: int = 20) -> dict`
  - `salt_get_job(jid: str) -> dict`
  - `salt_manage_schedule(tgt: str, action: str, job_name: str = "", function: str = "", schedule_spec: dict = None, args: list = None, kwargs: dict = None) -> dict`

- [ ] **Step 1: Write failing tests for job & schedule tools**

```python
# tests/test_tools_jobs_schedule.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from salt_mcp.tools.jobs import create_job_tools
from salt_mcp.tools.schedule import create_schedule_tools

@pytest.mark.asyncio
async def test_salt_get_job():
    adapter = MagicMock()
    adapter.run_job = AsyncMock(return_value={"web1": {"result": True}})
    guard = MagicMock()
    
    tools = create_job_tools(adapter, guard)
    res = await tools["salt_get_job"](jid="20261023150000000001")
    assert res == {"web1": {"result": True}}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools_jobs_schedule.py -v`
Expected: FAIL

- [ ] **Step 3: Implement jobs and schedule tools**

Implement runner calls (`jobs.active`, `jobs.list_jobs`, `jobs.lookup_jid`) and minion schedule functions (`schedule.list`, `schedule.add`, `schedule.delete`, `schedule.enable`, `schedule.disable`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools_jobs_schedule.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/salt_mcp/tools/jobs.py src/salt_mcp/tools/schedule.py tests/test_tools_jobs_schedule.py
git commit -m "feat: implement job lookup and schedule management tools"
```

---

### Task 8: FastMCP Server Integration, CLI Entrypoint & Documentation

**Files:**
- Create: `src/salt_mcp/server.py`
- Create: `src/salt_mcp/__main__.py`
- Create: `README.md`
- Test: `tests/test_server_registration.py`

**Interfaces:**
- Produces: `create_server() -> FastMCP`, `main() -> None`

- [ ] **Step 1: Write test to verify all tools are registered in FastMCP instance**

```python
# tests/test_server_registration.py
from salt_mcp.server import create_server

def test_fastmcp_server_tools_registered():
    mcp = create_server()
    registered_tools = [t.name for t in mcp._tool_manager.list_tools()]
    expected_tools = [
        "salt_ping", "salt_get_grains", "salt_get_pillar",
        "salt_list_keys", "salt_manage_key",
        "salt_run_command", "salt_run_module", "salt_apply_state",
        "salt_list_jobs", "salt_get_job", "salt_manage_schedule"
    ]
    for tool_name in expected_tools:
        assert tool_name in registered_tools
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_server_registration.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `server.py`, `__main__.py`, and comprehensive `README.md`**

Register all tools into FastMCP app; setup CLI parser for `--config` and stdio runner. Write README with Claude Desktop JSON config and salt permissions guide.

- [ ] **Step 4: Run full test suite to verify everything passes**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/salt_mcp/server.py src/salt_mcp/__main__.py README.md tests/test_server_registration.py
git commit -m "feat: integrate FastMCP server, CLI entrypoint, and documentation"
```
