import { memo } from "react";
import { TableCell, TableRow } from "@/components/ui/table";
import type { AdminUserItem } from "@/lib/api/services/fetchAdmin";
import { UserActionsMenu } from "./UserActionsMenu";

interface UserTableRowProps {
  item: AdminUserItem;
  isFetching: boolean;
  rowBusy: boolean;
  onGenerateOtp: (userId: string) => void;
  onClearOtp: (userId: string) => void;
  onBlockUser: (userId: string) => void;
  onUnblockUser: (userId: string) => void;
  onDeleteUser: (userId: string) => void;
  onCopyOtp: (otp: string) => void;
}

export const UserTableRow = memo(({ 
  item, 
  isFetching,
  rowBusy,
  onGenerateOtp,
  onClearOtp,
  onBlockUser,
  onUnblockUser,
  onDeleteUser,
  onCopyOtp
}: UserTableRowProps) => {
  const isAdmin = item.role.trim().toLowerCase() === "admin";
  const keyStatusClass = item.course_access_active
    ? "rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700"
    : "rounded-full bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-700";
  
  return (
    <TableRow className={isFetching ? "opacity-50 transition-opacity" : ""}>
      <TableCell className="font-medium text-foreground">{item.email}</TableCell>
      <TableCell>
        <span className="rounded-full bg-[#fff3e5] px-2 py-1 text-xs font-semibold text-[#9a5a18]">
          {item.role}
        </span>
      </TableCell>
      <TableCell>{item.is_active ? "Đang hoạt động" : "Đã khóa"}</TableCell>
      <TableCell>
        <span className={keyStatusClass}>
          {item.course_access_active ? "Đang có key" : "Chưa có key"}
        </span>
      </TableCell>
      <TableCell>
        <div
          className="cursor-pointer rounded-md p-2 transition-colors hover:bg-muted"
          onClick={() => item.last_generated_otp && onCopyOtp(item.last_generated_otp)}
        >
          <span className="font-mono text-xs">{item.last_generated_otp || "-"}</span>
        </div>
      </TableCell>
      <TableCell className="max-w-55 truncate">{item.blocked_reason || "-"}</TableCell>
      <TableCell>
        <div className="flex justify-end">
          <UserActionsMenu
            isAdmin={isAdmin}
            rowBusy={rowBusy}
            isActive={item.is_active}
            onGenerateOtp={() => onGenerateOtp(item.id)}
            onClearOtp={() => onClearOtp(item.id)}
            onBlockUser={() => onBlockUser(item.id)}
            onUnblockUser={() => onUnblockUser(item.id)}
            onDeleteUser={() => onDeleteUser(item.id)}
          />
        </div>
      </TableCell>
    </TableRow>
  );
});

UserTableRow.displayName = "UserTableRow";

/** Số user mỗi trang (đồng bộ với phân trang trong `UserManagementView`). */
export const USER_TABLE_PAGE_SIZE = 5;
