import { useEffect } from "react";

import { TabId, useEditorStore } from "../../app/store/editorStore";

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "project", label: "Project Info" },
  { id: "lineage", label: "Lineage" },
  { id: "model", label: "Model Editor" },
  { id: "sql", label: "SQL Editor" },
  { id: "validate", label: "Validate" },
  { id: "parameters", label: "Parameters" },
  { id: "build", label: "Build" },
  { id: "admin", label: "Admin" },
];

export default function TabBar() {
  const activeTab = useEditorStore((state) => state.activeTab);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      const index = Number(event.key);
      if (Number.isNaN(index) || index < 1 || index > tabs.length) return;
      event.preventDefault();
      setActiveTab(tabs[index - 1].id);
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setActiveTab]);

  return (
    <nav className="tabbar">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={activeTab === tab.id ? "tab-item tab-item-active" : "tab-item"}
          onClick={() => setActiveTab(tab.id)}
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
