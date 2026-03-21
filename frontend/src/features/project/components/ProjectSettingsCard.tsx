import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import YAML from "yaml";

import { saveFileContent } from "../../../api/projects";
import { useUiStore } from "../../../app/store/uiStore";
import Button from "../../../shared/components/ui/Button";
import Input from "../../../shared/components/ui/Input";
import { PropertiesEditor, type PropertyRow } from "./PropertiesEditor";

interface ProjectSettingsDraft {
  name: string;
  description: string;
  template: string;
  properties: PropertyRow[];
}

function createPropertyRow(key = "", value = ""): PropertyRow {
  return {
    id: `${key}-${value}-${Math.random().toString(36).slice(2, 8)}`,
    key,
    value,
  };
}

function normalizeProperties(properties: unknown): PropertyRow[] {
  if (!properties || typeof properties !== "object") return [];
  return Object.entries(properties as Record<string, unknown>).map(([key, value]) => createPropertyRow(key, String(value ?? "")));
}

function parseProjectYaml(content: string): ProjectSettingsDraft {
  const parsed = YAML.parse(content) as Record<string, unknown> | null;
  return {
    name: typeof parsed?.name === "string" ? parsed.name : "",
    description: typeof parsed?.description === "string" ? parsed.description : "",
    template: typeof parsed?.template === "string" ? parsed.template : "",
    properties: normalizeProperties(parsed?.properties),
  };
}

function safelyParseProjectYaml(content: string): { draft: ProjectSettingsDraft; error: string | null } {
  try {
    return {
      draft: parseProjectYaml(content),
      error: null,
    };
  } catch (error) {
    return {
      draft: {
        name: "",
        description: "",
        template: "",
        properties: [],
      },
      error: error instanceof Error ? error.message : "Invalid YAML",
    };
  }
}

function buildYamlFromDraft(draft: ProjectSettingsDraft): string {
  const propertyMap = Object.fromEntries(
    draft.properties
      .filter((item) => item.key.trim())
      .map((item) => [item.key.trim(), item.value]),
  );

  const nextDoc: Record<string, unknown> = {
    name: draft.name,
    description: draft.description,
  };

  if (draft.template.trim()) {
    nextDoc.template = draft.template.trim();
  }
  if (Object.keys(propertyMap).length > 0) {
    nextDoc.properties = propertyMap;
  }

  return YAML.stringify(nextDoc, {
    defaultStringType: "QUOTE_DOUBLE",
    lineWidth: 0,
  }).trimEnd() + "\n";
}

export function ProjectSettingsCard({
  projectId,
  initialContent,
}: {
  projectId: string;
  initialContent: string;
}) {
  const queryClient = useQueryClient();
  const addToast = useUiStore((state) => state.addToast);
  const initialState = useMemo(() => safelyParseProjectYaml(initialContent), [initialContent]);
  const [draft, setDraft] = useState<ProjectSettingsDraft>(initialState.draft);
  const [rawDraft, setRawDraft] = useState(initialContent);
  const [parseError, setParseError] = useState<string | null>(initialState.error);

  useEffect(() => {
    const next = safelyParseProjectYaml(initialContent);
    setDraft(next.draft);
    setRawDraft(initialContent);
    setParseError(next.error);
  }, [initialContent]);

  const isDirty = rawDraft !== initialContent;

  const saveMutation = useMutation({
    mutationFn: () => saveFileContent(projectId, "project.yml", rawDraft),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["project-info"] });
      addToast("project.yml saved", "success");
    },
    onError: () => addToast("Failed to save project.yml", "error"),
  });

  const updateDraft = (patch: Partial<ProjectSettingsDraft>) => {
    const nextDraft = { ...draft, ...patch };
    setDraft(nextDraft);
    setRawDraft(buildYamlFromDraft(nextDraft));
    setParseError(null);
  };

  const handleRawChange = (value: string) => {
    setRawDraft(value);
    try {
      setDraft(parseProjectYaml(value));
      setParseError(null);
    } catch (error) {
      setParseError(error instanceof Error ? error.message : "Invalid YAML");
    }
  };

  const propertyCount = useMemo(
    () => draft.properties.filter((item) => item.key.trim()).length,
    [draft.properties],
  );

  return (
    <section className="project-card project-settings-card">
      <div className="project-card-head">
        <div>
          <p className="project-card-eyebrow">Project Settings</p>
          <h2>project.yml</h2>
        </div>
        <div className="project-card-actions">
          <span className={parseError ? "project-status-pill project-status-pill-error" : "project-status-pill"}>
            {parseError ? "YAML invalid" : "YAML valid"}
          </span>
          <Button type="button" onClick={() => handleRawChange(initialContent)} disabled={!isDirty || saveMutation.isPending}>
            Reset
          </Button>
          <Button
            className="action-btn-primary"
            type="button"
            onClick={() => saveMutation.mutate()}
            disabled={!isDirty || Boolean(parseError) || saveMutation.isPending}
          >
            {saveMutation.isPending ? "Saving..." : "Save"}
          </Button>
        </div>
      </div>

      <div className="project-settings-layout">
        <div className="project-settings-form">
          <label className="project-field">
            <span>Name</span>
            <Input value={draft.name} onChange={(event) => updateDraft({ name: event.target.value })} />
          </label>

          <label className="project-field">
            <span>Template</span>
            <Input
              value={draft.template}
              onChange={(event) => updateDraft({ template: event.target.value })}
              placeholder="flx"
            />
          </label>

          <label className="project-field">
            <span>Description</span>
            <textarea
              className="project-textarea"
              value={draft.description}
              onChange={(event) => updateDraft({ description: event.target.value })}
              rows={5}
            />
          </label>

          <div className="project-field">
            <div className="project-field-head">
              <span>Custom properties</span>
              <Button
                type="button"
                onClick={() => updateDraft({ properties: [...draft.properties, createPropertyRow()] })}
              >
                Add property
              </Button>
            </div>
            <PropertiesEditor items={draft.properties} onChange={(properties) => updateDraft({ properties })} />
            <p className="project-inline-meta">{propertyCount} properties in file</p>
          </div>
        </div>

        <div className="project-settings-raw">
          <div className="project-field-head">
            <span>Raw YAML</span>
            <span className="project-inline-meta">Direct edit mode</span>
          </div>
          <textarea
            className="project-code-editor"
            value={rawDraft}
            onChange={(event) => handleRawChange(event.target.value)}
            spellCheck={false}
            rows={20}
          />
          {parseError ? <p className="project-error-copy">{parseError}</p> : <p className="project-muted-copy">Structured form and YAML stay in sync.</p>}
        </div>
      </div>
    </section>
  );
}
