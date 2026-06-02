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

---

## Trivy image scan (Ngày 18)

Workflow: **`.github/workflows/beyond8-trivy-image-scan.yml`** (root repo `DevSecOps-30-days`).

**Không cần secret** — chỉ build + scan trên runner GitHub.

**Trigger:** push/PR lên `main`/`master` khi đổi `Infrastructure/week-02-docker-security/**`, hoặc **Run workflow** thủ công.

**Luồng CI:**

```text
Checkout → tạo .env CI → docker build API/Web
  → Trivy report (HIGH,CRITICAL) → upload artifact
  → Trivy gate CRITICAL (fail pipeline nếu còn CRITICAL có bản vá)
```

| Image tag | Nguồn build |
|-----------|-------------|
| `beyond8-api:${{ github.sha }}` | `beyond8-mfa/Dockerfile` |
| `beyond8-web:${{ github.sha }}` | `beyond8-mfa-fe/Dockerfile` |

**Policy hiện tại:**

```yaml
severity: CRITICAL
exit-code: '1'
ignore-unfixed: true
vuln-type: os,library
```

Sau khi image sạch hơn, có thể nâng gate lên `HIGH,CRITICAL`.

**Artifact:** `trivy-reports-<run_id>` gồm `trivy-api-ci.txt`, `trivy-web-ci.txt` (Actions → run → Artifacts).

### Local (tuỳ chọn, Ngày 12–13)

```bash
cd Infrastructure/week-02-docker-security
docker compose build api web
docker tag beyond8-api beyond8-api:latest   # tên image sau compose có thể là beyond8-api
trivy image --severity HIGH,CRITICAL --ignore-unfixed beyond8-api:latest
trivy image --severity HIGH,CRITICAL --ignore-unfixed beyond8-web:latest
```

Xem thêm `reports/README.md` và file `reports/trivy-*-after.txt` (scan local trước đó).

### Lỗi thường gặp

| Lỗi | Cách xử lý |
|-----|------------|
| Trivy không tìm thấy image | Kiểm tra step **Show built images**; `image-ref` phải trùng tag vừa `docker build -t`. |
| Gate CRITICAL fail | `docker build --pull --no-cache`, cập nhật base image / dependency, scan lại. |
| Scan rất lâu (lần đầu) | Trivy tải vulnerability DB; các lần sau nhanh hơn. |
| Report không upload | Bước generate report dùng `continue-on-error`; gate CRITICAL chạy sau. |

**Phân biệt pipeline:** Ngày 15 = build; Ngày 16 = SAST; Ngày 17 = SCA manifest; **Ngày 18 = scan image vừa build**.

---

## Push image lên DOCR (Ngày 19)

Workflow: **`.github/workflows/beyond8-docr-push.yml`**.

**Secret bắt buộc:** `DIGITALOCEAN_ACCESS_TOKEN` (DigitalOcean Personal Access Token, quyền đọc/ghi Container Registry).

**Chỉ chạy khi push `main`/`master`** — không push trên PR (an toàn hơn).

**Luồng:**

```text
Build image (tag DOCR đầy đủ)
  → Trivy CRITICAL gate
  → doctl registry login
  → docker push API + Web
  → Cosign sign + verify (Ngày 20)
```

| Image trên DOCR | Ví dụ |
|-----------------|--------|
| API | `registry.digitalocean.com/devsecops-registry/beyond8:api-<sha>` |
| Web | `registry.digitalocean.com/devsecops-registry/beyond8:web-<sha>` |

**DOCR Starter** chỉ cho **1 repository** trong registry — workflow dùng **một repo `beyond8`**, hai tag `api-*` / `web-*` (không tách `beyond8-api` + `beyond8-web`). Nâng plan DO nếu muốn 2 repository riêng.

Mặc định workflow dùng registry name **`devsecops-registry`** — sửa `DOCR_REGISTRY_NAME` trong file workflow nếu bạn đặt tên khác trên DigitalOcean.

Nếu lần push trước đã tạo repo `beyond8-api` trên DO: **xóa repository đó** (tab Repositories) rồi re-run workflow để tránh vẫn占 slot 1/1.

**Day 19 PASS:** Trivy pass → push thành công → thấy 2 repository trên DO UI.

### Local test trước CI (tuỳ chọn)

```bash
brew install doctl
doctl auth init

doctl registry create devsecops-registry --region sgp1   # bỏ qua nếu đã có
doctl registry login

cd Infrastructure/week-02-docker-security
docker build -t beyond8-api:local ./beyond8-mfa
docker build -t beyond8-web:local ./beyond8-mfa-fe

docker tag beyond8-api:local registry.digitalocean.com/devsecops-registry/beyond8:api-local
docker tag beyond8-web:local registry.digitalocean.com/devsecops-registry/beyond8:web-local
docker push registry.digitalocean.com/devsecops-registry/beyond8:api-local
docker push registry.digitalocean.com/devsecops-registry/beyond8:web-local

doctl registry repository list
```

### Lỗi thường gặp

| Lỗi | Cách xử lý |
|-----|------------|
| `unauthorized` / `authentication required` | Kiểm tra `DIGITALOCEAN_ACCESS_TOKEN`; token cần quyền registry read/write. |
| `registry not found` | Tạo registry trên DO hoặc sửa `DOCR_REGISTRY_NAME` cho khớp. |
| Trivy fail, không push | Đúng thiết kế — sửa image rồi push lại. |
| `requested access denied` | Sai format tag; phải `registry.digitalocean.com/<registry>/<image>:<tag>`. |
| `registry contains 1 repositories, limit is 1` | Plan Starter — xóa repo cũ trên DO, dùng 1 repo `beyond8` + tag `api-*`/`web-*` (workflow đã cấu hình). |

**Cleanup:** Xóa tag `local` / SHA cũ trên DO khi học xong để giảm dung lượng registry.

---

## Cosign ký image (Ngày 20)

Workflow: **cùng file** `.github/workflows/beyond8-docr-push.yml` (job đã gộp Ngày 19 + 20).

**Secret thêm:** không cần — dùng **Cosign keyless** qua GitHub OIDC (`id-token: write`).

**Luồng sau push:**

```text
Resolve digest (@sha256:…)
  → cosign sign --yes (keyless)
  → cosign verify (đúng repo + issuer GitHub Actions)
```

| Image | Ký theo |
|-------|---------|
| API | `registry.digitalocean.com/.../beyond8@sha256:…` (digest tag `api-<sha>`) |
| Web | cùng repo `beyond8`, digest riêng |

**Day 20 PASS:** Actions xanh tới **Verify API/Web image signature**; log có digest + verify OK.

### Verify local (tuỳ chọn)

Sau khi CI chạy, copy digest từ log workflow:

```bash
brew install cosign
doctl registry login

cosign verify registry.digitalocean.com/devsecops-registry/beyond8@sha256:<digest-api> \
  --certificate-identity-regexp "https://github.com/<owner>/<repo>/.github/workflows/.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

### Lỗi thường gặp

| Lỗi | Cách xử lý |
|-----|------------|
| Cosign sign fail OIDC | Thêm `id-token: write` trong workflow `permissions`. |
| Verify identity mismatch | Regexp phải khớp `github.repository` thật (owner/repo). |
| Sign/verify unauthorized | Chạy `doctl registry login` trước (CI đã login trước push). |
| Không lấy được digest | Push phải thành công; `docker inspect` cần `RepoDigests`. |
