import { useMemo, useState } from "react";

import { useProjectStore } from "../../app/store/projectStore";
import { CreateProjectModal } from "./components/CreateProjectModal";
import { DeleteProjectModal } from "./components/DeleteProjectModal";
import { EditProjectModal } from "./components/EditProjectModal";
import { HubSidebar } from "./components/HubSidebar";
import { HubToolbar } from "./components/HubToolbar";
import { MetricCard } from "./components/MetricCard";
import { ProjectCard } from "./components/ProjectCard";
import { ProjectsTable } from "./components/ProjectsTable";
import { ProjectCardSkeleton, StatsRowSkeleton } from "./components/skeletons";
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

  return (
    <div style={{ display: "flex", height: "calc(100vh - var(--hub-topbar-h))" }}>
      <div className="hub-sidebar-wrap">
        <HubSidebar counts={counts} filters={filters} onFilter={patchFilter} />
      </div>

      <main style={{ flex: 1, minWidth: 0, padding: "var(--hub-page-py) var(--hub-page-px)", overflowY: "auto" }}>
        <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
          <div>
            <h1 style={{ fontSize: "var(--hub-text-xl)", fontWeight: "var(--hub-weight-medium)", color: "var(--color-text-primary)", marginBottom: 4 }}>All projects</h1>
            <p style={{ fontSize: "var(--hub-text-sm)", color: "var(--color-text-secondary)" }}>
              {hasActiveFilters ? `Showing ${filtered.length} of ${projects.length}` : "Manage and open DQCR projects"}
            </p>
          </div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <button className="hub-btn-primary" onClick={() => setModal({ type: "create", mode: "create" })}>
              + New project
            </button>
            <button className="hub-btn-secondary" onClick={() => setModal({ type: "create", mode: "import" })}>
              ↓ Import
            </button>
          </div>
        </div>

        {!hasActiveFilters && !isLoading && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginBottom: 20 }}>
            <MetricCard value={counts.all} label="All projects" />
            <MetricCard value={counts.public} label="Public" />
            <MetricCard value={totalModels} label="Models" />
            <MetricCard value={totalSql} label="SQL files" />
          </div>
        )}

        {isLoading && <StatsRowSkeleton />}

        <HubToolbar filters={filters} onFilter={patchFilter} view={view} setView={setView} />

        {isError && (
          <div style={{ textAlign: "center", padding: "48px 20px" }}>
            <div style={{ fontSize: 28, marginBottom: 10, color: "var(--hub-danger-text)", opacity: 0.4 }}>⚠</div>
            <h3 style={{ fontSize: 14, fontWeight: "var(--hub-weight-medium)", marginBottom: 6 }}>Failed to load projects</h3>
            <p style={{ fontSize: "var(--hub-text-sm)", color: "var(--color-text-secondary)", marginBottom: 14 }}>{error?.message ?? "Unknown error"}</p>
            <button className="hub-btn-secondary" onClick={() => void refetch()}>
              ↻ Retry
            </button>
          </div>
        )}

        {isLoading && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <ProjectCardSkeleton key={i} />
            ))}
          </div>
        )}

        {!isLoading && !isError && projects.length === 0 && (
          <div style={{ textAlign: "center", padding: "80px 20px" }}>
            <div style={{ fontSize: 36, marginBottom: 14, color: "var(--color-text-tertiary)", opacity: 0.3 }}>⊟</div>
            <h3 style={{ fontSize: 16, fontWeight: "var(--hub-weight-medium)", marginBottom: 8 }}>No projects yet</h3>
            <p style={{ fontSize: "var(--hub-text-sm)", color: "var(--color-text-secondary)", maxWidth: 320, margin: "0 auto 20px", lineHeight: 1.6 }}>
              Create your first DQCR project or import an existing one to get started.
            </p>
            <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
              <button className="hub-btn-primary" onClick={() => setModal({ type: "create", mode: "create" })}>
                + New project
              </button>
              <button className="hub-btn-secondary" onClick={() => setModal({ type: "create", mode: "import" })}>
                ↓ Import
              </button>
            </div>
          </div>
        )}

        {!isLoading && !isError && projects.length > 0 && filtered.length === 0 && (
          <div style={{ textAlign: "center", padding: "48px 20px" }}>
            <div style={{ fontSize: 28, marginBottom: 10, opacity: 0.25 }}>⊘</div>
            <h3 style={{ fontSize: 14, fontWeight: "var(--hub-weight-medium)", marginBottom: 6, color: "var(--color-text-secondary)" }}>No projects match filters</h3>
            <p style={{ fontSize: "var(--hub-text-sm)", color: "var(--color-text-tertiary)", marginBottom: 14 }}>Try changing the search query or removing filters.</p>
            <button className="hub-btn-secondary" onClick={clearFilters}>
              Clear all filters
            </button>
          </div>
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
                    onEdit={(projectId) => {
                      const target = projects.find((item) => item.project_id === projectId);
                      if (target) setModal({ type: "edit", project: target });
                    }}
                    onDelete={(projectId) => {
                      const target = projects.find((item) => item.project_id === projectId);
                      if (target) setModal({ type: "delete", project: target });
                    }}
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
                onEdit={(projectId) => {
                  const target = projects.find((item) => item.project_id === projectId);
                  if (target) setModal({ type: "edit", project: target });
                }}
                onDelete={(projectId) => {
                  const target = projects.find((item) => item.project_id === projectId);
                  if (target) setModal({ type: "delete", project: target });
                }}
              />
            )}
          </>
        )}
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
