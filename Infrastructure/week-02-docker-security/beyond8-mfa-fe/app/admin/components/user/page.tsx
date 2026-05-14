"use client";

import { useCallback, useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import {
  useAdminStats,
  useAdminUsers,
  useBlockUser,
  useClearVerifiedOtpKey,
  useDeleteUserPermanently,
  useGenerateOtpByUserId,
  useUnblockUser,
} from "@/hooks/useAdmin";
import type { AdminUserItem } from "@/lib/api/services/fetchAdmin";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useMobile } from "@/hooks/use-mobile";
import { UserCardSkeletonList } from "./components/UserCardSkeletonList";
import { StatCard } from "./components/StatCard";
import { UserActionsMenu } from "./components/UserActionsMenu";
import { UserSearchBar } from "./components/UserSearchBar";
import { UserTableRow, USER_TABLE_PAGE_SIZE } from "./components/UserTableRow";
import { UserTableSkeleton } from "./components/UserTableSkeleton";

type UserFilter = "all" | "active" | "blocked";

export function UserManagementView() {
  const isMobile = useMobile();
  const [search, setSearch] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [filter, setFilter] = useState<UserFilter>("all");
  const [listPage, setListPage] = useState(1);
  const [deleteConfirmUserId, setDeleteConfirmUserId] = useState<string | null>(null);

  const { data: stats, isLoading: statsLoading } = useAdminStats();
  const {
    data: usersData,
    isLoading: usersLoading,
    isPlaceholderData: usersFetching,
  } = useAdminUsers({ search: activeSearch });
  const users = useMemo(() => usersData?.users ?? [], [usersData?.users]);
  const clearOtpMutation = useClearVerifiedOtpKey();
  const generateOtpMutation = useGenerateOtpByUserId();
  const blockMutation = useBlockUser();
  const unblockMutation = useUnblockUser();
  const deleteMutation = useDeleteUserPermanently();
  const totalRevenue = useMemo(
    () => `${new Intl.NumberFormat("vi-VN").format((stats?.total_successful_verifications || 0) * 35000)} VND`,
    [stats?.total_successful_verifications]
  );

  const filteredUsers = useMemo(() => {
    if (filter === "active") return users.filter((u) => u.is_active);
    if (filter === "blocked") return users.filter((u) => !u.is_active);
    return users;
  }, [filter, users]);

  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / USER_TABLE_PAGE_SIZE));
  const currentPage = Math.min(Math.max(1, listPage), totalPages);

  const paginatedUsers = useMemo(() => {
    const start = (currentPage - 1) * USER_TABLE_PAGE_SIZE;
    return filteredUsers.slice(start, start + USER_TABLE_PAGE_SIZE);
  }, [filteredUsers, currentPage]);

  const handleSearchSubmit = useCallback((e: FormEvent) => {
    e.preventDefault();
    setActiveSearch(search.trim());
    setListPage(1);
  }, [search]);

  const handleFilterChange = useCallback((next: UserFilter) => {
    setFilter(next);
    setListPage(1);
  }, []);

  const handleCopyOtp = useCallback((otp: string) => {
    navigator.clipboard
      .writeText(otp)
      .then(() => toast.success("Đã copy OTP"))
      .catch(() => toast.error("Không thể copy OTP"));
  }, []);

  const handleClearOtp = useCallback(
    (userId: string) => {
      clearOtpMutation.mutate({ userId, search: activeSearch || undefined });
    },
    [activeSearch, clearOtpMutation]
  );

  const handleGenerateOtp = useCallback(
    (userId: string) => {
      generateOtpMutation.mutate(userId);
    },
    [generateOtpMutation]
  );

  const handleBlockUser = useCallback(
    (userId: string) => {
      blockMutation.mutate({ userId, payload: { reason: "Khóa bởi admin từ trang quản trị" } });
    },
    [blockMutation]
  );

  const handleUnblockUser = useCallback(
    (userId: string) => {
      unblockMutation.mutate(userId);
    },
    [unblockMutation]
  );

  const handleDeleteUser = useCallback(
    (userId: string) => {
      setDeleteConfirmUserId(userId);
    },
    []
  );

  const handleConfirmDelete = useCallback(() => {
    if (!deleteConfirmUserId) return;
    deleteMutation.mutate(deleteConfirmUserId, {
      onSettled: () => setDeleteConfirmUserId(null),
    });
  }, [deleteConfirmUserId, deleteMutation]);

  const busyUserId = useMemo(() => {
    if (clearOtpMutation.isPending) return clearOtpMutation.variables?.userId;
    if (generateOtpMutation.isPending) {
      const v = generateOtpMutation.variables;
      return typeof v === "string" ? v : undefined;
    }
    if (blockMutation.isPending) return blockMutation.variables?.userId;
    if (unblockMutation.isPending) {
      const v = unblockMutation.variables;
      return typeof v === "string" ? v : undefined;
    }
    if (deleteMutation.isPending) {
      const v = deleteMutation.variables;
      return typeof v === "string" ? v : undefined;
    }
    return undefined;
  }, [
    clearOtpMutation.isPending,
    clearOtpMutation.variables,
    generateOtpMutation.isPending,
    generateOtpMutation.variables,
    blockMutation.isPending,
    blockMutation.variables,
    unblockMutation.isPending,
    unblockMutation.variables,
    deleteMutation.isPending,
    deleteMutation.variables,
  ]);
  const rowBusyMap = useMemo(() => new Set(busyUserId ? [busyUserId] : []), [busyUserId]);
  const isRowBusy = useCallback((item: AdminUserItem) => rowBusyMap.has(item.id), [rowBusyMap]);
  const deleteConfirmUserEmail = useMemo(() => {
    if (!deleteConfirmUserId) return "";
    return users.find((u) => u.id === deleteConfirmUserId)?.email || deleteConfirmUserId;
  }, [deleteConfirmUserId, users]);

  return (
    <div className="w-full min-w-0">
      <div className="mb-4 flex flex-col items-start gap-1 md:flex-row md:items-center md:justify-between">
        <h2 className="text-lg font-semibold">Tổng quan hệ thống</h2>
        <p className="text-xs text-muted-foreground md:text-sm">Theo dữ liệu realtime từ API admin</p>
      </div>

      <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard
          title="Số lượt mua key"
          value={stats?.total_successful_verifications ?? 0}
          loading={statsLoading && !stats}
        />
        <StatCard title="Doanh thu ước tính" value={totalRevenue} loading={statsLoading && !stats} />
        <StatCard title="Tổng user" value={stats?.verified_users ?? 0} loading={statsLoading && !stats} />
      </div>

      <Card className="mt-5 w-full border bg-white shadow-sm">
        <CardHeader className="space-y-3 border-b bg-[#fffdf8] pb-4">
          <div>
            <CardTitle className="text-lg">Quản lý người dùng</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Tra cứu user, lọc trạng thái và thao tác OTP theo từng tài khoản.
            </p>
          </div>
          <div className="rounded-xl border bg-white p-3">
            <UserSearchBar
              search={search}
              onSearchChange={setSearch}
              onSearchSubmit={handleSearchSubmit}
              filter={filter}
              onFilterChange={handleFilterChange}
            />
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {usersLoading && users.length === 0 ? (
            isMobile ? <UserCardSkeletonList /> : <UserTableSkeleton />
          ) : filteredUsers.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">Chưa có dữ liệu phù hợp</div>
          ) : isMobile ? (
            <div className="space-y-3">
              {paginatedUsers.map((item) => {
                const isAdmin = item.role.trim().toLowerCase() === "admin";
                const rowBusy = isRowBusy(item);
                const generatedOtp = item.last_generated_otp;
                return (
                  <Card
                    key={item.id}
                    className={usersFetching ? "border-dashed opacity-60 transition-opacity" : ""}
                  >
                    <CardHeader className="space-y-2 pb-3">
                      <CardTitle className="break-all text-sm">{item.email}</CardTitle>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="secondary">{item.role}</Badge>
                        <Badge variant="outline">
                          {item.is_active ? "Đang hoạt động" : "Đã khóa"}
                        </Badge>
                        <Badge
                          variant="outline"
                          className={
                            item.course_access_active
                              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                              : "border-rose-200 bg-rose-50 text-rose-700"
                          }
                        >
                          {item.course_access_active ? "Đang có key" : "Chưa có key"}
                        </Badge>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-3 pt-0">
                      <button
                        type="button"
                        className="w-full rounded-md border bg-muted/40 px-3 py-2 text-center text-[16px] font-bold transition-colors hover:bg-muted"
                        onClick={() => generatedOtp && handleCopyOtp(generatedOtp)}
                        disabled={!generatedOtp}
                      >
                        <span className="font-mono break-all">{generatedOtp || "-"}</span>
                      </button>
                      <p className="text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">Lý do khóa:</span>{" "}
                        {item.blocked_reason || "-"}
                      </p>

                      <div className="flex justify-end">
                        <UserActionsMenu
                          isAdmin={isAdmin}
                          rowBusy={rowBusy}
                          isActive={item.is_active}
                          onGenerateOtp={() => handleGenerateOtp(item.id)}
                          onClearOtp={() => handleClearOtp(item.id)}
                          onBlockUser={() => handleBlockUser(item.id)}
                          onUnblockUser={() => handleUnblockUser(item.id)}
                          onDeleteUser={() => handleDeleteUser(item.id)}
                        />
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          ) : (
            <div className="w-full overflow-x-auto rounded-xl border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Trạng thái</TableHead>
                    <TableHead>Key OTP</TableHead>
                    <TableHead>OTP vừa tạo</TableHead>
                    <TableHead>Lý do khóa</TableHead>
                    <TableHead className="text-right">Thao tác</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedUsers.map((item) => (
                    <UserTableRow
                      key={item.id}
                      item={item}
                      isFetching={usersFetching}
                      rowBusy={isRowBusy(item)}
                      onGenerateOtp={handleGenerateOtp}
                      onClearOtp={handleClearOtp}
                      onBlockUser={handleBlockUser}
                      onUnblockUser={handleUnblockUser}
                      onDeleteUser={handleDeleteUser}
                      onCopyOtp={handleCopyOtp}
                    />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          {!usersLoading && filteredUsers.length > 0 ? (
            <div className="mt-4 grid gap-2 border-t border-border/80 pt-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-full sm:w-auto sm:justify-self-start"
                disabled={currentPage <= 1 || usersFetching}
                onClick={() => setListPage(currentPage - 1)}
              >
                Trang trước
              </Button>
              <span className="text-center text-xs text-muted-foreground">
                Trang {currentPage} / {totalPages}
                <span className="mt-0.5 block font-normal">
                  {(currentPage - 1) * USER_TABLE_PAGE_SIZE + 1}–
                  {Math.min(currentPage * USER_TABLE_PAGE_SIZE, filteredUsers.length)} trong{" "}
                  {filteredUsers.length} người dùng
                </span>
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-full sm:w-auto sm:justify-self-end"
                disabled={currentPage >= totalPages || usersFetching}
                onClick={() => setListPage(currentPage + 1)}
              >
                Trang sau
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>
      <AlertDialog
        open={Boolean(deleteConfirmUserId)}
        onOpenChange={(isOpen) => {
          if (!isOpen) setDeleteConfirmUserId(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xóa người dùng vĩnh viễn?</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn đang xóa tài khoản <span className="font-medium">{deleteConfirmUserEmail}</span>. Hành động này
              không thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Hủy</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMutation.isPending}
              onClick={handleConfirmDelete}
            >
              {deleteMutation.isPending ? "Đang xóa..." : "Xóa vĩnh viễn"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

export default UserManagementView;
