"""Materialization: Stage with CalcID."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from FW.models.step import WorkflowStepModel
    from FW.models.workflow import WorkflowModel
    from FW.macros.env import MacroEnv


CALCID_F110 = "RF110.get_base_calc_id()"


def materialization_stage_calcid(
    step: "WorkflowStepModel",
    workflow: "WorkflowModel",
    env: "MacroEnv"
):
    """Materialization: Stage with CalcID.
    
    Creates a temporary stage table filtered by CalcID.
    
    Args:
        step: Workflow шаг с sql_model (может быть None)
        workflow: Workflow модель
        env: Окружение с API для рендеринга (содержит step)
    """
    actual_step = env.step if env.step is not None else step
    if actual_step is not None and actual_step.sql_model is not None:
        sql_model = actual_step.sql_model
    else:
        return
    
    tool = env.tools[0] if env.tools else None
    if not tool:
        return
    
    sql_model.target_table = f"tmp_{sql_model.name}_{{{{calc_id}}}}"
    
    distribution_key = None
    if sql_model.attributes:
        for attr in sql_model.attributes:
            if attr.distribution_key is not None:
                distribution_key = attr.name
                break
    
    render_kwargs = {
        "tool": tool,
        "calcid_f110": CALCID_F110,
        "sql_model": sql_model,
        "distribution_key": distribution_key
    }
    
    rendered = env.render_template(
        "materialization/stage_calcid",
        **render_kwargs
    )
    
    sql_model.rendered_sql[tool] = rendered
