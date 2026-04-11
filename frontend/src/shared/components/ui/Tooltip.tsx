import { type PropsWithChildren } from "react";

import { cn } from "../../lib/cn";

interface TooltipProps {
  text: string;
  className?: string;
}

export default function Tooltip({ children, text, className }: PropsWithChildren<TooltipProps>) {
  return (
    <span className={cn("ui-tooltip-wrap", className)} title={text}>
      {children}
    </span>
  );
}
