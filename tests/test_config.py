import os
import pytest
from salt_mcp.config import load_config, SaltMcpConfig, AuthConfig, TargetFilters, SafetyRules

def test_load_default_config():
    config = load_config()
    assert isinstance(config, SaltMcpConfig)
    assert config.auth.mode == "safe_ops"
    assert "rm -rf /" in config.safety_rules.cmd_denylist
    assert config.safety_rules.require_dry_run_first is True

def test_load_custom_yaml_config(tmp_path):
    custom_yaml = tmp_path / "custom.yaml"
    custom_yaml.write_text("""
auth:
  mode: "read_only"
target_filters:
  allowed: ["dev-*"]
  denied: ["prod-*"]
safety_rules:
  require_dry_run_first: false
  cmd_denylist:
    - "custom_kill"
""", encoding="utf-8")
    
    config = load_config(str(custom_yaml))
    assert config.auth.mode == "read_only"
    assert config.target_filters.allowed == ["dev-*"]
    assert config.target_filters.denied == ["prod-*"]
    assert "custom_kill" in config.safety_rules.cmd_denylist
