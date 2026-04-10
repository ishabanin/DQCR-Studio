import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import YAML from "yaml";

import { createProjectModel, fetchProjects, saveFileContent } from "../../api/projects";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import ProjectStructureDialog, { type ProjectStructureActionState } from "../../shared/components/ProjectStructureDialog";
import { ContextsCard } from "./components/ContextsCard";
import { ModelSummaryGrid } from "./components/ModelSummaryGrid";
import { ParametersSummaryCard } from "./components/ParametersSummaryCard";
import { PageHeader } from "./components/PageHeader";
import { ProjectSettingsCard } from "./components/ProjectSettingsCard";
import { PropertiesEditor } from "./components/PropertiesEditor";
import { StatsRow } from "./components/StatsRow";
import { useProjectInfo } from "./hooks/useProjectInfo";
import type { ProjectSettings, PropertyEntry } from "./types";
import "./project-info.css";

const SYSTEM_PROPS = ["dqcr_visibility", "dqcr_tags"];

function serializeProjectYml(
  originalYmlContent: string,
  draft: { settings: ProjectSettings; properties: PropertyEntry[] },
): string {
  let yml = {} as Record<string, unknown>;

  try {
    yml = (YAML.parse(originalYmlContent) as Record<string, unknown> | null) ?? {};
  } catch {
    yml = {};
  }

  yml.name = draft.settings.name;
  yml.description = draft.settings.description;
  yml.template = draft.settings.template;

  const currentProps =
    typeof yml.properties === "object" && yml.properties !== null
      ? (yml.properties as Record<string, unknown>)
      : {};

  const systemProps = Object.fromEntries(
    SYSTEM_PROPS.filter((key) => key in currentProps).map((key) => [key, currentProps[key]]),
  );

  const customProps = Object.fromEntries(
    draft.properties
      .filter((entry) => entry.key.trim() !== "")
      .map((entry) => [entry.key.trim(), entry.value]),
  );

  const nextProps = {
    ...systemProps,
    version: draft.settings.version || undefined,
    owner: draft.settings.owner || undefined,
    ...customProps,
  };

  for (const key of Object.keys(nextProps)) {
    if ((nextProps as Record<string, unknown>)[key] === undefined) {
      delete (nextProps as Record<string, unknown>)[key];
    }
  }

  if (Object.keys(nextProps).length > 0) {
    yml.properties = nextProps;
  } else {
    delete yml.properties;
  }

  return `${YAML.stringify(yml, { lineWidth: 0 }).trimEnd()}\n`;
}

function ModelCardSkeleton() {
  return (
    <div className="pi-card">
      <div style={{ padding: "10px 14px 8px", borderBottom: "var(--pi-border-subtle)" }}>
        <div className="pi-skeleton" style={{ height: 14, width: "60%" }} />
      </div>
      <div style={{ padding: "8px 14px", display: "flex", flexDirection: "column", gap: 6 }}>
        {[1, 2, 3].map((item) => (
          <div key={item} style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <div className="pi-skeleton" style={{ width: 6, height: 6, borderRadius: "50%", flexShrink: 0 }} />
            <div className="pi-skeleton" style={{ height: 11, flex: 1 }} />
            <div className="pi-skeleton" style={{ height: 11, width: 20 }} />
          </div>
        ))}
      </div>
      <div
        style={{
          padding: "6px 14px",
          background: "var(--pi-bg-panel)",
          borderTop: "var(--pi-border-subtle)",
          display: "flex",
          gap: 6,
          alignItems: "center",
        }}
      >
        <div className="pi-skeleton" style={{ width: 7, height: 7, borderRadius: "50%", flexShrink: 0 }} />
        <div className="pi-skeleton" style={{ height: 10, flex: 1 }} />
        <div className="pi-skeleton" style={{ height: 16, width: 28, borderRadius: 10 }} />
      </div>
    </div>
  );
}

function SkeletonPage() {
  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
        <div className="pi-skeleton" style={{ width: 36, height: 36, borderRadius: 8, flexShrink: 0 }} />
        <div>
          <div className="pi-skeleton" style={{ height: 20, width: 200, marginBottom: 6 }} />
          <div className="pi-skeleton" style={{ height: 12, width: 280 }} />
        </div>
      </div>

      <div className="pi-stats-grid">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="pi-stat-card">
            <div className="pi-skeleton" style={{ height: 28, width: 48, marginBottom: 8 }} />
            <div className="pi-skeleton" style={{ height: 13, width: 72 }} />
          </div>
        ))}
      </div>

      <div className="pi-two-col" style={{ marginBottom: 20 }}>
        {Array.from({ length: 2 }).map((_, index) => (
          <div key={index} className="pi-card">
            <div style={{ height: 38, background: "var(--pi-bg-panel)", borderBottom: "var(--pi-border-subtle)" }} />
            {Array.from({ length: 4 }).map((_, row) => (
              <div
                key={row}
                style={{
                  display: "flex",
                  gap: 8,
                  padding: "7px 14px",
                  borderBottom: "var(--pi-border-subtle)",
                }}
              >
                <div className="pi-skeleton" style={{ height: 12, width: 80, flexShrink: 0 }} />
                <div className="pi-skeleton" style={{ height: 12, flex: 1 }} />
              </div>
            ))}
          </div>
        ))}
      </div>

      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
          <div className="pi-skeleton" style={{ height: 14, width: 60 }} />
          <div className="pi-skeleton" style={{ height: 12, width: 160 }} />
        </div>
        <div className="pi-models-grid">
          {Array.from({ length: 3 }).map((_, index) => (
            <ModelCardSkeleton key={index} />
          ))}
        </div>
      </div>
    </>
  );
}

export function ProjectInfoScreen() {
  const queryClient = useQueryClient();
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const addToast = useUiStore((state) => state.addToast);
  const setInitialModelId = useUiStore((state) => state.setInitialModelId);
  const setBottomPanelTab = useUiStore((state) => state.setBottomPanelTab);
  const toggleBottomPanel = useUiStore((state) => state.toggleBottomPanel);
  const bottomPanelExpanded = useUiStore((state) => state.bottomPanelExpanded);

  const { data, isLoading, isError, error, refetch } = useProjectInfo(currentProjectId);
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
    staleTime: 60_000,
  });

  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved">("idle");
  const [draftSettings, setDraftSettings] = useState<ProjectSettings | null>(null);
  const [draftProperties, setDraftProperties] = useState<PropertyEntry[] | null>(null);
  const [createModelState, setCreateModelState] = useState<ProjectStructureActionState | null>(null);
  const [createModelValue, setCreateModelValue] = useState("NewModel");

  useEffect(() => {
    if (!data || isDirty) return;
    setDraftSettings(data.settings);
    setDraftProperties(data.properties);
  }, [data, isDirty]);

  const projectMeta = useMemo(
    () => projectsQuery.data?.find((project) => project.id === currentProjectId) ?? null,
    [currentProjectId, projectsQuery.data],
  );

  const createModelMutation = useMutation({
    mutationFn: (modelId: string) => createProjectModel(currentProjectId as string, modelId),
    onSuccess: async (payload) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projectTree", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["project-info", "tree", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["project-info", "workflow", currentProjectId] }),
      ]);
      setInitialModelId(payload.model_id);
      setActiveTab("model");
      setCreateModelState(null);
      addToast("Model created", "success");
    },
    onError: () => addToast("Failed to create model", "error"),
  });

  const handleSave = async () => {
    if (!currentProjectId || !data || !draftSettings || !draftProperties || isSaving) return;

    setIsSaving(true);
    try {
      const nextContent = serializeProjectYml(data.projectYml, {
        settings: draftSettings,
        properties: draftProperties,
      });
      await saveFileContent(currentProjectId, "project.yml", nextContent);
      await queryClient.invalidateQueries({ queryKey: ["project-info", "project-yml", currentProjectId] });
      await refetch();
      setIsDirty(false);
      setSaveStatus("saved");
      addToast("✓ Saved", "success");
      window.setTimeout(() => setSaveStatus("idle"), 1500);
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "Unknown error";
      addToast(`Failed to save: ${message}`, "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    if (!data) return;
    setDraftSettings(data.settings);
    setDraftProperties(data.properties);
    setIsDirty(false);
  };

  const handleOpenModel = (_modelId: string) => {
    useEditorStore.getState().setLineageTarget({ modelId: _modelId, nodePath: null });
    setActiveTab("lineage");
  };

  const handleOpenTerminal = () => {
    setBottomPanelTab("terminal");
    if (!bottomPanelExpanded) {
      toggleBottomPanel();
    }
  };

  const handleOpenCreateModel = () => {
    setCreateModelValue("NewModel");
    setCreateModelState({ mode: "new-model", path: ".", nodeType: "directory" });
  };

  const handleCreateModel = () => {
    const modelId = createModelValue.trim();
    if (!modelId) {
      addToast("Model ID is required", "error");
      return;
    }
    createModelMutation.mutate(modelId);
  };

  if (!currentProjectId) {
    return null;
  }

  return (
    <div className="pi-page">
      {isLoading ? <SkeletonPage /> : null}

      {isError ? (
        <div className="pi-error-banner">
          <span style={{ fontSize: 16, color: "var(--pi-danger-text)", flexShrink: 0 }}>⚠</span>
          <div>
            <div
              style={{
                fontSize: "var(--pi-text-sm)",
                fontWeight: "var(--pi-weight-medium)",
                color: "var(--pi-danger-text)",
                marginBottom: 4,
              }}
            >
              Failed to load project data
            </div>
            <div style={{ fontSize: "var(--pi-text-xs)", color: "var(--color-text-secondary)" }}>
              {error instanceof Error ? error.message : "Unknown error"}
            </div>
          </div>
          <button className="pi-btn-secondary" style={{ marginLeft: "auto" }} onClick={() => refetch()}>
            ↻ Retry
          </button>
        </div>
      ) : null}

      {!isLoading && data && draftSettings && draftProperties ? (
        <>
          <PageHeader
            projectId={currentProjectId}
            name={draftSettings.name || projectMeta?.name || currentProjectId}
            template={draftSettings.template || "flx"}
            projectType={projectMeta?.project_type ?? projectMeta?.source_type ?? "internal"}
            projectPath={projectMeta?.source_path ?? `/projects/${currentProjectId}`}
            isDirty={isDirty}
            isSaving={isSaving}
            saveStatus={saveStatus}
            onSave={handleSave}
            onOpenTerminal={handleOpenTerminal}
          />

          {isDirty ? (
            <div
              className="pi-dirty-banner"
              style={{ marginBottom: "var(--pi-gap-lg)", borderRadius: "var(--pi-radius-md)" }}
            >
              <span style={{ fontSize: 14 }}>⚠</span>
              <span>You have unsaved changes</span>
              <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                <button
                  className="pi-btn-secondary"
                  style={{ fontSize: 11, padding: "3px 10px" }}
                  onClick={handleDiscard}
                >
                  Discard
                </button>
                <button
                  className="pi-btn-primary visible"
                  style={{ fontSize: 11, padding: "3px 14px" }}
                  onClick={handleSave}
                  disabled={isSaving}
                >
                  {isSaving ? "Saving…" : "Save changes"}
                </button>
              </div>
            </div>
          ) : null}

          <div className="pi-stats-grid">
            <StatsRow
              models={data.models.length}
              totalFolders={data.totalFolders}
              totalSqlFiles={data.totalSqlFiles}
              totalContexts={data.totalContexts}
            />
          </div>

          <div className="pi-two-col">
            <ProjectSettingsCard
              draft={draftSettings}
              onChange={(key, value) => {
                setDraftSettings((prev) => (prev ? { ...prev, [key]: value } : prev));
                setIsDirty(true);
              }}
              onReset={handleDiscard}
            />

            <PropertiesEditor
              entries={draftProperties}
              onChange={(entries) => {
                setDraftProperties(entries);
                setIsDirty(true);
              }}
            />
          </div>

          <ModelSummaryGrid
            models={data.models}
            cacheStatuses={data.cacheStatuses}
            totalFolders={data.totalFolders}
            totalSql={data.totalSqlFiles}
            onOpenModel={handleOpenModel}
            onCreateModel={handleOpenCreateModel}
          />

          <div className="pi-two-col" style={{ marginBottom: 0 }}>
            <ContextsCard contexts={data.contexts} />
            <ParametersSummaryCard
              globalParams={data.globalParams}
              modelScopedCount={data.modelScopedCount}
            />
          </div>
        </>
      ) : null}

      <ProjectStructureDialog
        state={createModelState}
        value={createModelValue}
        availableModes={["new-model"]}
        onValueChange={setCreateModelValue}
        onModeChange={() => undefined}
        onCancel={() => setCreateModelState(null)}
        onConfirm={handleCreateModel}
        pending={createModelMutation.isPending}
      />
    </div>
  );
}
