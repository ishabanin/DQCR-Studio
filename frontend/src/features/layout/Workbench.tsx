import { useEditorStore } from "../../app/store/editorStore";
import AdminScreen from "../admin/AdminScreen";
import BuildScreen from "../build/BuildScreen";
import LineageScreen from "../lineage/LineageScreen";
import ModelEditorScreen from "../model/ModelEditorScreen";
import ParametersScreen from "../parameters/ParametersScreen";
import { ProjectInfoScreen } from "../project/ProjectInfoScreen";
import SqlEditorScreen from "../sql/SqlEditorScreen";
import ValidateScreen from "../validate/ValidateScreen";

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

  if (activeTab === "sql") {
    return <SqlEditorScreen />;
  }
  if (activeTab === "project") {
    return <ProjectInfoScreen />;
  }
  if (activeTab === "lineage") {
    return <LineageScreen />;
  }
  if (activeTab === "validate") {
    return <ValidateScreen />;
  }
  if (activeTab === "model") {
    return <ModelEditorScreen />;
  }
  if (activeTab === "parameters") {
    return <ParametersScreen />;
  }
  if (activeTab === "build") {
    return <BuildScreen />;
  }
  if (activeTab === "admin") {
    return <AdminScreen />;
  }

  return (
    <section className="workbench">
      <h1>{tabTitleMap[activeTab]}</h1>
      <p>Текущий срез реализации: layout + навигация по проекту + дерево файлов.</p>
      <p>Открытые файлы: {openFiles.length > 0 ? openFiles.join(", ") : "нет"}</p>
    </section>
  );
}
