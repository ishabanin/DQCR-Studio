import { useContextStore } from "../../app/store/contextStore";
import { useProjectStore } from "../../app/store/projectStore";

export default function StatusBar() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const activeContext = useContextStore((state) => state.activeContext);
  const activeContexts = useContextStore((state) => state.activeContexts);
  const multiMode = useContextStore((state) => state.multiMode);

  return (
    <footer className="statusbar">
      <span>Project: {currentProjectId ?? "none"}</span>
      <span>Context: {multiMode ? activeContexts.join(", ") : activeContext}</span>
      <span>Template: n/a</span>
      <span>Status: ready</span>
    </footer>
  );
}
