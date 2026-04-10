"""Model reference resolution - table macro.

Преобразует _m.<path> в реальное имя таблицы.

Примеры:
    _m.dwh.ClientChr -> "DWH"."CLIENT_CHR"
    _m.RF110.RF110RestTurnReg.seq -> "RF110"."RF110RESTTURNREG_SEQ"

Работает с WorkflowNewModel через MacroEnv.
"""
from typing import Optional, TYPE_CHECKING, List, Dict, Any

from FW.logging_config import get_logger as _get_logger

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.macros.env import BaseMacroEnv
    from FW.models.parameter import ParameterModel

logger = _get_logger("model_ref.table")


def _create_get_entities_param() -> "ParameterModel":
    """Создать параметр get_entities.
    
    Returns:
        ParameterModel с параметром get_entities
    """
    from FW.models.parameter import ParameterModel, ParameterValue
    
    param = ParameterModel(
        name="get_entities",
        domain_type="record",
        description="Таблицы для логических сущностей",
        attributes=[],
        values={
            "all": ParameterValue(type="dynamic", value="")
        },
        generated=True
    )
    
    return param


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
            f"    get_table_name('{entity}') AS table_{entity}"
        )
    return ",\n".join(case_parts)

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
    
    sql = f"""SELECT 
{select_clause}"""
    
    if "all" in param_model.values:
        param_model.values["all"].value = sql
    else:
        param_model.values["all"] = ParameterValue(type="dynamic", value=sql)
    
    logger.debug(f"Updated get_entities SQL with module='{module}', entity='{entity}'")


def resolve_model_ref(
    path: str, 
    tool: Optional[str] = None, 
    context: Optional[str] = None,
    workflow_new: "Optional[WorkflowNewModel]" = None,
    env: "Optional[BaseMacroEnv]" = None,
    obj_type: str = "sql_object",
    obj_key: str = None,
) -> str:
    """Преобразовать _m.<path> в реальное имя таблицы.
    
    При наличии workflow_new и env создаёт параметр get_entities с динамическим SQL
    для получения table_name по entity_name и module_name из md_entity2table.
    
    Args:
        path: Путь после _m. (напр. dwh.ClientChr)
        tool: Целевой tool (oracle, adb, postgresql)
        context: Имя контекста
        workflow_new: Модель workflow_new
        env: Окружение макроса
        obj_type: Тип объекта ("sql_object" или "parameter")
        obj_key: Ключ объекта для которого вызван макрос
        
    Returns:
        Имя таблицы в формате schema.table или ссылка на параметр
    """
    parts = path.split('.')
    
    if len(parts) >= 2 and env is not None and workflow_new is not None:
        return _resolve_entity_ref(path, tool, context, workflow_new, env, obj_type, obj_key)
    
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
    workflow_new: "WorkflowNewModel",
    env: "BaseMacroEnv",
    obj_type: str = "sql_object",
    obj_key: str = None,
) -> str:
    """Обработать ссылку вида _m.<module>.<entity>.
    
    Создаёт/обновляет параметр get_entities и возвращает ссылку на атрибут.
    
    Args:
        path: Путь (напр. dwh.ClientChr)
        tool: Целевой tool
        context: Имя контекста
        workflow_new: WorkflowNewModel
        env: Окружение макроса
        obj_type: Тип объекта ("sql_object" или "parameter")
        obj_key: Ключ объекта для которого вызван макрос
        
    Returns:
        Ссылка на атрибут параметра {{get_entities.table_<entity>}}
    """
    parts = path.split('.')
    if len(parts) < 2:
        raise ValueError(f"Invalid entity reference: {path}")
    
    module = parts[0].lower()
    entity = parts[1].lower()
    attr_name = f"table_{entity}"
    
    prep_param = env.get_parameter("get_entities")
    
    if not prep_param:
        prep_param = _create_get_entities_param()
        env.add_parameter(prep_param)
        logger.info(f"Created get_entities parameter")
    
    source_obj = None
    if obj_type == "sql_object" and obj_key:
        source_obj = workflow_new.sql_objects.get(obj_key)
    elif obj_type == "parameter" and obj_key:
        source_obj = workflow_new.parameters.get(obj_key)
    
    for ctx in workflow_new.contexts.keys():
        if source_obj and ctx in source_obj.config:
            ctx_config = source_obj.config[ctx]
            ctx_tools = ctx_config.get("tools", []) if ctx_config else []
        else:
            ctx_obj = workflow_new.contexts.get(ctx)
            ctx_tools = ctx_obj.tools if ctx_obj and ctx_obj.tools else workflow_new.tools
        
        prep_param.config[ctx] = {"tools": ctx_tools}
        
        for t in ctx_tools:
            if not env.has_step_in_graph("get_entities", ctx, t):
                env.add_step_to_graph("parameter", "get_entities", ctx, t, "param")
    
    existing_attr_names = [a.get('name') for a in prep_param.attributes if isinstance(a, dict)]
    
    if attr_name not in existing_attr_names:
        prep_param.attributes.append({
            'name': attr_name,
            'domain_type': 'sql.identifier'
        })
        
        _update_param_sql(prep_param, module, entity)
        
        actual_context = context if context else "all"
        
        for ctx in workflow_new.contexts.keys():
            if source_obj and ctx in source_obj.config:
                ctx_config = source_obj.config[ctx]
                ctx_tools = ctx_config.get("tools", []) if ctx_config else []
            else:
                ctx_obj = workflow_new.contexts.get(ctx)
                ctx_tools = ctx_obj.tools if ctx_obj and ctx_obj.tools else workflow_new.tools
            
            for t in ctx_tools:
                value = prep_param.values.get("all", "").value if prep_param.values.get("all") else ""
                if t == "oracle":
                   value = value + "\nfrom dual"
                env.update_compiled("parameter", "get_entities", ctx, t, "prepared_sql", value)
                env.update_compiled("parameter", "get_entities", ctx, t, "model_refs", {})
        
        logger.info(f"Added entity '{module}.{entity}' to get_entities, attr: {attr_name}")
    
    return f"{{{{ {attr_name} }}}}"
