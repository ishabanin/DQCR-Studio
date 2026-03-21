import { useEffect, useMemo, useRef, useState } from "react";

import type { PropertyEntry } from "../types";

function createEntry(): PropertyEntry {
  return {
    id: `prop-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    key: "",
    value: "",
  };
}

function normalizeKey(value: string): string {
  return value.trim();
}

export function PropertiesEditor({
  entries,
  onChange,
}: {
  entries: PropertyEntry[];
  onChange: (entries: PropertyEntry[]) => void;
}) {
  const keyRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [touchedKeys, setTouchedKeys] = useState<Record<string, boolean>>({});

  const duplicates = useMemo(() => {
    const freq = new Map<string, number>();
    for (const entry of entries) {
      const key = normalizeKey(entry.key);
      if (!key) continue;
      freq.set(key, (freq.get(key) ?? 0) + 1);
    }

    return new Set(
      entries
        .filter((entry) => {
          const key = normalizeKey(entry.key);
          return Boolean(key) && (freq.get(key) ?? 0) > 1;
        })
        .map((entry) => entry.id),
    );
  }, [entries]);

  useEffect(() => {
    if (!focusedId) return;
    keyRefs.current[focusedId]?.focus();
    setFocusedId(null);
  }, [focusedId, entries]);

  const updateEntry = (id: string, patch: Partial<PropertyEntry>) => {
    onChange(entries.map((entry) => (entry.id === id ? { ...entry, ...patch } : entry)));
  };

  const addEntry = () => {
    const next = createEntry();
    onChange([...entries, next]);
    setFocusedId(next.id);
  };

  const deleteEntry = (id: string) => {
    onChange(entries.filter((entry) => entry.id !== id));
  };

  return (
    <div className="pi-card">
      <div className="pi-card-header">
        <span className="pi-card-title">Custom properties</span>
        <button className="pi-card-action" onClick={addEntry}>
          ＋ Add
        </button>
      </div>

      {entries.map((entry) => {
        const isEmptyTouched = touchedKeys[entry.id] && normalizeKey(entry.key) === "";
        const isInvalid = isEmptyTouched || duplicates.has(entry.id);

        return (
          <div key={entry.id} className="pi-prop-row">
            <input
              ref={(element) => {
                keyRefs.current[entry.id] = element;
              }}
              className="pi-prop-key-input"
              value={entry.key}
              placeholder="key"
              onChange={(event) => updateEntry(entry.id, { key: event.target.value })}
              onBlur={(event) => {
                const normalized = event.target.value.replace(/\s+/g, "_");
                updateEntry(entry.id, { key: normalized });
                setTouchedKeys((prev) => ({ ...prev, [entry.id]: true }));
              }}
              style={isInvalid ? { borderColor: "var(--pi-danger-text)" } : undefined}
            />
            <input
              className="pi-prop-val-input"
              value={entry.value}
              placeholder="value"
              onChange={(event) => updateEntry(entry.id, { value: event.target.value })}
            />
            <button className="pi-prop-del" onClick={() => deleteEntry(entry.id)} title="Remove">
              ✕
            </button>
          </div>
        );
      })}

      <button className="pi-add-row" onClick={addEntry}>
        ＋ Add property
      </button>
    </div>
  );
}
