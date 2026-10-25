// src/components/ui/card.tsx
import { cn } from "@/lib/utils";

export function Card({ className, children }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>
      {children}
    </div>
  );
}
export function CardHeader({ className, children }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-4 pb-2", className)}>{children}</div>;
}
export function CardTitle({ className, children }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-sm font-semibold text-slate-500 uppercase tracking-wide", className)}>{children}</h3>;
}
export function CardContent({ className, children }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-4 pb-4", className)}>{children}</div>;
}
