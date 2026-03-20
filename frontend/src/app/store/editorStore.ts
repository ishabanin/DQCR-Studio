import { create } from "zustand";

export type TabId = "lineage" | "model" | "sql" | "validate" | "parameters" | "build" | "admin";

export interface EditorNavigationTarget {
  path: string;
  line: number | null;
}

interface EditorStore {
  activeTab: TabId;
  openFiles: string[];
  activeFilePath: string | null;
  dirtyFiles: Record<string, boolean>;
  pendingNavigationTarget: EditorNavigationTarget | null;
  setActiveTab: (tab: TabId) => void;
  openFile: (path: string) => void;
  setActiveFile: (path: string | null) => void;
  closeFile: (path: string) => void;
  reorderFiles: (fromPath: string, toPath: string) => void;
  setDirty: (path: string, dirty: boolean) => void;
  setPendingNavigationTarget: (target: EditorNavigationTarget | null) => void;
}

export const useEditorStore = create<EditorStore>((set) => ({
  activeTab: "lineage",
  openFiles: [],
  activeFilePath: null,
  dirtyFiles: {},
  pendingNavigationTarget: null,
  setActiveTab: (tab) => set({ activeTab: tab }),
  openFile: (path) =>
    set((state) => ({
      openFiles: state.openFiles.includes(path) ? state.openFiles : [...state.openFiles, path],
      activeFilePath: path,
    })),
  setActiveFile: (path) => set({ activeFilePath: path }),
  closeFile: (path) =>
    set((state) => {
      const nextOpen = state.openFiles.filter((item) => item !== path);
      return {
        openFiles: nextOpen,
        activeFilePath: state.activeFilePath === path ? (nextOpen[0] ?? null) : state.activeFilePath,
      };
    }),
  reorderFiles: (fromPath, toPath) =>
    set((state) => {
      if (fromPath === toPath) return state;
      const fromIndex = state.openFiles.indexOf(fromPath);
      const toIndex = state.openFiles.indexOf(toPath);
      if (fromIndex < 0 || toIndex < 0) return state;

      const next = [...state.openFiles];
      const [moved] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, moved);
      return { openFiles: next };
    }),
  setDirty: (path, dirty) =>
    set((state) => ({
      dirtyFiles: {
        ...state.dirtyFiles,
        [path]: dirty,
      },
    })),
  setPendingNavigationTarget: (target) => set({ pendingNavigationTarget: target }),
}));
