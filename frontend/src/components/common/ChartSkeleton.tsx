// src/components/common/ChartSkeleton.tsx
import { Skeleton } from "@/components/ui/skeleton";
export function ChartSkeleton({ height = 300 }: { height?: number }) {
  return (
    <div style={{ height }} className="flex flex-col gap-2 p-4">
      <Skeleton className="h-4 w-40" />
      <Skeleton className="flex-1 w-full" />
    </div>
  );
}
