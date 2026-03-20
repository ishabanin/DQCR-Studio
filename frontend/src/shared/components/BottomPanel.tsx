import { useUiStore } from "../../app/store/uiStore";
import Terminal from "./Terminal";

const tabs: Array<{ id: "terminal" | "logs" | "output"; label: string }> = [
  { id: "terminal", label: "Terminal" },
  { id: "logs", label: "Logs" },
  { id: "output", label: "Output" },
];

export default function BottomPanel() {
  const bottomPanelExpanded = useUiStore((state) => state.bottomPanelExpanded);
  const bottomPanelTab = useUiStore((state) => state.bottomPanelTab);
  const toggleBottomPanel = useUiStore((state) => state.toggleBottomPanel);
  const setBottomPanelTab = useUiStore((state) => state.setBottomPanelTab);
  const apiLogs = useUiStore((state) => state.apiLogs);
  const clearApiLogs = useUiStore((state) => state.clearApiLogs);

  return (
    <section className={bottomPanelExpanded ? "bottom-panel" : "bottom-panel bottom-panel-collapsed"}>
      <div className="bottom-panel-head">
        <div className="bottom-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={bottomPanelTab === tab.id ? "bottom-tab bottom-tab-active" : "bottom-tab"}
              onClick={() => setBottomPanelTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>
        <button type="button" onClick={toggleBottomPanel}>
          {bottomPanelExpanded ? "Collapse" : "Expand"}
        </button>
      </div>

      {bottomPanelExpanded ? (
        <div className="bottom-panel-content">
          {bottomPanelTab === "terminal" ? <Terminal /> : null}
          {bottomPanelTab === "logs" ? (
            <div className="bottom-logs">
              <button type="button" className="action-btn" onClick={clearApiLogs}>
                Clear Logs
              </button>
              <pre>{apiLogs.length > 0 ? apiLogs.join("\n") : "No API calls yet."}</pre>
            </div>
          ) : null}
          {bottomPanelTab === "output" ? "Output placeholder" : null}
        </div>
      ) : null}
    </section>
  );
}
