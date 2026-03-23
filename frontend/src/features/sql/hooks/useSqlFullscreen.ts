import { useEffect } from "react";

import { useSqlTabsStore } from "../../../app/store/sqlTabsStore";

interface UseSqlFullscreenOptions {
  enabled: boolean;
  onEnter?: () => void;
  onExit?: () => void;
}

export function useSqlFullscreen({ enabled, onEnter, onExit }: UseSqlFullscreenOptions) {
  const isFullscreen = useSqlTabsStore((state) => state.isFullscreen);
  const enterFullscreen = useSqlTabsStore((state) => state.enterFullscreen);
  const exitFullscreen = useSqlTabsStore((state) => state.exitFullscreen);

  const enter = () => {
    if (!enabled) return;
    enterFullscreen();
    onEnter?.();
  };

  const exit = () => {
    exitFullscreen();
    onExit?.();
  };

  useEffect(() => {
    if (!enabled) return;
    const handler = (event: KeyboardEvent) => {
      const isEnterShortcut = (event.ctrlKey || event.metaKey) && event.shiftKey && event.key === "Enter";
      if (isEnterShortcut) {
        event.preventDefault();
        if (isFullscreen) {
          exit();
        } else {
          enter();
        }
        return;
      }
      if (event.key === "Escape" && isFullscreen) {
        event.preventDefault();
        exit();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [enabled, isFullscreen]);

  return {
    isFullscreen,
    enter,
    exit,
  };
}
