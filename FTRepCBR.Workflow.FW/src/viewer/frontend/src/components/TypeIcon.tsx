import { useIcon } from './Icons';

interface TypeIconProps {
  domainType?: string;
  showLabel?: boolean;
  className?: string;
}

const DOMAIN_TYPE_TO_ICON: Record<string, string> = {
  number: 'type_number',
  string: 'type_string',
  date: 'type_date',
  datetime: 'type_datetime',
  timestamp: 'type_datetime',
  bool: 'type_number',
  boolean: 'type_number',
  record: 'type_sql_expression',
  array: 'type_sql_expression',
  'sql.expression': 'type_sql_expression',
  'sql.condition': 'type_sql_condition',
  'sql.identifier': 'type_sql_condition',
};

export function TypeIcon({ domainType, showLabel = true, className }: TypeIconProps) {
  const iconType = domainType 
    ? (DOMAIN_TYPE_TO_ICON[domainType.toLowerCase()] || 'type_undefined')
    : 'type_undefined';

  const { iconSrc } = useIcon(iconType as any);

  const label = domainType || 'undefined';

  return (
    <span className={`type-icon ${className || ''}`} title={label}>
      {iconSrc ? (
        <img src={iconSrc} alt="" className="type-icon-img" />
      ) : (
        <span className="type-icon-text">?</span>
      )}
      {showLabel && <span className="type-icon_label">{label}</span>}
    </span>
  );
}
