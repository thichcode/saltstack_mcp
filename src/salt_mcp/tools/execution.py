from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from salt_mcp.salt_adapter import SaltAdapter
from salt_mcp.safety import SafetyGuard


def create_execution_tools(adapter: SaltAdapter, guard: SafetyGuard) -> Dict[str, Callable]:
    """Creates command execution and module calling tools."""

    async def salt_run_command(
        tgt: str,
        command: str,
        tgt_type: str = "glob",
        cwd: str = "",
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Runs a shell command (via cmd.run) on target minions with safety inspection."""
        allowed, reason = guard.check_operation_allowed("salt_run_command")
        if not allowed:
            guard.audit.log_event("salt_run_command", {"tgt": tgt, "command": command}, allowed=False, reason=reason)
            return {"error": reason}

        allowed, reason = guard.check_target(tgt)
        if not allowed:
            guard.audit.log_event("salt_run_command", {"tgt": tgt, "command": command}, allowed=False, reason=reason)
            return {"error": reason}

        allowed, reason = guard.check_command(command)
        if not allowed:
            guard.audit.log_event("salt_run_command", {"tgt": tgt, "command": command}, allowed=False, reason=reason)
            return {"error": reason}

        kwarg = {"cwd": cwd}
        try:
            res = await adapter.cmd(tgt=tgt, fun="cmd.run", arg=[command], kwarg=kwarg, tgt_type=tgt_type, timeout=timeout)
            guard.audit.log_event("salt_run_command", {"tgt": tgt, "command": command}, allowed=True, result_summary=f"Command executed on: {len(res) if isinstance(res, dict) else 1} minions")
            return res
        except Exception as e:
            guard.audit.log_event("salt_run_command", {"tgt": tgt, "command": command}, allowed=True, result_summary=f"Error: {e}")
            return {"error": f"Lỗi khi thực thi lệnh: {str(e)}"}

    async def salt_run_module(
        tgt: str,
        fun: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        tgt_type: str = "glob",
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Runs an arbitrary Salt execution module (e.g. service.status, pkg.install) on target minions."""
        allowed, reason = guard.check_operation_allowed("salt_run_module")
        if not allowed:
            guard.audit.log_event("salt_run_module", {"tgt": tgt, "fun": fun}, allowed=False, reason=reason)
            return {"error": reason}

        allowed, reason = guard.check_target(tgt)
        if not allowed:
            guard.audit.log_event("salt_run_module", {"tgt": tgt, "fun": fun}, allowed=False, reason=reason)
            return {"error": reason}

        arg_list = args or []
        kwarg_dict = kwargs or {}

        try:
            res = await adapter.cmd(tgt=tgt, fun=fun, arg=arg_list, kwarg=kwarg_dict, tgt_type=tgt_type, timeout=timeout)
            guard.audit.log_event("salt_run_module", {"tgt": tgt, "fun": fun}, allowed=True, result_summary=f"Module {fun} executed")
            return res
        except Exception as e:
            guard.audit.log_event("salt_run_module", {"tgt": tgt, "fun": fun}, allowed=True, result_summary=f"Error: {e}")
            return {"error": f"Lỗi khi thực thi module {fun}: {str(e)}"}

    return {
        "salt_run_command": salt_run_command,
        "salt_run_module": salt_run_module,
    }
