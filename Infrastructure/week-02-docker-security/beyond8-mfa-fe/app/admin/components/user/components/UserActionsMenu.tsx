"use client";

import { useEffect, useRef, useState } from "react";
import { MoreVertical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";

interface UserActionsMenuProps {
  isAdmin: boolean;
  rowBusy: boolean;
  isActive: boolean;
  onGenerateOtp: () => void;
  onClearOtp: () => void;
  onBlockUser: () => void;
  onUnblockUser: () => void;
  onDeleteUser: () => void;
}

export function UserActionsMenu({
  isAdmin,
  rowBusy,
  isActive,
  onGenerateOtp,
  onClearOtp,
  onBlockUser,
  onUnblockUser,
  onDeleteUser,
}: UserActionsMenuProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  const isActionDisabled = rowBusy || isAdmin;

  const runAction = (action: () => void, disabled: boolean) => {
    if (disabled) return;
    action();
    setOpen(false);
  };

  return (
    <div className="relative" ref={containerRef}>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Mở menu thao tác"
        disabled={rowBusy}
        onClick={() => setOpen((prev) => !prev)}
      >
        <MoreVertical className="h-4 w-4" />
      </Button>

      {open ? (
        <div className="absolute right-0 z-30 mt-2 w-40 rounded-xl border bg-white p-1 shadow-lg">
          <button
            type="button"
            disabled={isActionDisabled}
            onClick={() => runAction(onGenerateOtp, isActionDisabled)}
            className={cn(
              "w-full rounded-lg px-3 py-2 text-left text-sm font-semibold",
              isActionDisabled ? "cursor-not-allowed text-muted-foreground" : "hover:bg-accent"
            )}
          >
            Lấy OTP
          </button>
          <button
            type="button"
            disabled={isActionDisabled}
            onClick={() => runAction(onClearOtp, isActionDisabled)}
            className={cn(
              "w-full rounded-lg px-3 py-2 text-left text-sm font-semibold",
              isActionDisabled ? "cursor-not-allowed text-muted-foreground" : "hover:bg-accent"
            )}
          >
            Clear OTP
          </button>
          <button
            type="button"
            disabled={isActionDisabled}
            onClick={() => runAction(isActive ? onBlockUser : onUnblockUser, isActionDisabled)}
            className={cn(
              "w-full rounded-lg px-3 py-2 text-left text-sm font-semibold",
              isActionDisabled ? "cursor-not-allowed text-muted-foreground" : "hover:bg-accent"
            )}
          >
            {isActive ? "Khóa" : "Mở khóa"}
          </button>
          <button
            type="button"
            disabled={isActionDisabled}
            onClick={() => runAction(onDeleteUser, isActionDisabled)}
            className={cn(
              "w-full rounded-lg px-3 py-2 text-left text-sm font-semibold",
              isActionDisabled
                ? "cursor-not-allowed text-muted-foreground"
                : "text-destructive hover:bg-destructive/10"
            )}
          >
            Xóa
          </button>
        </div>
      ) : null}
    </div>
  );
}
