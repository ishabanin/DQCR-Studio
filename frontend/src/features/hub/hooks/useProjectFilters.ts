import { useMemo, useState } from "react";

import type { FilterState, ProjectListItem, SortDir, SortKey } from "../types";

export function useProjectFilters(projects: ProjectListItem[]) {
  const [filters, setFilters] = useState<FilterState>({
    search: "",
    visibility: null,
    type: null,
    tag: null,
  });
  const [sortBy, setSortBy] = useState<SortKey>("modified_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const filtered = useMemo(() => {
    let result = projects;

    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter(
        (p) => p.name.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q) || p.tags.some((t) => t.toLowerCase().includes(q)),
      );
    }
    if (filters.visibility) result = result.filter((p) => p.visibility === filters.visibility);
    if (filters.type) result = result.filter((p) => p.project_type === filters.type);
    if (filters.tag) result = result.filter((p) => p.tags.includes(filters.tag as string));

    const sorted = [...result].sort((a, b) => {
      let va: string | number = a[sortBy] ?? "";
      let vb: string | number = b[sortBy] ?? "";
      if (typeof va === "string") va = va.toLowerCase();
      if (typeof vb === "string") vb = vb.toLowerCase();
      if (va === vb) return 0;
      return sortDir === "asc" ? (va < vb ? -1 : 1) : va > vb ? -1 : 1;
    });

    return sorted;
  }, [projects, filters, sortBy, sortDir]);

  const counts = useMemo(
    () => ({
      all: projects.length,
      public: projects.filter((p) => p.visibility === "public").length,
      private: projects.filter((p) => p.visibility === "private").length,
      internal: projects.filter((p) => p.project_type === "internal").length,
      imported: projects.filter((p) => p.project_type === "imported").length,
      linked: projects.filter((p) => p.project_type === "linked").length,
      byTag: Object.fromEntries(
        [...new Set(projects.flatMap((p) => p.tags))].map((tag) => [tag, projects.filter((p) => p.tags.includes(tag)).length]),
      ) as Record<string, number>,
    }),
    [projects],
  );

  const allTags = useMemo(() => [...new Set(projects.flatMap((p) => p.tags))].sort(), [projects]);

  const patchFilter = (patch: Partial<FilterState>) => setFilters((f) => ({ ...f, ...patch }));
  const clearFilters = () => setFilters({ search: "", visibility: null, type: null, tag: null });

  const toggleSort = (key: SortKey) => {
    if (sortBy === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortBy(key);
      setSortDir("asc");
    }
  };

  return {
    filtered,
    filters,
    patchFilter,
    clearFilters,
    counts,
    allTags,
    sortBy,
    sortDir,
    toggleSort,
  };
}
