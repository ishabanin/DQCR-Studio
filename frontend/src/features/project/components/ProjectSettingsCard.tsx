import type { ProjectSettings } from "../types";

const SETTINGS_FIELDS: Array<{
  key: keyof ProjectSettings;
  label: string;
  type?: "input" | "select";
  options?: string[];
  width?: number;
}> = [
  { key: "name", label: "Name", type: "input" },
  { key: "description", label: "Description", type: "input" },
  { key: "template", label: "Template", type: "select", options: ["flx", "dwh_mart", "dq_control"] },
  { key: "version", label: "Version", type: "input", width: 100 },
  { key: "owner", label: "Owner", type: "input" },
];

export function ProjectSettingsCard({
  draft,
  onChange,
  onReset,
}: {
  draft: ProjectSettings;
  onChange: (key: keyof ProjectSettings, value: string) => void;
  onReset: () => void;
}) {
  return (
    <div className="pi-card" onKeyDown={(event) => event.key === "Escape" && onReset()}>
      <div className="pi-card-header">
        <span className="pi-card-title">Project settings</span>
        <span className="pi-card-subtitle">project.yml</span>
      </div>

      {SETTINGS_FIELDS.map((field) => (
        <div key={field.key} className="pi-form-row">
          <span className="pi-form-label">{field.label}</span>
          <div className="pi-form-value">
            {field.type === "select" ? (
              <select
                className="pi-select"
                value={draft[field.key]}
                onChange={(event) => onChange(field.key, event.target.value)}
              >
                {(field.options ?? []).map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            ) : (
              <input
                className="pi-input"
                value={draft[field.key]}
                onChange={(event) => onChange(field.key, event.target.value)}
                style={field.width ? { width: field.width, flex: "0 0 auto" } : undefined}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
