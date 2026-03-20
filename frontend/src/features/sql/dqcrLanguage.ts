import type * as Monaco from "monaco-editor";

const DQCR_LANGUAGE_ID = "dqcr-sql";
const DQCR_THEME_LIGHT = "dqcr-light";
const DQCR_THEME_DARK = "dqcr-dark";

const sqlKeywords = [
  "select",
  "from",
  "where",
  "join",
  "left",
  "right",
  "inner",
  "outer",
  "cross",
  "on",
  "with",
  "as",
  "and",
  "or",
  "not",
  "null",
  "is",
  "in",
  "exists",
  "case",
  "when",
  "then",
  "else",
  "end",
  "group",
  "by",
  "order",
  "having",
  "limit",
  "offset",
  "insert",
  "into",
  "update",
  "delete",
  "create",
  "table",
  "view",
  "distinct",
  "union",
  "all",
  "over",
  "partition",
  "rows",
  "range",
  "between",
  "asc",
  "desc",
];

const dqcrConfigKeys = [
  "materialized",
  "target_table",
  "depends_on",
  "engine",
  "schema",
  "description",
  "tags",
  "folder",
];

const macroFunctions = ["ref", "source", "env_var", "var", "config", "adapter", "run_query", "generate_series"];

let configured = false;
let dynamicConfigKeys: string[] = [...dqcrConfigKeys];
let dynamicMacroFunctions: string[] = [...macroFunctions];
let dynamicParameters: string[] = [];

export interface DqcrAutocompleteData {
  parameters: string[];
  macros: string[];
  configKeys: string[];
}

function uniqLower(items: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of items) {
    const value = raw.trim();
    if (!value) continue;
    const key = value.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(value);
  }
  return result;
}

export function setDqcrAutocompleteData(data: DqcrAutocompleteData): void {
  dynamicParameters = uniqLower(data.parameters);
  dynamicMacroFunctions = uniqLower([...macroFunctions, ...data.macros]);
  dynamicConfigKeys = uniqLower([...dqcrConfigKeys, ...data.configKeys]);
}

function inMacroContext(model: Monaco.editor.ITextModel, position: Monaco.Position): boolean {
  const linePrefix = model.getValueInRange({
    startLineNumber: position.lineNumber,
    startColumn: 1,
    endLineNumber: position.lineNumber,
    endColumn: position.column,
  });
  const openIndex = linePrefix.lastIndexOf("{{");
  const closeIndex = linePrefix.lastIndexOf("}}");
  return openIndex > closeIndex;
}

export function configureDqcrMonaco(monaco: typeof Monaco): void {
  if (configured) {
    return;
  }

  try {
    monaco.languages.register({ id: DQCR_LANGUAGE_ID });

  monaco.languages.setMonarchTokensProvider(DQCR_LANGUAGE_ID, {
    ignoreCase: true,
    defaultToken: "",
    sqlKeywords,
    dqcrConfigKeys,
    macroFunctions,
    tokenizer: {
      root: [
        [/--.*$/, "comment"],
        [/\/\*/, "comment", "@comment"],
        [/\{\{/, "keyword.dqcr.macro.start", "@macro"],
        [/[@]config\b/, "keyword.dqcr.config"],
        [/"(?:[^"]|"")*"/, "string"],
        [/'[^']*'/, "string"],
        [/\b\d+(?:\.\d+)?\b/, "number"],
        [/[;,.]/, "delimiter"],
        [/\(|\)/, "delimiter.parenthesis"],
        [/[a-zA-Z_][\w$]*/, {
          cases: {
            "@dqcrConfigKeys": "variable.dqcr.key",
            "@sqlKeywords": "keyword",
            "@default": "identifier",
          },
        }],
        [/[-+\/%=<>!~|&^]+/, "operator"],
      ],

      comment: [
        [/[^\/*]+/, "comment"],
        [/\*\//, "comment", "@pop"],
        [/[\/*]/, "comment"],
      ],

      macro: [
        [/\}\}/, "keyword.dqcr.macro.end", "@pop"],
        [/\s+/, ""],
        [/[a-zA-Z_][\w$]*/, {
          cases: {
            "@macroFunctions": "entity.name.function.dqcr",
            "@default": "variable.parameter.dqcr",
          },
        }],
        [/"(?:[^"]|"")*"/, "string"],
        [/'[^']*'/, "string"],
        [/\b\d+(?:\.\d+)?\b/, "number"],
        [/[()]/, "delimiter.parenthesis"],
        [/[=,+\-*/<>!]+/, "operator"],
      ],
    },
  });

  monaco.languages.registerCompletionItemProvider(DQCR_LANGUAGE_ID, {
    triggerCharacters: ["{", "@", ":"],
    provideCompletionItems: (model, position) => {
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };
      const completionItems: Monaco.languages.CompletionItem[] = [];
      const isMacroContext = inMacroContext(model, position);

      if (isMacroContext) {
        completionItems.push(
          ...dynamicParameters.map((name) => ({
            label: name,
            kind: monaco.languages.CompletionItemKind.Variable,
            insertText: name,
            detail: "DQCR parameter",
            range,
          })),
        );
        completionItems.push(
          ...dynamicMacroFunctions.map((name) => ({
            label: name,
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: `${name}($0)`,
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            detail: "DQCR macro",
            range,
          })),
        );
      }

      completionItems.push(
        ...dynamicConfigKeys.map((name) => ({
          label: name,
          kind: monaco.languages.CompletionItemKind.Property,
          insertText: `${name}: `,
          detail: "@config key",
          range,
        })),
      );
      completionItems.push({
        label: "@config",
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: "@config(\n  $0\n)",
        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        detail: "DQCR inline config block",
        range,
      });
      completionItems.push({
        label: "{{...}}",
        kind: monaco.languages.CompletionItemKind.Snippet,
        insertText: "{{$0}}",
        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        detail: "DQCR template expression",
        range,
      });

      return { suggestions: completionItems };
    },
  });

  monaco.editor.defineTheme(DQCR_THEME_LIGHT, {
    base: "vs",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "0F6E56", fontStyle: "bold" },
      { token: "keyword.dqcr.config", foreground: "F0997B" },
      { token: "keyword.dqcr.macro.start", foreground: "85B7EB", fontStyle: "bold" },
      { token: "keyword.dqcr.macro.end", foreground: "85B7EB", fontStyle: "bold" },
      { token: "variable.dqcr.key", foreground: "0F6E56", fontStyle: "bold" },
      { token: "variable.parameter.dqcr", foreground: "BA7517" },
      { token: "entity.name.function.dqcr", foreground: "85B7EB" },
      { token: "string", foreground: "8B6914" },
      { token: "comment", foreground: "888780", fontStyle: "italic" },
    ],
    colors: {
      "editor.background": "#FFFFFF",
      "editor.foreground": "#444441",
      "editor.lineHighlightBackground": "#F7F7F5",
      "editor.selectionBackground": "#C8EEE180",
      "editorLineNumber.foreground": "#B4B2A9",
      "editorLineNumber.activeForeground": "#5F5E5A",
      "editorIndentGuide.background": "#F1EFE8",
      "editorCursor.foreground": "#1D9E75",
      "editorGutter.background": "#FAFAF8",
    },
  });

  monaco.editor.defineTheme(DQCR_THEME_DARK, {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "5DCAA5", fontStyle: "bold" },
      { token: "keyword.dqcr.config", foreground: "F0997B" },
      { token: "keyword.dqcr.macro.start", foreground: "85B7EB" },
      { token: "keyword.dqcr.macro.end", foreground: "85B7EB" },
      { token: "variable.dqcr.key", foreground: "5DCAA5" },
      { token: "variable.parameter.dqcr", foreground: "FAC775" },
      { token: "entity.name.function.dqcr", foreground: "85B7EB" },
      { token: "string", foreground: "FAC775" },
      { token: "comment", foreground: "6A9955", fontStyle: "italic" },
    ],
    colors: {
      "editor.background": "#1E1E1E",
      "editor.foreground": "#CDCDCD",
      "editor.lineHighlightBackground": "#282828",
      "editor.selectionBackground": "#264F78",
      "editorLineNumber.foreground": "#5F5E5A",
      "editorLineNumber.activeForeground": "#9D9D9D",
      "editorGutter.background": "#252526",
      "editorCursor.foreground": "#AEAFAD",
      "scrollbar.shadow": "#000000",
    },
  });

    configured = true;
  } catch (error) {
    // Keep editor usable even if custom language setup fails.
    console.error("Failed to configure DQCR Monaco language", error);
    configured = true;
  }
}

export function getDqcrTheme(theme: "light" | "dark"): string {
  return theme === "dark" ? DQCR_THEME_DARK : DQCR_THEME_LIGHT;
}

export { DQCR_LANGUAGE_ID };
