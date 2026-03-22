type PatternTranslation = {
  pattern: RegExp;
  replace: string | ((...args: string[]) => string);
};

const EXACT_TRANSLATIONS = new Map<string, string>([
  ["Studio", "Студия"],
  ["All projects", "Все проекты"],
  ["Project switcher", "Выбор проекта"],
  ["Context switcher", "Выбор контекста"],
  ["Validate", "Проверить"],
  ["Build", "Сборка"],
  ["Admin", "Админ"],
  ["Dark", "Тёмная"],
  ["Light", "Светлая"],
  ["Single Context", "Один контекст"],
  ["Multi Context", "Несколько контекстов"],
  ["Project Explorer", "Проводник проекта"],
  ["Terminal", "Терминал"],
  ["Logs", "Логи"],
  ["Output", "Вывод"],
  ["Collapse", "Свернуть"],
  ["Expand", "Развернуть"],
  ["Clear Logs", "Очистить логи"],
  ["No API calls yet.", "Вызовов API пока нет."],
  ["Output placeholder", "Панель вывода в разработке"],
  ["New file", "Новый файл"],
  ["New folder", "Новая папка"],
  ["New model", "Новая модель"],
  ["Rename", "Переименовать"],
  ["Delete", "Удалить"],
  ["Collapse all", "Свернуть всё"],
  ["Reveal active file", "Показать активный файл"],
  ["Expand sidebar", "Развернуть боковую панель"],
  ["Collapse sidebar", "Свернуть боковую панель"],
  ["Resize sidebar", "Изменить размер боковой панели"],
  ["Resize bottom panel", "Изменить размер нижней панели"],
  ["Close", "Закрыть"],
  ["Cancel", "Отмена"],
  ["Apply", "Применить"],
  ["Working...", "Выполняется..."],
  ["No file selected", "Файл не выбран"],
  ["No files found.", "Файлы не найдены."],
  ["Quick Open (Ctrl+P)", "Быстрое открытие (Ctrl+P)"],
  ["Find (Ctrl+H)", "Найти (Ctrl+H)"],
  ["Replace", "Заменить"],
  ["Expanded workspace", "Расширенное рабочее пространство"],
  ["Query workspace", "Рабочее пространство запроса"],
  ["Saved", "Сохранено"],
  ["Editing", "Редактирование"],
  ["No matches found", "Совпадения не найдены"],
  ["Validation failed", "Проверка завершилась с ошибкой"],
  ["Validation completed", "Проверка завершена"],
  ["Auto validation failed", "Автопроверка завершилась с ошибкой"],
  ["Failed to save file", "Не удалось сохранить файл"],
  ["Workflow rebuild failed", "Не удалось пересобрать workflow"],
  ["Workflow rebuilt", "Workflow пересобран"],
  ["Run Build", "Запустить сборку"],
  ["Building...", "Сборка..."],
  ["Rebuilding...", "Пересборка..."],
  ["Rebuild Workflow", "Пересобрать workflow"],
  ["Lineage exported", "Линейность экспортирована"],
  ["No project selected", "Проект не выбран"],
  ["No models found", "Модели не найдены"],
  ["No folders match", "Нет подходящих папок"],
]);

const PATTERN_TRANSLATIONS: PatternTranslation[] = [
  {
    pattern: /^Validation: (\d+) errors, (\d+) warnings, (\d+) passed$/,
    replace: (_whole, errors, warnings, passed) => `Проверка: ${errors} ошибок, ${warnings} предупреждений, ${passed} успешно`,
  },
  {
    pattern: /^Auto validation: (\d+) errors, (\d+) warnings, (\d+) passed$/,
    replace: (_whole, errors, warnings, passed) => `Автопроверка: ${errors} ошибок, ${warnings} предупреждений, ${passed} успешно`,
  },
  {
    pattern: /^Replaced (\d+) matches$/,
    replace: (_whole, count) => `Заменено совпадений: ${count}`,
  },
  {
    pattern: /^Project: (.+)$/,
    replace: (_whole, value) => `Проект: ${value}`,
  },
  {
    pattern: /^Context: (.+)$/,
    replace: (_whole, value) => `Контекст: ${value}`,
  },
];

function withOriginalSpacing(next: string, original: string): string {
  const leading = original.match(/^\s*/)?.[0] ?? "";
  const trailing = original.match(/\s*$/)?.[0] ?? "";
  return `${leading}${next}${trailing}`;
}

function translate(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return raw;

  const exact = EXACT_TRANSLATIONS.get(trimmed);
  if (exact) {
    return withOriginalSpacing(exact, raw);
  }

  for (const rule of PATTERN_TRANSLATIONS) {
    if (!rule.pattern.test(trimmed)) continue;
    const replaced = trimmed.replace(rule.pattern, rule.replace as never);
    return withOriginalSpacing(replaced, raw);
  }

  return raw;
}

function translateNodeText(node: Text): void {
  const current = node.nodeValue;
  if (!current) return;
  const next = translate(current);
  if (next !== current) {
    node.nodeValue = next;
  }
}

function translateElementAttributes(element: Element): void {
  for (const attribute of ["placeholder", "title", "aria-label"]) {
    const current = element.getAttribute(attribute);
    if (!current) continue;
    const next = translate(current);
    if (next !== current) {
      element.setAttribute(attribute, next);
    }
  }
}

function walkAndTranslate(root: Node): void {
  if (root.nodeType === Node.TEXT_NODE) {
    translateNodeText(root as Text);
    return;
  }

  if (root.nodeType !== Node.ELEMENT_NODE) return;

  const element = root as Element;
  translateElementAttributes(element);

  for (const child of Array.from(element.childNodes)) {
    walkAndTranslate(child);
  }
}

let started = false;

export function initRuRuntimeLocalization(): void {
  if (started) return;
  started = true;

  const root = document.body;
  walkAndTranslate(root);

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === "characterData") {
        translateNodeText(mutation.target as Text);
      }
      if (mutation.type === "attributes" && mutation.target.nodeType === Node.ELEMENT_NODE) {
        translateElementAttributes(mutation.target as Element);
      }
      for (const node of Array.from(mutation.addedNodes)) {
        walkAndTranslate(node);
      }
    }
  });

  observer.observe(root, {
    subtree: true,
    childList: true,
    characterData: true,
    attributes: true,
    attributeFilter: ["placeholder", "title", "aria-label"],
  });
}
