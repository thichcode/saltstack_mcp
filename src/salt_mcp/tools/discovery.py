from __future__ import annotations

from typing import Any, Callable, Dict, Optional
from salt_mcp.salt_adapter import SaltAdapter
from salt_mcp.safety import SafetyGuard


def create_discovery_tools(adapter: SaltAdapter, guard: SafetyGuard) -> Dict[str, Callable]:
    """Creates discovery and query tools."""

    async def salt_ping(tgt: str = "*", tgt_type: str = "glob", timeout: int = 60) -> Dict[str, Any]:
        """Pings minions to check connectivity and online status."""
        allowed, reason = guard.check_operation_allowed("salt_ping")
        if not allowed:
            guard.audit.log_event("salt_ping", {"tgt": tgt}, allowed=False, reason=reason)
            return {"error": reason}

        allowed, reason = guard.check_target(tgt)
        if not allowed:
            guard.audit.log_event("salt_ping", {"tgt": tgt}, allowed=False, reason=reason)
            return {"error": reason}

        try:
            res = await adapter.cmd(tgt=tgt, fun="test.ping", tgt_type=tgt_type, timeout=timeout)
            guard.audit.log_event("salt_ping", {"tgt": tgt}, allowed=True, result_summary=f"Minions responded: {len(res) if isinstance(res, dict) else 1}")
            return res
        except Exception as e:
            guard.audit.log_event("salt_ping", {"tgt": tgt}, allowed=True, result_summary=f"Error: {e}")
            return {"error": f"Lỗi khi thực thi test.ping: {str(e)}"}

    async def salt_get_grains(tgt: str, item: str = "", tgt_type: str = "glob", timeout: int = 60) -> Dict[str, Any]:
        """Fetches grain items (OS, hardware, networking, custom grains) from target minions."""
        allowed, reason = guard.check_operation_allowed("salt_get_grains")
        if not allowed:
            guard.audit.log_event("salt_get_grains", {"tgt": tgt, "item": item}, allowed=False, reason=reason)
            return {"error": reason}

        allowed, reason = guard.check_target(tgt)
        if not allowed:
            guard.audit.log_event("salt_get_grains", {"tgt": tgt, "item": item}, allowed=False, reason=reason)
            return {"error": reason}

        fun = "grains.item" if item else "grains.items"
        arg = [item] if item else None

        try:
            res = await adapter.cmd(tgt=tgt, fun=fun, arg=arg, tgt_type=tgt_type, timeout=timeout)
            guard.audit.log_event("salt_get_grains", {"tgt": tgt, "item": item}, allowed=True, result_summary=f"Fetched grains for: {len(res) if isinstance(res, dict) else 1} minions")
            return res
        except Exception as e:
            guard.audit.log_event("salt_get_grains", {"tgt": tgt, "item": item}, allowed=True, result_summary=f"Error: {e}")
            return {"error": f"Lỗi khi lấy grains: {str(e)}"}

    async def salt_get_pillar(tgt: str, item: str = "", tgt_type: str = "glob", timeout: int = 60) -> Dict[str, Any]:
        """Fetches pillar data from target minions."""
        allowed, reason = guard.check_operation_allowed("salt_get_pillar")
        if not allowed:
            guard.audit.log_event("salt_get_pillar", {"tgt": tgt, "item": item}, allowed=False, reason=reason)
            return {"error": reason}

        allowed, reason = guard.check_target(tgt)
        if not allowed:
            guard.audit.log_event("salt_get_pillar", {"tgt": tgt, "item": item}, allowed=False, reason=reason)
            return {"error": reason}

        fun = "pillar.item" if item else "pillar.items"
        arg = [item] if item else None

        try:
            res = await adapter.cmd(tgt=tgt, fun=fun, arg=arg, tgt_type=tgt_type, timeout=timeout)
            guard.audit.log_event("salt_get_pillar", {"tgt": tgt, "item": item}, allowed=True, result_summary=f"Fetched pillar for: {len(res) if isinstance(res, dict) else 1} minions")
            return res
        except Exception as e:
            guard.audit.log_event("salt_get_pillar", {"tgt": tgt, "item": item}, allowed=True, result_summary=f"Error: {e}")
            return {"error": f"Lỗi khi lấy pillar: {str(e)}"}

    return {
        "salt_ping": salt_ping,
        "salt_get_grains": salt_get_grains,
        "salt_get_pillar": salt_get_pillar,
    }
