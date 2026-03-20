import { PropsWithChildren } from "react";

export default function Badge({ children }: PropsWithChildren) {
  return <span className="ui-badge">{children}</span>;
}

