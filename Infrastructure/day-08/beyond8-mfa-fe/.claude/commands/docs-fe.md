---
description: Generate a concise FE handoff doc for changed endpoints — branch, APIs, request/response contracts, search params, error codes
argument-hint: [blank = git changes | feature/<name> | path/to/file | "keyword"]
---

Generate a frontend handoff document.

**Input:** `$ARGUMENTS`

## Mode Selection

| Input | Mode | Scope |
|-------|------|-------|
| blank | **git** | staged + unstaged changes (`git diff HEAD`) |
| starts with `feature/` or `feat/` | **feature** | endpoint files matching that feature name |
| ends with a file extension (`.cs`, `.ts`, `.py`, …) | **file** | that specific file |
| any other text | **keyword** | search endpoint files for the keyword |

---

## Steps

### 1. Resolve scope

**git mode:** run `git diff --name-only HEAD` + `git diff --cached --name-only`. Filter to changed files that contain endpoint/route definitions.

**feature mode:** search the API layer for files matching the feature name. Check `CLAUDE.md` for the project's API file locations; fall back to common patterns:
- `src/**/Api/**/*{keyword}*.cs` (.NET)
- `src/**/routes/**/*{keyword}*` (Node/Express)
- `**/views.py` or `**/router.py` (Python)

**file mode:** use the given path directly.

**keyword mode:** glob API layer files, then grep content for the keyword.

If no endpoint files found, stop: "No changed endpoint files found. Pass a feature name, file path, or keyword."

### 2. Determine commit type and title

From the resolved scope and (if git mode) recent commits `git log --oneline -5`, determine:
- **commit type**: `feat`, `refactor`, or `fix`
- **short title in kebab-case**
- **date**: today's date in `YYYY-MM-DD`

Save as: `docs/fe/{YYYY-MM-DD}-{type}-{short-title}.md`

### 3. Identify changed endpoints

Read the resolved files to list every endpoint added or modified:
- HTTP method + path
- Auth requirement (roles or "any authenticated user")
- Brief purpose (1 line)

### 4. Collect contracts

For each changed endpoint, read relevant DTO/schema/validator/serializer files:

**Request:**
- Route params
- Query params (search, pagination, filters)
- Body fields (name, type, required/optional, constraints)

**Response:**
- `data` shape and fields
- Pagination metadata if paged

### 5. Collect error codes

Scan changed service/handler files for new or changed error codes/messages used in this feature:

| HTTP | code | message |
|------|------|---------|

### 6. Write the document

Save to `docs/fe/{date}-{type}-{title}.md`:

```markdown
# FE Handoff: {Human-readable title}

> Branch: `{current git branch}`
> Date: {YYYY-MM-DD}

## 1) Endpoint map

- `METHOD /path` — one-line description

## 2) Contracts

### {endpoint title}

`METHOD /full/path`

**Auth:** {roles or "any authenticated user"}

**Query params:** (if applicable)
| Param | Type | Default | Note |
|-------|------|---------|------|

**Body:** (if applicable)
```json
{ "field": "example" }
```

Validation rules:
- ...

**Response `data`:**
- `field` — type, description

## 3) Error codes

| HTTP | code | message |
|------|------|---------|

## 4) FE notes

Short bullet list of gotchas, suggested call order, or UX considerations.
```

Keep the document concise — no filler, no repeating information already obvious from the contract.
