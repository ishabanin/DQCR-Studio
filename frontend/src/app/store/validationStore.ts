import { create } from "zustand";

import type { ValidationRunResult } from "../../api/projects";

interface ValidationStore {
  latestRun: ValidationRunResult | null;
  lastCategories: string[] | null;
  setLatestRun: (run: ValidationRunResult | null) => void;
  setLastCategories: (categories: string[] | null) => void;
}

export const useValidationStore = create<ValidationStore>((set) => ({
  latestRun: null,
  lastCategories: null,
  setLatestRun: (run) => set({ latestRun: run }),
  setLastCategories: (categories) => set({ lastCategories: categories }),
}));
