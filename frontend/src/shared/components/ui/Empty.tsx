import type { HTMLAttributes, PropsWithChildren } from "react";

import { cn } from "../../lib/cn";

interface EmptyProps extends HTMLAttributes<HTMLDivElement>, PropsWithChildren {
  icon?: string;
  title: string;
  description?: string;
}

export default function Empty({ icon, title, description, className, children, ...props }: EmptyProps) {
  return (
    <div className={cn("shad-empty", className)} {...props}>
      {icon ? <div className="shad-empty-icon">{icon}</div> : null}
      <h3 className="shad-empty-title">{title}</h3>
      {description ? <p className="shad-empty-description">{description}</p> : null}
      {children ? <div className="shad-empty-actions">{children}</div> : null}
    </div>
  );
}
