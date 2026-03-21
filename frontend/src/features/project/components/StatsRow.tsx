export function StatsRow({
  models,
  totalFolders,
  totalSqlFiles,
  totalContexts,
}: {
  models: number;
  totalFolders: number;
  totalSqlFiles: number;
  totalContexts: number;
}) {
  const stats = [
    { value: models, label: "Models" },
    { value: totalFolders, label: "SQL folders" },
    { value: totalSqlFiles, label: "SQL files" },
    { value: totalContexts, label: "Contexts" },
  ];

  return (
    <>
      {stats.map((item) => (
        <div key={item.label} className="pi-stat-card">
          <div className="pi-stat-n">{item.value}</div>
          <div className="pi-stat-l">{item.label}</div>
        </div>
      ))}
    </>
  );
}
