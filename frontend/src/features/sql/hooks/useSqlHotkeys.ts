import { useEffect, useRef } from "react";
import type { RefObject } from "react";

import type { SqlViewMode } from "../types/sqlView";

interface UseSqlHotkeysOptions {
  activeFilePath: string | null;
  mode: SqlViewMode;
  draft: string;
  quickOpenVisible: boolean;
  quickOpenCandidates: string[];
  quickOpenIndex: number;
  findVisible: boolean;
  isFullscreen: boolean;
  isEditorExpanded: boolean;
  setFindVisible: (visible: boolean) => void;
  setQuickOpenVisible: (visible: boolean) => void;
  setQuickOpenIndex: (value: number | ((prev: number) => number)) => void;
  setQuickOpenQuery: (value: string) => void;
  setIsEditorExpanded: (value: boolean | ((current: boolean) => boolean)) => void;
  findInputRef: RefObject<HTMLInputElement>;
  quickOpenInputRef: RefObject<HTMLInputElement>;
  onSave: (draft: string) => void;
  onFormat: () => void | Promise<void>;
  onGoToDefinition: () => void;
  onOpenPathInSql: (path: string) => void;
}

export function useSqlHotkeys({
  activeFilePath,
  mode,
  draft,
  quickOpenVisible,
  quickOpenCandidates,
  quickOpenIndex,
  findVisible,
  isFullscreen,
  isEditorExpanded,
  setFindVisible,
  setQuickOpenVisible,
  setQuickOpenIndex,
  setQuickOpenQuery,
  setIsEditorExpanded,
  findInputRef,
  quickOpenInputRef,
  onSave,
  onFormat,
  onGoToDefinition,
  onOpenPathInSql,
}: UseSqlHotkeysOptions) {
  const onSaveRef = useRef(onSave);
  const onFormatRef = useRef(onFormat);
  const onGoToDefinitionRef = useRef(onGoToDefinition);
  const onOpenPathInSqlRef = useRef(onOpenPathInSql);
  const snapshotRef = useRef({
    activeFilePath,
    mode,
    draft,
    quickOpenVisible,
    quickOpenCandidates,
    quickOpenIndex,
    findVisible,
    isFullscreen,
    isEditorExpanded,
  });

  useEffect(() => {
    onSaveRef.current = onSave;
  }, [onSave]);

  useEffect(() => {
    onFormatRef.current = onFormat;
  }, [onFormat]);

  useEffect(() => {
    onGoToDefinitionRef.current = onGoToDefinition;
  }, [onGoToDefinition]);

  useEffect(() => {
    onOpenPathInSqlRef.current = onOpenPathInSql;
  }, [onOpenPathInSql]);

  useEffect(() => {
    snapshotRef.current = {
      activeFilePath,
      mode,
      draft,
      quickOpenVisible,
      quickOpenCandidates,
      quickOpenIndex,
      findVisible,
      isFullscreen,
      isEditorExpanded,
    };
  }, [
    activeFilePath,
    mode,
    draft,
    quickOpenVisible,
    quickOpenCandidates,
    quickOpenIndex,
    findVisible,
    isFullscreen,
    isEditorExpanded,
  ]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const snapshot = snapshotRef.current;
      const isSave = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s";
      const isFindReplace = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "h";
      const isQuickOpen = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "p";
      const isFormat = (event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "f";
      const isGotoDefinition = event.key === "F12";

      if (isSave && snapshot.activeFilePath && snapshot.mode === "source") {
        event.preventDefault();
        onSaveRef.current(snapshot.draft);
        return;
      }
      if (isFindReplace) {
        event.preventDefault();
        setFindVisible(true);
        setTimeout(() => findInputRef.current?.focus(), 0);
        return;
      }
      if (isQuickOpen) {
        event.preventDefault();
        setQuickOpenVisible(true);
        setQuickOpenIndex(0);
        setTimeout(() => quickOpenInputRef.current?.focus(), 0);
        return;
      }
      if (isFormat && snapshot.activeFilePath && snapshot.mode === "source") {
        event.preventDefault();
        void onFormatRef.current();
        return;
      }
      if (isGotoDefinition && snapshot.activeFilePath) {
        event.preventDefault();
        onGoToDefinitionRef.current();
      }

      if (snapshot.quickOpenVisible) {
        if (event.key === "ArrowDown") {
          event.preventDefault();
          setQuickOpenIndex((prev) => Math.min(prev + 1, Math.max(snapshot.quickOpenCandidates.length - 1, 0)));
          return;
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          setQuickOpenIndex((prev) => Math.max(prev - 1, 0));
          return;
        }
        if (event.key === "Enter") {
          event.preventDefault();
          const selected = snapshot.quickOpenCandidates[snapshot.quickOpenIndex];
          if (selected) {
            onOpenPathInSqlRef.current(selected);
            setQuickOpenVisible(false);
            setQuickOpenQuery("");
          }
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          setQuickOpenVisible(false);
          setQuickOpenQuery("");
          return;
        }
      }

      if (snapshot.findVisible && event.key === "Escape") {
        if (snapshot.isFullscreen) return;
        event.preventDefault();
        setFindVisible(false);
        return;
      }

      if (snapshot.isEditorExpanded && event.key === "Escape") {
        if (snapshot.isFullscreen) return;
        event.preventDefault();
        setIsEditorExpanded(false);
        return;
      }

      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === ".") {
        event.preventDefault();
        setIsEditorExpanded((current) => !current);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [findInputRef, quickOpenInputRef, setFindVisible, setIsEditorExpanded, setQuickOpenIndex, setQuickOpenQuery, setQuickOpenVisible]);
}
