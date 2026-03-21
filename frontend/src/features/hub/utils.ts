export const PROJECT_ICON_PALETTES = [
  { bg: "#E1F5EE", color: "#085041" },
  { bg: "#E6F1FB", color: "#0C447C" },
  { bg: "#FAEEDA", color: "#633806" },
  { bg: "#EEEDFE", color: "#3C3489" },
  { bg: "#FAECE7", color: "#712B13" },
  { bg: "#EAF3DE", color: "#27500A" },
] as const;

export function getProjectPalette(projectId: string) {
  const hash = projectId.split("").reduce((acc, c) => (acc * 31 + c.charCodeAt(0)) & 0xffff, 0);
  return PROJECT_ICON_PALETTES[Math.abs(hash) % PROJECT_ICON_PALETTES.length];
}

const TAG_DOT_COLORS = ["#1D9E75", "#378ADD", "#BA7517", "#888780", "#D85A30", "#639922", "#D4537E", "#7F77DD"] as const;

export function getTagColor(tag: string) {
  const hash = tag.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
  return TAG_DOT_COLORS[Math.abs(hash) % TAG_DOT_COLORS.length];
}

export const CACHE_LABELS: Record<string, string> = {
  ready: "cache ready",
  stale: "cache stale",
  building: "building…",
  error: "cache error",
  missing: "no cache",
};

export function formatRelativeDate(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffH = Math.floor(diffMs / 3600000);
  const diffD = Math.floor(diffMs / 86400000);

  if (diffMin < 5) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffH < 24) return `today, ${date.toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" })}`;
  if (diffD === 1) return `yesterday, ${date.toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" })}`;
  if (diffD < 7) return `${diffD} days ago`;
  return date.toLocaleDateString("ru", { day: "numeric", month: "short", year: "numeric" });
}

export function sanitizeTag(raw: string): string {
  return raw.trim().toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9_-]/g, "").slice(0, 20);
}
