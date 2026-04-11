import { Suspense, lazy } from "react";
import { useEditorStore } from "../../app/store/editorStore";
import Badge from "../../shared/components/ui/Badge";

const AdminScreen = lazy(() => import("../admin/AdminScreen"));
const BuildScreen = lazy(() => import("../build/BuildScreen"));
const LineageScreen = lazy(() => import("../lineage/LineageScreen"));
const ModelEditorScreen = lazy(() => import("../model/ModelEditorScreen"));
const ParametersScreen = lazy(() => import("../parameters/ParametersScreen"));
const ProjectInfoScreen = lazy(() =>
  import("../project/ProjectInfoScreen").then((module) => ({ default: module.ProjectInfoScreen })),
);
const SqlEditorScreen = lazy(() => import("../sql/SqlEditorScreen"));
const ValidateScreen = lazy(() => import("../validate/ValidateScreen"));

const tabTitleMap: Record<string, string> = {
  project: "Информация о проекте",
  lineage: "Линейность",
  model: "Редактор модели",
  sql: "Редактор SQL",
  validate: "Проверка",
  parameters: "Параметры",
  build: "Сборка",
  admin: "Администрирование",
};

export default function Workbench() {
  const activeTab = useEditorStore((state) => state.activeTab);
  const openFiles = useEditorStore((state) => state.openFiles);

  let screen: JSX.Element | null = null;

  if (activeTab === "sql") {
    screen = <SqlEditorScreen />;
  } else if (activeTab === "project") {
    screen = <ProjectInfoScreen />;
  } else if (activeTab === "lineage") {
    screen = <LineageScreen />;
  } else if (activeTab === "validate") {
    screen = <ValidateScreen />;
  } else if (activeTab === "model") {
    screen = <ModelEditorScreen />;
  } else if (activeTab === "parameters") {
    screen = <ParametersScreen />;
  } else if (activeTab === "build") {
    screen = <BuildScreen />;
  } else if (activeTab === "admin") {
    screen = <AdminScreen />;
  }

  const title = tabTitleMap[activeTab] ?? "Редактор";

  return (
    <Suspense
      fallback={
        <section className="workbench-shell">
          <header className="workbench-headline">
            <div className="workbench-breadcrumb">
              <span>Workspace</span>
              <span>/</span>
              <span className="workbench-breadcrumb-current">Loading</span>
            </div>
            <h1>Загрузка…</h1>
          </header>
          <div className="workbench">
            <p>Подготавливаем раздел редактора.</p>
          </div>
        </section>
      }
    >
      <section className="workbench-shell">
        <header className="workbench-headline">
          <div className="workbench-breadcrumb">
            <span>Workspace</span>
            <span>/</span>
            <span>Editor</span>
            <span>/</span>
            <span className="workbench-breadcrumb-current">{title}</span>
          </div>
          <div className="workbench-headline-row">
            <h1>{title}</h1>
            <Badge variant="secondary">Open files: {openFiles.length}</Badge>
          </div>
        </header>

        {screen ?? (
          <section className="workbench">
            <p>Текущий срез реализации: layout + навигация по проекту + дерево файлов.</p>
            <p>Открытые файлы: {openFiles.length > 0 ? openFiles.join(", ") : "нет"}</p>
          </section>
        )}
      </section>
    </Suspense>
  );
}
