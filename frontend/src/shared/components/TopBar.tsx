import { useMutation, useQuery } from "@tanstack/react-query";

import { fetchProjectContexts, fetchProjects, runProjectValidation } from "../../api/projects";
import { useTheme } from "../../app/providers/ThemeProvider";
import { useContextStore } from "../../app/store/contextStore";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import { useValidationStore } from "../../app/store/validationStore";
import Badge from "./ui/Badge";
import Button from "./ui/Button";
import Select from "./ui/Select";
import Tooltip from "./ui/Tooltip";

interface TopBarProps {
  hubMode?: boolean;
}

export default function TopBar({ hubMode = false }: TopBarProps) {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const setProject = useProjectStore((state) => state.setProject);
  const activeContext = useContextStore((state) => state.activeContext);
  const activeContexts = useContextStore((state) => state.activeContexts);
  const multiMode = useContextStore((state) => state.multiMode);
  const setActiveContext = useContextStore((state) => state.setActiveContext);
  const toggleMultiMode = useContextStore((state) => state.toggleMultiMode);
  const toggleContextInMultiMode = useContextStore((state) => state.toggleContextInMultiMode);
  const { theme, toggleTheme } = useTheme();
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const userRole = useUiStore((state) => state.userRole);
  const setUserRole = useUiStore((state) => state.setUserRole);
  const userEmail = useUiStore((state) => state.userEmail);
  const addToast = useUiStore((state) => state.addToast);
  const setLatestRun = useValidationStore((state) => state.setLatestRun);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
    enabled: !hubMode,
  });

  const contextsQuery = useQuery({
    queryKey: ["contexts", currentProjectId],
    queryFn: () => fetchProjectContexts(currentProjectId as string),
    enabled: Boolean(currentProjectId) && !hubMode,
  });

  const validateMutation = useMutation({
    mutationFn: () => runProjectValidation(currentProjectId as string),
    onSuccess: (result) => {
      setLatestRun(result);
      addToast(
        `Validation: ${result.summary.errors} errors, ${result.summary.warnings} warnings, ${result.summary.passed} passed`,
        result.summary.errors > 0 ? "error" : "success",
      );
      setActiveTab("validate");
    },
    onError: () => {
      addToast("Validation failed", "error");
      setActiveTab("validate");
    },
  });

  return (
    <header
      style={{
        height: "var(--hub-topbar-h)",
        background: "var(--hub-surface-card)",
        borderBottom: "var(--hub-border-subtle)",
        display: "flex",
        alignItems: "center",
        padding: "0 16px",
        gap: 8,
        flexShrink: 0,
        zIndex: 100,
      }}
    >
      <span
        style={{
          fontSize: "var(--hub-text-lg)",
          fontWeight: "var(--hub-weight-medium)",
          color: "var(--hub-accent-600)",
          letterSpacing: "-0.2px",
        }}
      >
        DQCR
      </span>
      <span style={{ fontSize: "var(--hub-text-lg)", color: "var(--color-text-secondary)" }}> Studio</span>

      {!hubMode && (
        <button className="hub-btn-secondary" style={{ marginLeft: 8, fontSize: 11, padding: "3px 10px" }} onClick={() => setProject(null)}>
          ⊟ All projects
        </button>
      )}

      <div style={{ flex: 1 }} />

      {hubMode ? (
        <span style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>{userEmail}</span>
      ) : (
        <div className="topbar-controls">
          <Select value={currentProjectId ?? ""} onChange={(event) => setProject(event.target.value || null)} aria-label="Project switcher">
            {(projectsQuery.data ?? []).map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </Select>

          {!multiMode ? (
            <Select value={activeContext} onChange={(event) => setActiveContext(event.target.value)} aria-label="Context switcher">
              {(contextsQuery.data ?? [{ id: "default", name: "default" }]).map((context) => (
                <option key={context.id} value={context.id}>
                  {context.name}
                </option>
              ))}
            </Select>
          ) : (
            <div className="multi-context-list">
              {(contextsQuery.data ?? [{ id: "default", name: "default" }]).map((context) => (
                <label key={context.id}>
                  <input
                    type="checkbox"
                    checked={activeContexts.includes(context.id)}
                    onChange={() => toggleContextInMultiMode(context.id)}
                  />
                  {context.name}
                </label>
              ))}
            </div>
          )}

          <Button disabled={!currentProjectId || validateMutation.isPending} onClick={() => validateMutation.mutate()} type="button">
            Validate
          </Button>
          <Button className="action-btn-primary action-btn-build" disabled={!currentProjectId} onClick={() => setActiveTab("build")} type="button">
            Build
          </Button>
          <Button disabled={userRole !== "admin"} onClick={() => setActiveTab("admin")} type="button">
            Admin
          </Button>
          <Select value={userRole} onChange={(event) => setUserRole(event.target.value as "user" | "admin" | "viewer")} aria-label="Role">
            <option value="user">role:user</option>
            <option value="admin">role:admin</option>
            <option value="viewer">role:viewer</option>
          </Select>
          <Button onClick={toggleTheme} type="button">
            {theme === "light" ? "Dark" : "Light"}
          </Button>
          <Tooltip text="Switch between one context and multiple contexts">
            <Button onClick={toggleMultiMode} type="button">
              {multiMode ? "Single Context" : "Multi Context"}
            </Button>
          </Tooltip>
          {multiMode ? <Badge>{activeContexts.length} selected</Badge> : null}
        </div>
      )}
    </header>
  );
}
