import pytest
from salt_mcp.config import SaltMcpConfig, TargetFilters, SafetyRules, AuthConfig
from salt_mcp.safety import SafetyGuard
from salt_mcp.audit import AuditLogger

@pytest.fixture
def test_guard(tmp_path):
    config = SaltMcpConfig(
        auth=AuthConfig(mode="safe_ops"),
        target_filters=TargetFilters(allowed=["*"], denied=["prod-*", "db-master-*"]),
        safety_rules=SafetyRules(
            require_dry_run_first=True,
            cmd_denylist=["rm -rf /", "rm -rf /*", "mkfs", "dd if=", "reboot", "shutdown"]
        )
    )
    audit = AuditLogger(str(tmp_path / "audit.jsonl"))
    return SafetyGuard(config, audit)

def test_target_filter_denied(test_guard):
    ok, reason = test_guard.check_target("prod-web01")
    assert ok is False
    assert "bị từ chối" in reason.lower() or "denied" in reason.lower()

    ok, reason = test_guard.check_target("db-master-1")
    assert ok is False

def test_target_filter_allowed(test_guard):
    ok, _ = test_guard.check_target("dev-web01")
    assert ok is True

    ok, _ = test_guard.check_target("staging-api")
    assert ok is True

def test_command_denylist_exact_and_variations(test_guard):
    ok, _ = test_guard.check_command("ls -la /var/log")
    assert ok is True

    # Exact match
    ok, reason = test_guard.check_command("rm -rf /")
    assert ok is False

    # Extra spacing variation
    ok, reason = test_guard.check_command("rm   -rf   /")
    assert ok is False

    # Sudo variation
    ok, reason = test_guard.check_command("sudo rm -rf /")
    assert ok is False

    # Dangerous binary
    ok, reason = test_guard.check_command("mkfs.ext4 /dev/sda1")
    assert ok is False

    ok, reason = test_guard.check_command("reboot")
    assert ok is False

def test_state_apply_safety(test_guard):
    # test mode is always safe
    ok, _ = test_guard.check_state_apply(test_mode=True, confirm_live=False)
    assert ok is True

    # live run without confirmation must fail
    ok, reason = test_guard.check_state_apply(test_mode=False, confirm_live=False)
    assert ok is False
    assert "confirm_live_run" in reason

    # live run with confirmation is allowed
    ok, _ = test_guard.check_state_apply(test_mode=False, confirm_live=True)
    assert ok is True

def test_key_action_safety(test_guard):
    # accept is allowed
    ok, _ = test_guard.check_key_action(action="accept", confirm=False)
    assert ok is True

    # reject and delete require confirmation
    ok, reason = test_guard.check_key_action(action="delete", confirm=False)
    assert ok is False
    assert "confirm=True" in reason

    ok, _ = test_guard.check_key_action(action="delete", confirm=True)
    assert ok is True

def test_readonly_mode(tmp_path):
    config = SaltMcpConfig(auth=AuthConfig(mode="read_only"))
    guard = SafetyGuard(config, AuditLogger(str(tmp_path / "audit.jsonl")))

    ok, reason = guard.check_operation_allowed("salt_run_command")
    assert ok is False
    assert "read_only" in reason.lower()

    ok, _ = guard.check_operation_allowed("salt_ping")
    assert ok is True
