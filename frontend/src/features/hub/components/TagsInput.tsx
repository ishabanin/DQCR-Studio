import { useMemo, useRef, useState, type KeyboardEvent } from "react";

import { sanitizeTag } from "../utils";

interface TagsInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  suggestions: string[];
}

function TagPill({ tag, onRemove }: { tag: string; onRemove: () => void }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 3,
        padding: "2px 7px",
        borderRadius: "var(--hub-radius-pill)",
        background: "var(--hub-accent-50)",
        color: "var(--hub-accent-700)",
        fontSize: "var(--hub-text-xs)",
        lineHeight: 1.4,
      }}
    >
      {tag}
      <span
        onClick={(event) => {
          event.stopPropagation();
          onRemove();
        }}
        style={{ cursor: "pointer", opacity: 0.6, fontSize: 10, lineHeight: 1 }}
        onMouseEnter={(event) => {
          event.currentTarget.style.opacity = "1";
        }}
        onMouseLeave={(event) => {
          event.currentTarget.style.opacity = "0.6";
        }}
      >
        ✕
      </span>
    </span>
  );
}

export function TagsInput({ tags, onChange, suggestions }: TagsInputProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const addTag = (raw: string) => {
    const clean = sanitizeTag(raw);
    if (!clean || tags.includes(clean) || tags.length >= 10) return;
    onChange([...tags, clean]);
  };

  const removeTag = (tag: string) => {
    onChange(tags.filter((item) => item !== tag));
  };

  const visibleSuggestions = useMemo(
    () =>
      suggestions
        .filter((s) => !tags.includes(s) && (inputValue === "" || s.includes(inputValue.toLowerCase())))
        .slice(0, 8),
    [suggestions, tags, inputValue],
  );

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    const value = event.currentTarget.value;

    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      const clean = sanitizeTag(value.replace(",", ""));
      if (clean && clean.length >= 1 && clean.length <= 20 && !tags.includes(clean) && tags.length < 10) {
        addTag(clean);
      }
      setInputValue("");
    }

    if (event.key === "Backspace" && value === "" && tags.length > 0) {
      removeTag(tags[tags.length - 1]);
    }

    if (event.key === "Escape") {
      setInputValue("");
    }
  }

  return (
    <div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 5,
          padding: "6px 8px",
          borderRadius: "var(--hub-radius-sm)",
          border: isFocused ? "0.5px solid var(--hub-accent-400)" : "var(--hub-border-medium)",
          background: "var(--hub-surface-input)",
          minHeight: 38,
          alignItems: "center",
          cursor: "text",
          boxShadow: isFocused ? "var(--hub-focus-ring)" : "none",
          transition: "border-color var(--hub-transition-fast), box-shadow var(--hub-transition-fast)",
        }}
        onClick={() => inputRef.current?.focus()}
      >
        {tags.map((tag) => (
          <TagPill key={tag} tag={tag} onRemove={() => removeTag(tag)} />
        ))}
        <input
          ref={inputRef}
          style={{
            border: "none",
            background: "transparent",
            outline: "none",
            fontSize: "var(--hub-text-sm)",
            color: "var(--color-text-primary)",
            fontFamily: "var(--hub-font-ui)",
            minWidth: 80,
            flex: 1,
          }}
          placeholder={tags.length === 0 ? "Add tags…" : ""}
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
        />
      </div>

      {visibleSuggestions.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
          {visibleSuggestions.map((s) => (
            <span
              key={s}
              onClick={() => addTag(s)}
              style={{
                fontSize: "var(--hub-text-2xs)",
                padding: "2px 8px",
                borderRadius: "var(--hub-radius-pill)",
                background: "var(--hub-surface-panel)",
                color: "var(--color-text-secondary)",
                border: "var(--hub-border-subtle)",
                cursor: "pointer",
                transition: "all var(--hub-transition-fast)",
              }}
              onMouseEnter={(event) => {
                event.currentTarget.style.background = "var(--hub-accent-50)";
                event.currentTarget.style.color = "var(--hub-accent-700)";
                event.currentTarget.style.borderColor = "var(--hub-accent-200)";
              }}
              onMouseLeave={(event) => {
                event.currentTarget.style.background = "";
                event.currentTarget.style.color = "";
                event.currentTarget.style.borderColor = "";
              }}
            >
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
