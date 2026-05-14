import { memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const statCardClass = "rounded-2xl border bg-white p-5 shadow-sm";

interface StatCardProps {
  title: string;
  value: string | number;
  loading: boolean;
}

export const StatCard = memo(({ title, value, loading }: StatCardProps) => (
  <Card className={statCardClass}>
    <CardHeader className="p-0 pb-2">
      <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
    </CardHeader>
    <CardContent className="p-0">
      {loading ? <Skeleton className="h-9 w-32" /> : <div className="text-3xl font-bold">{value}</div>}
    </CardContent>
  </Card>
));

StatCard.displayName = "StatCard";
