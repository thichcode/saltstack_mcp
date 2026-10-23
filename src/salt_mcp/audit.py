from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import threading
from typing import Any, Dict, Optional


class AuditLogger:
    """Thread-safe JSON Lines audit logger for Salt MCP tool execution."""

    def __init__(self, log_file: str = "salt-mcp-audit.jsonl", enabled: bool = True):
        self.log_file = log_file
        self.enabled = enabled
        self._lock = threading.Lock()

    def log_event(
        self,
        tool: str,
        args: Dict[str, Any],
        allowed: bool,
        reason: str = "",
        result_summary: str = "",
    ) -> None:
        """Appends an event record to the audit log."""
        if not self.enabled:
            return

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "args": args,
            "allowed": allowed,
            "reason": reason,
            "result_summary": result_summary,
        }

        line = json.dumps(record, ensure_ascii=False) + "\n"

        with self._lock:
            # Ensure directory exists if path has directories
            dirname = os.path.dirname(self.log_file)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname, exist_ok=True)

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line)
