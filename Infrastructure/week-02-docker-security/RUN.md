# Beyond8 MFA — Docker (week 02)

Làm việc trong thư mục **`Infrastructure/week-02-docker-security`** khi dùng Docker Compose (project **`beyond8`**: container `beyond8-db`, `beyond8-redis`, …; volume Postgres **`beyond8_pgdata`**).

| Dịch vụ | Cổng (máy bạn) |
|---------|----------------|
| API | 8000 |
| Next | 3000 |
| Postgres | 5432 |
| Redis | 6379 |
| Adminer (UI Postgres) | 8080 |

---

## Một lần — cả stack (Postgres + Redis + API + Next)

```bash
cd Infrastructure/week-02-docker-security
docker compose up --build
```

- Web: http://localhost:3000  
- API: http://localhost:8000  
- **Adminer** (quản lý DB, image nhẹ): http://localhost:8080 — chọn hệ **PostgreSQL**, server **`db`**, user / pass / database: **`beyond8`** / **`beyond8`** / **`beyond8_mfa`**.

*(Tuỳ chọn: build FE đúng theo `beyond8-mfa-fe/.env` — `docker compose --env-file ./beyond8-mfa-fe/.env up --build`.)*

---

## Riêng từng repo (API / FE trên máy, DB + Redis bằng Docker)

**1. Bật DB + Redis (một lần, hoặc mỗi khi tắt Docker):**

```bash
cd Infrastructure/week-02-docker-security
docker compose up -d db redis adminer
```

Adminer: http://localhost:8080 — **PostgreSQL**, server **`db`**, user **`beyond8`**, mật khẩu **`beyond8`**, database **`beyond8_mfa`**.

**2. Backend** (`beyond8-mfa/.env` trỏ `127.0.0.1` cho DB/Redis):

```bash
cd Infrastructure/week-02-docker-security/beyond8-mfa
python3 -m venv .venv && source .venv/bin/activate   # lần đầu
pip install -r requirements-dev.txt
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**3. Frontend** (`beyond8-mfa-fe/.env` có `NEXT_PUBLIC_API_URL=http://localhost:8000`):

```bash
cd Infrastructure/week-02-docker-security/beyond8-mfa-fe
npm install
npm run dev
```

Hai repo = hai terminal (BE rồi FE).

---

## Lệnh Docker hay dùng

Tất cả chạy từ `Infrastructure/week-02-docker-security` (cùng chỗ với `docker-compose.yml`).

```bash
cd Infrastructure/week-02-docker-security
```

| Việc | Lệnh |
|------|------|
| Xem container đang chạy | `docker compose ps` |
| Xem log (tất cả) | `docker compose logs -f` |
| Log một service | `docker compose logs -f api` |
| Liệt kê volume Docker | `docker volume ls` (tìm `beyond8_pgdata`) |
| Dừng stack (giữ volume DB) | `docker compose stop` |
| Tắt và xóa container (giữ volume) | `docker compose down` |
| Tắt + xóa volume Postgres (**mất dữ liệu**) | `docker compose down -v` |
| Chỉ dừng db + redis + adminer | `docker compose stop db redis adminer` |
| Build lại rồi chạy | `docker compose up --build` |
| Vào shell Postgres | `docker compose exec db psql -U beyond8 -d beyond8_mfa` |
| Ping Redis | `docker compose exec redis redis-cli ping` |
| Chỉ bật UI DB (kèm Postgres) | `docker compose up -d db adminer` |

---

## GitHub Actions (Ngày 15 — CI build Docker)

Workflow nằm ở **root repo** `DevSecOps-30-days`:

```text
.github/workflows/beyond8-docker-ci.yml
```

**Kích hoạt:** push / PR lên `main` hoặc `master` khi đổi file trong `Infrastructure/week-02-docker-security/`, hoặc **Actions → Run workflow** (manual).

**CI làm gì:**

1. Checkout code  
2. Tạo `.env` tạm từ `.env.example` (không dùng secret thật)  
3. `docker compose build api web` — build image **beyond8-mfa** (API) và **beyond8-mfa-fe** (Web)

**Sau khi sửa Dockerfile / compose:** commit + push, mở tab **Actions** trên GitHub để xem pass/fail.

**Lưu ý:** Ngày 15 chưa push image lên Docker Hub / registry; chỉ kiểm tra build trên runner GitHub.

---

## SonarCloud SAST (Ngày 16)

Workflow: **`.github/workflows/beyond8-sonarcloud-sast.yml`** (root repo `DevSecOps-30-days`).

| Loại | Tên trên GitHub | Ghi chú |
|------|-----------------|--------|
| **Secret** | `SONAR_TOKEN` | Token từ SonarCloud → My Account → Security (bạn đã setup) |
| **Variable** | `SONAR_PROJECT_KEY` | Project key trên SonarCloud (vd. `org_repo`) |
| **Variable** | `SONAR_ORGANIZATION` | Organization key (vd. tên org SonarCloud) |

**Lấy key:** SonarCloud → chọn project đã import repo → **Project Information**.

**Trigger:** push/PR khi đổi code trong `beyond8-mfa/`, `beyond8-mfa-fe/`, hoặc **Run workflow** thủ công.

**Scan gì:** mã nguồn Python (`beyond8-mfa`) + TypeScript/Next (`beyond8-mfa-fe`) — **không** quét Docker image (Trivy là Ngày 18).

**Kết quả:** tab **Actions** trên GitHub + dashboard **SonarCloud** (Quality Gate, Bugs, Vulnerabilities, Security Hotspots).

Mẫu config local: `sonar-project.properties.example` (không commit `sonar-project.properties` nếu chỉ dùng CI generate).

**Lỗi thường gặp**

| Lỗi | Cách xử lý |
|-----|------------|
| `CI analysis while Automatic Analysis is enabled` | SonarCloud → **Administration → Analysis Method** → tắt **Automatic Analysis**, re-run workflow. |
| `can't be indexed twice` (file test) | `sonar.sources` không được chứa thư mục test; dùng `beyond8-mfa/app` + `sonar.tests=beyond8-mfa/app/tests` + exclude `**/app/tests/**` (đã cấu hình trong workflow). |

---

## Snyk SCA (Ngày 17)

Workflow: **`.github/workflows/beyond8-snyk-sca.yml`** (root repo `DevSecOps-30-days`).

| Loại | Tên trên GitHub | Ghi chú |
|------|-----------------|--------|
| **Secret** | `SNYK_TOKEN` | Snyk → **Account Settings → Auth Token** (Generate) |

**Trigger:** push/PR lên `main`/`master` khi đổi `beyond8-mfa/`, `beyond8-mfa-fe/`, hoặc **Run workflow** thủ công.

**Scan gì (SCA — thư viện, không phải source code):**

| Project | Manifest | Thư mục |
|---------|----------|---------|
| Web (Next.js) | `package.json` + `package-lock.json` | `beyond8-mfa-fe/` |
| API (Python) | `requirements.txt` (prod) | `beyond8-mfa/` |

**Chính sách mặc định:** `snyk test --severity-threshold=high` → job **fail** nếu có **HIGH** hoặc **CRITICAL** (đúng Lab 5 plan Ngày 17). Ngày 17 vẫn **đạt** nếu pipeline chạy được và bạn **đọc được** report (fix dần sau).

**Artifact:** JSON `reports/snyk-frontend.json`, `snyk-backend.json` (tải từ tab **Actions → run → Artifacts**).

### Local (tuỳ chọn)

```bash
brew install snyk
snyk auth

cd Infrastructure/week-02-docker-security/beyond8-mfa-fe
npm ci
snyk test --severity-threshold=high

cd ../beyond8-mfa
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
snyk test --severity-threshold=high --file=requirements.txt
```

### Lỗi thường gặp

| Lỗi | Cách xử lý |
|-----|------------|
| `Authentication failed` / thiếu token | Thêm `SNYK_TOKEN` trong GitHub Secrets. |
| `snyk: command not found` (local) | `brew install snyk` hoặc `npm install -g snyk`. |
| `npm ci` fail | Commit `package-lock.json` khớp `package.json`. |
| Job fail nhưng vẫn muốn lưu report | Workflow đã có bước upload JSON với `continue-on-error`. |

**Phân biệt:** Sonar (Ngày 16) = **SAST** (code); Snyk (Ngày 17) = **SCA** (dependency); Trivy image (Ngày 18) = OS/package trong Docker image.
