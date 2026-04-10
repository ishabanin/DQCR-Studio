import type * as Monaco from "monaco-editor";
import type { RefObject } from "react";

interface UseSqlFindReplaceOptions {
  editorRef: RefObject<Monaco.editor.IStandaloneCodeEditor | null>;
  findQuery: string;
  findRegex: boolean;
  replaceQuery: string;
  addToast: (title: string, type?: "success" | "info" | "error") => void;
}

export function useSqlFindReplace({ editorRef, findQuery, findRegex, replaceQuery, addToast }: UseSqlFindReplaceOptions) {
  const findMatches = () => {
    const editor = editorRef.current;
    const model = editor?.getModel();
    if (!editor || !model || !findQuery) return [];
    return model.findMatches(findQuery, true, findRegex, false, null, false, 1000);
  };

  const selectNextMatch = () => {
    const editor = editorRef.current;
    if (!editor) return false;
    const matches = findMatches();
    if (matches.length === 0) {
      addToast("No matches found", "error");
      return false;
    }

    const position = editor.getPosition();
    const currentOffset = position ? editor.getModel()?.getOffsetAt(position) ?? 0 : 0;
    const next = matches.find((item) => {
      const start = editor.getModel()?.getOffsetAt(item.range.getStartPosition()) ?? 0;
      return start > currentOffset;
    });
    const target = next ?? matches[0];
    editor.setSelection(target.range);
    editor.revealRangeInCenter(target.range);
    editor.focus();
    return true;
  };

  const replaceOne = () => {
    const editor = editorRef.current;
    if (!editor) return;
    const selection = editor.getSelection();
    if (selection && !selection.isEmpty()) {
      editor.executeEdits("replace-one", [{ range: selection, text: replaceQuery }]);
      selectNextMatch();
      return;
    }
    if (selectNextMatch()) {
      const selected = editor.getSelection();
      if (selected && !selected.isEmpty()) {
        editor.executeEdits("replace-one", [{ range: selected, text: replaceQuery }]);
      }
    }
  };

  const replaceAll = () => {
    const editor = editorRef.current;
    const model = editor?.getModel();
    if (!editor || !model) return;
    const matches = findMatches();
    if (matches.length === 0) {
      addToast("No matches found", "error");
      return;
    }
    editor.executeEdits(
      "replace-all",
      [...matches].reverse().map((match) => ({
        range: match.range,
        text: replaceQuery,
      })),
    );
    addToast(`Replaced ${matches.length} matches`, "success");
  };

  return {
    selectNextMatch,
    replaceOne,
    replaceAll,
  };
}
