import type * as Monaco from "monaco-editor";

const DQCR_LANGUAGE_ID = "dqcr-sql";
const DQCR_THEME_LIGHT = "dqcr-github-light";
const DQCR_THEME_DARK = "dqcr-dracula";

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
  description?: string | null;
}

export interface DqcrAutocompleteObject {
  name: string;
  kind: "target_table" | "workflow_query" | "catalog_entity";
  source: "project_workflow" | "project_model_fallback" | "catalog";
  model_id?: string | null;
  module?: string | null;
  object_name?: string | null;
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
  mode: "macro" | "member" | "object" | "default" | "model_module" | "model_object" | "model_attribute";
  objectSuggestions: DqcrAutocompleteObject[];
  columnSuggestions: DqcrAutocompleteObjectColumn[];
  moduleSuggestions: string[];
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
      description: item.description ?? null,
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

function normalizeModelNamespaceToken(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function objectModuleName(item: DqcrAutocompleteObject): string {
  const direct = normalizeModelNamespaceToken(item.module);
  if (direct) return direct;
  const fallback = normalizeModelNamespaceToken(item.model_id);
  if (fallback) return fallback;
  return "";
}

function objectEntityName(item: DqcrAutocompleteObject): string {
  const direct = normalizeModelNamespaceToken(item.object_name);
  if (direct) return direct;
  if (item.kind === "target_table") {
    const parts = item.name.split(".").map((part) => part.trim()).filter(Boolean);
    return parts.length > 0 ? parts[parts.length - 1] : item.name;
  }
  return item.name;
}

function modelNamespaceCandidates(objects: DqcrAutocompleteObject[]): DqcrAutocompleteObject[] {
  return objects.filter((item) => item.kind === "target_table" || item.kind === "catalog_entity");
}

function parseModelNamespaceContext(textBeforeCursor: string): { stage: "module" | "object" | "attribute"; module?: string; object?: string } | null {
  if (/_m\.$/.test(textBeforeCursor)) {
    return { stage: "module" };
  }

  const objectMatch = textBeforeCursor.match(/_m\.([A-Za-z_][\w$]*)\.$/);
  if (objectMatch?.[1]) {
    return { stage: "object", module: objectMatch[1] };
  }

  const attrMatch = textBeforeCursor.match(/_m\.([A-Za-z_][\w$]*)\.([A-Za-z_][\w$]*)\.$/);
  if (attrMatch?.[1] && attrMatch?.[2]) {
    return { stage: "attribute", module: attrMatch[1], object: attrMatch[2] };
  }

  return null;
}

function resolveModuleSuggestions(objects: DqcrAutocompleteObject[], activeModelId: string | null): string[] {
  const seen = new Set<string>();
  const rows: Array<{ value: string; priority: number }> = [];
  for (const item of modelNamespaceCandidates(objects)) {
    const moduleName = objectModuleName(item);
    if (!moduleName) continue;
    const key = moduleName.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    const priority = normalizeSqlName(moduleName) === normalizeSqlName(activeModelId ?? "") ? 0 : item.source === "catalog" ? 2 : 1;
    rows.push({ value: moduleName, priority });
  }
  return rows.sort((left, right) => left.priority - right.priority || left.value.localeCompare(right.value)).map((item) => item.value);
}

function resolveNamespacedObjects(
  objects: DqcrAutocompleteObject[],
  moduleName: string,
  activeModelId: string | null,
): DqcrAutocompleteObject[] {
  const wantedModule = normalizeSqlName(moduleName);
  const seen = new Set<string>();
  const result: DqcrAutocompleteObject[] = [];
  const sorted = sortObjects(modelNamespaceCandidates(objects), activeModelId);
  for (const item of sorted) {
    if (normalizeSqlName(objectModuleName(item)) !== wantedModule) continue;
    const objectName = objectEntityName(item);
    const dedupeKey = normalizeSqlName(objectName);
    if (!dedupeKey || seen.has(dedupeKey)) continue;
    seen.add(dedupeKey);
    result.push({
      ...item,
      name: objectName,
    });
  }
  return result;
}

function resolveNamespacedColumns(objects: DqcrAutocompleteObject[], moduleName: string, objectName: string): DqcrAutocompleteObjectColumn[] {
  const wantedModule = normalizeSqlName(moduleName);
  const wantedObject = normalizeSqlName(objectName);
  const matched = modelNamespaceCandidates(objects).find((item) => {
    return normalizeSqlName(objectModuleName(item)) === wantedModule && normalizeSqlName(objectEntityName(item)) === wantedObject;
  });
  return matched?.columns ?? [];
}

function rankObject(item: DqcrAutocompleteObject, activeModelId: string | null): number {
  if (item.kind === "workflow_query" && item.model_id === activeModelId) return 0;
  if (item.kind === "target_table" && item.model_id === activeModelId) return 1;
  if (item.kind === "catalog_entity") return 2;
  if (item.kind === "workflow_query") return 3;
  if (item.kind === "target_table") return 4;
  return 5;
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
    return { mode: "macro", objectSuggestions: [], columnSuggestions: [], moduleSuggestions: [], localCtes };
  }

  const namespaceContext = parseModelNamespaceContext(textBeforeCursor);
  if (namespaceContext?.stage === "module") {
    return {
      mode: "model_module",
      objectSuggestions: [],
      columnSuggestions: [],
      moduleSuggestions: resolveModuleSuggestions(objects, data.activeModelId ?? null),
      localCtes,
    };
  }
  if (namespaceContext?.stage === "object" && namespaceContext.module) {
    return {
      mode: "model_object",
      objectSuggestions: resolveNamespacedObjects(objects, namespaceContext.module, data.activeModelId ?? null),
      columnSuggestions: [],
      moduleSuggestions: [],
      localCtes,
    };
  }
  if (namespaceContext?.stage === "attribute" && namespaceContext.module && namespaceContext.object) {
    return {
      mode: "model_attribute",
      objectSuggestions: [],
      columnSuggestions: resolveNamespacedColumns(objects, namespaceContext.module, namespaceContext.object),
      moduleSuggestions: [],
      localCtes,
    };
  }

  const memberMatch = textBeforeCursor.match(/([A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)*)\.([A-Za-z_][\w$]*)?$/);
  if (memberMatch?.[1]) {
    return {
      mode: "member",
      objectSuggestions: [],
      columnSuggestions: resolveColumnsForQualifier(memberMatch[1], aliases, localCtes, objects),
      moduleSuggestions: [],
      localCtes,
    };
  }

  if (objectContextPattern.test(textBeforeCursor)) {
    return {
      mode: "object",
      objectSuggestions: resolveObjectSuggestions(localCtes, objects, data.activeModelId ?? null),
      columnSuggestions: [],
      moduleSuggestions: [],
      localCtes,
    };
  }

  return {
    mode: "default",
    objectSuggestions: sortObjects(objects, data.activeModelId ?? null),
    columnSuggestions: [],
    moduleSuggestions: [],
    localCtes,
  };
}

function buildObjectDetail(item: DqcrAutocompleteObject): string {
  if (item.kind === "workflow_query") return `Workflow query${item.path ? ` · ${item.path}` : ""}`;
  if (item.kind === "catalog_entity") return "Catalog entity";
  return `Project table${item.path ? ` · ${item.path}` : ""}`;
}

function buildModuleSuggestions(
  monaco: typeof Monaco,
  range: Monaco.IRange,
  items: string[],
): Monaco.languages.CompletionItem[] {
  return items.map((item, index) => ({
    label: item,
    kind: monaco.languages.CompletionItemKind.Module,
    insertText: item,
    detail: "Model module",
    sortText: `${String(index).padStart(4, "0")}-${item.toLowerCase()}`,
    range,
  }));
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
    detail: item.description ? `${item.domain_type ? `Column · ${item.domain_type}` : "Column"} · ${item.description}` : item.domain_type ? `Column · ${item.domain_type}` : "Column",
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
        if (context.mode === "member" || context.mode === "model_attribute") {
          completionItems.push(...buildColumnSuggestions(monaco, range, context.columnSuggestions));
        } else if (context.mode === "model_module") {
          completionItems.push(...buildModuleSuggestions(monaco, range, context.moduleSuggestions));
        } else if (context.mode === "model_object") {
          completionItems.push(...buildObjectSuggestions(monaco, range, context.objectSuggestions));
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
        { token: "keyword", foreground: "CF222E", fontStyle: "bold" },
        { token: "keyword.dqcr.config", foreground: "6639BA" },
        { token: "keyword.dqcr.macro.start", foreground: "0550AE", fontStyle: "bold" },
        { token: "keyword.dqcr.macro.end", foreground: "0550AE", fontStyle: "bold" },
        { token: "variable.dqcr.key", foreground: "116329", fontStyle: "bold" },
        { token: "variable.parameter.dqcr", foreground: "953800" },
        { token: "entity.name.function.dqcr", foreground: "8250DF" },
        { token: "string", foreground: "0A3069" },
        { token: "comment", foreground: "6E7781", fontStyle: "italic" },
      ],
      colors: {
        "editor.background": "#FFFFFF",
        "editor.foreground": "#24292F",
        "editor.lineHighlightBackground": "#F6F8FA",
        "editor.selectionBackground": "#B6D6FA80",
        "editorLineNumber.foreground": "#8C959F",
        "editorLineNumber.activeForeground": "#57606A",
        "editorIndentGuide.background": "#D0D7DE",
        "editorCursor.foreground": "#0969DA",
        "editorGutter.background": "#FFFFFF",
      },
    });

    monaco.editor.defineTheme(DQCR_THEME_DARK, {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "keyword", foreground: "FF79C6", fontStyle: "bold" },
        { token: "keyword.dqcr.config", foreground: "FFB86C" },
        { token: "keyword.dqcr.macro.start", foreground: "8BE9FD" },
        { token: "keyword.dqcr.macro.end", foreground: "8BE9FD" },
        { token: "variable.dqcr.key", foreground: "50FA7B" },
        { token: "variable.parameter.dqcr", foreground: "FFB86C" },
        { token: "entity.name.function.dqcr", foreground: "8BE9FD" },
        { token: "string", foreground: "F1FA8C" },
        { token: "comment", foreground: "6272A4", fontStyle: "italic" },
      ],
      colors: {
        "editor.background": "#282A36",
        "editor.foreground": "#F8F8F2",
        "editor.lineHighlightBackground": "#343746",
        "editor.selectionBackground": "#44475A",
        "editorLineNumber.foreground": "#6272A4",
        "editorLineNumber.activeForeground": "#BD93F9",
        "editorGutter.background": "#282A36",
        "editorCursor.foreground": "#F8F8F2",
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
