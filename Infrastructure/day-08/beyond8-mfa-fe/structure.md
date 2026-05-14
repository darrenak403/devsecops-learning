# Research Hub Client — Kiến trúc, pattern & data layer

Tài liệu tóm tắt **design pattern**, **architecture**, **cách gọi API** và **custom hook** của frontend.  
Chi tiết đầy đủ hơn nằm trong `.claude/skills/01-architecture.md`, `.claude/skills/02-api-and-hooks.md` và `.claude/skills/04-code-flow.md`.

---

## 0. Nguyên tắc render khi deploy (SSR-first)

Mục tiêu triển khai: **luôn render HTML trước** để tối ưu SEO, TTFB và perceived performance; sau đó client mới hydrate và gọi API bổ sung.

### 0.1 Chiến lược bắt buộc

1. **Ưu tiên Server Components** cho page/segment chính để trả HTML sớm từ server.
2. **Client Components** chỉ dùng cho phần có tương tác (filter, tab động, mutation, dialog...).
3. Nếu dữ liệu chưa sẵn sàng hoặc fetch ở client:
   - render **Skeleton** ngay trong HTML ban đầu hoặc fallback gần nhất;
   - sau khi client mount mới gọi API qua React Query hooks.
4. Tận dụng `loading.tsx` ở route segment để có loading UI nhất quán.
5. Không chặn toàn bộ trang vì một API phụ; giữ khung UI tĩnh + skeleton từng vùng.

### 0.2 Pattern Server + Client Components

```text
Server Page (RSC)
  -> render layout + HTML khung + truyền params ban đầu
  -> nhúng Client Feature Component

Client Feature Component ("use client")
  -> gọi useQuery/useMutation qua custom hooks
  -> trong lúc loading: render Skeleton
  -> khi có data: render bảng/card/form
```

### 0.3 Checklist nhanh cho mỗi page

- Có thể render phần nào ở server thì render trước.
- Có `loading.tsx` hoặc skeleton fallback cho vùng dữ liệu chính.
- API call nằm trong `hooks/` (không gọi trực tiếp trong component UI).
- Tránh layout shift: skeleton giữ kích thước gần với content thật.

---

## 1. Stack & vai trò từng phần

| Layer | Công nghệ | Vai trò |
|-------|-----------|---------|
| Framework | Next.js (App Router) | Routing, layouts, RSC/client boundaries |
| UI | Tailwind CSS v4, Radix UI, Framer Motion | Component primitive, token semantic, motion dialog |
| Client auth state | Redux Toolkit + redux-persist | User, token, session client |
| Server state | TanStack React Query | Cache, refetch, mutations, invalidation |
| HTTP | Axios (một instance) | Gọi backend `NEXT_PUBLIC_API_URL` |
| Realtime | SignalR (provider riêng) | Thông báo / cập nhật realtime (ngoài phạm vi HTTP bảng dưới) |

---

## 2. Kiến trúc thư mục (tóm tắt)

```text
app/                        -> App Router: `page.tsx`, `layout.tsx`, route groups `(admin)`, `(auth)`, `(project)`, ...
components/ui/              -> Thành phần dùng chung (Button, Dialog, ...)
components/layout/          -> AppLayout, sidebar, header
components/widget/<domain>/ -> Dialog/form theo feature, thường lazy-load
hooks/                      -> useQuery / useMutation bọc service
lib/api/core.ts             -> Axios singleton + interceptors
lib/api/services/*.ts       -> Hàm gọi API theo domain (fetchProject, fetchUsers, ...)
lib/navigation.ts           -> Link, useRouter, usePathname (helper điều hướng của dự án)
lib/providers/              -> QueryClientProvider, SignalR, ...
lib/redux/                  -> Store, authSlice
types/api.ts                -> ApiResponse, ApiError dùng chung
```

**Nguyên tắc đặt file:** UI tái sử dụng -> `components/ui/`; form dialog theo nghiệp vụ -> `components/widget/`; HTTP thuần -> `lib/api/services/`; tương tác server từ React -> `hooks/`.

### 2.1 Components colocated trong `app/`

Code UI **chỉ phục vụ một nhánh route** nên đặt **cạnh** `page.tsx` của nhánh đó, trong thư mục `components/`, thay vì kéo hết logic vào một file page dài.

| Thư mục | Mục đích |
|--------|-----------|
| `components/features/<TenFeature>/` | Một tab, một kênh, hoặc một màn nghiệp vụ. Thường có `page.tsx` (entry, có thể default export) hoặc file `*Feature.tsx` làm container. |
| `components/features/<TenFeature>/components/` | Sub-component chỉ dùng trong feature đó (bảng, card, form nhỏ, ...). |
| `components/layout/` *(tuỳ route)* | Khung riêng segment (sidebar, danh sách panel, ...), import từ `page.tsx` hoặc từ container feature. |

Càng **sâu trong URL** (ví dụ project theo `slug`, rồi major -> course), có thể lồng thêm `components/features/Major/Course/...` để mirror cấu trúc nghiệp vụ - vẫn là **colocation**: file gần route dùng nhiều nhất.

Phần **shared** toàn app (`Button`, `Dialog`, widget dialog dùng nhiều role) vẫn nằm ở `components/ui/` và `components/widget/`, không duplicate vào `app/` trừ khi thật sự chỉ dùng một route.

### 2.2 Import vào page chính

1. **`page.tsx`** (hoặc client wrapper cạnh đó, ví dụ `AdminRolePageClient.tsx`) đảm nhiệm **điều phối**: đọc query/tab, gọi vài hook dữ liệu tối thiểu, render nhánh đúng feature.
2. Page **không** chứa toàn bộ JSX nghiệp vụ: import **một lớp** từ `./components/features/...` (đường dẫn **relative** so với file đang đứng).
3. **Bên trong** một feature lớn (container kiểu `ProjectMainContent`), tiếp tục import các màn con bằng path **relative trong cùng cây** `components/features/` (ví dụ `./Overview/page`, `./Major/Course/CourseQuestion/page`).
4. Mọi thứ **dùng chung** giữ nguyên alias **`@/`**: `@/components/ui/...`, `@/hooks/...`, `@/lib/...` - không import chéo từ `app/` của route khác (tránh coupling); nếu cần share giữa nhiều app route, cân nhắc nâng lên `components/widget/` hoặc `hooks/`.

---

## 3. Design patterns chính

### 3.1 Phân tách state: Redux vs React Query

- **Redux:** chỉ **auth** (token, user, logout). Không dùng Redux để list/detail API.
- **React Query:** toàn bộ **dữ liệu từ server** (list, detail, mutation). Cache theo `queryKey`, refetch sau mutation qua `invalidateQueries`.

### 3.2 Layered data access (Repository-style trên client)

Luồng bắt buộc khi thêm/chỉnh feature có API:

```text
Types (DTO / response) -> fetch*.ts (service) -> hooks/use*.ts -> Page / Dialog / Component
```

Component **không** import `apiService` trực tiếp để CRUD; chỉ gọi hook.

### 3.3 Singleton HTTP client

- Một **`ApiService`** trong `lib/api/core.ts`, export **`apiService`**.
- Interceptor: gắn Bearer token, xử lý 401 + refresh token, chuẩn hóa lỗi, hỗ trợ FormData (bỏ `Content-Type` để browser set boundary).
- **Không** `axios.create()` mới trong feature.

### 3.4 Query Key Factory

Trong `hooks/use*.ts`, export object dạng `*_QUERY_KEYS` (ví dụ `PROJECT_QUERY_KEYS`) với:

- `all` -> root key domain
- `lists()`, `list(params)`, `details()`, `detail(id)` -> cấu trúc phân cấp để `invalidateQueries` theo nhánh (invalidate `lists()` refetch mọi list con).

### 3.5 Điều hướng

- Ưu tiên **`Link`, `useRouter`, `usePathname`** từ `@/lib/navigation` thay cho import trực tiếp từ `next/link` hoặc `next/navigation` khi codebase dùng helper này.

---

## 4. Cách fetch API (chi tiết)

### 4.1 Bước 1 — Types

- Dùng **`ApiResponse<T>`**, **`ApiError`** từ `types/api.ts` khi khớp chuẩn backend.
- Request/response đặc thù domain: khai báo trong **`lib/api/services/fetchX.ts`** (hoặc file types chung nếu dùng nhiều nơi).

### 4.2 Bước 2 — Service (`lib/api/services/fetch*.ts`)

- Import **`apiService`** từ `@/lib/api/core`.
- Export object (ví dụ `fetchProjects`, `fetchUsers`) chứa các hàm `async`:
  - `apiService.get/post/put/patch/delete` (và `request` khi cần blob / tùy biến).
- Path thường dạng **`api/v1/...`** (tương đối `baseURL`).
- Hàm service trả về **`response.data`** (unwrap Axios), type là body JSON đã thỏa thuận với backend.

### 4.3 Query params

- Backend .NET thường dùng **PascalCase** query; trong code có helper chuyển từ object params -> `RequestParams` trong `core` / helper riêng từng service.

### 4.4 Upload / media

- `fetchMedia`: presign + confirm qua API app; upload binary lên URL presign có thể dùng axios riêng (không qua `apiService` base) - xem `fetchMedia.ts`.

---

## 5. Custom hook (React Query)

### 5.1 Query (`useQuery`)

- `queryKey`: dùng factory ở trên (đủ tham số để cache đúng trang/filter).
- `queryFn`: gọi một hàm trong `fetch*.ts`.
- `select`: tùy chọn - map response -> shape gọn cho UI (items, pagination, `hasNextPage`, ...).
- `enabled`: chỉ fetch khi có `id` / điều kiện business.
- `placeholderData: keepPreviousData`: giữ UI ổn khi đổi trang/filter.
- `staleTime`: tuỳ độ "tươi" của dữ liệu (ví dụ vài phút cho list ít đổi).

### 5.2 Mutation (`useMutation`)

- `mutationFn`: gọi service POST/PUT/PATCH/DELETE.
- `onSuccess`: `toast.success` (hoặc feedback tương đương), `queryClient.invalidateQueries({ queryKey: ... })` đúng nhánh key.
- `onError`: hiển thị lỗi (ví dụ `toast.error`) từ `ApiError` (`message`, `code`, ...) theo convention UI của dự án.

### 5.3 Hook không chỉ “API”

- `hooks/` có thể chứa hook UI (`use-mobile`, ...) hoặc helper scroll vô hạn (`useInfinityScroll`) - tách biệt với hook domain `useProject`, `useUsers`, ...

---

## 6. Luồng end-to-end (một feature mới)

1. Thêm/cập nhật **interface** (request/response/params).
2. Thêm hàm vào **`lib/api/services/fetch....ts`** dùng `apiService`.
3. Thêm **`useQuery` / `useMutation`** trong **`hooks/use....ts`** + query keys + invalidate.
4. Gắn vào **page / widget dialog**; không gọi service trực tiếp từ component.
5. Bổ sung **loading state bằng skeleton** cho vùng dữ liệu chính để phù hợp SSR-first.

---

## 7. Tham chiếu nhanh

| Mục | File / thư mục |
|-----|----------------|
| Axios + token + refresh (+ Bearer cookie MFA khi Redux chưa có token) | `lib/api/core.ts` |
| Điều hướng tập trung | `lib/navigation.ts` |
| Service ví dụ (deck / học theo đề) | `lib/api/services/fetchDeckProgress.ts` |
| Hook + query keys ví dụ | `hooks/useDeckProgress.ts` |
| Api types chung | `types/api.ts` |
| Query provider | `lib/providers/queryProvider.tsx` |
| Danh sách endpoint đã dùng | `docs/used-api-endpoints.md` |

---

## 8. Mẫu skeleton theo Client Component

```tsx
"use client";

import { useGetProjects } from "@/hooks/useProjects";
import { Skeleton } from "@/components/ui/skeleton";

export function ProjectListClient() {
  const { data, isLoading, isFetching } = useGetProjects({ pageNumber: 1, pageSize: 10 });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, idx) => (
          <Skeleton key={idx} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* render data thật */}
      {isFetching && <div className="text-sm text-muted-foreground">Refreshing...</div>}
      {/* ... */}
    </div>
  );
}
```

> Gợi ý: Kết hợp `loading.tsx` (route-level fallback) + skeleton trong client feature để có trải nghiệm mượt cho cả initial load và refetch.

---

*Tài liệu này phản ánh convention của repo tại thời điểm viết; khi đổi skill hoặc rule trong `.cursor/`, nên cập nhật `structure.md` cho khớp.*
