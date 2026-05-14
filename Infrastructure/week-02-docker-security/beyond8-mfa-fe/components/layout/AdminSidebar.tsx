"use client";

import { CircleHelp, FilePenLine, LayoutGrid, Users, type LucideIcon } from "lucide-react";
import {
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { MOBILE_BREAKPOINT_PX } from "@/hooks/use-mobile";

export type AdminView = "users" | "questions" | "deck-markdown";

interface AdminSidebarProps {
  activeView: AdminView;
  onSelectView: (view: AdminView) => void;
  userEmail: string;
  onLogout: () => void;
}

const navItems: Array<{ key: AdminView; label: string; description: string; icon: LucideIcon }> = [
  {
    key: "users",
    label: "Quản lý người dùng",
    description: "OTP, trạng thái tài khoản, lịch sử",
    icon: Users,
  },
  {
    key: "questions",
    label: "Quản lý question",
    description: "Môn học, source markdown, câu hỏi",
    icon: CircleHelp,
  },
  {
    key: "deck-markdown",
    label: "Soạn deck MD",
    description: "Upload & merge bank markdown",
    icon: FilePenLine,
  },
];

export function AdminSidebar({ activeView, onSelectView, userEmail, onLogout }: AdminSidebarProps) {
  const { setOpen } = useSidebar();

  const handleSelectView = (key: AdminView) => {
    onSelectView(key);
    if (typeof window !== "undefined" && window.innerWidth < MOBILE_BREAKPOINT_PX) {
      setOpen(false);
    }
  };

  return (
    <>
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1">
          <div className="rounded-md bg-primary/10 p-1.5 text-primary">
            <LayoutGrid className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-extrabold leading-tight tracking-tight">Beyond8 Auth</p>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Modules</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
        {navItems.map((item) => {
          const isActive = activeView === item.key;
          const Icon = item.icon;
          return (
            <SidebarMenuItem key={item.key}>
            <SidebarMenuButton
              key={item.key}
              isActive={isActive}
              className="h-auto items-start py-3"
              onClick={() => handleSelectView(item.key)}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-semibold">{item.label}</p>
                <p className="hidden text-xs text-muted-foreground md:block">{item.description}</p>
              </div>
            </SidebarMenuButton>
            </SidebarMenuItem>
          );
        })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t border-border/80 bg-muted/20">
        <div className="flex flex-col gap-2 px-1 py-1">
          <p className="truncate px-1 text-xs text-muted-foreground" title={userEmail}>
            {userEmail}
          </p>
          <Button variant="outline" size="sm" className="w-full" onClick={onLogout}>
            Đăng xuất
          </Button>
        </div>
      </SidebarFooter>
    </>
  );
}
