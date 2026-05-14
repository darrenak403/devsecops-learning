"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function UserCardSkeletonList() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, idx) => (
        <Card key={idx}>
          <CardHeader className="space-y-2 pb-3">
            <Skeleton className="h-5 w-3/4" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-6 w-28" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <div className="grid grid-cols-2 gap-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
