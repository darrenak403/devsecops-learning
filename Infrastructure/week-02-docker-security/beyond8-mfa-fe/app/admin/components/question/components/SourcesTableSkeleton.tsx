"use client";

import { Skeleton } from "@/components/ui/skeleton";

interface SourcesTableSkeletonProps {
  variant?: "table" | "cards";
}

export function SourcesTableSkeleton({ variant = "table" }: SourcesTableSkeletonProps) {
  if (variant === "cards") {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, idx) => (
          <div key={idx} className="space-y-3 rounded-xl border bg-card p-4">
            <Skeleton className="h-5 w-2/5" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-[85%]" />
            <Skeleton className="h-9 w-full max-w-[120px] self-end" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-5 gap-2">
        {Array.from({ length: 5 }).map((_, idx) => (
          <Skeleton key={`head-${idx}`} className="h-6 w-full" />
        ))}
      </div>
      {Array.from({ length: 6 }).map((_, idx) => (
        <div key={idx} className="grid grid-cols-5 gap-2">
          {Array.from({ length: 5 }).map((__, colIdx) => (
            <Skeleton key={`row-${idx}-${colIdx}`} className="h-10 w-full" />
          ))}
        </div>
      ))}
    </div>
  );
}
