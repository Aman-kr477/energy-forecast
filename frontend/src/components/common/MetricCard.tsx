// src/components/common/MetricCard.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface Props {
  title: string;
  value: string;
  caption: string;
  loading?: boolean;
}

export function MetricCard({ title, value, caption, loading }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <>
            <Skeleton className="h-8 w-32 mb-2" />
            <Skeleton className="h-4 w-48" />
          </>
        ) : (
          <>
            <p className="text-2xl font-bold text-slate-900">{value}</p>
            <p className="mt-1 text-xs text-slate-500">{caption}</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
