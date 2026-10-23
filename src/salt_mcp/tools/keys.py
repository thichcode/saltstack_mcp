from __future__ import annotations

from typing import Any, Callable, Dict, Literal
from salt_mcp.salt_adapter import SaltAdapter
from salt_mcp.safety import SafetyGuard


def create_key_tools(adapter: SaltAdapter, guard: SafetyGuard) -> Dict[str, Callable]:
    """Creates minion key management tools."""

    async def salt_list_keys() -> Dict[str, Any]:
        """Lists all minion keys by status: minions (accepted), minions_pre (unaccepted), minions_rejected, minions_denied."""
        allowed, reason = guard.check_operation_allowed("salt_list_keys")
        if not allowed:
            guard.audit.log_event("salt_list_keys", {}, allowed=False, reason=reason)
            return {"error": reason}

        try:
            res = await adapter.list_keys()
            guard.audit.log_event("salt_list_keys", {}, allowed=True, result_summary="Listed keys")
            return res
        except Exception as e:
            guard.audit.log_event("salt_list_keys", {}, allowed=True, result_summary=f"Error: {e}")
            return {"error": f"Lỗi khi liệt kê keys: {str(e)}"}

    async def salt_manage_key(
        action: Literal["accept", "reject", "delete"],
        match: str,
        confirm: bool = False,
    ) -> Dict[str, Any]:
        """Manages minion keys: accept, reject, or delete. Reject/delete requires confirm=True."""
        allowed, reason = guard.check_operation_allowed("salt_manage_key")
        if not allowed:
            guard.audit.log_event("salt_manage_key", {"action": action, "match": match}, allowed=False, reason=reason)
            return {"error": reason}

        allowed, reason = guard.check_key_action(action=action, confirm=confirm)
        if not allowed:
            guard.audit.log_event("salt_manage_key", {"action": action, "match": match, "confirm": confirm}, allowed=False, reason=reason)
            return {"error": reason}

        try:
            res = await adapter.manage_key(action=action, match=match)
            guard.audit.log_event("salt_manage_key", {"action": action, "match": match}, allowed=True, result_summary=f"Action {action} succeeded")
            return res
        except Exception as e:
            guard.audit.log_event("salt_manage_key", {"action": action, "match": match}, allowed=True, result_summary=f"Error: {e}")
            return {"error": f"Lỗi khi thao tác key: {str(e)}"}

    return {
        "salt_list_keys": salt_list_keys,
        "salt_manage_key": salt_manage_key,
    }
