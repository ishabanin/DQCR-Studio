import { useMemo } from "react";
import YAML from "yaml";

import { useProjectStore } from "../../app/store/projectStore";
import { ContextsCard } from "./components/ContextsCard";
import { ModelSummaryGrid } from "./components/ModelSummaryGrid";
import { ParametersSummaryCard } from "./components/ParametersSummaryCard";
import { ProjectSettingsCard } from "./components/ProjectSettingsCard";
import { useProjectInfo } from "./hooks/useProjectInfo";

function parseProjectHeader(projectYml: string): { name: string; description: string } {
  try {
    const parsed = YAML.parse(projectYml) as Record<string, unknown> | null;
    return {
      name: typeof parsed?.name === "string" ? parsed.name : "Untitled project",
      description: typeof parsed?.description === "string" ? parsed.description : "Project summary and editable settings.",
    };
  } catch {
    return {
      name: "Untitled project",
      description: "Project summary and editable settings.",
    };
  }
}

export function ProjectInfoScreen() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const { data, isLoading, error } = useProjectInfo(currentProjectId);

  const header = useMemo(
    () => parseProjectHeader(data?.projectYml ?? ""),
    [data?.projectYml],
  );

  if (!currentProjectId) {
    return (
      <section className="project-info-screen project-info-empty">
        <div className="project-hero">
          <p className="project-card-eyebrow">Project Info</p>
          <h1>Select a project</h1>
          <p>Choose a project in the top bar to load its summary, contexts, parameters, and editable project.yml.</p>
        </div>
      </section>
    );
  }

  if (isLoading || !data) {
    return (
      <section className="project-info-screen">
        <div className="project-hero">
          <p className="project-card-eyebrow">Project Info</p>
          <h1>Loading project summary...</h1>
          <p>Collecting file tree, workflow cache, contexts, parameters, and project settings.</p>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="project-info-screen">
        <div className="project-hero">
          <p className="project-card-eyebrow">Project Info</p>
          <h1>Failed to load project data</h1>
          <p>{error instanceof Error ? error.message : "Unknown error"}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="project-info-screen">
      <header className="project-hero">
        <div className="project-hero-copy">
          <p className="project-card-eyebrow">Project Info</p>
          <h1>{header.name}</h1>
          <p>{header.description}</p>
        </div>
        <div className="project-summary-grid">
          <div className="project-summary-tile">
            <strong>{data.models.length}</strong>
            <span>models</span>
          </div>
          <div className="project-summary-tile">
            <strong>{data.totalFolders}</strong>
            <span>folders</span>
          </div>
          <div className="project-summary-tile">
            <strong>{data.totalSqlFiles}</strong>
            <span>SQL files</span>
          </div>
          <div className="project-summary-tile">
            <strong>{data.totalContexts}</strong>
            <span>contexts</span>
          </div>
          <div className="project-summary-tile">
            <strong>{data.totalGlobalParams}</strong>
            <span>global params</span>
          </div>
          <div className="project-summary-tile">
            <strong>{data.totalModelParams}</strong>
            <span>model params</span>
          </div>
        </div>
      </header>

      <ProjectSettingsCard projectId={currentProjectId} initialContent={data.projectYml} />

      <div className="project-secondary-grid">
        <ParametersSummaryCard parameters={data.parameters} models={data.models} />
        <ContextsCard contexts={data.contexts} />
      </div>

      <ModelSummaryGrid models={data.models} />
    </section>
  );
}
