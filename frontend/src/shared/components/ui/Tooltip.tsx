import { PropsWithChildren } from "react";

export default function Tooltip({ children, text }: PropsWithChildren<{ text: string }>) {
  return (
    <span className="ui-tooltip-wrap" title={text}>
      {children}
    </span>
  );
}

