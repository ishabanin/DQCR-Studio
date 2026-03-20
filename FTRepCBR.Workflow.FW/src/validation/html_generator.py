"""HTML report generator for validation results."""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from FW.validation.models import ValidationReport, ValidationLevel


def generate_html_report(
    report: ValidationReport,
    output_path: Optional[str] = None
) -> str:
    """Сгенерировать HTML отчёт валидации.
    
    Args:
        report: Отчёт валидации
        output_path: Путь для сохранения HTML (опционально)
        
    Returns:
        HTML код отчёта
    """
    html = _generate_html(report)
    
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding='utf-8')
    
    return html


def _generate_html(report: ValidationReport) -> str:
    """Сгенерировать HTML код."""
    json_data = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation Report - {report.model_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        
        .meta {{
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 14px;
        }}
        
        .summary {{
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        
        .summary-card {{
            flex: 1;
            min-width: 150px;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .summary-card.total {{ background: #ecf0f1; }}
        .summary-card.errors {{ background: #fee; color: #c0392b; }}
        .summary-card.warnings {{ background: #ffc; color: #f39c12; }}
        .summary-card.info {{ background: #e8f4f8; color: #3498db; }}
        
        .summary-card .count {{
            font-size: 36px;
            font-weight: bold;
        }}
        
        .summary-card .label {{
            font-size: 14px;
            text-transform: uppercase;
            margin-top: 5px;
        }}
        
        .filters {{
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            border: 2px solid #ddd;
            border-radius: 4px;
            background: white;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }}
        
        .filter-btn:hover {{
            border-color: #3498db;
        }}
        
        .filter-btn.active {{
            background: #3498db;
            color: white;
            border-color: #3498db;
        }}
        
        .filter-btn.errors {{ border-color: #e74c3c; }}
        .filter-btn.errors.active {{ background: #e74c3c; }}
        
        .filter-btn.warnings {{ border-color: #f39c12; }}
        .filter-btn.warnings.active {{ background: #f39c12; }}
        
        .filter-btn.info {{ border-color: #3498db; }}
        
        .issues-list {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        
        .issue {{
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #ddd;
            background: #fafafa;
        }}
        
        .issue.error {{ border-left-color: #e74c3c; }}
        .issue.warning {{ border-left-color: #f39c12; }}
        .issue.info {{ border-left-color: #3498db; }}
        
        .issue-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        
        .issue-level {{
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .issue-level.error {{ background: #e74c3c; color: white; }}
        .issue-level.warning {{ background: #f39c12; color: white; }}
        .issue-level.info {{ background: #3498db; color: white; }}
        
        .issue-rule {{
            font-size: 12px;
            color: #7f8c8d;
        }}
        
        .issue-message {{
            font-size: 15px;
            margin-bottom: 8px;
        }}
        
        .issue-location {{
            font-size: 13px;
            color: #3498db;
            font-family: monospace;
        }}
        
        .issue-category {{
            font-size: 12px;
            color: #95a5a6;
            margin-left: 10px;
        }}
        
        .details {{
            margin-top: 10px;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            display: none;
        }}
        
        .details.show {{
            display: block;
        }}
        
        .toggle-details {{
            cursor: pointer;
            color: #3498db;
            font-size: 12px;
            margin-top: 5px;
        }}
        
        .empty {{
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
        }}
        
        .json-link {{
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: #2c3e50;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }}
        
        .json-link:hover {{
            background: #34495e;
        }}
        
        .template-issues {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
        }}
        
        .template-issues h2 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Validation Report</h1>
        <div class="meta">
            <strong>Project:</strong> {report.project_name} | 
            <strong>Model:</strong> {report.model_name} | 
            <strong>Template:</strong> {report.template_name} | 
            <strong>Timestamp:</strong> {report.timestamp}
        </div>
        
        <div class="summary">
            <div class="summary-card total">
                <div class="count">{report.total_issues}</div>
                <div class="label">Total Issues</div>
            </div>
            <div class="summary-card errors">
                <div class="count">{report.error_count}</div>
                <div class="label">Errors</div>
            </div>
            <div class="summary-card warnings">
                <div class="count">{report.warning_count}</div>
                <div class="label">Warnings</div>
            </div>
            <div class="summary-card info">
                <div class="count">{report.info_count}</div>
                <div class="label">Info</div>
            </div>
        </div>
        
        <div class="filters">
            <button class="filter-btn active" data-filter="all">All</button>
            <button class="filter-btn errors" data-filter="error">Errors</button>
            <button class="filter-btn warnings" data-filter="warning">Warnings</button>
            <button class="filter-btn info" data-filter="info">Info</button>
        </div>
        
        <div class="issues-list" id="issuesList">
            { _render_issues(report.issues) }
        </div>
        
        { _render_template_issues(report.template_issues) }
        
        <div style="margin-top: 30px;">
            <h3>Raw JSON Data</h3>
            <pre style="background: #f5f7fa; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px;">{json_data}</pre>
        </div>
    </div>
    
    <script>
        const issues = document.querySelectorAll('.issue');
        const buttons = document.querySelectorAll('.filter-btn');
        
        buttons.forEach(btn => {{
            btn.addEventListener('click', () => {{
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                const filter = btn.dataset.filter;
                issues.forEach(issue => {{
                    if (filter === 'all' || issue.dataset.level === filter) {{
                        issue.style.display = 'block';
                    }} else {{
                        issue.style.display = 'none';
                    }}
                }});
            }});
        }});
        
        function toggleDetails(id) {{
            const details = document.getElementById('details-' + id);
            details.classList.toggle('show');
        }}
    </script>
</body>
</html>"""


def _render_issues(issues) -> str:
    """Сгенерировать HTML для списка проблем."""
    if not issues:
        return '<div class="empty">No issues found</div>'
    
    html_parts = []
    for i, issue in enumerate(issues):
        level_class = issue.level.value
        level_label = {
            "error": "ERROR",
            "warning": "WARNING", 
            "info": "INFO"
        }.get(issue.level.value, issue.level.value)
        
        details_json = json.dumps(issue.details, ensure_ascii=False) if issue.details else ""
        
        html_parts.append(f"""
        <div class="issue {level_class}" data-level="{level_class}">
            <div class="issue-header">
                <span class="issue-level {level_class}">{level_label}</span>
                <span class="issue-rule">{issue.rule}<span class="issue-category">[{issue.category}]</span></span>
            </div>
            <div class="issue-message">{issue.message}</div>
            {f'<div class="issue-location">{issue.location}</div>' if issue.location else ''}
            {f'<div class="toggle-details" onclick="toggleDetails({i})">Show details</div><div class="details" id="details-{i}">{details_json}</div>' if details_json else ''}
        </div>
        """)
    
    return "\n".join(html_parts)


def _render_template_issues(template_issues) -> str:
    """Сгенерировать HTML для проблем шаблона."""
    if not template_issues:
        return ""
    
    return f"""
    <div class="template-issues">
        <h2>Template Validation Issues</h2>
        <div class="issues-list">
            { _render_issues(template_issues) }
        </div>
    </div>
    """


def generate_json_report(
    report: ValidationReport,
    output_path: Optional[str] = None
) -> str:
    """Сгенерировать JSON отчёт.
    
    Args:
        report: Отчёт валидации
        output_path: Путь для сохранения JSON (опционально)
        
    Returns:
        JSON код
    """
    json_data = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json_data, encoding='utf-8')
    
    return json_data
