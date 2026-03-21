import type { CSSProperties } from "react";
import { useEffect } from "react";
import { fetchProject } from "./api/projects";
import { useProjectStore } from "./app/store/projectStore";
import ProjectsHub from "./features/hub/ProjectsHub";
import Workbench from "./features/layout/Workbench";
import ProjectWizardModal from "./features/wizard/ProjectWizardModal";
import { useUiStore } from "./app/store/uiStore";
import BottomPanel from "./shared/components/BottomPanel";
import Sidebar from "./shared/components/Sidebar";
import StatusBar from "./shared/components/StatusBar";
import TabBar from "./shared/components/TabBar";
import ToastViewport from "./shared/components/ToastViewport";
import TopBar from "./shared/components/TopBar";

export default function App() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const projectWizardOpen = useUiStore((state) => state.projectWizardOpen);
  const sidebarCollapsed = useUiStore((state) => state.sidebarCollapsed);
  const sidebarWidth = useUiStore((state) => state.sidebarWidth);
  const hasActiveProject = Boolean(currentProjectId);

  useEffect(() => {
    const lastId = window.localStorage.getItem("dqcr_last_project_id");
    if (!currentProjectId && lastId) {
      fetchProject(lastId)
        .then((project) => {
          useProjectStore.getState().setProject(project.id);
        })
        .catch(() => {
          window.localStorage.removeItem("dqcr_last_project_id");
        });
    }
  }, [currentProjectId]);

  return (
    <>
      {!hasActiveProject ? (
        <div className="hub">
          <TopBar hubMode />
          <ProjectsHub />
          <ToastViewport />
          {projectWizardOpen ? <ProjectWizardModal /> : null}
        </div>
      ) : (
        <div
          className="app-shell"
          style={
            {
              "--width-sidebar": `${sidebarCollapsed ? 64 : sidebarWidth}px`,
            } as CSSProperties
          }
        >
          <TopBar />
          <div className="layout-main">
            <Sidebar />
            <div className="main-column">
              <TabBar />
              <Workbench />
              <BottomPanel />
            </div>
          </div>
          <StatusBar />
          <ToastViewport />
          {projectWizardOpen ? <ProjectWizardModal /> : null}
        </div>
      )}
    </>
  );
}
