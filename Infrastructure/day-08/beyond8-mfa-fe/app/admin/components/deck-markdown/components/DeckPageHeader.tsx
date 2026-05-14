"use client";

import { Link } from "@/lib/navigation";
import { Button } from "@/components/ui/button";

interface DeckPageHeaderProps {
  onLogout: () => void;
  embedded?: boolean;
}

export function DeckPageHeader({ onLogout, embedded = false }: DeckPageHeaderProps) {
  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div className="min-w-0">
        <h1 className="text-lg font-bold md:text-xl">Soạn deck markdown</h1>
        <p className="text-sm text-muted-foreground">
          Chuẩn hoá giống tool Python, upload riêng, hợp nhất ngân hàng qua API riêng.
        </p>
      </div>
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <Button asChild variant="outline" className="w-full sm:w-auto">
          <Link href="/admin?view=questions">Quản lý sources</Link>
        </Button>
        {!embedded ? (
          <Button variant="outline" className="w-full sm:w-auto" onClick={onLogout}>
            Đăng xuất
          </Button>
        ) : null}
      </div>
    </div>
  );
}
