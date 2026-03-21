const PROJECT_ICON_PALETTES = [
  { bg: "#E1F5EE", color: "#085041" },
  { bg: "#E6F1FB", color: "#0C447C" },
  { bg: "#FAEEDA", color: "#633806" },
  { bg: "#EEEDFE", color: "#3C3489" },
  { bg: "#FAECE7", color: "#712B13" },
  { bg: "#EAF3DE", color: "#27500A" },
] as const;

export function getProjectPalette(projectId: string) {
  const hash = projectId.split("").reduce((acc, c) => (acc * 31 + c.charCodeAt(0)) & 0xffff, 0);
  return PROJECT_ICON_PALETTES[hash % PROJECT_ICON_PALETTES.length];
}

export function PageHeader({
  projectId,
  name,
  template,
  projectType,
  projectPath,
  isDirty,
  isSaving,
  saveStatus,
  onSave,
  onOpenTerminal,
}: {
  projectId: string;
  name: string;
  template: string;
  projectType: string;
  projectPath: string;
  isDirty: boolean;
  isSaving: boolean;
  saveStatus: "idle" | "saved";
  onSave: () => void;
  onOpenTerminal: () => void;
}) {
  const palette = getProjectPalette(projectId);

  return (
    <div className="pi-page-header">
      <div className="pi-page-header-main">
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: "var(--pi-radius-icon)",
            background: palette.bg,
            color: palette.color,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            fontWeight: "var(--pi-weight-medium)",
            flexShrink: 0,
            border: `0.5px solid ${palette.color}30`,
          }}
        >
          {name.charAt(0).toUpperCase() || "P"}
        </div>

        <div style={{ minWidth: 0 }}>
          <h1 className="pi-page-title">{name}</h1>
          <div className="pi-page-meta">
            <span>template: {template || "—"}</span>
            <span style={{ color: "var(--pi-gray-300)" }}>·</span>
            <span>{projectType}</span>
            <span style={{ color: "var(--pi-gray-300)" }}>·</span>
            <span style={{ opacity: 0.7 }}>{projectPath}</span>
          </div>
        </div>
      </div>

      <div className="pi-page-actions">
        <button
          className={`pi-btn-primary ${isDirty ? "visible" : ""}`}
          onClick={onSave}
          disabled={isSaving}
          style={{
            background: saveStatus === "saved" ? "var(--pi-accent-400)" : undefined,
          }}
        >
          {saveStatus === "saved" ? "✓ Saved" : isSaving ? "Saving…" : "Save changes"}
        </button>

        <button className="pi-btn-secondary" onClick={onOpenTerminal}>
          Open in terminal
        </button>
      </div>
    </div>
  );
}
