"""Макрос папки synchIter - создает loop/endLoop шаги для синхронной итерации.

Создает шаг loop (pre) и endLoop (post) для итерации по результатам SQL-запроса.

Пример использования в model.yml:
workflow:
  folders:
    002_LoopFolder:
      pre:
        - synch_iter

При этом в папке parameters должен быть параметр с именем 002_LoopFolder
"""
from pathlib import Path

from FW.models.step import WorkflowStepModel, StepType
from FW.parsing.sql_metadata import SQLMetadataParser


def folder_macro_synch_iter(step, workflow, env):
    """Макрос папки для создания loop/endLoop шагов.
    
    Алгоритм:
    1. Ищет параметр с именем {folder_name} (где folder_name = папка с заменой / на _)
    2. Создает loop шаг с sql_model из source_sql параметра
    3. Создает endLoop шаг со ссылкой на loop шаг
    """
    folder_path = env.folder_path
    folder_name = folder_path.replace("/", "_") if folder_path else ""
    
    param_name = f"{folder_name}"
    
    all_steps = workflow._all_steps if workflow._all_steps else []
    
    param_step = None
    for s in all_steps:
        if s.step_type == StepType.PARAM and s.name == f"param_{param_name}":
            param_step = s
            break
    
    if not param_step or not param_step.param_model:
        return
    
    param_sql = param_step.param_model.source_sql
    if not param_sql:
        return
    
    param_step.enabled = False
    
    parser = SQLMetadataParser()
    metadata = parser.parse(param_sql)
    
    from FW.models.sql_query import SQLQueryModel
    
    folder_contexts = env.folder.contexts if env.folder else ['all']
    context = folder_contexts[0] if folder_contexts and folder_contexts != ['all'] else 'all'
    
    sql_model = SQLQueryModel(
        name=f"loop_{folder_name}",
        path=Path("."),
        source_sql=param_sql,
        metadata=metadata,
        materialization="ephemeral",
        context=context
    )
    
    sql_model.prepared_sql = param_step.param_model.prepared_sql.copy()
    sql_model.rendered_sql = param_step.param_model.rendered_sql.copy()
    
    loop_step = WorkflowStepModel(
        step_id=f"loop_{folder_name}",
        name=f"loop_{folder_name}",
        folder=folder_path or "",
        full_name=f"{folder_path}/loop_{folder_name}" if folder_path else f"loop_{folder_name}",
        step_type=StepType.LOOP,
        step_scope="pre",
        sql_model=sql_model,
        asynch=False,
        enabled=False,
        param_model=None,
        dependencies=[],
        context=context,
        is_ephemeral=False
    )
    env.add_step(loop_step)
    
    end_loop_step = WorkflowStepModel(
        step_id=f"endloop_{folder_name}",
        name=f"endloop_{folder_name}",
        folder=folder_path or "",
        full_name=f"{folder_path}/endloop_{folder_name}" if folder_path else f"endloop_{folder_name}",
        step_type=StepType.END_LOOP,
        step_scope="post",
        sql_model=None,
        asynch=False,
        enabled=False,
        loop_step_ref=loop_step.full_name,
        param_model=None,
        dependencies=[loop_step.full_name],
        context=context,
        is_ephemeral=False
    )
    env.add_step(end_loop_step)
