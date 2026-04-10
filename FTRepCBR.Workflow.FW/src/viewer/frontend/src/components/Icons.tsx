import { useState, useEffect } from 'react';

export type IconType = 'folder' | 'folder_open' | 'sql' | 'config' | 'parameter' | 'context' | 'model' | 'graph' | 'workflow' | 'contexts' | 'parameters' | 'sqls' | 'models' | 'target' | 'type_number' | 'type_string' | 'type_date' | 'type_datetime' | 'type_sql_expression' | 'type_sql_condition' | 'type_undefined';

interface IconMap {
  [key: string]: string;
}

const ICON_CACHE: IconMap = {};

const DEFAULT_ICONS: Record<IconType, string> = {
  folder: '📁',
  folder_open: '📂',
  sql: '📄',
  config: '⚙️',
  parameter: '📋',
  context: '🎯',
  model: '📦',
  graph: '📊',
  workflow: '⚡',
  contexts: '🎯',
  parameters: '📋',
  sqls: '📄',
  models: '📦',
  target: '🎯',
  type_number: '🔢',
  type_string: '🔤',
  type_date: '📅',
  type_datetime: '⏰',
  type_sql_expression: '🔣',
  type_sql_condition: '🔍',
  type_undefined: '❓',
};

export function getDefaultIcon(type: IconType): string {
  return DEFAULT_ICONS[type] || '📁';
}

export function getIconFileName(type: IconType, name?: string): string {
  if (name) {
    return `/icons/${type}_${name}.svg`;
  }
  return `/icons/${type}.svg`;
}

interface UseIconResult {
  icon: string;
  isLoading: boolean;
  iconSrc: string | null;
}

export function useIcon(type: IconType, name?: string): UseIconResult {
  const [icon, setIcon] = useState<string>(getDefaultIcon(type));
  const [isLoading, setIsLoading] = useState(false);
  const [iconSrc, setIconSrc] = useState<string | null>(null);

  useEffect(() => {
    const cacheKey = `${type}_${name || 'default'}`;
    
    if (ICON_CACHE[cacheKey]) {
      setIcon(ICON_CACHE[cacheKey]);
      return;
    }

    const fileName = getIconFileName(type, name);
    
    setIsLoading(true);
    
    const img = new Image();
    img.onload = () => {
      ICON_CACHE[cacheKey] = fileName;
      setIconSrc(fileName);
      setIsLoading(false);
    };
    img.onerror = () => {
      ICON_CACHE[cacheKey] = getDefaultIcon(type);
      setIconSrc(null);
      setIsLoading(false);
    };
    img.src = fileName;
  }, [type, name]);

  return { icon, isLoading, iconSrc };
}

export function Icon({ type, name, className }: { type: IconType; name?: string; className?: string }) {
  const { icon, iconSrc } = useIcon(type, name);

  if (iconSrc) {
    return <img src={iconSrc} alt="" className={`icon-img ${className || ''}`} />;
  }

  return <span className={`icon-emoji ${className || ''}`}>{icon}</span>;
}
