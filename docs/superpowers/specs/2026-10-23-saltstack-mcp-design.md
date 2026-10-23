# Thiết Kế Chi Tiết: SaltStack MCP Server (FastMCP)

- **Ngày tạo:** 2026-10-23
- **Trạng thái:** Chờ phê duyệt (Draft)
- **Tác giả:** Antigravity & User

---

## 1. Tổng Quan & Mục Tiêu

### 1.1. Bối cảnh
SaltStack (Salt) là hệ thống quản lý cấu hình và thực thi lệnh từ xa phân tán (Event-driven infrastructure & configuration management). Hiện tại, việc tương tác với SaltStack đòi hỏi quản trị viên phải chạy CLI trực tiếp trên Salt Master hoặc qua Salt API.

### 1.2. Mục tiêu dự án
Xây dựng một **Model Context Protocol (MCP) Server** chuẩn chạy trực tiếp trên máy chủ **Salt Master**, cho phép các AI Assistant (như Claude Desktop, Antigravity, Cursor) tương tác, truy vấn trạng thái, thu thập grains/pillar, kiểm tra kết nối, thực thi lệnh và áp dụng Salt States một cách an toàn, có kiểm soát.

### 1.3. Yêu cầu chính
- **Giao thức:** Chuẩn MCP qua kênh truyền `stdio` (JSON-RPC).
- **Công nghệ nền tảng:** Python (`mcp` SDK / `FastMCP`), tích hợp trực tiếp qua Salt Python API (`salt.client.LocalClient`, `salt.key.Key`, `salt.runner.RunnerClient`).
- **An toàn & Phân quyền (AuthN/AuthZ):**
  - Tuân thủ quyền hệ điều hành & IPC socket của Salt Master.
  - Tích hợp lớp kiểm duyệt an toàn (Safety Guard): Chặn lệnh phá hoại, lọc target (phân tách dev/staging/prod), mặc định dry-run (`test=True`) cho mọi thao tác thay đổi cấu hình (`state.apply`).
- **Xử lý bất đồng bộ (Non-blocking):** Bọc các lời gọi Salt blocking bằng `asyncio.to_thread` để đảm bảo MCP event loop luôn phản hồi mượt mà.

---

## 2. Kiến Trúc Hệ Thống & Bảo Mật

### 2.1. Sơ đồ kiến trúc

```
+-------------------------------------------------------------+
|                     Claude / AI Client                      |
+-------------------------------------------------------------+
                              |
                    stdio (MCP JSON-RPC)
                              v
+-------------------------------------------------------------+
|                   SaltStack FastMCP Server                  |
|                                                             |
|  +--------------------+             +--------------------+  |
|  |     Tools API      |             |    Safety Guard    |  |
|  | (FastMCP decorator)| ----------> | (Denylist, dry-run,|  |
|  +--------------------+             |  target filter)    |  |
|            |                        +--------------------+  |
|            v                                                |
|  +-------------------------------------------------------+  |
|  |      Async Salt Adapter (asyncio.to_thread)           |  |
|  |                                                       |  |
|  |  * salt.client.LocalClient()    (Command & State)     |  |
|  |  * salt.key.Key()               (Minion Key Auth)     |  |
|  |  * salt.runner.RunnerClient()   (Jobs & Runners)      |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
                              |
                     Unix IPC / ZeroMQ Sockets
                              v
+-------------------------------------------------------------+
|                     Salt Master Daemon                      |
|                 (Kiểm tra publisher_acl)                    |
+-------------------------------------------------------------+
                              |
                              v
                      [Salt Minions...]
```

### 2.2. Cơ chế Xác thực & Phân quyền (3 Lớp)

1. **Lớp 1 - Quyền hệ điều hành (AuthN):**
   - Tiến trình MCP chạy dưới tài khoản có quyền truy cập Unix Socket của Salt Master (`/var/run/salt/master/`).
   - Có thể chạy dưới user `root` hoặc user chuyên dụng (vd: `salt-mcp`) thuộc group `salt`.

2. **Lớp 2 - Salt Core ACL (AuthZ Master-level):**
   - Tận dụng `publisher_acl` trong cấu hình `/etc/salt/master` để giới hạn các module mà user chạy MCP được phép gọi tới minion.

3. **Lớp 3 - MCP Safety Guard (AuthZ AI-level):**
   - Cấu hình qua file `salt-mcp-config.yaml` hoặc biến môi trường:
     - `SALT_MCP_MODE`: `read_only` (chỉ xem), `safe_ops` (cho phép thay đổi có kiểm soát), hoặc `full_admin`.
     - `target_filters.allowed`: Danh sách glob/regex minion được phép tác động (vd: `["dev-*", "test-*"]`).
     - `target_filters.denied`: Danh sách minion cấm tác động (vd: `["prod-*", "db-master-*"]`).
     - `cmd_denylist`: Regex chặn các câu lệnh nguy hiểm (`rm -rf /`, `mkfs`, `dd if=`, `shutdown`, `reboot`).
     - `require_dry_run_first`: Bắt buộc chạy `state.apply` với `test=True` trước khi thực thi thật.

---

## 3. Cấu Trúc Thư Mục Dự Án

```text
salt-mcp/
├── pyproject.toml               # Quản lý packaging, dependencies (mcp, pyyaml, pydantic)
├── salt_mcp_config.example.yaml # File cấu hình bảo mật mẫu
├── README.md                    # Hướng dẫn setup, cấu hình Claude Desktop / Antigravity
├── src/
│   └── salt_mcp/
│       ├── __init__.py
│       ├── __main__.py          # Entrypoint chạy CLI `python -m salt_mcp`
│       ├── server.py            # FastMCP app setup, đăng ký routes/tools
│       ├── config.py            # Load cấu hình yaml & env vars
│       ├── safety.py            # Engine kiểm duyệt an toàn (Safety Guard)
│       ├── salt_adapter.py      # Bọc Salt LocalClient, Key, Runner bất đồng bộ
│       └── tools/
│           ├── __init__.py
│           ├── discovery.py     # ping, grains, pillar
│           ├── keys.py          # list, accept, reject, delete keys
│           ├── execution.py     # run_command (cmd.run), run_module
│           ├── state.py         # apply_state, highstate (test mode default)
│           └── jobs.py          # lookup_jid, active_jobs
└── tests/
    ├── conftest.py              # Mock salt modules cho môi trường test
    ├── test_safety.py           # Unit tests kiểm tra denylist, dry-run, target filtering
    └── test_tools.py            # Unit tests cho tools
```

---

## 4. Đặc Tả Danh Sách Tools

### 4.1. Nhóm Discovery & Khảo sát

#### `salt_ping`
- **Mô tả:** Kiểm tra phản hồi (ping/pong) từ các minion.
- **Tham số:**
  - `tgt` (str, mặc định `"*"`): Target minion (tên, glob, hoặc pattern).
  - `tgt_type` (str, mặc định `"glob"`): Kiểu target (`glob`, `grain`, `pillar`, `compound`, `pcre`).
- **Phản hồi:** Dict ánh xạ `{ minion_id: true/false }`.

#### `salt_get_grains`
- **Mô tả:** Lấy thông tin hệ thống (grains) của target minions (OS, CPU, RAM, IP...).
- **Tham số:**
  - `tgt` (str): Target minion.
  - `item` (str, tùy chọn): Tên grain cụ thể cần lấy (ví dụ: `"os"`, `"ipv4"`). Nếu bỏ trống sẽ lấy toàn bộ.
  - `tgt_type` (str, mặc định `"glob"`).
- **Phản hồi:** Dict grains tương ứng từng minion.

#### `salt_get_pillar`
- **Mô tả:** Truy vấn dữ liệu Pillar của target minions.
- **Tham số:**
  - `tgt` (str): Target minion.
  - `item` (str, tùy chọn): Tên key pillar cần lấy.
  - `tgt_type` (str, mặc định `"glob"`).
- **Phản hồi:** Dict dữ liệu pillar.

### 4.2. Nhóm Quản lý Key (`salt-key`)

#### `salt_list_keys`
- **Mô tả:** Liệt kê toàn bộ minion keys và phân loại trạng thái (minions, minions_pre/unaccepted, minions_rejected, minions_denied).
- **Tham số:** Không.
- **Phản hồi:** Danh sách key theo từng trạng thái.

#### `salt_manage_key`
- **Mô tả:** Thao tác với key của minion (chấp nhận, từ chối hoặc xóa).
- **Tham số:**
  - `action` (str): `"accept"`, `"reject"`, hoặc `"delete"`.
  - `match` (str): Minion ID hoặc pattern key.
  - `confirm` (bool, mặc định `False`): Bắt buộc `True` khi thực hiện `reject` hoặc `delete`.
- **Phản hồi:** Kết quả cập nhật trạng thái key.

### 4.3. Nhóm Thực thi & Command

#### `salt_run_command`
- **Mô tả:** Chạy một câu lệnh shell trực tiếp trên minion (sử dụng `cmd.run`).
- **Tham số:**
  - `tgt` (str): Target minion.
  - `command` (str): Lệnh shell cần chạy.
  - `tgt_type` (str, mặc định `"glob"`).
  - `cwd` (str, tùy chọn): Thư mục làm việc trên minion.
- **Cơ chế an toàn:**
  - Kiểm tra `command` qua bộ lọc `cmd_denylist`. Nếu vi phạm sẽ dừng ngay lập tức.
  - Kiểm tra `tgt` có nằm trong `target_filters.denied` không.
- **Phản hồi:** Dict `{ minion_id: stdout/stderr }`.

#### `salt_run_module`
- **Mô tả:** Thực thi một module hàm Salt bất kỳ (ví dụ: `service.status`, `pkg.version`, `file.file_exists`).
- **Tham số:**
  - `tgt` (str): Target minion.
  - `fun` (str): Tên hàm Salt (ví dụ: `"service.status"`).
  - `args` (list, tùy chọn): Danh sách tham số vị trí.
  - `kwargs` (dict, tùy chọn): Danh sách tham số đặt tên.
  - `tgt_type` (str, mặc định `"glob"`).
- **Phản hồi:** Kết quả trả về từ execution module.

### 4.4. Nhóm Quản lý Cấu hình (States)

#### `salt_apply_state`
- **Mô tả:** Áp dụng cấu hình Salt State (`state.apply` hoặc `state.highstate`).
- **Tham số:**
  - `tgt` (str): Target minion.
  - `mods` (str, tùy chọn): Tên state SLS (nếu rỗng và `highstate=False` thì áp dụng highstate mặc định).
  - `highstate` (bool, mặc định `False`): Chạy `state.highstate`.
  - `test` (bool, mặc định `True`): Chế độ Dry-Run (chỉ mô phỏng thay đổi, không ghi đè hệ thống).
  - `confirm_live_run` (bool, mặc định `False`): Bắt buộc `True` nếu `test=False`.
  - `tgt_type` (str, mặc định `"glob"`).
- **Phản hồi:** Báo cáo chi tiết thay đổi state (Changes, Succeeded, Failed).

### 4.5. Nhóm Quản lý Jobs & Scheduler

#### `salt_list_jobs`
- **Mô tả:** Liệt kê các jobs đang chạy (active) hoặc lịch sử các jobs vừa thực thi gần đây trên Salt Master.
- **Tham số:**
  - `active_only` (bool, mặc định `False`): Nếu `True`, chỉ trả về các jobs đang chạy trong thời gian thực.
  - `limit` (int, mặc định `20`): Số lượng jobs gần nhất cần xem.
- **Phản hồi:** Danh sách thông tin job (JID, target, function, thời gian bắt đầu).

#### `salt_get_job`
- **Mô tả:** Tra cứu chi tiết kết quả thực thi và output của một Job ID (`jid`).
- **Tham số:**
  - `jid` (str): Mã Job ID (ví dụ: `"20261023153012345678"`).
- **Phản hồi:** Chi tiết kết quả trả về từ runner `jobs.lookup_jid`.

#### `salt_manage_schedule`
- **Mô tả:** Quản lý lịch trình tự động (Salt Scheduler) trên minion hoặc master (`schedule.list`, `schedule.add`, `schedule.delete`, `schedule.enable`, `schedule.disable`).
- **Tham số:**
  - `tgt` (str): Target minion cần cấu hình lịch (hoặc Master).
  - `action` (str): Hành động: `"list"`, `"add"`, `"delete"`, `"enable"`, `"disable"`.
  - `job_name` (str, tùy chọn): Tên của task schedule.
  - `function` (str, tùy chọn): Tên hàm Salt thực thi (ví dụ: `"state.apply"`, `"pkg.upgrade"`).
  - `schedule_spec` (dict, tùy chọn): Cấu hình thời gian (ví dụ: `{"minutes": 30}`, `{"cron": "0 2 * * *"}`).
  - `args` / `kwargs` (tùy chọn): Tham số cho hàm thực thi.
- **Phản hồi:** Trạng thái cấu hình lịch trình sau khi cập nhật.

---

### 4.6. Tính Năng Audit Log (Nhật Ký Kiểm Toán)
Để quản trị viên dễ dàng theo dõi, MCP Server sẽ tự động ghi nhật ký mọi hành động của AI vào file `salt-mcp-audit.jsonl`:
- Timestamp (thời gian gọi).
- Tool name (tên công cụ AI gọi).
- Arguments (tham số AI truyền vào: target, command, state, flags).
- Safety Decision (Cho phép / Bị chặn bởi Denylist hoặc Target filter).
- Execution Result / Status (Thành công, Thất bại hoặc Bị từ chối).

---

## 5. Chiến Lược Kiểm Thử (Testing Strategy)

1. **Unit Test (Không cần Salt Master thật):**
   - Viết mock wrapper cho `salt.client.LocalClient`, `salt.key.Key`, `salt.runner.RunnerClient`.
   - Kiểm thử toàn diện module `safety.py`:
     - Test chặn câu lệnh nguy hiểm (`rm -rf /`, `mkfs.ext4 /dev/sda`).
     - Test chặn target cấm (`prod-*`).
     - Test bắt buộc `test=True` khi apply state nếu không có cờ xác nhận.
2. **Integration Test (Môi trường có Salt Master):**
   - Kiểm tra kết nối qua `test.ping` và đọc grains.
   - Kiểm tra chạy state thử nghiệm (`test=True`).

---

## 6. Kế Hoạch Triển Khai Tiếp Theo
Sau khi bản thiết kế (Spec) này được người dùng phê duyệt:
1. Lưu tài liệu thiết kế vào `docs/superpowers/specs/2026-10-23-saltstack-mcp-design.md`.
2. Kích hoạt kỹ năng `writing-plans` để lập kế hoạch triển khai từng bước (Implementation Plan).
3. Bắt đầu hiện thực hóa mã nguồn (TDD) theo kế hoạch đã lập.
