# Chạy nhanh — day-08 (Beyond8 MFA)

## Database & Redis hiện tại

- **Postgres**: image Docker `postgres:16-alpine`, user / mật khẩu / DB: `beyond8` / `beyond8` / `beyond8_mfa`, dữ liệu trong volume `beyond8_pgdata`, cổng host **`5432`**.
- **Redis**: image `redis:7-alpine`, cổng host **`6379`**.
- Khi chạy **full stack** bằng compose, API trong container **không** dùng `127.0.0.1` trong `.env` — compose **ghi đè** chuỗi kết nối trỏ tới service `db` và `redis` trong mạng Docker.

---

## Chỉ backend (API trên máy)

Cần `beyond8-mfa/.env` (DB/Redis trỏ `127.0.0.1` như đã cấu hình).

```bash
cd Infrastructure/day-08
docker compose up -d db redis
```

```bash
cd Infrastructure/day-08/beyond8-mfa
source .venv/bin/activate   # hoặc tạo .venv trước: python3 -m venv .venv
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API: `http://localhost:8000`

---

## Chỉ frontend (Next trên máy)

Cần API đang chạy (ví dụ cổng **8000**) và `beyond8-mfa-fe/.env` (`NEXT_PUBLIC_API_URL=http://localhost:8000`).

```bash
cd Infrastructure/day-08/beyond8-mfa-fe
npm install
npm run dev
```

App: `http://localhost:3000`

---

## Backend + frontend cùng lúc (trên máy, không Docker hóa API/FE)

Hai terminal:

1. `docker compose up -d db redis` (từ `Infrastructure/day-08`) → rồi uvicorn như mục **Chỉ backend**.  
2. `npm run dev` trong `beyond8-mfa-fe`.

---

## Tất cả trong Docker (db + redis + api + web)

Từ `Infrastructure/day-08`:

```bash
docker compose up --build
```

- API: `http://localhost:8000`  
- Web: `http://localhost:3000`  

Build web đúng theo `beyond8-mfa-fe/.env` (nếu cần):

```bash
docker compose --env-file ./beyond8-mfa-fe/.env up --build
```

---

## Gợi ý nhanh

| Mục | Giá trị |
|-----|--------|
| API (local / compose publish) | **8000** |
| Next (dev / compose) | **3000** |
| Postgres (host) | **5432** |
| Redis (host) | **6379** |

Dừng chỉ db + redis: `docker compose stop db redis`. Xóa luôn dữ liệu Postgres: `docker compose down -v` (cẩn thận: mất volume).
