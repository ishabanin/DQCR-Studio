"""Materialization: Parameter."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from FW.models.step import WorkflowStepModel
    from FW.models.workflow import WorkflowModel
    from FW.macros.env import MacroEnv


DOMAIN_TYPE_MAP = {
    'date': 'date',
    'number': 'numeric',
    'numeric': 'numeric',
    'integer': 'integer',
    'int': 'integer',
}


def materialization_param(
    step: "WorkflowStepModel",
    workflow: "WorkflowModel",
    env: "MacroEnv"
):
    """Materialization: Parameter.
    
    Generates SQL for parameter based on its type:
    - dynamic: returns prepared_sql directly (no wrapper)
    - static: renders SQL wrapper (SELECT 'value' FROM DUAL)
    
    Args:
        step: Workflow шаг с param_model (может быть None)
        workflow: Workflow модель
        env: Окружение с API для рендеринга (содержит param_model)
    """
    param_model = env.param_model
    if param_model is None:
        return
    
    tool = env.tools[0] if env.tools else None
    if not tool:
        return
    
    context_name = getattr(param_model, '_current_context', 'all')
    
    if param_model.is_dynamic(context_name):
        prepared = param_model.prepared_sql.get(tool, "")
        param_model.rendered_sql[tool] = prepared
        return
    
    p_domain = param_model.domain_type
    ptype = DOMAIN_TYPE_MAP.get(p_domain, 'text')
    
    render_kwargs = {
        "tool": tool,
        "param_model": param_model,
        "context_name": context_name,
        "ptype": ptype
    }
    
    rendered = env.render_template(
        "materialization/param",
        **render_kwargs
    )
    param_model.rendered_sql[tool] = rendered
