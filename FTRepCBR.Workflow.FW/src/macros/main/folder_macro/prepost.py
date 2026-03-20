"""Пример макроса папки с pre/post обработкой.

Создает prehook шаг в начале и post шаг в конце содержимого папки.
"""
from FW.models.step import WorkflowStepModel, StepType


def folder_macro_prepost(step, workflow, env):
    """Макрос папки для добавления pre/post шагов.
    
    Пример использования в model.yml:
    workflow:
      folders:
        001_Load:
          pre:
            - prepost
          post:
            - prepost
    
    Пример использования в template:
    rules:
      folders:
        "*_Load*":
          pre:
            - prepost
          post:
            - prepost
    """
    if not env.folder_steps:
        return
    
    folder_path = env.folder_path
    folder_name = folder_path.replace("/", "_") if folder_path else ""
    
    folder_steps = env.folder_steps
    if not folder_steps:
        return
    
    first_step = folder_steps[0]
    last_step = folder_steps[-1]
    
    existing_pre_step = None
    for s in folder_steps:
        if s.step_scope == "pre":
            existing_pre_step = s
            break
    
    if not existing_pre_step:
        pre_step = WorkflowStepModel(
            step_id=f"pre_{folder_name}" if folder_name else "pre",
            name=f"pre" if not folder_name else f"pre_{folder_name}",
            folder=folder_path or "",
            full_name=f"{folder_path}/pre" if folder_path else "pre",
            step_type=StepType.SQL,
            step_scope="pre",
            sql_model=None,
            param_model=None,
            dependencies=list(first_step.dependencies) if first_step.dependencies else [],
            context="all",
            is_ephemeral=False
        )
        first_step.dependencies = [pre_step.full_name]
        env.add_step(pre_step)
    else:
        first_step.dependencies = [existing_pre_step.full_name]
    
    post_step = WorkflowStepModel(
        step_id=f"post_{folder_name}" if folder_name else "post",
        name=f"post" if not folder_name else f"post_{folder_name}",
        folder=folder_path or "",
        full_name=f"{folder_path}/post" if folder_path else "post",
        step_type=StepType.SQL,
        step_scope="post",
        sql_model=None,
        param_model=None,
        dependencies=[last_step.full_name],
        context="all",
        is_ephemeral=False
    )
    
    env.add_step(post_step)
