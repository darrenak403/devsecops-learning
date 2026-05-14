# Beyond8 Auth API - Backend Service

Hệ thống cung cấp service xác thực (Auth) và hệ thống sinh mã OTP (dạng Stateless OTP Auto-rotate) cho hệ sinh thái khóa học Beyond8.

👉 **Nếu bạn là Frontend Developer**, vui lòng xem hướng dẫn chi tiết về API và luồng tích hợp tại file: **[FE_INTEGRATION_PLAN.md](./FE_INTEGRATION_PLAN.md)**

---

## 1. Kiến trúc hệ thống

Hệ thống được xây dựng bằng thiết kế **Stateless OTP với HMAC time-window**:

- **Không lưu OTP "rác" vào database:** Quá trình hàm `generate_otp()` chạy thuần túy logic HMAC, không tốn bất kỳ operation Write nào xuống DB.
- **Auto-rotate:** Lưu lại `rotate_count` trong database (singleton table `otp_state`). Mỗi lần một tài khoản xác thực mã thành công, biến `rotate_count` tăng một đơn vị lập tức làm thay đổi khóa OTP hiện hành của toàn hệ thống, khiến OTP cũ bị tiêu hủy và trở nên vô nghĩa với những người dùng phía sau.
- **Bảo mật tuyệt đối:** Audit log chỉ luu đúng bản ghi vào bảng `otp_verifications` **DUY NHẤT** khi một phiên kích hoạt thành công (dùng Unique ID trên time-window để chống race conditions / double spend).

### 1.1 Quy ước kiến trúc code (refactor-safe)

- Luồng chuẩn cho module: `endpoint -> service -> crud -> db/models`.
- Endpoint chỉ làm routing, DI, map request/response; không gọi DB layer trực tiếp.
- Service chứa business logic và orchestration, không nhúng SQL.
- CRUD tập trung đọc/ghi dữ liệu; không chứa HTTP contract dành riêng endpoint.
- Transaction owner mặc định là request scope (`get_db`), tránh commit phân tán trong nhiều tầng.
- Module mới nên đi theo template: `api/v1/endpoints/<module>.py`, `services/<module>_service.py`, `crud/crud_<module>.py`, `schemas/<module>.py`, test service + API contract.

## 2. Các tham số Môi trường (.env)

Tạo file `.env` ở thư mục gốc của repo (cùng cấp với `app/`):

```env
APP_NAME=Beyond8 Auth Service
API_PREFIX=/api

DATABASE_URL=postgresql+psycopg2://postgres.<ref>:<password>@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres

JWT_SECRET_KEY=replace-with-strong-secret
JWT_ALGORITHM=HS256
COURSE_ACCESS_TOKEN_EXPIRE_DAYS=30

KEY_PREFIX=BY8
OTP_TTL_SECONDS=60
OTP_REFRESH_COOLDOWN_SECONDS=60

CORS_ORIGINS=http://127.0.0.1:5500,http://localhost:5500,http://localhost:3000,http://127.0.0.1:8989,http://localhost:8989,https://source.beyond8.io.vn,https://mfa.beyond8.io.vn,https://hoctot.beyond8.io.vn
```

## 3. Khởi tạo Backend Cục bộ (Local commands)

Hệ thống nên được đưa vào venv để khởi chạy:

```bash
# Ở thư mục gốc của repo backend

# Cài đặt dependencies
.venv\Scripts\pip.exe install -r requirements.txt

# Tự động đẩy DB lên trạng thái mới nhất
.venv\Scripts\python.exe run_migration.py

# Khởi chạy server API
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3636
```

## 4. Question Sources — phân trang

### 4.1 Danh sách (mặc định `page=1`, `limit=10`, tối đa `limit=100`)

Các endpoint sau luôn trả `data` dạng object **`{ items, page, limit, total, totalPages, hasNext, hasPrevious }`**:

- `GET /api/v1/subjects`
- `GET /api/v1/admin/question-sources/subjects`
- `GET /api/v1/admin/question-sources/subjects/{slug}/sources`
- `GET /api/v1/subjects/{slug}/decks`

### 4.2 Ngân hàng câu (`/bank`) — do FE chỉ định trang

`GET /api/v1/subjects/{slug}/bank`

- **Không `page`:** `data` là **mảng** toàn bộ câu (hành vi cũ).
- **Có `page`:** `data` là object phân trang như mục 4.1; `limit` tùy chọn (mặc định 10, tối đa 100).

### 4.3 Câu theo từng đề (`/decks/{deck_id}/questions`)

`GET /api/v1/subjects/{slug}/decks/{deck_id}/questions`

- **Không query:** `data` là **mảng** toàn bộ câu (hành vi cũ, có cache Redis full deck).
- **Có `page` (≥1):** `data` là **object** phân trang.
  - `limit`: tùy chọn, 1–50; **mặc định 1** khi chỉ gửi `page` (một câu mỗi trang).
  - `total` lấy từ `question_count` của deck trên DB.
  - Mỗi phần tử `items` vẫn có `answer`. Muốn chấm điểm tin cậy, dùng `POST .../questions/{question_id}/check`.

Ví dụ một câu mỗi trang: `.../questions?page=2` (tương đương `page=2&limit=1`). Sau khi trả lời đúng, client gọi trang tiếp theo.
