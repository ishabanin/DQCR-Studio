"""Model reference resolution - table macro.

Преобразует _m.<path> в реальное имя таблицы.

Примеры:
    _m.dwh.ClientChr -> "DWH"."CLIENT_CHR"
    _m.RF110.RF110RestTurnReg.seq -> "RF110"."RF110RESTTURNREG_SEQ"

Также поддерживает расширенный режим с доступом к workflow и env:
    def resolve_model_ref(path, tool, context, workflow=None, env=None) -> str:

При наличии workflow и env создаёт параметр get_entities для динамического
получения имён таблиц по логическим сущностям из md_entity2table.
"""
from typing import Optional, TYPE_CHECKING, List, Dict, Any

from FW.logging_config import get_logger as _get_logger

if TYPE_CHECKING:
    from FW.models.workflow import WorkflowModel
    from FW.macros.env import MacroEnv
    from FW.models.step import WorkflowStepModel
    from FW.models.parameter import ParameterModel

logger = _get_logger("model_ref.table")


def _create_get_entities_param_step() -> "WorkflowStepModel":
    """Создать PARAM шаг для get_entities.
    
    Returns:
        WorkflowStepModel с параметром get_entities
    """
    from FW.models.parameter import ParameterModel, ParameterValue
    from FW.models.step import WorkflowStepModel, StepType
    
    param_model = ParameterModel(
        name="get_entities",
        domain_type="record",
        description="Таблицы для логических сущностей",
        attributes=[],
        values={
            "all": ParameterValue(type="dynamic", value="")
        }
    )
    
    step = WorkflowStepModel(
        step_id="get_entities",
        name="get_entities",
        folder="",
        full_name="get_entities",
        step_type=StepType.PARAM,
        step_scope="pre",
        param_model=param_model,
        context="all",
        is_ephemeral=False
    )
    
    return step


def _get_existing_entities(param_model: "ParameterModel") -> List[tuple]:
    """Получить список уже зарегистрированных (module, entity) из атрибутов.
    
    Args:
        param_model: Модель параметра
        
    Returns:
        Список кортежей [(module, entity), ...] в порядке добавления атрибутов
    """
    result: List[tuple] = []
    seen: set = set()
    for attr in param_model.attributes:
        attr_name = attr.get('name', '')
        if attr_name.startswith('table_'):
            parts = attr_name[6:].split('_', 1)
            if len(parts) == 2:
                key = (parts[0], parts[1])
                if key not in seen:
                    seen.add(key)
                    result.append(key)
    return result


def _build_select_clause(entities_list: List[tuple]) -> str:
    """Построить SELECT clause с CASE выражениями.
    
    Args:
        entities_list: Список кортежей [(module, entity), ...] в порядке добавления
        
    Returns:
        SQL для SELECT части
    """
    case_parts = []
    for module, entity in entities_list:
        case_parts.append(
            f"    MAX(CASE WHEN entity_name = '{entity}' AND module_name = '{module}' THEN table_name END) AS table_{module}_{entity}"
        )
    return ",\n".join(case_parts)


def _build_where_clause(entities_list: List[tuple]) -> str:
    """Построить WHERE clause.
    
    Args:
        entities_list: Список кортежей [(module, entity), ...] в порядке добавления
        
    Returns:
        SQL для WHERE части
    """
    all_entities = []
    for module, entity in entities_list:
        all_entities.append(f"(entity_name = '{entity}' AND module_name = '{module}')")
    
    if not all_entities:
        return "WHERE 1=0"
    
    where_parts = " OR ".join(all_entities)
    return f"WHERE {where_parts}"


def _update_param_sql(param_model: "ParameterModel", module: str, entity: str) -> None:
    """Обновить SQL запрос параметра с новой сущностью.
    
    Args:
        param_model: Модель параметра
        module: Имя модуля
        entity: Имя сущности
    """
    from FW.models.parameter import ParameterValue
    
    existing_list = _get_existing_entities(param_model)
    
    entity_key = (module, entity.lower())
    if entity_key not in existing_list:
        existing_list.append(entity_key)
    
    select_clause = _build_select_clause(existing_list)
    where_clause = _build_where_clause(existing_list)
    
    sql = f"""SELECT 
{select_clause}
FROM md_entity2table
{where_clause}"""
    
    if "all" in param_model.values:
        param_model.values["all"].value = sql
    else:
        param_model.values["all"] = ParameterValue(type="dynamic", value=sql)
    
    logger.debug(f"Updated get_entities SQL with module='{module}', entity='{entity}'")


def resolve_model_ref(
    path: str, 
    tool: Optional[str] = None, 
    context: Optional[str] = None,
    workflow: "Optional[WorkflowModel]" = None,
    env: "Optional[MacroEnv]" = None,
    step: "Optional[WorkflowStepModel]" = None
) -> str:
    """Преобразовать _m.<path> в реальное имя таблицы.
    
    При наличии workflow и env создаёт параметр get_entities с динамическим SQL
    для получения table_name по entity_name и module_name из md_entity2table.
    
    Args:
        path: Путь после _m. (напр. dwh.ClientChr)
        tool: Целевой tool (oracle, adb, postgresql)
        context: Имя контекста
        workflow: Модель workflow (опционально)
        env: Окружение макроса (опционально)
        step: Шаг workflow (опционально)
        
    Returns:
        Имя таблицы в формате schema.table или ссылка на параметр
    """
    parts = path.split('.')
    
    if len(parts) >= 2 and env is not None:
        return _resolve_entity_ref(path, tool, context, env, step)
    
    if len(parts) == 1:
        schema = "PUBLIC"
        table = parts[0].upper()
    elif len(parts) == 2:
        schema = parts[0].upper()
        table = parts[1].upper()
    else:
        schema = parts[0].upper()
        table = '_'.join(parts[1:]).upper()
    
    return f'"{schema}"."{table}"'


def _resolve_entity_ref(
    path: str, 
    tool: Optional[str], 
    context: Optional[str],
    env: "MacroEnv",
    step: "Optional[WorkflowStepModel]" = None
) -> str:
    """Обработать ссылку вида _m.<module>.<entity>.
    
    Создаёт/обновляет параметр get_entities и возвращает ссылку на атрибут.
    
    Args:
        path: Путь (напр. dwh.ClientChr)
        tool: Целевой tool
        context: Имя контекста
        env: Окружение макроса
        
    Returns:
        Ссылка на атрибут параметра {{get_entities.table_<module>_<entity>}}
    """
    parts = path.split('.')
    if len(parts) < 2:
        raise ValueError(f"Invalid entity reference: {path}")
    
    module = parts[0].lower()
    entity = parts[1].lower()
    attr_name = f"table_{module}_{entity}"
    
    prep_step = env.get_step_by_name("get_entities")
    
    if not prep_step:
        prep_step = _create_get_entities_param_step()
        env.add_step(prep_step)
        logger.info(f"Created get_entities parameter step")
    
    param_model = prep_step.param_model
    
    existing_attr_names = [a.get('name') for a in param_model.attributes if isinstance(a, dict)]
    
    if attr_name not in existing_attr_names:
        param_model.attributes.append({
            'name': attr_name,
            'type': 'sql.identifier'
        })
        
        _update_param_sql(param_model, module, entity)
        
        actual_context = context if context else "all"
        env.regenerate_param(param_model, actual_context)
        
        logger.info(f"Added entity '{module}.{entity}' to get_entities, attr: {attr_name}")
    
    return f"{{{{ {attr_name} }}}}"
