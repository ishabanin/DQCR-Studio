import { create } from "zustand";

import { useProjectStore } from "./projectStore";
import type { SqlViewMode } from "../../features/sql/types/sqlView";

const MAX_SQL_TABS = 20;

export interface SqlTab {
  id: string;
  filePath: string;
  fileName: string;
  isDirty: boolean;
  viewMode: SqlViewMode;
  selectedTool: string | null;
  scrollTop: number;
}

interface SqlTabsStore {
  tabs: SqlTab[];
  activeTabId: string | null;
  isFullscreen: boolean;
  openTab: (filePath: string) => { ok: boolean; reason?: "limit" };
  closeTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  setTabDirty: (tabId: string, isDirty: boolean) => void;
  updateTabMode: (tabId: string, mode: SqlViewMode, tool?: string | null) => void;
  updateTabScroll: (tabId: string, scrollTop: number) => void;
  clearAllTabs: () => void;
  enterFullscreen: () => void;
  exitFullscreen: () => void;
}

function makeTab(filePath: string): SqlTab {
  const fileName = filePath.split("/").pop() ?? filePath;
  return {
    id: `${filePath}::${Date.now()}::${Math.random().toString(36).slice(2, 8)}`,
    filePath,
    fileName,
    isDirty: false,
    viewMode: "source",
    selectedTool: null,
    scrollTop: 0,
  };
}

export const useSqlTabsStore = create<SqlTabsStore>((set) => ({
  tabs: [],
  activeTabId: null,
  isFullscreen: false,
  openTab: (filePath) => {
    let result: { ok: boolean; reason?: "limit" } = { ok: true };
    set((state) => {
      const existing = state.tabs.find((tab) => tab.filePath === filePath);
      if (existing) {
        return { activeTabId: existing.id };
      }
      if (state.tabs.length >= MAX_SQL_TABS) {
        result = { ok: false, reason: "limit" };
        return state;
      }
      const tab = makeTab(filePath);
      return {
        tabs: [...state.tabs, tab],
        activeTabId: tab.id,
      };
    });
    return result;
  },
  closeTab: (tabId) =>
    set((state) => {
      const index = state.tabs.findIndex((tab) => tab.id === tabId);
      if (index < 0) return state;
      const nextTabs = state.tabs.filter((tab) => tab.id !== tabId);
      if (state.activeTabId !== tabId) {
        return { tabs: nextTabs };
      }
      const rightNeighbor = state.tabs[index + 1];
      const leftNeighbor = state.tabs[index - 1];
      const nextActive = rightNeighbor?.id ?? leftNeighbor?.id ?? null;
      return { tabs: nextTabs, activeTabId: nextActive };
    }),
  setActiveTab: (tabId) => set({ activeTabId: tabId }),
  setTabDirty: (tabId, isDirty) =>
    set((state) => ({
      tabs: state.tabs.map((tab) => (tab.id === tabId ? { ...tab, isDirty } : tab)),
    })),
  updateTabMode: (tabId, mode, tool) =>
    set((state) => ({
      tabs: state.tabs.map((tab) =>
        tab.id === tabId
          ? {
              ...tab,
              viewMode: mode,
              selectedTool: tool !== undefined ? tool : tab.selectedTool,
            }
          : tab,
      ),
    })),
  updateTabScroll: (tabId, scrollTop) =>
    set((state) => ({
      tabs: state.tabs.map((tab) => (tab.id === tabId ? { ...tab, scrollTop } : tab)),
    })),
  clearAllTabs: () => set({ tabs: [], activeTabId: null, isFullscreen: false }),
  enterFullscreen: () => set({ isFullscreen: true }),
  exitFullscreen: () => set({ isFullscreen: false }),
}));

let lastProjectId = useProjectStore.getState().currentProjectId;
useProjectStore.subscribe((state) => {
  if (state.currentProjectId !== lastProjectId) {
    lastProjectId = state.currentProjectId;
    useSqlTabsStore.getState().clearAllTabs();
  }
});
