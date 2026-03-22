import { useEffect } from "react";
import Editor from "@monaco-editor/react";

interface ExpandedFieldEditorModalProps {
  isOpen: boolean;
  title: string;
  language: string;
  value: string;
  theme: string;
  confirmLabel?: string;
  onChange: (value: string) => void;
  onClose: () => void;
  onApply: () => void;
}

export default function ExpandedFieldEditorModal({
  isOpen,
  title,
  language,
  value,
  theme,
  confirmLabel = "Применить",
  onChange,
  onClose,
  onApply,
}: ExpandedFieldEditorModalProps) {
  useEffect(() => {
    if (!isOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      const isApply = (event.ctrlKey || event.metaKey) && event.key === "Enter";
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (isApply) {
        event.preventDefault();
        onApply();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onApply, onClose]);

  if (!isOpen) return null;

  return (
    <div className="expanded-editor-modal-overlay" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className="expanded-editor-modal" onClick={(event) => event.stopPropagation()}>
        <div className="expanded-editor-modal-head">
          <div>
            <p className="expanded-editor-modal-eyebrow">Расширенный редактор</p>
            <h3>{title}</h3>
          </div>
          <button type="button" className="action-btn" onClick={onClose} aria-label="Закрыть расширенный редактор">
            ✕
          </button>
        </div>
        <div className="expanded-editor-modal-body">
          <Editor
            height="100%"
            language={language}
            theme={theme}
            value={value}
            options={{
              minimap: { enabled: false },
              fontSize: 12.5,
              lineHeight: 20,
              fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", "Courier New", monospace',
              automaticLayout: true,
              wordWrap: "on",
              scrollBeyondLastLine: false,
            }}
            onMount={(editor) => {
              window.setTimeout(() => editor.focus(), 0);
            }}
            onChange={(nextValue) => onChange(nextValue ?? "")}
          />
        </div>
        <div className="expanded-editor-modal-actions">
          <span className="expanded-editor-modal-hint">Esc — закрыть, Ctrl/Cmd+Enter — применить</span>
          <div className="expanded-editor-modal-actions-group">
            <button type="button" className="action-btn" onClick={onClose}>
              Отмена
            </button>
            <button type="button" className="action-btn action-btn-primary" onClick={onApply}>
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
