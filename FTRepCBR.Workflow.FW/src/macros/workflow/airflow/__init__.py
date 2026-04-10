"""Airflow workflow generator.

Генерирует Airflow DAG с задачами для каждого SQL шага workflow.

Структура вывода:
    target/airflow/<workflow_name>/
    └── dags/
        └── <workflow_name>_dag.py
"""
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from FW.macros.env import WorkflowMacroEnv
    from FW.models.workflow import WorkflowModel


def generate_workflow(workflow: "WorkflowModel", env: "WorkflowMacroEnv"):
    """Генерирует Airflow DAG.
    
    Args:
        workflow: Модель workflow
        env: Окружение для создания файлов
    """
    env.create_directory("dags")
    
    sql_steps = [s for s in env.get_all_steps() if s.is_sql_step()]
    
    dag_content = env.render_template(
        "dag",
        tool="airflow",
        workflow=workflow,
        steps=sql_steps,
        dag_name=workflow.model_name,
        schedule_interval=None
    )
    
    dag_file = f"dags/{workflow.model_name}_dag.py"
    env.create_file(dag_file, dag_content)
    
    print(f"[Airflow] Generated DAG: {dag_file} ({len(dag_content)} chars)")
    print(f"[Airflow] Total tasks: {len(sql_steps)}")
