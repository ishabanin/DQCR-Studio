"""HTML report generator for validation results."""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

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
    available_model_groups = report.available_model_groups or []
    available_workflows = report.available_workflows or {}
    all_workflows = []
    for workflows in available_workflows.values():
        all_workflows.extend(workflows)
    all_workflows = sorted(set(all_workflows))
    
    categories = ["general", "sql", "adb", "descriptions", "template"]
    
    model_groups_json = json.dumps(available_model_groups, ensure_ascii=False)
    workflows_json = json.dumps(available_workflows, ensure_ascii=False)
    all_workflows_json = json.dumps(all_workflows, ensure_ascii=False)
    categories_json = json.dumps(categories, ensure_ascii=False)
    
    json_data = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation Report - {report.model_name or 'Summary'}</title>
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
            max-width: 1400px;
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
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .filter-group {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .filter-group label {{
            font-size: 13px;
            font-weight: 500;
            color: #555;
        }}
        
        .filter-select {{
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 4px;
            background: white;
            cursor: pointer;
            font-size: 14px;
            min-width: 150px;
        }}
        
        .filter-select:hover {{
            border-color: #3498db;
        }}
        
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
        
        .issue-meta {{
            font-size: 11px;
            color: #aaa;
            margin-top: 5px;
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
            <strong>Model:</strong> {report.model_name or 'All'} | 
            <strong>Template:</strong> {report.template_name} | 
            <strong>Timestamp:</strong> {report.timestamp}
        </div>
        
        <div class="summary">
            <div class="summary-card total">
                <div class="count" id="totalCount">{report.total_issues}</div>
                <div class="label">Total Issues</div>
            </div>
            <div class="summary-card errors">
                <div class="count" id="errorCount">{report.error_count}</div>
                <div class="label">Errors</div>
            </div>
            <div class="summary-card warnings">
                <div class="count" id="warningCount">{report.warning_count}</div>
                <div class="label">Warnings</div>
            </div>
            <div class="summary-card info">
                <div class="count" id="infoCount">{report.info_count}</div>
                <div class="label">Info</div>
            </div>
        </div>
        
        <div class="filters">
            <div class="filter-group">
                <label>Model Group:</label>
                <select id="modelGroupFilter" class="filter-select">
                    <option value="all">All Model Groups</option>
                    {''.join(f'<option value="{g}">{g}</option>' for g in available_model_groups)}
                </select>
            </div>
            
            <div class="filter-group">
                <label>Workflow:</label>
                <select id="workflowFilter" class="filter-select">
                    <option value="all">All Workflows</option>
                    {''.join(f'<option value="{w}">{w}</option>' for w in all_workflows)}
                </select>
            </div>
            
            <div class="filter-group">
                <label>Category:</label>
                <select id="categoryFilter" class="filter-select">
                    <option value="all">All Categories</option>
                    {''.join(f'<option value="{c}">{c}</option>' for c in categories)}
                </select>
            </div>
            
            <div class="filter-group">
                <label>Level:</label>
                <select id="levelFilter" class="filter-select">
                    <option value="all">All Levels</option>
                    <option value="error">Error</option>
                    <option value="warning">Warning</option>
                    <option value="info">Info</option>
                </select>
            </div>
        </div>
        
        <div class="issues-list" id="issuesList">
            { _render_issues(report.issues + report.template_issues) }
        </div>
        
        <div style="margin-top: 30px;">
            <h3>Raw JSON Data</h3>
            <pre style="background: #f5f7fa; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px; max-height: 400px;">{json_data}</pre>
        </div>
    </div>
    
    <script>
        const availableModelGroups = {model_groups_json};
        const availableWorkflows = {workflows_json};
        const allWorkflows = {all_workflows_json};
        const categories = {categories_json};
        
        const modelGroupFilter = document.getElementById('modelGroupFilter');
        const workflowFilter = document.getElementById('workflowFilter');
        const categoryFilter = document.getElementById('categoryFilter');
        const levelFilter = document.getElementById('levelFilter');
        
        const totalCount = document.getElementById('totalCount');
        const errorCount = document.getElementById('errorCount');
        const warningCount = document.getElementById('warningCount');
        const infoCount = document.getElementById('infoCount');
        
        modelGroupFilter.addEventListener('change', () => {{
            const selectedGroup = modelGroupFilter.value;
            
            workflowFilter.innerHTML = '<option value="all">All Workflows</option>';
            
            if (selectedGroup === 'all') {{
                allWorkflows.forEach(w => {{
                    workflowFilter.innerHTML += `<option value="${{w}}">${{w}}</option>`;
                }});
            }} else {{
                const workflows = availableWorkflows[selectedGroup] || [];
                workflows.forEach(w => {{
                    workflowFilter.innerHTML += `<option value="${{w}}">${{w}}</option>`;
                }});
            }}
            
            filterIssues();
        }});
        
        function filterIssues() {{
            const selectedGroup = modelGroupFilter.value;
            const selectedWorkflow = workflowFilter.value;
            const selectedCategory = categoryFilter.value;
            const selectedLevel = levelFilter.value;
            
            const issues = document.querySelectorAll('.issue');
            let visibleTotal = 0;
            let visibleErrors = 0;
            let visibleWarnings = 0;
            let visibleInfo = 0;
            
            issues.forEach(issue => {{
                const issueGroup = issue.dataset.modelGroup || '';
                const issueWorkflow = issue.dataset.modelName || '';
                const issueCategory = issue.dataset.category || '';
                const issueLevel = issue.dataset.level || '';
                
                const matchGroup = selectedGroup === 'all' || issueGroup === selectedGroup;
                const matchWorkflow = selectedWorkflow === 'all' || issueWorkflow === selectedWorkflow;
                const matchCategory = selectedCategory === 'all' || issueCategory === selectedCategory;
                const matchLevel = selectedLevel === 'all' || issueLevel === selectedLevel;
                
                if (matchGroup && matchWorkflow && matchCategory && matchLevel) {{
                    issue.style.display = 'block';
                    visibleTotal++;
                    if (issueLevel === 'error') visibleErrors++;
                    else if (issueLevel === 'warning') visibleWarnings++;
                    else if (issueLevel === 'info') visibleInfo++;
                }} else {{
                    issue.style.display = 'none';
                }}
            }});
            
            totalCount.textContent = visibleTotal;
            errorCount.textContent = visibleErrors;
            warningCount.textContent = visibleWarnings;
            infoCount.textContent = visibleInfo;
        }}
        
        workflowFilter.addEventListener('change', filterIssues);
        categoryFilter.addEventListener('change', filterIssues);
        levelFilter.addEventListener('change', filterIssues);
        
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
        
        location_html = ""
        if issue.file_path:
            location_html = f'<div class="issue-location">{issue.file_path}</div>'
        elif issue.location:
            location_html = f'<div class="issue-location">{issue.location}</div>'
        
        model_group = issue.model_group or ""
        model_name = issue.model_name or ""
        
        html_parts.append(f"""
        <div class="issue {level_class}" data-level="{level_class}" data-model-group="{model_group}" data-model-name="{model_name}" data-category="{issue.category}">
            <div class="issue-header">
                <span class="issue-level {level_class}">{level_label}</span>
                <span class="issue-rule">{issue.rule}<span class="issue-category">[{issue.category}]</span></span>
            </div>
            <div class="issue-message">{issue.message}</div>
            {location_html}
            <div class="issue-meta">Model: {model_name} | Group: {model_group}</div>
            {f'<div class="toggle-details" onclick="toggleDetails({i})">Show details</div><div class="details" id="details-{i}">{details_json}</div>' if details_json else ''}
        </div>
        """)
    
    return "\n".join(html_parts)


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
