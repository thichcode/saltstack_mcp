from __future__ import annotations

from typing import Any, Callable, Dict, List, Literal, Optional
from salt_mcp.salt_adapter import SaltAdapter
from salt_mcp.safety import SafetyGuard


def create_schedule_tools(adapter: SaltAdapter, guard: SafetyGuard) -> Dict[str, Callable]:
    """Creates scheduler management tools."""

    async def salt_manage_schedule(
        tgt: str,
        action: Literal["list", "add", "delete", "enable", "disable"],
        job_name: str = "",
        function: str = "",
        schedule_spec: Optional[Dict[str, Any]] = None,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        tgt_type: str = "glob",
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Manages Salt scheduled tasks (schedule.list, add, delete, enable, disable)."""
        allowed, reason = guard.check_operation_allowed("salt_manage_schedule")
        if not allowed:
            guard.audit.log_event("salt_manage_schedule", {"tgt": tgt, "action": action}, allowed=False, reason=reason)
            return {"error": reason}

        allowed, reason = guard.check_target(tgt)
        if not allowed:
            guard.audit.log_event("salt_manage_schedule", {"tgt": tgt, "action": action}, allowed=False, reason=reason)
            return {"error": reason}

        fun = f"schedule.{action}"
        arg_list: Optional[List[Any]] = None
        kwarg_dict: Dict[str, Any] = {}

        if action == "list":
            arg_list = None
        elif action in ("delete", "enable", "disable"):
            if not job_name:
                return {"error": f"Hành động '{action}' yêu cầu truyền job_name"}
            arg_list = [job_name]
        elif action == "add":
            if not job_name or not function:
                return {"error": "Hành động 'add' yêu cầu truyền cả job_name và function"}
            arg_list = [job_name]
            kwarg_dict["function"] = function
            if schedule_spec:
                kwarg_dict.update(schedule_spec)
            if args:
                kwarg_dict["job_args"] = args
            if kwargs:
                kwarg_dict["job_kwargs"] = kwargs

        try:
            res = await adapter.cmd(
                tgt=tgt,
                fun=fun,
                arg=arg_list,
                kwarg=kwarg_dict,
                tgt_type=tgt_type,
                timeout=timeout,
            )
            guard.audit.log_event(
                "salt_manage_schedule",
                {"tgt": tgt, "action": action, "job_name": job_name},
                allowed=True,
                result_summary=f"Schedule action {action} completed",
            )
            return res
        except Exception as e:
            guard.audit.log_event(
                "salt_manage_schedule",
                {"tgt": tgt, "action": action, "job_name": job_name},
                allowed=True,
                result_summary=f"Error: {e}",
            )
            return {"error": f"Lỗi khi quản lý schedule: {str(e)}"}

    return {
        "salt_manage_schedule": salt_manage_schedule,
    }
