"use client";

import { type ReactNode } from "react";
import { Skeleton } from "@/components/ui/skeleton";

export function ClientHydrationGate({ hydrated, children }: { hydrated: boolean; children: ReactNode }) {
  if (!hydrated) {
    return (
      <main className="min-h-screen bg-[#fcfaf6] px-4 py-6 md:px-6 md:py-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-56 w-full" />
          <Skeleton className="h-105 w-full" />
        </div>
      </main>
    );
  }
  return <>{children}</>;
}
