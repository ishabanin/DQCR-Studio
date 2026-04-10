import type { SqlTab } from "../../../app/store/sqlTabsStore";

interface SqlTabBarProps {
  tabs: SqlTab[];
  activeTabId: string | null;
  onSelectTab: (tabId: string) => void;
  onRequestClose: (tabId: string) => void;
}

export default function SqlTabBar({ tabs, activeTabId, onSelectTab, onRequestClose }: SqlTabBarProps) {
  return (
    <div className="sql-tabbar" role="tablist" aria-label="Open SQL files">
      {tabs.map((tab) => (
        <div key={tab.id} className={tab.id === activeTabId ? "sql-tab sql-tab-active" : "sql-tab"}>
          <button
            type="button"
            id={`sql-tab-${tab.id}`}
            role="tab"
            aria-controls={`sql-panel-${tab.id}`}
            aria-selected={tab.id === activeTabId}
            tabIndex={tab.id === activeTabId ? 0 : -1}
            className="sql-tab-main"
            onClick={() => onSelectTab(tab.id)}
          >
            <span className="sql-tab-icon" aria-hidden="true">
              📄
            </span>
            <span className="sql-tab-label">{tab.fileName}</span>
            {tab.isDirty ? <span className="sql-tab-dirty">●</span> : null}
          </button>
          <button
            type="button"
            className="sql-tab-close"
            aria-label={`Close ${tab.fileName}`}
            onClick={(event) => {
              event.stopPropagation();
              onRequestClose(tab.id);
            }}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
