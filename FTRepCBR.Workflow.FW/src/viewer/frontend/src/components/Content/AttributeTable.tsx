import { useCallback } from 'react';
import { highlightSql } from '../../utils/highlightSql';
import { TypeIcon } from '../TypeIcon';

interface TableInfo {
  alias: string;
  is_variable: boolean;
  is_cte: boolean;
  model_ref?: string;
}

interface AttributeItem {
  name: string;
  expression?: string;
  domain_type?: string;
  constraints?: string[];
  required?: boolean;
  distribution_key?: number | null;
  partition_key?: number | null;
}

interface AttributeTableProps {
  attributes: AttributeItem[];
  tables?: Record<string, TableInfo>;
  onParamClick?: (paramName: string) => void;
  onTableClick?: (tableName: string) => void;
}

export function AttributeTable({ attributes, tables, onParamClick, onTableClick }: AttributeTableProps) {
  const handleExpressionClick = useCallback((e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    const paramEl = target.closest('.sql-param') as HTMLElement;
    const tableEl = target.closest('.sql-table') as HTMLElement;
    
    if (paramEl) {
      const paramName = paramEl.getAttribute('data-param');
      if (paramName && onParamClick) {
        onParamClick(paramName);
      }
    }
    if (tableEl) {
      const tableName = tableEl.getAttribute('data-table');
      if (tableName && onTableClick) {
        onTableClick(tableName);
      }
    }
  }, [onParamClick, onTableClick]);

  return (
    <div className="table-container">
      <table className="attr-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Required</th>
            <th>Constraints</th>
            <th>Dist</th>
            <th>Part</th>
            <th>Expression</th>
          </tr>
        </thead>
        <tbody>
          {attributes.map((attr, i) => (
            <tr key={i}>
              <td>{attr.name}</td>
              <td><TypeIcon domainType={attr.domain_type} /></td>
              <td>{attr.required ? '✓' : ''}</td>
              <td>{attr.constraints?.join(', ') || ''}</td>
              <td>{attr.distribution_key !== undefined && attr.distribution_key !== null ? attr.distribution_key : ''}</td>
              <td>{attr.partition_key !== undefined && attr.partition_key !== null ? attr.partition_key : ''}</td>
              <td className="expression-cell" onClick={handleExpressionClick}>
                {attr.expression ? (
                  <code dangerouslySetInnerHTML={{ __html: highlightSql(attr.expression, tables) }} />
                ) : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
