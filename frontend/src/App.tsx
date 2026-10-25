// src/App.tsx
// App shell: two tabs (Decision | Accuracy), loads meta on mount.
import { useState } from "react";
import { api } from "@/lib/api";
import { useApiCall } from "@/hooks/useApi";
import { DecisionScreen } from "@/features/decision/DecisionScreen";
import { AccuracyScreen } from "@/features/accuracy/AccuracyScreen";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";

const TABS = [
  { id: "decision", label: "Forecast for decision" },
  { id: "accuracy", label: "Forecast accuracy" },
] as const;
type TabId = typeof TABS[number]["id"];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("decision");
  const metaState = useApiCall(() => api.meta(), []);

  const isLoading = metaState.status === "loading" || metaState.status === "idle";
  const isError = metaState.status === "error";
  const meta = metaState.status === "success" ? metaState.data : null;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Wind Forecast Dashboard</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              GB day-ahead wind generation · January 2026 · Data: Elexon BMRS
            </p>
          </div>
          <span className="hidden sm:inline-flex items-center rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-700">
            Live snapshots
          </span>
        </div>
      </header>

      {/* Tab bar */}
      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-0" role="tablist">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`panel-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-brand-600 ${
                  activeTab === tab.id
                    ? "border-brand-600 text-brand-600"
                    : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        {isLoading && (
          <div className="space-y-4">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-64 w-full" />
          </div>
        )}
        {isError && (
          <Alert variant="error">
            Could not connect to the API. Make sure the backend is running.{" "}
            <span className="font-mono text-xs">
              {(metaState as { status: "error"; message: string }).message}
            </span>
          </Alert>
        )}
        {meta && (
          <>
            <div
              id="panel-decision"
              role="tabpanel"
              aria-labelledby="tab-decision"
              hidden={activeTab !== "decision"}
            >
              <DecisionScreen meta={meta} />
            </div>
            <div
              id="panel-accuracy"
              role="tabpanel"
              aria-labelledby="tab-accuracy"
              hidden={activeTab !== "accuracy"}
            >
              <AccuracyScreen meta={meta} />
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-16 border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        Data sourced from{" "}
        <a href="https://bmrs.elexon.co.uk" className="underline hover:text-slate-600" target="_blank" rel="noreferrer">
          Elexon BMRS
        </a>{" "}
        · All times UTC · Built with AI assistance
      </footer>
    </div>
  );
}
