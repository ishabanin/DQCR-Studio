import { type MouseEvent as ReactMouseEvent, useRef } from "react";
import { useUiStore } from "../../app/store/uiStore";
import Terminal from "./Terminal";

const tabs: Array<{ id: "terminal" | "logs" | "output"; label: string }> = [
  { id: "terminal", label: "Терминал" },
  { id: "logs", label: "Логи" },
  { id: "output", label: "Вывод" },
];

export default function BottomPanel() {
  const bottomPanelExpanded = useUiStore((state) => state.bottomPanelExpanded);
  const bottomPanelHeight = useUiStore((state) => state.bottomPanelHeight);
  const bottomPanelTab = useUiStore((state) => state.bottomPanelTab);
  const toggleBottomPanel = useUiStore((state) => state.toggleBottomPanel);
  const setBottomPanelTab = useUiStore((state) => state.setBottomPanelTab);
  const setBottomPanelHeight = useUiStore((state) => state.setBottomPanelHeight);
  const apiLogs = useUiStore((state) => state.apiLogs);
  const clearApiLogs = useUiStore((state) => state.clearApiLogs);
  const resizeStateRef = useRef<{ startY: number; startHeight: number } | null>(null);

  const startResize = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (!bottomPanelExpanded) return;
    event.preventDefault();

    resizeStateRef.current = {
      startY: event.clientY,
      startHeight: bottomPanelHeight,
    };

    document.body.classList.add("app-resizing-bottom-panel");

    const handlePointerMove = (moveEvent: MouseEvent) => {
      if (!resizeStateRef.current) return;
      const delta = resizeStateRef.current.startY - moveEvent.clientY;
      setBottomPanelHeight(resizeStateRef.current.startHeight + delta);
      window.dispatchEvent(new Event("resize"));
    };

    const stopResize = () => {
      resizeStateRef.current = null;
      document.body.classList.remove("app-resizing-bottom-panel");
      window.removeEventListener("mousemove", handlePointerMove);
      window.removeEventListener("mouseup", stopResize);
      window.dispatchEvent(new Event("resize"));
    };

    window.addEventListener("mousemove", handlePointerMove);
    window.addEventListener("mouseup", stopResize);
  };

  return (
    <section className={bottomPanelExpanded ? "bottom-panel" : "bottom-panel bottom-panel-collapsed"}>
      {bottomPanelExpanded ? (
        <div
          className="bottom-panel-resize-handle"
          onMouseDown={startResize}
          role="separator"
          aria-orientation="horizontal"
          aria-label="Изменить размер нижней панели"
        />
      ) : null}
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
          {bottomPanelExpanded ? "Свернуть" : "Развернуть"}
        </button>
      </div>

      {bottomPanelExpanded ? (
        <div className="bottom-panel-content">
          {bottomPanelTab === "terminal" ? <Terminal /> : null}
          {bottomPanelTab === "logs" ? (
            <div className="bottom-logs">
              <button type="button" className="action-btn" onClick={clearApiLogs}>
                Очистить логи
              </button>
              <pre>{apiLogs.length > 0 ? apiLogs.join("\n") : "Вызовов API пока нет."}</pre>
            </div>
          ) : null}
          {bottomPanelTab === "output" ? "Панель вывода в разработке" : null}
        </div>
      ) : null}
    </section>
  );
}
