import { create } from "zustand";

import type { ValidationRunResult } from "../../api/projects";

interface ValidationStore {
  latestRun: ValidationRunResult | null;
  setLatestRun: (run: ValidationRunResult | null) => void;
}

export const useValidationStore = create<ValidationStore>((set) => ({
  latestRun: null,
  setLatestRun: (run) => set({ latestRun: run }),
}));
