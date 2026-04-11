import { useMemo, useState } from "react";

import { useProjectStore } from "../../app/store/projectStore";
import Button from "../../shared/components/ui/Button";
import Empty from "../../shared/components/ui/Empty";
import { CreateProjectModal } from "./components/CreateProjectModal";
import { DeleteProjectModal } from "./components/DeleteProjectModal";
import { EditProjectModal } from "./components/EditProjectModal";
import { HubSidebar } from "./components/HubSidebar";
import { HubToolbar } from "./components/HubToolbar";
import { MetricCard } from "./components/MetricCard";
import { ProjectCard } from "./components/ProjectCard";
import { ProjectsTable } from "./components/ProjectsTable";
import { ProjectCardSkeleton, StatsRowSkeleton } from "./components/skeletons";
import CatalogPanel from "./CatalogPanel";
import { useProjectFilters } from "./hooks/useProjectFilters";
import { useProjects } from "./hooks/useProjects";
import type { CreateProjectPayload, MetadataUpdatePayload, ProjectListItem } from "./types";
import "./hub.css";

type ModalState =
  | { type: "create"; mode: "create" | "import" }
  | { type: "edit"; project: ProjectListItem }
  | { type: "delete"; project: ProjectListItem }
  | null;

export default function ProjectsHub() {
  const setProject = useProjectStore((state) => state.setProject);
  const {
    projects,
    isLoading,
    isError,
    error,
    refetch,
    createProject,
    importProject,
    updateProject,
    deleteProject,
    isCreating,
    isImporting,
    isUpdating,
    isDeleting,
  } = useProjects();

  const [view, setViewState] = useState<"grid" | "list">(() => (window.localStorage.getItem("dqcr_hub_view") as "grid" | "list") ?? "grid");
  const [modal, setModal] = useState<ModalState>(null);
  const [catalogExpandSignal, setCatalogExpandSignal] = useState(0);

  const setView = (value: "grid" | "list") => {
    setViewState(value);
    window.localStorage.setItem("dqcr_hub_view", value);
  };

  const { filtered, filters, patchFilter, clearFilters, counts, allTags, sortBy, sortDir, toggleSort } = useProjectFilters(projects);

  const hasActiveFilters = Boolean(filters.search || filters.visibility || filters.type || filters.tag);

  const totalModels = useMemo(() => projects.reduce((acc, project) => acc + project.model_count, 0), [projects]);
  const totalSql = useMemo(() => projects.reduce((acc, project) => acc + project.sql_count, 0), [projects]);

  const openProject = (projectId: string) => {
    setProject(projectId);
  };

  const openCatalogPanel = () => {
    setCatalogExpandSignal((prev) => prev + 1);
    window.setTimeout(() => {
      document.getElementById("hub-catalog-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  };

  const submitCreate = async (payload: CreateProjectPayload) => {
    await createProject(payload);
    setModal(null);
  };

  const submitImport = async (payload: {
    files: File[];
    relativePaths: string[];
    project_id?: string;
    name?: string;
    description?: string;
  }) => {
    await importProject(payload);
    setModal(null);
  };

  const submitEdit = async (projectId: string, payload: MetadataUpdatePayload) => {
    await updateProject({ projectId, data: payload });
    setModal(null);
  };

  const submitDelete = async (projectId: string) => {
    await deleteProject(projectId);
    setModal(null);
  };

  const getProjectById = (projectId: string) => projects.find((item) => item.project_id === projectId);

  const handleEditProject = (projectId: string) => {
    const target = getProjectById(projectId);
    if (target) setModal({ type: "edit", project: target });
  };

  const handleDeleteProject = (projectId: string) => {
    const target = getProjectById(projectId);
    if (target) setModal({ type: "delete", project: target });
  };

  return (
    <div className="hub-stage hub-stage-layout">
      <div className="hub-sidebar-wrap">
        <HubSidebar counts={counts} filters={filters} onFilter={patchFilter} />
      </div>

      <main className="hub-main">
        <section className="hub-hero">
          <div className="hub-hero-row">
            <div>
              <div className="hub-crumbs">
                <span>Workspace</span>
                <span>/</span>
                <span className="hub-crumbs-current">Projects</span>
              </div>
              <h1 className="hub-title">All projects</h1>
              <p className="hub-subtitle">
                {hasActiveFilters ? `Showing ${filtered.length} of ${projects.length}` : "Manage and open DQCR projects"}
              </p>
            </div>
            <div className="hub-hero-actions">
              <Button variant="default" onClick={() => setModal({ type: "create", mode: "create" })}>
                + New project
              </Button>
              <Button variant="secondary" onClick={() => setModal({ type: "create", mode: "import" })}>
                ↓ Import
              </Button>
            </div>
          </div>
          {!hasActiveFilters && !isLoading && (
            <div className="hub-metric-grid">
              <MetricCard value={counts.all} label="All projects" />
              <MetricCard value={counts.public} label="Public" />
              <MetricCard value={totalModels} label="Models" />
              <MetricCard value={totalSql} label="SQL files" />
            </div>
          )}
        </section>

        {/* toolbar is kept outside the hero card, similar to shadcn SidebarInset sections */}
        <div className="hub-toolbar-wrap">
          <HubToolbar filters={filters} onFilter={patchFilter} view={view} setView={setView} onOpenCatalog={openCatalogPanel} />
        </div>

        {isLoading && <StatsRowSkeleton />}

        {isError && (
          <Empty
            className="hub-state hub-state-error"
            icon="⚠"
            title="Failed to load projects"
            description={error?.message ?? "Unknown error"}
          >
            <Button variant="secondary" onClick={() => void refetch()}>
              ↻ Retry
            </Button>
          </Empty>
        )}

        {isLoading && (
          <div className="hub-grid">
            {Array.from({ length: 6 }).map((_, i) => (
              <ProjectCardSkeleton key={i} />
            ))}
          </div>
        )}

        {!isLoading && !isError && projects.length === 0 && (
          <Empty
            className="hub-state hub-state-empty"
            icon="⊟"
            title="No projects yet"
            description="Create your first DQCR project or import an existing one to get started."
          >
            <div className="hub-state-actions">
              <Button variant="default" onClick={() => setModal({ type: "create", mode: "create" })}>
                + New project
              </Button>
              <Button variant="secondary" onClick={() => setModal({ type: "create", mode: "import" })}>
                ↓ Import
              </Button>
            </div>
          </Empty>
        )}

        {!isLoading && !isError && projects.length > 0 && filtered.length === 0 && (
          <Empty
            className="hub-state hub-state-empty"
            icon="⊘"
            title="No projects match filters"
            description="Try changing the search query or removing filters."
          >
            <Button variant="secondary" onClick={clearFilters}>
              Clear all filters
            </Button>
          </Empty>
        )}

        {!isLoading && !isError && filtered.length > 0 && (
          <>
            {view === "grid" ? (
              <div className="hub-grid">
                {filtered.map((project) => (
                  <ProjectCard
                    key={project.project_id}
                    project={project}
                    onOpen={openProject}
                    onEdit={handleEditProject}
                    onDelete={handleDeleteProject}
                    onTagClick={(tag) => patchFilter({ tag })}
                  />
                ))}
              </div>
            ) : (
              <ProjectsTable
                projects={filtered}
                sortBy={sortBy}
                sortDir={sortDir}
                onSort={toggleSort}
                onOpen={openProject}
                onEdit={handleEditProject}
                onDelete={handleDeleteProject}
              />
            )}
          </>
        )}

        <CatalogPanel expandSignal={catalogExpandSignal} />
      </main>

      {modal?.type === "create" && (
        <CreateProjectModal
          key={`create-${modal.mode}`}
          existingIds={projects.map((project) => project.project_id)}
          tagSuggestions={allTags}
          defaultMode={modal.mode}
          onClose={() => setModal(null)}
          onSubmitCreate={submitCreate}
          onSubmitImport={submitImport}
          isSubmitting={isCreating || isImporting}
        />
      )}

      {modal?.type === "edit" && (
        <EditProjectModal
          project={modal.project}
          tagSuggestions={allTags}
          onClose={() => setModal(null)}
          onSubmit={(payload) => submitEdit(modal.project.project_id, payload)}
          isSubmitting={isUpdating}
        />
      )}

      {modal?.type === "delete" && (
        <DeleteProjectModal
          project={modal.project}
          onClose={() => setModal(null)}
          onSubmit={() => submitDelete(modal.project.project_id)}
          isSubmitting={isDeleting}
        />
      )}
    </div>
  );
}
