import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/cn";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./Dialog";

interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}

function Sheet({ open, onOpenChange, children }: SheetProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {children}
    </Dialog>
  );
}

interface SheetContentProps extends HTMLAttributes<HTMLDivElement> {
  side?: "right" | "bottom";
}

function SheetContent({ className, side = "right", ...props }: SheetContentProps) {
  return <DialogContent className={cn("shad-sheet-content", side === "bottom" ? "shad-sheet-bottom" : "shad-sheet-right", className)} {...props} />;
}

const SheetHeader = DialogHeader;
const SheetTitle = DialogTitle;
const SheetBody = DialogBody;
const SheetFooter = DialogFooter;

export { Sheet, SheetContent, SheetHeader, SheetTitle, SheetBody, SheetFooter };
