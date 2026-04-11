import {
  createContext,
  useContext,
  useEffect,
  type HTMLAttributes,
  type PropsWithChildren,
} from "react";

import { cn } from "../../lib/cn";

interface DialogContextValue {
  onOpenChange: (open: boolean) => void;
}

const DialogContext = createContext<DialogContextValue | null>(null);

function useDialogContext() {
  const value = useContext(DialogContext);
  if (!value) {
    throw new Error("Dialog components must be used inside <Dialog>");
  }
  return value;
}

interface DialogProps extends PropsWithChildren {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function Dialog({ open, onOpenChange, children }: DialogProps) {
  useEffect(() => {
    if (!open) return;
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onOpenChange(false);
    };
    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [open, onOpenChange]);

  if (!open) return null;

  return <DialogContext.Provider value={{ onOpenChange }}>{children}</DialogContext.Provider>;
}

function DialogOverlay({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  const { onOpenChange } = useDialogContext();
  return <div className={cn("shad-dialog-overlay", className)} onClick={() => onOpenChange(false)} {...props} />;
}

function DialogContent({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <>
      <DialogOverlay />
      <div className={cn("shad-dialog-content", className)} onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true" {...props}>
        {children}
      </div>
    </>
  );
}

function DialogHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("shad-dialog-header", className)} {...props} />;
}

function DialogTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("shad-dialog-title", className)} {...props} />;
}

function DialogDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("shad-dialog-description", className)} {...props} />;
}

function DialogBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("shad-dialog-body", className)} {...props} />;
}

function DialogFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("shad-dialog-footer", className)} {...props} />;
}

export { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogBody, DialogFooter };
