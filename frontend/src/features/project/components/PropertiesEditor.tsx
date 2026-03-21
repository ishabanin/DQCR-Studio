import Button from "../../../shared/components/ui/Button";
import Input from "../../../shared/components/ui/Input";

export interface PropertyRow {
  id: string;
  key: string;
  value: string;
}

export function PropertiesEditor({
  items,
  onChange,
}: {
  items: PropertyRow[];
  onChange: (items: PropertyRow[]) => void;
}) {
  const updateItem = (id: string, patch: Partial<PropertyRow>) => {
    onChange(items.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  };

  const removeItem = (id: string) => {
    onChange(items.filter((item) => item.id !== id));
  };

  return (
    <div className="project-properties">
      {items.length === 0 ? <p className="project-muted-copy">No custom properties yet.</p> : null}
      {items.map((item) => (
        <div key={item.id} className="project-property-row">
          <Input
            placeholder="property key"
            value={item.key}
            onChange={(event) => updateItem(item.id, { key: event.target.value })}
          />
          <Input
            placeholder="value"
            value={item.value}
            onChange={(event) => updateItem(item.id, { value: event.target.value })}
          />
          <Button type="button" onClick={() => removeItem(item.id)}>
            Remove
          </Button>
        </div>
      ))}
    </div>
  );
}
