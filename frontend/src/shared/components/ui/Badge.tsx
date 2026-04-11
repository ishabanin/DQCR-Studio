import { type HTMLAttributes, type PropsWithChildren } from "react";

import { cn } from "../../lib/cn";

type BadgeVariant = "default" | "secondary";

interface BadgeProps extends PropsWithChildren, HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export default function Badge({ children, className, variant = "default", ...props }: BadgeProps) {
  return <span className={cn("ui-badge", variant === "secondary" ? "ui-badge-secondary" : "", className)} {...props}>{children}</span>;
}
