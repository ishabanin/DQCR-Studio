# Frontend Architecture Review (React + TypeScript)

Дата: 2026-03-25  
Область: `frontend/src`  
Примечание: Serena MCP во время ревью была недоступна (`Transport closed`), анализ выполнен прямым проходом по коду.

## Найденные проблемы

### 1) God Component + нарушение границ `shared`

- 📍 Где: `src/shared/components/Sidebar.tsx`
- 🔴 Critical
- 💬 Объяснение проблемы: `Sidebar` одновременно содержит UI-рендер, бизнес-правила навигации, query/mutation к API, состояние resize/expand и диалоги действий. Это God Component и нарушение границ слоя `shared` (shared начинает зависеть от feature-логики и API).
- ✅ Пример исправления с кодом:

```tsx
// features/project-sidebar/ProjectSidebarContainer.tsx
export function ProjectSidebarContainer() {
  const vm = useProjectSidebarViewModel(); // queries, mutations, handlers
  return <ProjectSidebarView {...vm} />;   // чистый UI
}

// shared/components/project-tree/ProjectSidebarView.tsx
export function ProjectSidebarView(props: ProjectSidebarViewProps) {
  return <ProjectTree nodes={props.nodes} onOpen={props.onOpen} />;
}
```

### 2) Нет lazy-loading тяжёлых экранов

- 📍 Где: `src/features/layout/Workbench.tsx`
- 🟡 Major
- 💬 Объяснение проблемы: тяжёлые экраны (`SqlEditorScreen`, `ModelEditorScreen`, `ParametersScreen`) импортируются eagerly. Нет `React.lazy`/`Suspense`, стартовый бандл растёт, TTI ухудшается.
- ✅ Пример исправления с кодом:

```tsx
import { lazy, Suspense } from "react";

const SqlEditorScreen = lazy(() => import("../sql/SqlEditorScreen"));
const ModelEditorScreen = lazy(() => import("../model/ModelEditorScreen"));

export default function Workbench() {
  return (
    <Suspense fallback={<section className="workbench">Loading…</section>}>
      {/* switch by activeTab */}
    </Suspense>
  );
}
```

### 3) N+1 запросы в Hub

- 📍 Где: `src/features/hub/hooks/useProjects.ts`
- 🟡 Major
- 💬 Объяснение проблемы: в `queryFn` идёт `fetchProjects()`, затем N дополнительных запросов `fetchProjectWorkflowStatus(project.id)` (N+1), плюс периодический `refetchInterval`. На большом количестве проектов это перегружает сеть и backend.
- ✅ Пример исправления с кодом:

```ts
const projectsQuery = useQuery({
  queryKey: ["projects"],
  queryFn: async () => {
    const raw = await fetchProjects(); // backend already returns cache_status
    return raw.map(mapProject);
  },
  staleTime: 30_000,
  refetchInterval: 60_000,
});
```

```ts
// Альтернатива: один batch endpoint
// GET /projects/workflow-statuses -> { [projectId]: status }
```

### 4) Частая пересборка глобального keydown-handler

- 📍 Где: `src/features/sql/SqlEditorScreen.tsx`
- 🟡 Major
- 💬 Объяснение проблемы: глобальный keydown-handler пересоздаётся часто из-за длинного dependency array и нестабильных зависимостей. Это лишние subscribe/unsubscribe и риск нестабильности хоткеев.
- ✅ Пример исправления с кодом:

```tsx
const hotkeyStateRef = useRef<HotkeyState>(initialState);
hotkeyStateRef.current = { draft, mode, activeFilePath, quickOpenCandidates, quickOpenIndex };

useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    const s = hotkeyStateRef.current;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s" && s.mode === "source") {
      e.preventDefault();
      saveMutation.mutate(s.draft);
    }
  };
  window.addEventListener("keydown", handler);
  return () => window.removeEventListener("keydown", handler);
}, []);
```

### 5) Нет виртуализации длинных списков

- 📍 Где: `src/features/sql/SqlEditorScreen.tsx`, `src/shared/components/Sidebar.tsx`
- 🟡 Major
- 💬 Объяснение проблемы: quick-open и дерево файлов рендерятся целиком. На больших проектах это даст заметные просадки производительности.
- ✅ Пример исправления с кодом:

```tsx
import { FixedSizeList as List } from "react-window";

<List height={320} itemCount={quickOpenCandidates.length} itemSize={32} width="100%">
  {({ index, style }) => (
    <button style={style} onClick={() => openPathInSql(quickOpenCandidates[index])}>
      {quickOpenCandidates[index]}
    </button>
  )}
</List>
```

### 6) Дублирование source-of-truth в UI store

- 📍 Где: `src/app/store/uiStore.ts`
- 🟢 Minor
- 💬 Объяснение проблемы: одновременно существуют `userRole` и `role`, что повышает риск рассинхронизации.
- ✅ Пример исправления с кодом:

```ts
interface UiStore {
  role: UserRole;
  setRole: (role: UserRole) => void;
}
// убрать userRole и использовать только role
```

### 7) `any` в TS-коде для файлового API

- 📍 Где: `src/features/wizard/ProjectWizardModal.tsx`
- 🟢 Minor
- 💬 Объяснение проблемы: используются `handle: any` и `node: any`, что ломает преимущества strict typing.
- ✅ Пример исправления с кодом:

```ts
type FsHandle = FileSystemDirectoryHandle | FileSystemFileHandle;

async function collectFilesFromDirectoryHandle(
  handle: FileSystemDirectoryHandle
): Promise<{ files: File[]; relativePaths: string[] }> {
  const walk = async (node: FileSystemDirectoryHandle, prefix: string) => { /* ... */ };
  await walk(handle, "");
  return { files, relativePaths };
}
```

## Топ-3 приоритетных правки

1. Разрезать `Sidebar` на container + presentational и убрать feature/API-логику из `shared`.
2. Внедрить lazy-loading экранов в `Workbench`.
3. Убрать N+1 в `useProjects` (batch endpoint или использование `cache_status` без дополнительных запросов).
