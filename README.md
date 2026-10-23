# SaltStack MCP Server (FastMCP)

Một Model Context Protocol (MCP) Server hiệu năng cao, viết bằng Python chạy trực tiếp trên **Salt Master**, cho phép các AI Assistant (Claude Desktop, Cursor, Antigravity) quản lý, tự động hóa và giám sát hạ tầng SaltStack một cách an toàn và có kiểm soát.

---

## ✨ Tính Năng Nổi Bật

1. **Kết nối Native & Bất đồng bộ:** Sử dụng trực tiếp Salt Python API (`salt.client.LocalClient`, `salt.key.Key`, `salt.runner.RunnerClient`) qua `asyncio.to_thread` — không làm nghẽn MCP event loop.
2. **Cơ chế An toàn 3 Lớp (Safety Guard):**
   - **Target Filtering:** Lọc target minion bằng Glob/Regex (ví dụ cấm AI chạm vào minion `prod-*`).
   - **Command Denylist:** Tự động chặn các câu lệnh shell nguy hiểm (`rm -rf /`, `mkfs`, `reboot`, `shutdown`, v.v.).
   - **Dry-run Mặc định:** Mọi thao tác `salt_apply_state` đều mặc định chạy ở chế độ mô phỏng `test=True`. Muốn chạy thật bắt buộc phải có cờ `confirm_live_run=True`.
   - **Xác nhận Key:** Xóa hoặc từ chối minion key bắt buộc phải truyền `confirm=True`.
3. **Audit Log:** Ghi lại mọi tool call của AI vào file `salt-mcp-audit.jsonl` (timestamp, args, safety decision, output summary) để kiểm toán mà không cần hệ thống web phức tạp.
4. **Bộ công cụ toàn diện (11 Tools):**
   - Khám phá: `salt_ping`, `salt_get_grains`, `salt_get_pillar`.
   - Quản lý Key: `salt_list_keys`, `salt_manage_key`.
   - Thực thi & Cấu hình: `salt_run_command`, `salt_run_module`, `salt_apply_state`.
   - Jobs & Scheduler: `salt_list_jobs`, `salt_get_job`, `salt_manage_schedule`.

---

## 🚀 Cài Đặt

### 1. Yêu Cầu Hệ Thống
- Máy chủ đã cài đặt **Salt Master** (`salt-master`).
- Python 3.10 trở lên.
- Quyền truy cập Unix Socket của Salt Master (`/var/run/salt/master/`).

### 2. Cài Đặt Dependencies

Khuyên dùng `uv` hoặc `pip` trong virtualenv của Salt Master:

```bash
# Cài đặt qua pip
pip install -e .
```

Hoặc cài trực tiếp các thư viện:
```bash
pip install mcp pydantic pyyaml
```

---

## ⚙️ Cấu Hình Bảo Mật

Tạo file cấu hình bảo mật `salt-mcp-config.yaml` (dựa trên file mẫu `salt_mcp_config.example.yaml`):

```yaml
auth:
  mode: "safe_ops"   # "read_only" | "safe_ops" | "full_admin"

target_filters:
  allowed:
    - "*"
  denied:
    - "prod-*"
    - "db-master-*"

safety_rules:
  require_dry_run_first: true
  cmd_denylist:
    - "rm -rf /"
    - "rm -rf /*"
    - "mkfs"
    - "dd if="
    - "shutdown"
    - "reboot"

audit:
  enabled: true
  log_file: "salt-mcp-audit.jsonl"
```

---

## 🔌 Tích Hợp Claude Desktop / AI Clients

Thêm cấu hình sau vào file cấu hình Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "saltstack": {
      "command": "python",
      "args": [
        "-m",
        "salt_mcp",
        "--config",
        "/etc/salt/salt-mcp-config.yaml"
      ],
      "env": {
        "PYTHONPATH": "/path/to/salt-mcp/src"
      }
    }
  }
}
```

---

## 🧪 Chạy Kiểm Thử (Tests)

Toàn bộ test suite được viết với pytest và có thể chạy độc lập không cần Salt Master:

```bash
pytest tests/ -v
```
