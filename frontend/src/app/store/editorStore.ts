import { create } from "zustand";

export type TabId = "project" | "lineage" | "model" | "sql" | "validate" | "parameters" | "build" | "admin";

export interface EditorNavigationTarget {
  path: string;
  line: number | null;
}

export interface EditorCursorState {
  position: { lineNumber: number; column: number } | null;
  scrollTop: number;
  scrollLeft: number;
}

interface EditorStore {
  activeTab: TabId;
  openFiles: string[];
  activeFilePath: string | null;
  dirtyFiles: Record<string, boolean>;
  cursorStateByFile: Record<string, EditorCursorState>;
  navigateTo: EditorNavigationTarget | null;
  pendingNavigationTarget: EditorNavigationTarget | null;
  setActiveTab: (tab: TabId) => void;
  openFile: (path: string) => void;
  setActiveFile: (path: string | null) => void;
  closeFile: (path: string) => void;
  reorderFiles: (fromPath: string, toPath: string) => void;
  setDirty: (path: string, dirty: boolean) => void;
  setCursorState: (filePath: string, state: EditorCursorState) => void;
  setNavigateTo: (target: EditorNavigationTarget | null) => void;
  setPendingNavigationTarget: (target: EditorNavigationTarget | null) => void;
}

export const useEditorStore = create<EditorStore>((set) => ({
  activeTab: "project",
  openFiles: [],
  activeFilePath: null,
  dirtyFiles: {},
  cursorStateByFile: {},
  navigateTo: null,
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
  setCursorState: (filePath, state) =>
    set((prev) => ({
      cursorStateByFile: {
        ...prev.cursorStateByFile,
        [filePath]: state,
      },
    })),
  setNavigateTo: (target) => set({ navigateTo: target, pendingNavigationTarget: target }),
  setPendingNavigationTarget: (target) => set({ pendingNavigationTarget: target, navigateTo: target }),
}));
