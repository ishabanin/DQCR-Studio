import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/cn";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./Dialog";

interface AlertDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}

function AlertDialog({ open, onOpenChange, children }: AlertDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {children}
    </Dialog>
  );
}

function AlertDialogContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <DialogContent className={cn("shad-alert-content", className)} {...props} />;
}

const AlertDialogHeader = DialogHeader;
const AlertDialogTitle = DialogTitle;
const AlertDialogBody = DialogBody;
const AlertDialogFooter = DialogFooter;

export { AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogBody, AlertDialogFooter };
