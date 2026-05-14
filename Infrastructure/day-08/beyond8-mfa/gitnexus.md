# GitNexus Quickstart (VI)

Hướng dẫn ngắn nhất để setup, dùng hằng ngày, và gỡ setup GitNexus cho nhiều repo.

## 1) Bạn nhận được gì sau khi setup?

- Mỗi repo được index sẽ có thư mục `./.gitnexus/` (knowledge graph + metadata).
- Toàn bộ repo đã index được đăng ký trong `~/.gitnexus/registry.json`.
- AI agent (Claude Code/Cursor/Codex...) có thể dùng MCP tools để:
  - tìm code theo ngữ nghĩa,
  - xem call/context/impact,
  - detect change từ git diff,
  - rename đa file có preview.
- Có web local để xem/tra cứu nhiều repo qua `gitnexus serve`.

## 2) Setup chuẩn (làm 1 lần + theo repo)

### Bước A - setup global (chỉ 1 lần trên máy)

```bash
npx gitnexus setup
```

Lệnh này tự ghi MCP config global cho editor/agent được hỗ trợ.

### Bước B - index từng repo muốn dùng

Trong mỗi repo:

```bash
npx gitnexus analyze
```

## 3) Dùng hằng ngày

```bash
npx gitnexus status
npx gitnexus list
npx gitnexus analyze
npx gitnexus analyze --force
npx gitnexus serve
```

- `status`: kiểm tra index của repo hiện tại.
- `list`: xem tất cả repo đã index.
- `analyze`: cập nhật index khi code đổi.
- `serve`: mở backend local cho web UI/multi-repo.

## 4) Config riêng cho Claude Code và Cursor

## 4.1 Claude Code (manual)

```bash
# macOS/Linux
claude mcp add gitnexus -- npx -y gitnexus@latest mcp

# Windows
claude mcp add gitnexus -- cmd /c npx -y gitnexus@latest mcp
```

## 4.2 Cursor (manual)

Thêm vào file `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "gitnexus": {
      "command": "npx",
      "args": ["-y", "gitnexus@latest", "mcp"]
    }
  }
}
```

## 5) Muốn "bỏ setup" (gỡ GitNexus) thì làm sao?

Làm theo thứ tự để gỡ sạch và an toàn:

### Bước 1 - xóa index dữ liệu

```bash
gitnexus clean --all --force
```

Lệnh này xóa index các repo đã đăng ký qua GitNexus.

### Bước 2 - gỡ MCP config theo tool bạn dùng

- Claude Code: xóa server `gitnexus` trong cấu hình MCP của Claude Code.
- Cursor: mở `~/.cursor/mcp.json` rồi xóa key `mcpServers.gitnexus`.

> Nếu bạn dùng `gitnexus setup`, đây là phần quan trọng nhất để "ngắt kết nối" AI tool với GitNexus.

### Bước 3 - (tuỳ chọn) xóa registry/cache còn lại

Xóa thư mục global:

```bash
rm -rf ~/.gitnexus
```

Xóa dữ liệu theo từng repo (nếu còn):

```bash
rm -rf .gitnexus
```

## 6) Multi-repo hoạt động thế nào (siêu ngắn)

- Mỗi repo chạy `analyze` một lần.
- MCP server đọc `~/.gitnexus/registry.json`.
- Một lần config MCP, dùng cho tất cả repo đã index.

## 7) Quy trình khuyến nghị (3 lệnh)

```bash
npx gitnexus setup
cd /path/to/repo-a && npx gitnexus analyze
cd /path/to/repo-b && npx gitnexus analyze
```

Sau đó mở AI tool và dùng ngay trên nhiều repo.
