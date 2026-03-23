import { useEffect } from "react";
import { useSqlTabsStore } from "../../../app/store/sqlTabsStore";

const TOOL_STORAGE_KEY = "dqcr_sql_editor_selected_tool";

interface SqlViewModeState {
  mode: "source" | "prepared" | "rendered";
  setMode: (mode: "source" | "prepared" | "rendered") => void;
  selectedTool: string | null;
  setSelectedTool: (tool: string | null) => void;
}

export function useSqlViewMode(activeFilePath: string | null): SqlViewModeState {
  const activeTab = useSqlTabsStore((state) => state.tabs.find((tab) => tab.id === state.activeTabId) ?? null);
  const updateTabMode = useSqlTabsStore((state) => state.updateTabMode);

  const fallbackSelectedTool = (() => {
    const raw = window.localStorage.getItem(TOOL_STORAGE_KEY);
    return raw && raw.trim() ? raw : null;
  })();
  const mode = activeTab?.viewMode ?? "source";
  const selectedTool = activeTab?.selectedTool ?? fallbackSelectedTool;

  const setMode = (nextMode: "source" | "prepared" | "rendered") => {
    if (!activeTab) return;
    updateTabMode(activeTab.id, nextMode);
  };

  const setSelectedTool = (tool: string | null) => {
    if (!tool) {
      window.localStorage.removeItem(TOOL_STORAGE_KEY);
    } else {
      window.localStorage.setItem(TOOL_STORAGE_KEY, tool);
    }
    if (!activeTab) return;
    updateTabMode(activeTab.id, activeTab.viewMode, tool);
  };

  useEffect(() => {
    if (!activeTab || activeTab.selectedTool || !fallbackSelectedTool) return;
    updateTabMode(activeTab.id, activeTab.viewMode, fallbackSelectedTool);
  }, [activeTab, fallbackSelectedTool, updateTabMode, activeFilePath]);

  return { mode, setMode, selectedTool, setSelectedTool };
}
