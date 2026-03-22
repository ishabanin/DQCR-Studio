import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getCatalogStatus,
  getEntity,
  searchEntities,
  uploadCatalog,
  type CatalogMeta,
  type EntitySummary,
} from "../../api/catalog";
import { useUiStore } from "../../app/store/uiStore";

interface CatalogPanelBaseProps {
  mode: "hub" | "admin";
  expandSignal?: number;
}

function formatCatalogMeta(meta: CatalogMeta): string {
  const loadedAt = meta.loaded_at ? new Date(meta.loaded_at).toLocaleString() : "n/a";
  const version = meta.version_label?.trim() ? `${meta.version_label} · ` : "";
  return `${version}${meta.entity_count} entities · ${meta.attribute_count} attributes · Loaded ${loadedAt}`;
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object") return fallback;
  const withResponse = error as { response?: { status?: number; data?: { detail?: unknown } }; message?: string };
  if (withResponse.response?.status === 413) {
    return "Catalog file is too large. Max supported size is 50 MB.";
  }
  const detail = withResponse.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (typeof withResponse.message === "string" && withResponse.message.trim()) return withResponse.message;
  return fallback;
}

export default function CatalogPanelBase({ mode, expandSignal }: CatalogPanelBaseProps) {
  const queryClient = useQueryClient();
  const addToast = useUiStore((state) => state.addToast);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [expanded, setExpanded] = useState(mode === "admin");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [versionLabel, setVersionLabel] = useState("");
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [limit, setLimit] = useState(20);
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [showAllAttributes, setShowAllAttributes] = useState(false);

  const isHub = mode === "hub";
  const showPreview = mode === "admin";

  useEffect(() => {
    if (!isHub) return;
    if (!expandSignal) return;
    setExpanded(true);
  }, [expandSignal, isHub]);

  const statusQuery = useQuery({
    queryKey: ["catalogStatus"],
    queryFn: getCatalogStatus,
  });

  const uploadMutation = useMutation({
    mutationFn: (payload: { file: File; versionLabel: string }) => uploadCatalog(payload.file, payload.versionLabel),
    onSuccess: (result) => {
      setUploadError(null);
      setVersionLabel("");
      setSelectedFile(null);
      setShowUploadForm(false);
      void queryClient.invalidateQueries({ queryKey: ["catalogStatus"] });
      void queryClient.invalidateQueries({ queryKey: ["catalogEntitiesPreview"] });
      void queryClient.invalidateQueries({ queryKey: ["catalogEntityPreview"] });
      void queryClient.invalidateQueries({ queryKey: ["autocomplete"] });
      addToast(`Catalog loaded: ${result.meta?.entity_count ?? 0} entities`, "success");
    },
    onError: (error) => {
      setUploadError(extractErrorMessage(error, "Failed to upload catalog"));
    },
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setLimit(20);
  }, [debouncedSearch]);

  const entitiesQuery = useQuery({
    queryKey: ["catalogEntitiesPreview", debouncedSearch, limit],
    queryFn: () => searchEntities(debouncedSearch, limit),
    enabled: showPreview && expanded && statusQuery.data?.available === true,
  });

  const entityRows = useMemo(() => entitiesQuery.data?.entities ?? [], [entitiesQuery.data]);

  useEffect(() => {
    if (!showPreview) return;
    if (entityRows.length === 0) {
      setSelectedEntity(null);
      return;
    }
    if (!selectedEntity || !entityRows.some((item) => item.name === selectedEntity)) {
      setSelectedEntity(entityRows[0].name);
    }
  }, [entityRows, selectedEntity, showPreview]);

  const entityQuery = useQuery({
    queryKey: ["catalogEntityPreview", selectedEntity],
    queryFn: () => getEntity(selectedEntity as string),
    enabled: Boolean(showPreview && selectedEntity),
  });

  const handleChooseFile = () => {
    fileInputRef.current?.click();
  };

  const handleUploadStart = () => {
    if (!selectedFile) return;
    setUploadError(null);
    uploadMutation.mutate({ file: selectedFile, versionLabel: versionLabel.trim() });
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    if (!file) return;
    setSelectedFile(file);
    setShowUploadForm(true);
    setUploadError(null);
    event.target.value = "";
  };

  const status = statusQuery.data;
  const meta = status?.meta ?? null;

  return (
    <section id={isHub ? "hub-catalog-panel" : undefined} className="catalog-panel">
      <div className="catalog-panel-head">
        <h2>Data Catalog</h2>
        {isHub ? (
          <button type="button" className="action-btn" onClick={() => setExpanded((prev) => !prev)}>
            {expanded ? "▾" : "▸"}
          </button>
        ) : null}
      </div>

      {!expanded ? null : (
        <>
          {statusQuery.isLoading ? <p className="catalog-muted">Loading catalog status...</p> : null}

          {status?.available && meta ? (
            <div className="catalog-status-ok">
              <div className="catalog-status-title">✓ {meta.source_filename}</div>
              <div className="catalog-muted">{formatCatalogMeta(meta)}</div>
            </div>
          ) : null}

          {!status?.available ? (
            <div className="catalog-status-empty">
              <p className="catalog-muted">
                No catalog loaded. Upload a CBR DWH .xlsx file to enable entity suggestions in Model Editor and SQL autocomplete.
              </p>
            </div>
          ) : null}

          <input ref={fileInputRef} type="file" accept=".xlsx" style={{ display: "none" }} onChange={handleFileChange} />

          {!showUploadForm ? (
            <button type="button" className="action-btn" onClick={handleChooseFile}>
              {status?.available ? "Replace catalog" : "Upload .xlsx"}
            </button>
          ) : (
            <div className="catalog-upload-form">
              <div className="catalog-upload-file">{selectedFile?.name ?? "No file selected"}</div>
              <label>
                Version label (optional)
                <input
                  className="ui-input"
                  placeholder="e.g. DWH 7.1"
                  value={versionLabel}
                  onChange={(event) => setVersionLabel(event.target.value)}
                />
              </label>
              {uploadError ? <div className="catalog-error">{uploadError}</div> : null}
              <div className="catalog-upload-actions">
                <button type="button" className="action-btn" onClick={() => setShowUploadForm(false)} disabled={uploadMutation.isPending}>
                  Cancel
                </button>
                <button type="button" className="action-btn action-btn-primary" onClick={handleUploadStart} disabled={!selectedFile || uploadMutation.isPending}>
                  {uploadMutation.isPending ? "Parsing catalog..." : "Upload"}
                </button>
              </div>
            </div>
          )}

          {showPreview && status?.available ? (
            <div className="catalog-preview">
              <h3>Preview</h3>
              <input className="ui-input" placeholder="Search entities..." value={search} onChange={(event) => setSearch(event.target.value)} />

              <div className="catalog-preview-table-wrap">
                <table className="catalog-preview-table">
                  <thead>
                    <tr>
                      <th>Entity (sys)</th>
                      <th>Display name</th>
                      <th>Module</th>
                      <th>Attrs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entityRows.map((item: EntitySummary) => (
                      <tr
                        key={item.name}
                        className={selectedEntity === item.name ? "catalog-row-active" : ""}
                        onClick={() => {
                          setSelectedEntity(item.name);
                          setShowAllAttributes(false);
                        }}
                      >
                        <td>{item.name}</td>
                        <td>{item.display_name}</td>
                        <td>{item.module}</td>
                        <td>{item.attribute_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {entityRows.length < (entitiesQuery.data?.total ?? 0) ? (
                <button type="button" className="action-btn" onClick={() => setLimit((prev) => prev + 20)}>
                  Load more
                </button>
              ) : null}

              {entityQuery.data ? (
                <div className="catalog-entity-preview">
                  <div className="catalog-entity-title">{entityQuery.data.name}</div>
                  <table className="catalog-preview-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Display</th>
                        <th>Type</th>
                        <th>🔑</th>
                        <th>∅</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(showAllAttributes ? entityQuery.data.attributes : entityQuery.data.attributes.slice(0, 20)).map((attr) => (
                        <tr key={`${attr.name}-${attr.position}`}>
                          <td>{attr.name}</td>
                          <td>{attr.display_name}</td>
                          <td>{attr.domain_type}</td>
                          <td>{attr.is_key ? "yes" : ""}</td>
                          <td>{attr.is_nullable ? "yes" : ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {entityQuery.data.attributes.length > 20 ? (
                    <button type="button" className="action-btn" onClick={() => setShowAllAttributes((prev) => !prev)}>
                      {showAllAttributes ? "Show less" : `Show all ${entityQuery.data.attributes.length}`}
                    </button>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
