// src/hooks/useApi.ts
// Simple data-fetching hooks with loading/error state.
import { useEffect, useState } from "react";

export type ApiState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; message: string };

export function useApiCall<T>(
  fetcher: () => Promise<T>,
  deps: unknown[]
): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ status: "idle" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: "success", data });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ status: "error", message: err.message });
      });
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
