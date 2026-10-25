// src/components/ui/alert.tsx
import { cn } from "@/lib/utils";
export function Alert({ children, variant = "info", className }: {
  children: React.ReactNode; variant?: "info" | "error" | "warn"; className?: string;
}) {
  const v = {
    info:  "bg-blue-50 border-blue-200 text-blue-800",
    error: "bg-red-50 border-red-200 text-red-800",
    warn:  "bg-amber-50 border-amber-200 text-amber-800",
  }[variant];
  return <div role="alert" className={cn("rounded-lg border p-4 text-sm", v, className)}>{children}</div>;
}
