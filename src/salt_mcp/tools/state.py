from __future__ import annotations

from typing import Any, Callable, Dict
from salt_mcp.salt_adapter import SaltAdapter
from salt_mcp.safety import SafetyGuard


def create_state_tools(adapter: SaltAdapter, guard: SafetyGuard) -> Dict[str, Callable]:
    """Creates state configuration and application tools."""

    async def salt_apply_state(
        tgt: str,
        mods: str = "",
        highstate: bool = False,
        test: bool = True,
        confirm_live_run: bool = False,
        tgt_type: str = "glob",
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """Applies Salt States or Highstate. Defaults to dry-run (test=True). test=False requires confirm_live_run=True."""
        allowed, reason = guard.check_operation_allowed("salt_apply_state")
        if not allowed:
            guard.audit.log_event("salt_apply_state", {"tgt": tgt, "mods": mods, "test": test}, allowed=False, reason=reason)
            return {"error": reason}

        allowed, reason = guard.check_target(tgt)
        if not allowed:
            guard.audit.log_event("salt_apply_state", {"tgt": tgt, "mods": mods, "test": test}, allowed=False, reason=reason)
            return {"error": reason}

        allowed, reason = guard.check_state_apply(test_mode=test, confirm_live=confirm_live_run)
        if not allowed:
            guard.audit.log_event("salt_apply_state", {"tgt": tgt, "mods": mods, "test": test}, allowed=False, reason=reason)
            return {"error": reason}

        if highstate or not mods:
            fun = "state.highstate"
            arg = None
        else:
            fun = "state.apply"
            arg = [mods]

        kwarg = {"test": test}

        try:
            res = await adapter.cmd(tgt=tgt, fun=fun, arg=arg, kwarg=kwarg, tgt_type=tgt_type, timeout=timeout)
            guard.audit.log_event(
                "salt_apply_state",
                {"tgt": tgt, "mods": mods, "test": test},
                allowed=True,
                result_summary=f"Applied state {mods or 'highstate'} (test={test})",
            )
            return res
        except Exception as e:
            guard.audit.log_event(
                "salt_apply_state",
                {"tgt": tgt, "mods": mods, "test": test},
                allowed=True,
                result_summary=f"Error: {e}",
            )
            return {"error": f"Lỗi khi apply state: {str(e)}"}

    return {
        "salt_apply_state": salt_apply_state,
    }
