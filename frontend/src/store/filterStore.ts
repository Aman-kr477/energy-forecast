// src/store/filterStore.ts
// Zustand stores for filter state on each screen.
import { create } from "zustand";

interface DecisionFilters {
  deliveryDate: string;
  cutoff: string;
  showActuals: boolean;
  setDeliveryDate: (d: string) => void;
  setCutoff: (c: string) => void;
  setShowActuals: (v: boolean) => void;
}

export const useDecisionStore = create<DecisionFilters>((set) => ({
  deliveryDate: "",
  cutoff: "09:00",
  showActuals: false,
  setDeliveryDate: (d) => set({ deliveryDate: d }),
  setCutoff: (c) => set({ cutoff: c }),
  setShowActuals: (v) => set({ showActuals: v }),
}));

interface AccuracyFilters {
  startDate: string;
  endDate: string;
  horizon: number;
  setStartDate: (d: string) => void;
  setEndDate: (d: string) => void;
  setHorizon: (h: number) => void;
}

export const useAccuracyStore = create<AccuracyFilters>((set) => ({
  startDate: "",
  endDate: "",
  horizon: 16.5,
  setStartDate: (d) => set({ startDate: d }),
  setEndDate: (d) => set({ endDate: d }),
  setHorizon: (h) => set({ horizon: h }),
}));
