import Prism from 'prismjs';
import 'prismjs/components/prism-sql';

interface TableInfo {
  alias: string;
  is_variable: boolean;
  is_cte: boolean;
  model_ref?: string;
}

function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

export function highlightSql(sqlContent: string, tables?: Record<string, TableInfo>): string {
  if (!sqlContent) return '';
  
  const paramPlaceholders: Array<{ placeholder: string; param: string }> = [];
  let processed = sqlContent.replace(/\{\{(\w+)\}\}/g, (_match, param) => {
    const placeholder = `\x00PARAM${paramPlaceholders.length}\x00`;
    paramPlaceholders.push({ placeholder, param });
    return placeholder;
  });
  
  const tablePlaceholders: Array<{ placeholder: string; table: string }> = [];
  if (tables) {
    Object.keys(tables).forEach(table => {
      const regex = new RegExp(`\\b(${table})\\b`, 'gi');
      processed = processed.replace(regex, (_match) => {
        const placeholder = `\x00TABLE${tablePlaceholders.length}\x00`;
        tablePlaceholders.push({ placeholder, table });
        return placeholder;
      });
    });
  }
  
  let highlighted = Prism.highlight(processed, Prism.languages.sql, 'sql');
  
  tablePlaceholders.forEach(({ placeholder, table }) => {
    highlighted = highlighted.replace(placeholder, `<span class="sql-table" data-table="${escapeHtml(table)}">${escapeHtml(table)}</span>`);
  });
  
  paramPlaceholders.forEach(({ placeholder, param }) => {
    highlighted = highlighted.replace(placeholder, `<span class="sql-param" data-param="${escapeHtml(param)}">{{${escapeHtml(param)}}}</span>`);
  });
  
  return highlighted;
}
