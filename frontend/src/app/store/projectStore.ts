import { create } from "zustand";
import { persist } from "zustand/middleware";
import { useEditorStore } from "./editorStore";

interface ProjectStore {
  currentProjectId: string | null;
  setProject: (id: string | null) => void;
}

const LAST_PROJECT_KEY = "dqcr_last_project_id";

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set) => ({
      currentProjectId: null,
      setProject: (id) => {
        set({ currentProjectId: id });
        if (id) {
          window.localStorage.setItem(LAST_PROJECT_KEY, id);
          useEditorStore.getState().setActiveTab("project");
        } else {
          window.localStorage.removeItem(LAST_PROJECT_KEY);
        }
      },
    }),
    { name: "dqcr-project-store" },
  ),
);
