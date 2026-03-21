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
const objectContextPattern = /\b(?:from|join|update|into)\s+([A-Za-z0-9_$.]*)$/i;
const aliasPattern = /\b(?:from|join|update|into)\s+([A-Za-z_][\w]*(?:\.[A-Za-z0-9_][\w]*)*)(?:\s+(?:as\s+)?([A-Za-z_][\w$]*))?/gi;
const cteNamePattern = /^([A-Za-z_][\w]*)\s+as\s*\(/i;
const sqlKeywordSet = new Set(sqlKeywords.map((item) => item.toLowerCase()));

let configured = false;
let dynamicConfigKeys: string[] = [...dqcrConfigKeys];
let dynamicMacroFunctions: string[] = [...macroFunctions];
let dynamicParameters: string[] = [];
let dynamicObjects: DqcrAutocompleteObject[] = [];
let dynamicActiveModelId: string | null = null;

export interface DqcrAutocompleteObjectColumn {
  name: string;
  domain_type?: string | null;
  is_key?: boolean | null;
}

export interface DqcrAutocompleteObject {
  name: string;
  kind: "target_table" | "workflow_query";
  source: "project_workflow" | "project_model_fallback";
  model_id?: string | null;
  path?: string | null;
  lookup_keys: string[];
  columns: DqcrAutocompleteObjectColumn[];
}

export interface DqcrAutocompleteData {
  parameters: string[];
  macros: string[];
  configKeys: string[];
  objects: DqcrAutocompleteObject[];
  activeModelId?: string | null;
}

export interface LocalCteDefinition {
  name: string;
  columns: DqcrAutocompleteObjectColumn[];
}

export interface AutocompleteResolution {
  mode: "macro" | "member" | "object" | "default";
  objectSuggestions: DqcrAutocompleteObject[];
  columnSuggestions: DqcrAutocompleteObjectColumn[];
  localCtes: LocalCteDefinition[];
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

function normalizeSqlName(value: string): string {
  return value
    .trim()
    .split(".")
    .map((part) => part.trim().replace(/^["`\[]+|["`\]]+$/g, ""))
    .filter(Boolean)
    .join(".")
    .toLowerCase();
}

function normalizeLookupKeys(keys: string[]): string[] {
  return uniqLower(keys.map((item) => item.trim()).filter(Boolean));
}

function normalizeColumns(columns: DqcrAutocompleteObjectColumn[]): DqcrAutocompleteObjectColumn[] {
  const seen = new Set<string>();
  const result: DqcrAutocompleteObjectColumn[] = [];
  for (const item of columns) {
    const name = item.name.trim();
    if (!name) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    result.push({
      name,
      domain_type: item.domain_type ?? null,
      is_key: item.is_key ?? null,
    });
  }
  return result;
}

function normalizeObjects(objects: DqcrAutocompleteObject[]): DqcrAutocompleteObject[] {
  return objects.map((item) => ({
    ...item,
    lookup_keys: normalizeLookupKeys([item.name, ...(item.lookup_keys ?? [])]),
    columns: normalizeColumns(item.columns ?? []),
  }));
}

export function setDqcrAutocompleteData(data: DqcrAutocompleteData): void {
  dynamicParameters = uniqLower(data.parameters);
  dynamicMacroFunctions = uniqLower([...macroFunctions, ...data.macros]);
  dynamicConfigKeys = uniqLower([...dqcrConfigKeys, ...data.configKeys]);
  dynamicObjects = normalizeObjects(data.objects ?? []);
  dynamicActiveModelId = data.activeModelId ?? null;
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

function skipQuotedOrComment(sql: string, index: number): number {
  if (sql.startsWith("--", index)) {
    let cursor = index + 2;
    while (cursor < sql.length && sql[cursor] !== "\n") cursor += 1;
    return cursor;
  }
  if (sql.startsWith("/*", index)) {
    const end = sql.indexOf("*/", index + 2);
    return end >= 0 ? end + 2 : sql.length;
  }
  if (sql[index] === "'" || sql[index] === '"') {
    const quote = sql[index];
    let cursor = index + 1;
    while (cursor < sql.length) {
      if (sql[cursor] === quote) {
        if (quote === "'" && sql[cursor + 1] === "'") {
          cursor += 2;
          continue;
        }
        return cursor + 1;
      }
      cursor += 1;
    }
    return cursor;
  }
  return index + 1;
}

function findMatchingParen(sql: string, openIndex: number): number {
  let depth = 0;
  let cursor = openIndex;
  while (cursor < sql.length) {
    if (sql.startsWith("--", cursor) || sql.startsWith("/*", cursor) || sql[cursor] === "'" || sql[cursor] === '"') {
      cursor = skipQuotedOrComment(sql, cursor);
      continue;
    }
    if (sql[cursor] === "(") depth += 1;
    if (sql[cursor] === ")") {
      depth -= 1;
      if (depth === 0) return cursor;
    }
    cursor += 1;
  }
  return -1;
}

function findTopLevelKeyword(sql: string, keyword: string, start = 0): number {
  const lower = sql.toLowerCase();
  const target = keyword.toLowerCase();
  let depth = 0;

  for (let index = start; index < sql.length; index += 1) {
    if (sql.startsWith("--", index) || sql.startsWith("/*", index) || sql[index] === "'" || sql[index] === '"') {
      index = skipQuotedOrComment(sql, index) - 1;
      continue;
    }
    const char = sql[index];
    if (char === "(") {
      depth += 1;
      continue;
    }
    if (char === ")") {
      depth = Math.max(0, depth - 1);
      continue;
    }
    if (depth !== 0) continue;
    if (!lower.startsWith(target, index)) continue;
    const prev = index === 0 ? " " : lower[index - 1];
    const next = lower[index + target.length] ?? " ";
    if (/\w/.test(prev) || /\w/.test(next)) continue;
    return index;
  }

  return -1;
}

function splitTopLevelCommaSeparated(source: string): string[] {
  const result: string[] = [];
  let depth = 0;
  let start = 0;
  let index = 0;

  while (index < source.length) {
    if (source.startsWith("--", index) || source.startsWith("/*", index) || source[index] === "'" || source[index] === '"') {
      index = skipQuotedOrComment(source, index);
      continue;
    }
    const char = source[index];
    if (char === "(") depth += 1;
    if (char === ")") depth = Math.max(0, depth - 1);
    if (char === "," && depth === 0) {
      result.push(source.slice(start, index));
      start = index + 1;
    }
    index += 1;
  }

  result.push(source.slice(start));
  return result.map((item) => item.trim()).filter(Boolean);
}

function extractExpressionAlias(expression: string): string | null {
  const compact = expression
    .replace(/--.*$/gm, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .trim();
  if (!compact) return null;

  const asMatch = compact.match(/\bas\s+([A-Za-z_][\w$]*)\s*$/i);
  if (asMatch?.[1]) return asMatch[1];

  const trailingMatch = compact.match(/([A-Za-z_][\w$]*)\s*$/);
  if (trailingMatch?.[1]) {
    const value = trailingMatch[1];
    if (!sqlKeywordSet.has(value.toLowerCase())) return value;
  }

  const dottedMatch = compact.match(/(?:^|[^.\w])([A-Za-z_][\w$]*)\s*$/);
  return dottedMatch?.[1] ?? null;
}

function extractSelectColumns(sql: string): DqcrAutocompleteObjectColumn[] {
  const selectIndex = findTopLevelKeyword(sql, "select");
  if (selectIndex < 0) return [];
  const fromIndex = findTopLevelKeyword(sql, "from", selectIndex + 6);
  const selectBody = sql.slice(selectIndex + 6, fromIndex >= 0 ? fromIndex : sql.length);
  const expressions = splitTopLevelCommaSeparated(selectBody.replace(/^\s*distinct\b/i, ""));

  return normalizeColumns(
    expressions
      .map((expression) => extractExpressionAlias(expression))
      .filter((name): name is string => Boolean(name))
      .map((name) => ({ name, domain_type: null, is_key: null })),
  );
}

export function extractCteDefinitions(sql: string): LocalCteDefinition[] {
  const withIndex = findTopLevelKeyword(sql, "with");
  if (withIndex < 0) return [];

  const result: LocalCteDefinition[] = [];
  let cursor = withIndex + 4;

  while (cursor < sql.length) {
    while (cursor < sql.length && /\s/.test(sql[cursor])) cursor += 1;
    const chunk = sql.slice(cursor);
    const nameMatch = chunk.match(cteNamePattern);
    if (!nameMatch?.[1]) break;
    const name = nameMatch[1];
    const asOffset = chunk.search(/\bas\s*\(/i);
    if (asOffset < 0) break;
    const openIndex = cursor + asOffset + chunk.slice(asOffset).indexOf("(");
    const closeIndex = findMatchingParen(sql, openIndex);
    if (closeIndex < 0) break;

    result.push({
      name,
      columns: extractSelectColumns(sql.slice(openIndex + 1, closeIndex)),
    });

    cursor = closeIndex + 1;
    while (cursor < sql.length && /\s/.test(sql[cursor])) cursor += 1;
    if (sql[cursor] !== ",") break;
    cursor += 1;
  }

  return result;
}

export function extractAliasMappings(sql: string): Map<string, string> {
  const aliases = new Map<string, string>();

  for (const match of sql.matchAll(aliasPattern)) {
    const objectToken = match[1]?.trim();
    const alias = match[2]?.trim();
    if (!objectToken || !alias) continue;
    if (sqlKeywordSet.has(alias.toLowerCase())) continue;
    aliases.set(normalizeSqlName(alias), objectToken);
  }

  return aliases;
}

function rankObject(item: DqcrAutocompleteObject, activeModelId: string | null): number {
  if (item.kind === "workflow_query" && item.model_id === activeModelId) return 0;
  if (item.kind === "target_table" && item.model_id === activeModelId) return 1;
  if (item.kind === "target_table") return 2;
  return 3;
}

function sortObjects(items: DqcrAutocompleteObject[], activeModelId: string | null): DqcrAutocompleteObject[] {
  return [...items].sort((left, right) => {
    const rankDelta = rankObject(left, activeModelId) - rankObject(right, activeModelId);
    if (rankDelta !== 0) return rankDelta;
    return left.name.localeCompare(right.name);
  });
}

function findObjectByLookup(name: string, objects: DqcrAutocompleteObject[]): DqcrAutocompleteObject | null {
  const key = normalizeSqlName(name);
  return objects.find((item) => item.lookup_keys.some((candidate) => normalizeSqlName(candidate) === key)) ?? null;
}

function resolveColumnsForQualifier(
  qualifier: string,
  aliases: Map<string, string>,
  localCtes: LocalCteDefinition[],
  objects: DqcrAutocompleteObject[],
): DqcrAutocompleteObjectColumn[] {
  const normalizedQualifier = normalizeSqlName(qualifier);
  const objectToken = aliases.get(normalizedQualifier) ?? qualifier;
  const cte = localCtes.find((item) => normalizeSqlName(item.name) === normalizeSqlName(objectToken));
  if (cte) return cte.columns;
  return findObjectByLookup(objectToken, objects)?.columns ?? [];
}

function resolveObjectSuggestions(
  localCtes: LocalCteDefinition[],
  objects: DqcrAutocompleteObject[],
  activeModelId: string | null,
): DqcrAutocompleteObject[] {
  const cteObjects: DqcrAutocompleteObject[] = localCtes.map((cte) => ({
    name: cte.name,
    kind: "workflow_query",
    source: "project_workflow",
    model_id: activeModelId,
    path: null,
    lookup_keys: [cte.name],
    columns: cte.columns,
  }));

  const seen = new Set<string>();
  const result: DqcrAutocompleteObject[] = [];

  for (const item of [...cteObjects, ...sortObjects(objects, activeModelId)]) {
    const key = `${item.kind}:${normalizeSqlName(item.name)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(item);
  }

  return result;
}

export function resolveAutocompleteContext(
  sql: string,
  offset: number,
  data: DqcrAutocompleteData,
): AutocompleteResolution {
  const textBeforeCursor = sql.slice(0, offset);
  const objects = normalizeObjects(data.objects ?? []);
  const localCtes = extractCteDefinitions(sql);
  const aliases = extractAliasMappings(sql);

  const macroOpenIndex = textBeforeCursor.lastIndexOf("{{");
  const macroCloseIndex = textBeforeCursor.lastIndexOf("}}");
  if (macroOpenIndex > macroCloseIndex) {
    return { mode: "macro", objectSuggestions: [], columnSuggestions: [], localCtes };
  }

  const memberMatch = textBeforeCursor.match(/([A-Za-z_][\w$]*)\.([A-Za-z_][\w$]*)?$/);
  if (memberMatch?.[1]) {
    return {
      mode: "member",
      objectSuggestions: [],
      columnSuggestions: resolveColumnsForQualifier(memberMatch[1], aliases, localCtes, objects),
      localCtes,
    };
  }

  if (objectContextPattern.test(textBeforeCursor)) {
    return {
      mode: "object",
      objectSuggestions: resolveObjectSuggestions(localCtes, objects, data.activeModelId ?? null),
      columnSuggestions: [],
      localCtes,
    };
  }

  return {
    mode: "default",
    objectSuggestions: sortObjects(objects, data.activeModelId ?? null),
    columnSuggestions: [],
    localCtes,
  };
}

function buildObjectDetail(item: DqcrAutocompleteObject): string {
  if (item.kind === "workflow_query") return `Workflow query${item.path ? ` · ${item.path}` : ""}`;
  return `Project table${item.path ? ` · ${item.path}` : ""}`;
}

function buildObjectSuggestions(
  monaco: typeof Monaco,
  range: Monaco.IRange,
  items: DqcrAutocompleteObject[],
): Monaco.languages.CompletionItem[] {
  return items.map((item, index) => ({
    label: item.name,
    kind: item.kind === "workflow_query" ? monaco.languages.CompletionItemKind.Reference : monaco.languages.CompletionItemKind.Class,
    insertText: item.name,
    detail: buildObjectDetail(item),
    sortText: `${String(index).padStart(4, "0")}-${item.name.toLowerCase()}`,
    range,
  }));
}

function buildColumnSuggestions(
  monaco: typeof Monaco,
  range: Monaco.IRange,
  items: DqcrAutocompleteObjectColumn[],
): Monaco.languages.CompletionItem[] {
  return items.map((item, index) => ({
    label: item.name,
    kind: monaco.languages.CompletionItemKind.Field,
    insertText: item.name,
    detail: item.domain_type ? `Column · ${item.domain_type}` : "Column",
    sortText: `${String(index).padStart(4, "0")}-${item.name.toLowerCase()}`,
    range,
  }));
}

function buildStaticSuggestions(monaco: typeof Monaco, range: Monaco.IRange): Monaco.languages.CompletionItem[] {
  const completionItems: Monaco.languages.CompletionItem[] = [];

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

  return completionItems;
}

function buildMacroSuggestions(monaco: typeof Monaco, range: Monaco.IRange): Monaco.languages.CompletionItem[] {
  return [
    ...dynamicParameters.map((name) => ({
      label: name,
      kind: monaco.languages.CompletionItemKind.Variable,
      insertText: name,
      detail: "DQCR parameter",
      range,
    })),
    ...dynamicMacroFunctions.map((name) => ({
      label: name,
      kind: monaco.languages.CompletionItemKind.Function,
      insertText: `${name}($0)`,
      insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
      detail: "DQCR macro",
      range,
    })),
  ];
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
      triggerCharacters: ["{", "@", ":", "."],
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        const completionItems: Monaco.languages.CompletionItem[] = [];
        const sql = model.getValue();
        const offset = model.getOffsetAt(position);
        const context = resolveAutocompleteContext(sql, offset, {
          parameters: dynamicParameters,
          macros: dynamicMacroFunctions,
          configKeys: dynamicConfigKeys,
          objects: dynamicObjects,
          activeModelId: dynamicActiveModelId,
        });
        const isMacro = inMacroContext(model, position) || context.mode === "macro";

        if (isMacro) {
          completionItems.push(...buildMacroSuggestions(monaco, range));
        }
        if (context.mode === "member") {
          completionItems.push(...buildColumnSuggestions(monaco, range, context.columnSuggestions));
        } else if (context.mode === "object") {
          completionItems.push(...buildObjectSuggestions(monaco, range, context.objectSuggestions));
        } else if (context.mode === "default") {
          completionItems.push(...buildObjectSuggestions(monaco, range, context.objectSuggestions));
        }
        completionItems.push(...buildStaticSuggestions(monaco, range));

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
