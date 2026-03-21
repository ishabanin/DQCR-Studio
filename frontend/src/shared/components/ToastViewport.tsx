import { useEffect } from "react";

import { useUiStore } from "../../app/store/uiStore";

export default function ToastViewport() {
  const toasts = useUiStore((state) => state.toasts);
  const removeToast = useUiStore((state) => state.removeToast);

  useEffect(() => {
    if (toasts.length === 0) return;

    const timers = toasts
      .filter((toast) => toast.autoCloseMs !== null)
      .map((toast) =>
        window.setTimeout(() => {
          removeToast(toast.id);
        }, toast.autoCloseMs ?? 2500),
      );

    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [toasts, removeToast]);

  return (
    <div className="toast-viewport">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.type}`}>
          <div className="toast-title">{toast.title}</div>
          {toast.description ? <div className="toast-description">{toast.description}</div> : null}
          {toast.action ? (
            <button
              type="button"
              className="toast-action-btn"
              onClick={() => {
                toast.action?.onClick();
                removeToast(toast.id);
              }}
            >
              {toast.action.label}
            </button>
          ) : null}
        </div>
      ))}
    </div>
  );
}
