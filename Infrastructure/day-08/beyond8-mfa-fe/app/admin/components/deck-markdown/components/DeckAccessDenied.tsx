"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface DeckAccessDeniedProps {
  onLogout: () => void;
  embedded?: boolean;
}

export function DeckAccessDenied({ onLogout, embedded = false }: DeckAccessDeniedProps) {
  const card = (
    <Card className="w-full max-w-3xl">
      <CardHeader>
        <CardTitle>Không có quyền truy cập</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">Trang này chỉ dành cho admin.</p>
        <Button className="mt-4" onClick={onLogout}>
          Quay lại đăng nhập
        </Button>
      </CardContent>
    </Card>
  );

  if (embedded) {
    return <div className="flex w-full justify-center py-6">{card}</div>;
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-4 py-10">
      {card}
    </main>
  );
}
