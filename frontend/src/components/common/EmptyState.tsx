// src/components/common/EmptyState.tsx
interface Props { message: string; }
export function EmptyState({ message }: Props) {
  return (
    <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
      {message}
    </div>
  );
}
