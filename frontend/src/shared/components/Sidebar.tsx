import ProjectSidebar from "../../features/project-sidebar/ProjectSidebar";

// Compatibility wrapper. Feature-specific sidebar implementation lives in features/project-sidebar.
export default function Sidebar() {
  return (
    <aside className="sidebar-inset">
      <ProjectSidebar />
    </aside>
  );
}
