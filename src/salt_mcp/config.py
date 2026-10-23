from __future__ import annotations

import os
from typing import List, Literal, Optional
import yaml
from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    mode: Literal["read_only", "safe_ops", "full_admin"] = "safe_ops"


class TargetFilters(BaseModel):
    allowed: List[str] = Field(default_factory=lambda: ["*"])
    denied: List[str] = Field(default_factory=list)


class SafetyRules(BaseModel):
    require_dry_run_first: bool = True
    cmd_denylist: List[str] = Field(
        default_factory=lambda: [
            "rm -rf /",
            "rm -rf /*",
            "mkfs",
            "dd if=",
            "shutdown",
            "reboot",
            "init 0",
            "init 6",
            ":(){ :|:& };:",
        ]
    )


class AuditConfig(BaseModel):
    enabled: bool = True
    log_file: str = "salt-mcp-audit.jsonl"


class SaltMcpConfig(BaseModel):
    auth: AuthConfig = Field(default_factory=AuthConfig)
    target_filters: TargetFilters = Field(default_factory=TargetFilters)
    safety_rules: SafetyRules = Field(default_factory=SafetyRules)
    audit: AuditConfig = Field(default_factory=AuditConfig)


def load_config(config_path: Optional[str] = None) -> SaltMcpConfig:
    """Loads configuration from YAML file or environment variable, falling back to defaults."""
    path = config_path or os.environ.get("SALT_MCP_CONFIG")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return SaltMcpConfig.model_validate(data)

    # Check for simple env overrides
    mode_env = os.environ.get("SALT_MCP_MODE")
    config = SaltMcpConfig()
    if mode_env in ("read_only", "safe_ops", "full_admin"):
        config.auth.mode = mode_env  # type: ignore

    return config
