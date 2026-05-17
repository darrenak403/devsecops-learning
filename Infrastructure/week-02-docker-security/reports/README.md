# Security reports (week 02)

## Trivy (Ngày 13 — image scan)

```bash
cd Infrastructure/week-02-docker-security
trivy image --severity HIGH,CRITICAL beyond8-api:latest > reports/trivy-api-after.txt
trivy image --severity HIGH,CRITICAL beyond8-web:latest > reports/trivy-web-after.txt
```

Nếu Trivy báo lỗi DB (panic bbolt): `trivy clean --vuln-db` rồi quét lại.

## Snyk (Ngày 17 — SCA)

Local:

```bash
cd beyond8-mfa-fe && snyk test --json > ../reports/snyk-frontend.json
cd ../beyond8-mfa && snyk test --json --file=requirements.txt > ../reports/snyk-backend.json
```

CI: tải artifact `snyk-reports-*` từ GitHub Actions sau khi workflow chạy.
