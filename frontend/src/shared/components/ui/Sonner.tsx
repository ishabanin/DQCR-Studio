import { useEffect } from "react";

import { useUiStore } from "../../../app/store/uiStore";
import Button from "./Button";

export default function Sonner() {
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
    <div className="sonner-viewport">
      {toasts.map((toast) => (
        <div key={toast.id} className={`sonner-toast sonner-${toast.type}`}>
          <div className="sonner-content">
            <div className="sonner-title">{toast.title}</div>
            {toast.description ? <div className="sonner-description">{toast.description}</div> : null}
          </div>
          {toast.action ? (
            <Button
              variant="ghost"
              className="sonner-action-btn"
              onClick={() => {
                toast.action?.onClick();
                removeToast(toast.id);
              }}
            >
              {toast.action.label}
            </Button>
          ) : (
            <button type="button" className="sonner-close-btn" onClick={() => removeToast(toast.id)}>
              ✕
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
