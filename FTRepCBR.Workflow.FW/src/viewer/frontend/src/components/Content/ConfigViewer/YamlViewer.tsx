
import yaml from 'js-yaml';

interface YamlViewerProps {
  data: any;
}

export function YamlViewer({ data }: YamlViewerProps) {
  const yamlContent = yaml.dump(data, {
    indent: 2,
    lineWidth: 120,
    noRefs: true,
    sortKeys: false
  });

  return (
    <pre className="yaml-code">{yamlContent}</pre>
  );
}
