import CatalogPanelBase from "../catalog/CatalogPanelBase";

interface CatalogPanelProps {
  expandSignal?: number;
}

export default function CatalogPanel({ expandSignal }: CatalogPanelProps) {
  return <CatalogPanelBase mode="hub" expandSignal={expandSignal} />;
}
