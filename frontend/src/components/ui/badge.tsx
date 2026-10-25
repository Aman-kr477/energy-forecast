// src/components/ui/badge.tsx
import { cn } from "@/lib/utils";
export function Badge({ children, variant = "default", className }: {
  children: React.ReactNode; variant?: "default" | "success" | "warn" | "danger"; className?: string;
}) {
  const v = {
    default: "bg-slate-100 text-slate-700",
    success: "bg-emerald-100 text-emerald-700",
    warn:    "bg-amber-100 text-amber-700",
    danger:  "bg-red-100 text-red-700",
  }[variant];
  return <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", v, className)}>{children}</span>;
}
