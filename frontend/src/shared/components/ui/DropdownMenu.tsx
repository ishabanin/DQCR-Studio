import {
  cloneElement,
  createContext,
  isValidElement,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type HTMLAttributes,
  type MouseEvent as ReactMouseEvent,
  type ReactElement,
  type PropsWithChildren,
} from "react";

import { cn } from "../../lib/cn";

interface DropdownMenuState {
  open: boolean;
  setOpen: (value: boolean) => void;
}

const DropdownMenuContext = createContext<DropdownMenuState | null>(null);

function useDropdownMenuContext() {
  const value = useContext(DropdownMenuContext);
  if (!value) {
    throw new Error("DropdownMenu components must be used inside <DropdownMenu>");
  }
  return value;
}

function DropdownMenu({ children }: PropsWithChildren) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: globalThis.MouseEvent) => {
      const node = rootRef.current;
      if (!node) return;
      const target = event.target as Node | null;
      if (target && !node.contains(target)) {
        setOpen(false);
      }
    };

    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onEscape);
    return () => {
      window.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onEscape);
    };
  }, [open]);

  const value = useMemo(() => ({ open, setOpen }), [open]);

  return (
    <DropdownMenuContext.Provider value={value}>
      <div ref={rootRef} className="shad-dropdown-root">
        {children}
      </div>
    </DropdownMenuContext.Provider>
  );
}

interface DropdownMenuTriggerProps extends PropsWithChildren<HTMLAttributes<HTMLButtonElement>> {
  asChild?: boolean;
}

function DropdownMenuTrigger({ children, className, asChild, onClick, ...props }: DropdownMenuTriggerProps) {
  const { open, setOpen } = useDropdownMenuContext();

  if (asChild && isValidElement(children)) {
    const child = children as ReactElement<{ onClick?: (event: ReactMouseEvent<HTMLElement>) => void; className?: string }>;
    return (
      <span className="shad-dropdown-trigger-wrap">
        {cloneElement(child, {
          className: cn(child.props.className, className),
          onClick: (event: ReactMouseEvent<HTMLElement>) => {
            child.props.onClick?.(event);
            setOpen(!open);
          },
        })}
      </span>
    );
  }

  return (
    <button
      type="button"
      className={cn("shad-dropdown-trigger", className)}
      onClick={(event) => {
        onClick?.(event);
        setOpen(!open);
      }}
      {...props}
    >
      {children}
    </button>
  );
}

interface DropdownMenuContentProps extends HTMLAttributes<HTMLDivElement> {
  align?: "start" | "end";
}

function DropdownMenuContent({ children, className, align = "start", ...props }: DropdownMenuContentProps) {
  const { open } = useDropdownMenuContext();
  if (!open) return null;

  return (
    <div className={cn("shad-dropdown-content", align === "end" ? "shad-dropdown-content-end" : "", className)} role="menu" {...props}>
      {children}
    </div>
  );
}

interface DropdownMenuItemProps extends HTMLAttributes<HTMLButtonElement> {
  onSelect?: () => void;
}

function DropdownMenuItem({ children, className, onSelect, onClick, ...props }: DropdownMenuItemProps) {
  const { setOpen } = useDropdownMenuContext();
  return (
    <button
      type="button"
      role="menuitem"
      className={cn("shad-dropdown-item", className)}
      onClick={(event) => {
        onClick?.(event);
        onSelect?.();
        setOpen(false);
      }}
      {...props}
    >
      {children}
    </button>
  );
}

export { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem };
