import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getCatalogStatus, getEntity, searchEntities, type CatalogEntity } from "../../api/catalog";
import type { ModelAttributeItem } from "../../api/projects";
import Tooltip from "../../shared/components/ui/Tooltip";

export type ImportStrategy = "replace" | "merge";

interface EntityPickerDialogProps {
  open: boolean;
  existingAttributes: ModelAttributeItem[];
  onClose: () => void;
  onImport: (entity: CatalogEntity, strategy: ImportStrategy) => void;
}

function attributesEqual(left: ModelAttributeItem | undefined, right: ModelAttributeItem | undefined): boolean {
  if (!left || !right) return false;
  return (
    (left.domain_type ?? "") === (right.domain_type ?? "") &&
    Boolean(left.is_key) === Boolean(right.is_key) &&
    Boolean(left.required) === Boolean(right.required)
  );
}

export default function EntityPickerDialog({ open, existingAttributes, onClose, onImport }: EntityPickerDialogProps) {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [importStrategy, setImportStrategy] = useState<ImportStrategy>("replace");
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search, open]);

  useEffect(() => {
    if (!open) {
      setSearch("");
      setDebouncedSearch("");
      setSelectedName(null);
      setShowAll(false);
      setImportStrategy("replace");
      setConfirmed(false);
    }
  }, [open]);

  const hasExistingAttributes = existingAttributes.length > 0;

  const statusQuery = useQuery({
    queryKey: ["catalogStatus"],
    queryFn: getCatalogStatus,
    enabled: open,
  });

  const entitiesQuery = useQuery({
    queryKey: ["catalogEntitiesDialog", debouncedSearch],
    queryFn: () => searchEntities(debouncedSearch, 20),
    enabled: open && statusQuery.data?.available === true,
  });

  const rows = useMemo(() => entitiesQuery.data?.entities ?? [], [entitiesQuery.data]);

  useEffect(() => {
    if (!open) return;
    if (rows.length === 0) {
      setSelectedName(null);
      return;
    }
    if (!selectedName || !rows.some((item) => item.name === selectedName)) {
      setSelectedName(rows[0].name);
    }
  }, [open, rows, selectedName]);

  const entityQuery = useQuery({
    queryKey: ["catalogEntityDialog", selectedName],
    queryFn: () => getEntity(selectedName as string),
    enabled: open && Boolean(selectedName),
  });

  const diffSummary = useMemo(() => {
    const entity = entityQuery.data;
    if (!entity) return null;

    const incomingAttributes: ModelAttributeItem[] = entity.attributes.map((attribute) => ({
      name: attribute.name,
      domain_type: attribute.domain_type,
      is_key: attribute.is_key,
      required: attribute.is_nullable === false,
    }));

    const incomingByName = new Map(incomingAttributes.map((item) => [item.name, item]));
    const existingByName = new Map(existingAttributes.map((item) => [item.name, item]));

    let added = 0;
    let updated = 0;
    let unchanged = 0;

    for (const incoming of incomingAttributes) {
      const previous = existingByName.get(incoming.name);
      if (!previous) {
        added += 1;
      } else if (attributesEqual(previous, incoming)) {
        unchanged += 1;
      } else {
        updated += 1;
      }
    }

    let removed = 0;
    for (const existing of existingAttributes) {
      if (!incomingByName.has(existing.name)) {
        removed += 1;
      }
    }

    return {
      incomingCount: incomingAttributes.length,
      added,
      updated,
      removed,
      unchanged,
    };
  }, [entityQuery.data, existingAttributes]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (rows.length === 0) return;
      const currentIndex = rows.findIndex((item) => item.name === selectedName);

      if (event.key === "ArrowDown") {
        event.preventDefault();
        const nextIndex = currentIndex < 0 ? 0 : Math.min(rows.length - 1, currentIndex + 1);
        setSelectedName(rows[nextIndex].name);
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        const nextIndex = currentIndex <= 0 ? 0 : currentIndex - 1;
        setSelectedName(rows[nextIndex].name);
      }
      if (event.key === "Enter") {
        event.preventDefault();
        if (entityQuery.data && (!hasExistingAttributes || confirmed)) {
          onImport(entityQuery.data, importStrategy);
          return;
        }
        if (currentIndex >= 0) {
          setSelectedName(rows[currentIndex].name);
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose, rows, selectedName, entityQuery.data, hasExistingAttributes, confirmed, onImport, importStrategy]);

  if (!open) return null;

  return (
    <div className="entity-picker-overlay" onClick={onClose}>
      <div className="entity-picker-dialog" onClick={(event) => event.stopPropagation()}>
        <div className="entity-picker-head">
          <h3>Import attributes from catalog</h3>
          <button type="button" className="action-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        {!statusQuery.data?.available ? (
          <div className="catalog-muted">Catalog is not loaded. Upload it in Admin or Hub first.</div>
        ) : (
          <>
            <input className="ui-input" placeholder="Search entities..." value={search} onChange={(event) => setSearch(event.target.value)} />

            <div className="entity-picker-list">
              {rows.map((entity) => (
                <button
                  key={entity.name}
                  type="button"
                  className={selectedName === entity.name ? "entity-picker-row entity-picker-row-active" : "entity-picker-row"}
                  onClick={() => {
                    setSelectedName(entity.name);
                    setShowAll(false);
                    setConfirmed(false);
                  }}
                >
                  <span>{entity.name}</span>
                  <span>{entity.display_name}</span>
                  <span>{entity.attribute_count} attrs</span>
                </button>
              ))}
            </div>

            {entityQuery.data ? (
              <div className="entity-picker-preview">
                <div className="entity-picker-preview-title">Preview: {entityQuery.data.name}</div>
                <table className="catalog-preview-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>System name</th>
                      <th>Display name</th>
                      <th>Description</th>
                      <th>Type</th>
                      <th>Badges</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(showAll ? entityQuery.data.attributes : entityQuery.data.attributes.slice(0, 10)).map((attr) => (
                      <tr key={`${attr.name}-${attr.position}`}>
                        <td>{attr.position}</td>
                        <td>{attr.name}</td>
                        <td>{attr.display_name}</td>
                        <td>{attr.description ? <Tooltip text={attr.description}>{attr.description}</Tooltip> : ""}</td>
                        <td>{attr.domain_type}</td>
                        <td>
                          {attr.is_key ? "🔑" : ""} {attr.is_nullable ? "∅" : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {entityQuery.data.attributes.length > 10 ? (
                  <button type="button" className="action-btn" onClick={() => setShowAll((prev) => !prev)}>
                    {showAll ? "Show less" : `Show all ${entityQuery.data.attributes.length}`}
                  </button>
                ) : null}
              </div>
            ) : null}

            {hasExistingAttributes && diffSummary ? (
              <div className="catalog-warning">
                <div className="entity-picker-diff-head">Import impact</div>
                <div className="entity-picker-diff-grid">
                  <span className="entity-picker-diff-pill">+{diffSummary.added} added</span>
                  <span className="entity-picker-diff-pill">~{diffSummary.updated} changed</span>
                  <span className="entity-picker-diff-pill">-{diffSummary.removed} missing in catalog</span>
                  <span className="entity-picker-diff-pill">={diffSummary.unchanged} unchanged</span>
                </div>

                <div className="entity-picker-strategy">
                  <label className="entity-picker-radio">
                    <input
                      type="radio"
                      name="import-strategy"
                      checked={importStrategy === "replace"}
                      onChange={() => {
                        setImportStrategy("replace");
                        setConfirmed(false);
                      }}
                    />
                    Replace model attributes with catalog attributes ({diffSummary.incomingCount})
                  </label>
                  <label className="entity-picker-radio">
                    <input
                      type="radio"
                      name="import-strategy"
                      checked={importStrategy === "merge"}
                      onChange={() => {
                        setImportStrategy("merge");
                        setConfirmed(false);
                      }}
                    />
                    Merge catalog attributes into model attributes
                  </label>
                </div>

                <label className="entity-picker-confirm">
                  <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
                  I understand that existing model attributes will be modified.
                </label>
              </div>
            ) : null}

            <div className="entity-picker-actions">
              <button type="button" className="action-btn" onClick={onClose}>
                Cancel
              </button>
              <button
                type="button"
                className="action-btn action-btn-primary"
                disabled={!entityQuery.data || (hasExistingAttributes && !confirmed)}
                onClick={() => {
                  if (!entityQuery.data) return;
                  if (hasExistingAttributes && !confirmed) return;
                  onImport(entityQuery.data, importStrategy);
                }}
              >
                Import attributes
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
