import { create } from "zustand";

interface ProjectStore {
  currentProjectId: string | null;
  setProject: (id: string | null) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  currentProjectId: null,
  setProject: (id) => set({ currentProjectId: id }),
}));
