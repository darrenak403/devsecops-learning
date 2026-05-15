# Trivy reports (Ngày 13)

Xuất mẫu:

```bash
cd Infrastructure/week-02-docker-security
trivy image --severity HIGH,CRITICAL beyond8-api:latest > reports/trivy-api-after.txt
trivy image --severity HIGH,CRITICAL beyond8-web:latest > reports/trivy-web-after.txt
```

Nếu Trivy báo lỗi DB (panic bbolt): `trivy clean --vuln-db` rồi quét lại.
