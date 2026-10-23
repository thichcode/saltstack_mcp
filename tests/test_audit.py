import json
import os
import pytest
from salt_mcp.audit import AuditLogger

def test_audit_log_event(tmp_path):
    log_file = tmp_path / "test_audit.jsonl"
    logger = AuditLogger(str(log_file))
    logger.log_event("salt_ping", {"tgt": "minion1"}, allowed=True, reason="", result_summary="pong")

    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["tool"] == "salt_ping"
        assert record["allowed"] is True
        assert record["args"]["tgt"] == "minion1"
        assert record["result_summary"] == "pong"
        assert "timestamp" in record

def test_audit_log_denied_event(tmp_path):
    log_file = tmp_path / "test_audit.jsonl"
    logger = AuditLogger(str(log_file))
    logger.log_event("salt_run_command", {"command": "rm -rf /"}, allowed=False, reason="Denylisted command")

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["allowed"] is False
        assert record["reason"] == "Denylisted command"
