from __future__ import annotations

from typing import Any, Callable, Dict
from salt_mcp.salt_adapter import SaltAdapter
from salt_mcp.safety import SafetyGuard


def create_job_tools(adapter: SaltAdapter, guard: SafetyGuard) -> Dict[str, Callable]:
    """Creates job monitoring tools."""

    async def salt_list_jobs(active_only: bool = False, limit: int = 20) -> Dict[str, Any]:
        """Lists active running jobs or recent job history on Salt Master."""
        allowed, reason = guard.check_operation_allowed("salt_list_jobs")
        if not allowed:
            guard.audit.log_event("salt_list_jobs", {"active_only": active_only, "limit": limit}, allowed=False, reason=reason)
            return {"error": reason}

        fun = "jobs.active" if active_only else "jobs.list_jobs"

        try:
            res = await adapter.run_job(fun=fun, kwarg=None)
            if not active_only and isinstance(res, dict) and limit > 0:
                # Return most recent jobs up to limit
                sorted_items = sorted(res.items(), key=lambda x: str(x[0]), reverse=True)[:limit]
                res = dict(sorted_items)

            guard.audit.log_event("salt_list_jobs", {"active_only": active_only, "limit": limit}, allowed=True, result_summary=f"Jobs retrieved: {len(res) if isinstance(res, dict) else 1}")
            return res
        except Exception as e:
            guard.audit.log_event("salt_list_jobs", {"active_only": active_only, "limit": limit}, allowed=True, result_summary=f"Error: {e}")
            return {"error": f"Lỗi khi liệt kê jobs: {str(e)}"}

    async def salt_get_job(jid: str) -> Dict[str, Any]:
        """Looks up details and returns for a specific Job ID (JID)."""
        allowed, reason = guard.check_operation_allowed("salt_get_job")
        if not allowed:
            guard.audit.log_event("salt_get_job", {"jid": jid}, allowed=False, reason=reason)
            return {"error": reason}

        try:
            res = await adapter.run_job(fun="jobs.lookup_jid", kwarg={"jid": jid})
            guard.audit.log_event("salt_get_job", {"jid": jid}, allowed=True, result_summary=f"Job {jid} looked up")
            return res
        except Exception as e:
            guard.audit.log_event("salt_get_job", {"jid": jid}, allowed=True, result_summary=f"Error: {e}")
            return {"error": f"Lỗi khi tra cứu job {jid}: {str(e)}"}

    return {
        "salt_list_jobs": salt_list_jobs,
        "salt_get_job": salt_get_job,
    }
