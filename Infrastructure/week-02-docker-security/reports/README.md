# Security reports (week 02)

## Trivy (Ngày 13 local / Ngày 18 CI)

**Local** (sau `docker compose build api web`):

```bash
cd Infrastructure/week-02-docker-security
trivy image --severity HIGH,CRITICAL --ignore-unfixed beyond8-api:latest > reports/trivy-api-after.txt
trivy image --severity HIGH,CRITICAL --ignore-unfixed beyond8-web:latest > reports/trivy-web-after.txt
```

**CI (Ngày 18):** workflow `beyond8-trivy-image-scan.yml` build `beyond8-api:$GITHUB_SHA` / `beyond8-web:$GITHUB_SHA`, gate **CRITICAL**, artifact `trivy-reports-*` → `trivy-api-ci.txt`, `trivy-web-ci.txt`.

Nếu Trivy báo lỗi DB (panic bbolt): `trivy clean --vuln-db` rồi quét lại.

## Snyk (Ngày 17 — SCA)

Local:

```bash
cd beyond8-mfa-fe && snyk test --json > ../reports/snyk-frontend.json
cd ../beyond8-mfa && snyk test --json --file=requirements.txt > ../reports/snyk-backend.json
```

CI: tải artifact `snyk-reports-*` từ GitHub Actions sau khi workflow chạy.
