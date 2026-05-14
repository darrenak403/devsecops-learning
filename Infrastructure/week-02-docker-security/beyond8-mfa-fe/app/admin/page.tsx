"use client";

import { Suspense, useCallback, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { usePathname, useRouter, useSearchParams } from "@/lib/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sidebar, SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { useMobile } from "@/hooks/use-mobile";
import { hasAdminRole } from "@/lib/types/roles";

import { AdminSidebar, type AdminView } from "@/components/layout/AdminSidebar";
import { DeckMarkdownView } from "./components/deck-markdown/page";
import { QuestionManagementPlaceholder } from "./components/question/page";
import { UserManagementView } from "./components/user/page";

function parseAdminViewParam(raw: string | null): AdminView {
  if (raw === "questions") return "questions";
  if (raw === "deck-markdown") return "deck-markdown";
  return "users";
}

const VIEW_SUBTITLE: Record<AdminView, string> = {
  users: "Quản lý người dùng",
  questions: "Quản lý question sources",
  "deck-markdown": "Soạn deck markdown",
};

function AdminPageFallback() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#fcfaf6] px-4">
      <p className="text-sm text-muted-foreground">Đang tải trang quản trị…</p>
    </main>
  );
}

function AdminPageContent() {
  const isMobile = useMobile();
  const { user, doLogout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const viewParam = searchParams.get("view");
  const [activeView, setActiveView] = useState<AdminView>(() => parseAdminViewParam(viewParam));

  const handleSelectView = useCallback(
    (nextView: AdminView) => {
      setActiveView(nextView);
      const params = new URLSearchParams(searchParams.toString());
      params.set("view", nextView);
      router.replace(`${pathname}?${params.toString()}`);
    },
    [pathname, router, searchParams]
  );

  const roles = Array.isArray(user?.role) ? user.role : [];
  const legacyAdminSubstring =
    roles.join(" ").toLowerCase().includes("admin");
  if (!user || (!hasAdminRole(roles) && !legacyAdminSubstring)) {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-4 py-10">
        <Card className="w-full">
          <CardHeader>
            <CardTitle>Không có quyền truy cập</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Trang admin này chỉ dành cho tài khoản `admin`.
            </p>
            <div className="mt-4">
              <Button onClick={doLogout}>Quay lại đăng nhập</Button>
            </div>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="flex h-dvh flex-col overflow-hidden bg-[#fcfaf6] text-foreground">
      <SidebarProvider defaultOpen={!isMobile} className="flex min-h-0 flex-1 flex-col">
        <section className="relative flex min-h-0 flex-1 w-full overflow-hidden">
          <Sidebar className="border-r bg-white">
            <AdminSidebar
              activeView={activeView}
              onSelectView={handleSelectView}
              userEmail={user.email}
              onLogout={doLogout}
            />
          </Sidebar>

          <SidebarInset className="bg-[#fcfaf6]">
            <div className="flex h-full min-h-0 flex-col">
              <div className="flex shrink-0 items-center justify-between gap-2 border-b px-4 py-2 md:px-6">
                <p className="min-w-0 truncate text-sm text-muted-foreground">{VIEW_SUBTITLE[activeView]}</p>
                <SidebarTrigger aria-label="Đóng / mở menu điều hướng" />
              </div>
              <div
                className={
                  activeView === "deck-markdown"
                    ? "flex min-h-0 w-full flex-1 flex-col overflow-hidden px-3 py-4 sm:px-4 sm:py-5 md:px-6 md:py-6"
                    : "min-h-0 w-full flex-1 overflow-auto px-3 py-4 sm:px-4 sm:py-5 md:px-6 md:py-6"
                }
              >
                {activeView === "users" ? (
                  <UserManagementView />
                ) : activeView === "questions" ? (
                  <QuestionManagementPlaceholder />
                ) : (
                  <DeckMarkdownView />
                )}
              </div>
            </div>
          </SidebarInset>
        </section>
      </SidebarProvider>
    </main>
  );
}

export default function AdminPage() {
  return (
    <Suspense fallback={<AdminPageFallback />}>
      <AdminPageContent />
    </Suspense>
  );
}
