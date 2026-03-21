interface QuickFixPreviewData {
  filePath: string;
  description: string;
  diff: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
  preview: QuickFixPreviewData | null;
}

export default function QuickFixPreviewModal({ isOpen, onClose, onConfirm, isLoading, preview }: Props) {
  if (!isOpen) return null;

  return (
    <div className="quickfix-modal-overlay" role="dialog" aria-modal="true">
      <div className="quickfix-modal">
        <div className="quickfix-modal-head">
          <h3>Применить Quick Fix?</h3>
          <button type="button" className="action-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="quickfix-modal-meta">
          <p>
            <strong>Файл:</strong> {preview?.filePath ?? "—"}
          </p>
          <p>
            <strong>Действие:</strong> {preview?.description ?? "—"}
          </p>
        </div>

        <div className="quickfix-modal-diff-wrap">
          <div className="quickfix-modal-diff">
            {(preview?.diff ?? "Нет diff для отображения")
              .split("\n")
              .filter(Boolean)
              .map((line, index) => (
                <div
                  key={`${line}-${index}`}
                  className={line.startsWith("+") ? "quickfix-diff-line quickfix-diff-line-add" : "quickfix-diff-line"}
                >
                  {line}
                </div>
              ))}
          </div>
        </div>

        <div className="quickfix-modal-actions">
          <button type="button" className="action-btn" onClick={onClose} disabled={isLoading}>
            Отмена
          </button>
          <button type="button" className="action-btn action-btn-primary" onClick={onConfirm} disabled={isLoading || !preview}>
            {isLoading ? "Применяем..." : "Применить и re-run"}
          </button>
        </div>
      </div>
    </div>
  );
}
