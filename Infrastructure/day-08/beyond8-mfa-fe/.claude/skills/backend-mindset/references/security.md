# Security — Backend Principles

Secrets, input validation, injection, auth, error responses, PII, rate limiting.

## 1. Secrets Management

Never hardcode secrets in source code or config files committed to version control.

- Dev: use environment-local secret stores (dotenv, user secrets, OS keychain)
- Prod: environment variables or a secrets vault (Vault, AWS Secrets Manager, etc.)
- Rotate regularly; never log secrets

---

## 2. Input Validation

Validate all input at the transport boundary before it reaches business logic:
- Required fields present
- Type and format correct (length, pattern, enum values)
- File uploads: validate size + MIME type + extension

Validators check **shape** only — business rule violations (uniqueness, ownership) belong in the service layer.

---

## 3. Injection Prevention

- Use parameterized queries / ORM — never string-interpolate user input into SQL, shell commands, or HTML
- Escape output in templating engines
- Validate and sanitize file paths (no `../` traversal)

---

## 4. Authentication & Authorization

- Every endpoint must explicitly declare auth requirement — no implicit defaults
- Check **ownership** before mutations: verify the caller owns the resource or has the required role
- Use a centralized identity abstraction (`ICurrentUserService`, middleware) — never parse raw auth tokens in business logic
- Use role/permission constants — never magic strings

---

## 5. Error Responses

Never expose stack traces, exception messages, or internal structure to clients.

- Expected failures (404, 400, 409): return a structured error envelope
- Unexpected failures (500): return a generic message, log the detail server-side
- Global exception handler catches anything that escapes the service layer

---

## 6. PII & Credentials in Logs

Never log: passwords, tokens, full credit card numbers, SSNs, raw emails if sensitive.

Log identifiers (userId, orderId), not values. Mask partial data when needed (e.g., last 4 digits only).

---

## 7. Rate Limiting

Mandatory on:
- Auth endpoints (login, OTP, password reset)
- File upload endpoints
- Any endpoint callable by unauthenticated users

---

## Pre-Deployment Checklist

- [ ] No hardcoded secrets — env vars or vault
- [ ] All mutating endpoints validate input before service call
- [ ] No raw SQL string interpolation
- [ ] Every endpoint has explicit auth declaration
- [ ] Ownership checked before mutations
- [ ] No stack traces in error responses
- [ ] No credentials or PII in logs
- [ ] Rate limiting on auth + upload endpoints
- [ ] HTTPS enforced in production
- [ ] Soft delete only — queries filter deleted records
- [ ] Dependencies audited for known CVEs
