from __future__ import annotations

import fnmatch
import re
from typing import Tuple
from salt_mcp.config import SaltMcpConfig
from salt_mcp.audit import AuditLogger


class SafetyGuard:
    """Evaluates security constraints, target filtering, and command denylists."""

    def __init__(self, config: SaltMcpConfig, audit: AuditLogger):
        self.config = config
        self.audit = audit

    def check_operation_allowed(self, tool_name: str) -> Tuple[bool, str]:
        """Verifies if the tool execution is allowed under current auth mode."""
        if self.config.auth.mode == "read_only":
            read_only_tools = {
                "salt_ping",
                "salt_get_grains",
                "salt_get_pillar",
                "salt_list_keys",
                "salt_list_jobs",
                "salt_get_job",
            }
            if tool_name not in read_only_tools:
                reason = f"Quyền bị từ chối: Server đang chạy ở chế độ 'read_only', không thể thực thi tool '{tool_name}'."
                return False, reason

        return True, ""

    def check_target(self, tgt: str) -> Tuple[bool, str]:
        """Checks target minion against whitelist and denylist filters."""
        # Check denied targets first
        for denied_pattern in self.config.target_filters.denied:
            if fnmatch.fnmatch(tgt, denied_pattern):
                reason = f"Quyền bị từ chối: Target '{tgt}' khớp với danh sách cấm tác động ('{denied_pattern}')."
                return False, reason

        # Check allowed targets
        if self.config.target_filters.allowed:
            matched_any = any(
                fnmatch.fnmatch(tgt, allowed_pattern)
                for allowed_pattern in self.config.target_filters.allowed
            )
            if not matched_any:
                reason = f"Quyền bị từ chối: Target '{tgt}' không nằm trong danh sách được phép tác động."
                return False, reason

        return True, ""

    def check_command(self, command: str) -> Tuple[bool, str]:
        """Checks shell command against dangerous command patterns."""
        normalized_cmd = re.sub(r"\s+", " ", command.strip())

        for pattern in self.config.safety_rules.cmd_denylist:
            # Check normalized substring
            normalized_pattern = re.sub(r"\s+", " ", pattern.strip())
            if normalized_pattern in normalized_cmd:
                reason = f"Quyền bị từ chối: Lệnh shell chứa pattern nguy hiểm trong denylist: '{pattern}'."
                return False, reason

            # Word boundary regex check for commands like reboot, shutdown, mkfs
            if re.search(rf"\b{re.escape(pattern)}\b", normalized_cmd, re.IGNORECASE):
                reason = f"Quyền bị từ chối: Lệnh shell kích hoạt pattern cấm: '{pattern}'."
                return False, reason

        return True, ""

    def check_state_apply(self, test_mode: bool, confirm_live: bool) -> Tuple[bool, str]:
        """Verifies safety policy for applying states."""
        if not test_mode and self.config.safety_rules.require_dry_run_first:
            if not confirm_live:
                reason = (
                    "Quyền bị từ chối: state.apply chạy ở chế độ thực tế (test=False) "
                    "bắt buộc phải truyền tham số confirm_live_run=True."
                )
                return False, reason
        return True, ""

    def check_key_action(self, action: str, confirm: bool) -> Tuple[bool, str]:
        """Verifies safety policy for key management."""
        if action in ("reject", "delete") and not confirm:
            reason = f"Quyền bị từ chối: Thao tác '{action}' key bắt buộc phải truyền confirm=True để xác nhận."
            return False, reason
        return True, ""
