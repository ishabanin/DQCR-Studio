"""DQCR workflow template - default."""

from xml.etree.ElementTree import Element as ET_Element, SubElement as ET_SubElement
from FW.models.workflow_new import WorkflowNewModel


def generate_workflow(workflow: WorkflowNewModel, env):
    """Генерировать DQCR XML документы."""
    repsysname = workflow.project.project_properties.get("repsysname").get("value")
    model_name = workflow.model_name
    model_folder = f"{model_name}"

    files_info = []
    files_generated = 0

    for context in workflow.graph:
        for tool in workflow.graph[context]:
            steps = workflow.graph[context][tool]["steps"]
            xml_content = _generate_xml_doc(workflow, steps, tool, context, env)

            filename = f"{model_folder}/{workflow.model_name}_{context}_{tool}.xml"
            env.create_file(filename, xml_content, 'cp1251')

            files_info.append({"context": context, "tool": tool, "filename": filename})

            files_generated += 1
            print(
                f"[DQCR] Generated: {filename} ({len(workflow.graph[context][tool]['steps'])} steps)"
            )

    if files_info:
        main_xml = _generate_main_xml_doc(workflow, files_info)
        main_filename = f"{workflow.model_name}.xml"
        env.create_file(main_filename, main_xml, 'cp1251')

        files_info.append(
            {"context": "main", "tool": "main", "filename": main_filename}
        )

        files_generated += 1
        print(
            f"[DQCR] Generated: {main_filename} (includes {len(files_info) - 1} files)"
        )

    if files_generated == 0:
        print("[DQCR] Warning: No files generated")
    else:
        print(f"[DQCR] Total files: {files_generated}")


def _get_rendered_sql(workflow, step_data, tool):
    """Получить rendered_sql для шага из compiled."""
    object_id = step_data.get("object_id", "")
    step_type = step_data.get("step_type", "")
    step_context = step_data.get("context", "default")

    rendered = None
    if step_type == "sql":
        sql_objects = getattr(workflow, "sql_objects", {})
        sql_obj = sql_objects.get(object_id)
        if sql_obj:
            compiled = getattr(sql_obj, "compiled", {})
            ctx_data = compiled.get(step_context)
            if not ctx_data:
                ctx_data = compiled.get("default", {})
            if ctx_data:
                tool_data = ctx_data.get(tool)
                if tool_data and isinstance(tool_data, dict):
                    rendered = tool_data.get("rendered_sql")

    elif step_type == "param":
        parameters = getattr(workflow, "parameters", {})
        param = parameters.get(object_id)
        if param:
            compiled = getattr(param, "compiled", {})
            ctx_data = compiled.get(step_context)
            if not ctx_data:
                ctx_data = compiled.get("default", {})
            if ctx_data:
                tool_data = ctx_data.get(tool)
                if tool_data and isinstance(tool_data, dict):
                    rendered = tool_data.get("rendered_sql")
    if rendered:
        rendered = _apply_dqcr_param_syntax(workflow, rendered, tool)
    return rendered


def _get_param_attributes(workflow, step_data):
    """Получить атрибуты параметра для OUT property."""
    object_id = step_data.get("object_id", "")
    parameters = getattr(workflow, "parameters", {})
    param = parameters.get(object_id)

    if param:
        attrs = getattr(param, "attributes", None)
        if attrs and isinstance(attrs, list):
            return [a.get("name", "") for a in attrs if a.get("name")]
        name = getattr(param, "name", None)
        if name:
            return [name]
    return None


def _step_has_sql_for_tool(workflow, step, tool):
    """Проверить есть ли SQL для данного tool."""
    return _get_rendered_sql(workflow, step, tool) is not None


def _is_param_type(step_data):
    """Проверить является ли step_type PARAM."""
    step_type = step_data.get("step_type", "")
    return step_type == "param"


def _generate_xml_doc(workflow: WorkflowNewModel, steps, tool, context, env):
    """Сгенерировать XML для конкретного tool и context."""
    doc = ET_Element("doc")

    steps = _get_sorded_steps(workflow.graph[context][tool]["edges"], steps)

    _add_params_section(doc, workflow, tool=tool, context=context)

    _add_flag_params(doc, workflow, steps, tool, context)

    content = ET_SubElement(doc, "content")

    _add_includes(content)

    _add_sys_info_call(content)

    regular_object_names = []
    result_sql = None

    for step in steps:
        step_scope = step.get("step_scope", "")
        if step_scope == "flag":
            continue

        step_context = step.get("context", "all")
        if step_context != context:
            continue

        rendered_sql = _get_rendered_sql(workflow, step, tool)
        if not rendered_sql:
            continue

        step_type = step.get("step_type", "")
        object_id = step.get("object_id", "")

        materialized = _get_step_materialization(workflow, step)

        if step_type == "sql":
            if "/result/" in object_id and materialized == "insert_qc":
                result_sql = rendered_sql
                continue

            sql_obj = workflow.sql_objects[step["object_id"]]
            obj = ET_SubElement(content, "object")
            obj.set("type", "SQL")
            obj_name = (
                step["object_id"].split("/")[-1]
                if "/" in step["object_id"]
                else step["object_id"]
            ).replace(".", "_")
            obj.set("name", obj_name)
            regular_object_names.append(obj_name)

            desc_prop = ET_SubElement(obj, "property")
            desc_prop.set("name", "Description")

            desc = getattr(sql_obj, "description", None) if sql_obj else None
            if desc:
                desc_prop.text = _wrap_cdata(desc)
            else:
                desc_prop.text = _wrap_cdata(f"Step: {step['object_id']}")

            sql_prop = ET_SubElement(obj, "property")
            sql_prop.set("name", "SQL")
            sql_prop.text = _wrap_cdata(_format_sql_for_xml(rendered_sql))

        elif step_type == "param":
            obj = ET_SubElement(content, "object")
            obj.set("type", "SQL")
            obj.set("name", step["object_id"])

            desc_prop = ET_SubElement(obj, "property")
            desc_prop.set("name", "Description")

            parameters = getattr(workflow, "parameters", {})
            obj_id = step.get("object_id", "")
            param = parameters.get(obj_id)
            desc = getattr(param, "description", None) if param else None
            if desc:
                desc_prop.text = _wrap_cdata(desc)
            else:
                desc_prop.text = _wrap_cdata(f"Param: {step['object_id']}")

            sql_prop = ET_SubElement(obj, "property")
            sql_prop.set("name", "SQL")
            sql_prop.text = _wrap_cdata(_format_sql_for_xml(rendered_sql))

            out_attrs = _get_param_attributes(workflow, step)
            if out_attrs:
                out_prop = ET_SubElement(obj, "property")
                out_prop.set("name", "OUT")
                out_prop.text = _wrap_cdata(";".join(out_attrs))
            regular_object_names.append(step["object_id"])            

    _add_objects_call(content, regular_object_names, "EXISTS_RESULT;FULL")

    if result_sql:
        _add_create_qc_table_call(content, workflow, result_sql, tool)

    _add_qc_result_call(content)

    _add_export_control_object(content, workflow, tool)

    _add_export_call(content)

    _add_export_err_object(content)

    _add_err_call(content)

    result = "<?xml version='1.0' encoding='windows-1251'?>\n"
    result += _element_to_string(doc)

    return result


def _add_params_section(doc, workflow, tool="", context=""):
    """Добавить секцию params с параметрами workflow."""
    params = ET_SubElement(doc, "params")

    target_table = getattr(workflow, "target_table", None)
    title = (
        target_table.name
        if target_table
        else getattr(workflow, "model_name", "workflow")
    )

    title_param = ET_SubElement(params, "param")
    title_param.set("name", "Title")
    title_param.text = _wrap_cdata(title)

    desc_param = ET_SubElement(params, "param")
    desc_param.set("name", "Description")
    description = (
        getattr(workflow, "description", "")
        or f"DQCR workflow: {getattr(workflow, 'model_name', 'workflow')}"
    )

    if tool or context:
        suffix_parts = []
        if context:
            suffix_parts.append(f"для контекста {context}")
        if tool:
            suffix_parts.append(f"для tool {tool}")
        desc_param.text = _wrap_cdata(f"{description} ({', '.join(suffix_parts)})")
    else:
        desc_param.text = _wrap_cdata(description)


def _get_sorded_steps(edges, steps):
    sorted_steps = []
    current_step_keys = ["START"]
    while True:
        next_step_keys = []
        for e in edges:
            if e["from"] in current_step_keys and e["to"] != "FINISH":
                sorted_steps.append(steps[e["to"]])
                next_step_keys.append(e["to"])
        if len(next_step_keys) == 0:
            break
        current_step_keys = next_step_keys
    return sorted_steps


def _add_flag_params(doc, workflow: WorkflowNewModel, steps, tool, context):
    """Добавить параметры FlagSQL для флагов."""
    flag_steps = [
        s
        for s in steps
        if s.get("step_scope") == "flag"
        and _is_param_type(s)
        and s.get("context")
        and _step_has_sql_for_tool(workflow, s, tool)
    ]

    params = doc.find("params")
    if params is None:
        params = ET_SubElement(doc, "params")
    # special flags for dqcr
    # EXISTS_RESULT
    flag_sql = ET_SubElement(params, "param")
    flag_sql.set("name", "FlagSQL")
    sql_text = f"""
          select case when exists (
                                   select 1
                                     from DWR_tClcCalculationInfo clc
                                    where clc.branchid in (
                                                           select id from dwr_tCBRBranchList c
                                                            where c.reportdate = to_date(':DATE_END:','yyyymmdd')
                                                              and c.ParentBranchListID like '%,:BRANCH_ID:,%'
                                                          )
                                      and clc.DateBegin = to_date(':DATE_BEGIN:','yyyymmdd')
                                      and clc.DateEnd   = to_date(':DATE_END:','yyyymmdd')
                                      and clc.RepSysName = '{workflow.project.project_properties["repsysname"]["value"]}'
                                  )
                     then 'EXISTS_RESULT'
                     else 'NOT_EXISTS_RESULT'
                 end
          {"from dual" if tool == "oralce" else ""}              
""" + ("from dual" if tool == "oralce" else "")
    flag_sql.text = _wrap_cdata(_format_sql_for_xml(sql_text))

    # MODE
    flag_sql = ET_SubElement(params, "param")
    flag_sql.set("name", "FlagSQL")
    sql_text = f"select 'FULL' {'from dual' if tool == 'oracle' else ''}where ':MODE:' = 'FULL' or ':MODE:' = 'CHECK' or ':MODE:' = ':'||'MODE'||':'"
    flag_sql.text = _wrap_cdata(_format_sql_for_xml(sql_text))

    # EXPORT
    flag_sql = ET_SubElement(params, "param")
    flag_sql.set("name", "FlagSQL")
    sql_text = f"select 'EXPORT' {'from dual' if tool == 'oracle' else ''}where ':MODE:' = 'EXPORT' or ':MODE:' = 'FULL' or ':MODE:' = ':'||'MODE'||':'"
    flag_sql.text = _wrap_cdata(_format_sql_for_xml(sql_text))

    if not flag_steps:
        return

    for step in flag_steps:
        rendered_sql = _get_rendered_sql(workflow, step, tool)
        if not rendered_sql:
            continue

        step_key = step.get("_key", "")
        obj_id = step.get("object_id", step_key)

        sql_objects = getattr(workflow, "sql_objects", {})
        parameters = getattr(workflow, "parameters", {})

        desc = None
        if obj_id in parameters:
            param = parameters.get(obj_id)
            desc = getattr(param, "description", None)
        elif obj_id in sql_objects:
            sql_obj = sql_objects.get(obj_id)
            desc = getattr(sql_obj, "description", None)

        flag_sql = ET_SubElement(params, "param")
        flag_sql.set("name", "FlagSQL")

        if desc:
            escaped_desc = desc.replace("/*", "\\*").replace("*/", "*\\")
            comment = f"/* {escaped_desc} */\n"
            flag_sql.text = _wrap_cdata(comment + _format_sql_for_xml(rendered_sql))
        else:
            flag_sql.text = _wrap_cdata(_format_sql_for_xml(rendered_sql))


def _get_step_materialization(workflow, step):
    """Получить materialization для шага из config."""
    object_id = step.get("object_id", "")
    step_type = step.get("step_type", "")

    if step_type != "sql":
        return None

    sql_objects = getattr(workflow, "sql_objects", {})
    sql_obj = sql_objects.get(object_id)
    if not sql_obj:
        return None

    config = getattr(sql_obj, "config", {})
    if not config:
        return None

    ctx_data = config.get("default", {})
    if not ctx_data:
        return None

    materialized = ctx_data.get("materialized")
    if materialized:
        if hasattr(materialized, "value"):
            return materialized.value
        return materialized

    materialization = ctx_data.get("materialization")
    if materialization:
        if hasattr(materialization, "value"):
            return materialization.value
        return materialization

    return None


def _get_target_table_attributes(workflow):
    """Получить все атрибуты target_table."""
    target_table = getattr(workflow, "target_table", None)
    if not target_table:
        return []
    return getattr(target_table, "attributes", [])


def _get_distribute_key_attributes(workflow):
    """Получить атрибуты с distribution_key из target_table, отсортированные."""
    attrs = _get_target_table_attributes(workflow)
    dist_attrs = [a for a in attrs if getattr(a, "distribution_key", None) is not None]
    dist_attrs.sort(key=lambda x: getattr(x, "distribution_key", 0))
    return [a.name for a in dist_attrs]


def _map_domain_type_to_column_type(domain_type):
    """Маппинг domain_type в columnType для EXPORT_EXCEL."""
    if not domain_type:
        return "string"
    dt = domain_type.lower()
    if dt in ("number", "integer", "amount"):
        return "double"
    if dt == "date":
        return "date"
    return "text"


def _map_domain_type_to_column_style(domain_type):
    """Маппинг domain_type в columnStyle для EXPORT_EXCEL."""
    if not domain_type:
        return "usual"
    dt = domain_type.lower()
    if dt in ("number", "integer"):
        return "Integer"
    if dt == "amount":
        return "usual_sum"
    return "usual"


def _add_includes(content):
    """Добавить include для RULE_LIB и LIB_CBR_SQL."""
    include = ET_SubElement(content, "include")
    include.set("name", "RULE_LIB")
    include.set("src", "lib.xml")
    include.set("exec", "OFF")

    include = ET_SubElement(content, "include")
    include.set("name", "LIB_CBR_SQL")
    include.set("src", "../forms/Lib/lib_cbr_sql.xml")
    include.set("exec", "OFF")


def _add_sys_info_call(content):
    """Добавить CALL_SYS_INFO (MultiFunc)."""
    call = ET_SubElement(content, "call")
    call.set("type", "MultiFunc")
    call.set("name", "CALL_SYS_INFO")
    call.set("value", "")

    step = ET_SubElement(call, "step")
    step.text = "RULE_LIB.GET_SYS_INFO"

    step = ET_SubElement(call, "step")
    step.text = "RULE_LIB.SQL_GET_RULE_SYSNAME"


def _add_objects_call(content, object_names, callif):
    """Добавить call для объектов (все шаги кроме result с insert_qc)."""
    if not object_names:
        return

    call = ET_SubElement(content, "call")
    call.set("type", "MultiFunc")
    call.set("name", "EXEC_NON_RESULT")
    call.set("value", "")
    call.set("callif", callif)

    for obj_name in object_names:
        step = ET_SubElement(call, "step")
        step.text = obj_name


def _add_create_qc_table_call(content, workflow, result_sql, tool):
    """Добавить CALL_CREATE_QCTABLE (MultiParam)."""
    import re

    tab_name = "DWR_t:RULE_SYSNAME:_:CALC_ID:"
    dist_attrs = _get_distribute_key_attributes(workflow)
    dist_str = ";".join(dist_attrs) if dist_attrs else ""
    
    step_text = f";TAB_NAME={tab_name};TAB_ATTRS={result_sql};TAB_DSTR={dist_str}"

    call = ET_SubElement(content, "call")
    call.set("type", "MultiParam")
    call.set("name", "CALL_CREATE_QCTABLE")
    call.set("value", "LIB_FRM_SQL.SQL_CREATE_STG_TABLE")
    call.set("exec", "ON")
    call.set("callif", "EXISTS_RESULT;FULL")

    step = ET_SubElement(call, "step")
    step.text = _wrap_cdata(step_text)


def _extract_select_columns(sql: str) -> list:
    """Извлечь имена колонок из первого SELECT запроса (внешнего)."""
    import re

    if not sql:
        return []

    sql_upper = sql.strip().upper()

    select_match = re.match(r"SELECT\s+(.+?)$", sql_upper, re.DOTALL | re.IGNORECASE)
    if not select_match:
        return []

    select_part = select_match.group(1).strip()

    depth = 0
    col_parts = []
    current_col = ""
    for char in select_part:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            col_parts.append(current_col.strip())
            current_col = ""
            continue
        current_col += char
    if current_col.strip():
        col_parts.append(current_col.strip())

    columns = []
    for col in col_parts:
        if not col:
            continue

        col = re.sub(r"\s+as\s+\w+$", "", col, flags=re.IGNORECASE)
        col = col.strip()

        if "*" in col:
            continue

        if col.upper().startswith("CASE"):
            continue

        parts = col.split()
        if parts:
            columns.append(parts[-1])

    return columns


def _add_qc_result_call(content):
    """Добавить CALL_QCRESULT (MultiFunc)."""
    call = ET_SubElement(content, "call")
    call.set("type", "MultiFunc")
    call.set("name", "CALL_QCRESULT")
    call.set("value", "")
    call.set("callif", "EXISTS_RESULT;FULL")

    step = ET_SubElement(call, "step")
    step.text = "RULE_LIB.INSERT_QCRESULT"


def _add_export_control_object(content, workflow, tool):
    """Добавить EXPORT_CONTROL (EXPORT_EXCEL object)."""
    target_table = getattr(workflow, "target_table", None)
    if not target_table:
        return

    attrs = getattr(target_table, "attributes", [])

    obj = ET_SubElement(content, "object")
    obj.set("type", "EXPORT_EXCEL")
    obj.set("name", "EXPORT_CONTROL")

    desc_prop = ET_SubElement(obj, "property")
    desc_prop.set("name", "Description")
    desc_prop.text = _wrap_cdata("Экспорт данных")

    table_name = "DWR_t:RULE_SYSNAME:_:CALC_ID:"

    col_list = []
    sorded_attrs = sorted(attrs, key=lambda attr: (attr.order_num is None, attr.order_num if attr.order_num is not None else 0))
    for attr in sorded_attrs:
        if getattr(attr,"visible",True):
           attr_name = getattr(attr, "name", "")
           if attr_name:
              col_list.append(attr_name)
    cols_str = ", ".join(col_list)

    if tool == "oracle":
        sql_text = f"select {cols_str} from {table_name} where IsError = 1 and rownum <= :ROWNUM:"
    else:
        sql_text = (
            f"select {cols_str} from {table_name} where IsError = 1 limit :ROWNUM:"
        )

    sql_prop = ET_SubElement(obj, "property")
    sql_prop.set("name", "SQL")
    sql_prop.text = _wrap_cdata(_format_sql_for_xml(sql_text))

    params_prop = ET_SubElement(obj, "property")
    params_prop.set("name", "params")

    params_el = ET_SubElement(params_prop, "fileName")
    params_el.text = _wrap_cdata(f"{workflow.model_name}.xlsx")

    params_el = ET_SubElement(params_prop, "exportType")
    params_el.text = "plain"

    params_el = ET_SubElement(params_prop, "streamMode")
    params_el.text = "YES"

    params_el = ET_SubElement(params_prop, "sheetName")
    params_el.text = "Контроль"

    params_el = ET_SubElement(params_prop, "cleanFile")
    params_el.text = "YES"

    params_el = ET_SubElement(params_prop, "printTitle")
    params_el.text = "YES"

    params_el = ET_SubElement(params_prop, "startRow")
    params_el.text = "0"

    params_el = ET_SubElement(params_prop, "startColumn")
    params_el.text = "0"

    params_el = ET_SubElement(params_prop, "stylesPattern")
    params_el.text = "stylesPattern/styles.xlsx"

    col_descriptions = ET_SubElement(params_prop, "column-descriptions")

    for attr in sorded_attrs:
        attr_name = getattr(attr, "name", "")
        if not attr_name:
            continue

        domain_type = getattr(attr, "domain_type", None)
        column_type = _map_domain_type_to_column_type(domain_type)
        column_style = _map_domain_type_to_column_style(domain_type)

        attr_desc = getattr(attr, "description", "") or ""

        desc = ET_SubElement(col_descriptions, "description")
        desc.set("columnName", attr_name)
        desc.set("columnType", column_type)
        desc.set("columnStyle", column_style)
        desc.set("title", attr_desc)


def _add_export_call(content):
    """Добавить CALL_EXPORT (MultiFunc)."""
    call = ET_SubElement(content, "call")
    call.set("type", "MultiFunc")
    call.set("name", "CALL_EXPORT")
    call.set("value", "")
    call.set("callif", "EXISTS_RESULT;EXPORT")

    step = ET_SubElement(call, "step")
    step.text = "EXPORT_CONTROL"


def _add_export_err_object(content):
    """Добавить Export_Err (EXPORT_EXCEL object) для NOT_EXISTS_RESULT."""
    obj = ET_SubElement(content, "object")
    obj.set("type", "EXPORT_EXCEL")
    obj.set("name", "Export_Err")

    desc_prop = ET_SubElement(obj, "property")
    desc_prop.set("name", "Description")
    desc_prop.text = _wrap_cdata("Экспорт данных об ошибке")

    sql_text = (
        "select 'Перед выполнением правила необходимо рассчитать Форму 0409704' as err"
    )

    sql_prop = ET_SubElement(obj, "property")
    sql_prop.set("name", "SQL")
    sql_prop.text = _wrap_cdata(_format_sql_for_xml(sql_text))

    params_prop = ET_SubElement(obj, "property")
    params_prop.set("name", "params")

    params_el = ET_SubElement(params_prop, "fileName")
    params_el.text = _wrap_cdata("QCRF704CheckLnCat.xlsx")

    params_el = ET_SubElement(params_prop, "exportType")
    params_el.text = "plain"

    params_el = ET_SubElement(params_prop, "streamMode")
    params_el.text = "YES"

    params_el = ET_SubElement(params_prop, "sheetName")
    params_el.text = "Контроль"

    params_el = ET_SubElement(params_prop, "cleanFile")
    params_el.text = "YES"

    params_el = ET_SubElement(params_prop, "printTitle")
    params_el.text = "NO"

    params_el = ET_SubElement(params_prop, "startRow")
    params_el.text = "0"

    params_el = ET_SubElement(params_prop, "startColumn")
    params_el.text = "0"

    col_descriptions = ET_SubElement(params_prop, "column-descriptions")

    desc = ET_SubElement(col_descriptions, "description")
    desc.set("columnName", "err")
    desc.set("columnType", "string")
    desc.set("columnStyle", "usual")


def _add_err_call(content):
    """Добавить CALL_ERR (MultiFunc) для NOT_EXISTS_RESULT."""
    call = ET_SubElement(content, "call")
    call.set("type", "MultiFunc")
    call.set("name", "CALL_ERR")
    call.set("value", "")
    call.set("callif", "NOT_EXISTS_RESULT")

    step = ET_SubElement(call, "step")
    step.text = "Export_Err"

    step = ET_SubElement(call, "step")
    step.text = "RULE_LIB.INSERT_QCRESULT_ERROR"


def _add_call(doc, workflow: WorkflowNewModel, steps, tool, context):
    """Добавить call со всеми step внутри."""
    pass


def _wrap_cdata(text: str) -> str:
    """Обернуть текст в CDATA."""
    if not text:
        return ""
    return f"<![CDATA[{text}]]>"


def _format_sql_for_xml(sql_text: str) -> str:
    """Отформатировать SQL для красивого вывода в XML с отступами."""
    if not sql_text:
        return ""
    lines = sql_text.split("\n")
    indent = " " * 16
    formatted_lines = [indent + line for line in lines]
    return "\n" + "\n".join(formatted_lines) + "\n"


def _element_to_string(elem, indent: int = 0) -> str:
    """Преобразовать Element в XML строку."""
    prefix = "  " * indent

    children = list(elem)
    if children:
        result = f"{prefix}<{elem.tag}"
        for attr_key, attr_val in elem.attrib.items():
            result += f' {attr_key}="{attr_val}"'
        result += ">\n"
        for child in children:
            result += _element_to_string(child, indent + 1)
        result += f"{prefix}</{elem.tag}>\n"
    else:
        result = f"{prefix}<{elem.tag}"
        for attr_key, attr_val in elem.attrib.items():
            result += f' {attr_key}="{attr_val}"'

        if elem.text:
            result += f">{elem.text}</{elem.tag}>\n"
        else:
            result += f"/>\n"

    if elem.tail:
        result += elem.tail

    return result


def _generate_main_xml_doc(workflow, files_info):
    """Создать main.xml с include всех сгенерированных файлов."""
    doc = ET_Element("doc")

    _add_params_section(doc, workflow)

    content = ET_SubElement(doc, "content")

    for file_info in files_info:
        context = file_info["context"]
        tool = file_info["tool"]
        filename = file_info["filename"]

        tool_upper = tool.upper()
        context_upper = context.upper() if context != "all" else "ALL"

        include = ET_SubElement(content, "include")
        include.set("name", filename.replace(".xml", ""))
        include.set("src", "qualityControl/" + filename)
        include.set("exec", "ON")
        include.set("callif", f"IS{tool_upper};{context_upper}")

    result = "<?xml version='1.0' encoding='windows-1251'?>\n"
    result += _element_to_string(doc)

    return result

def _apply_dqcr_param_syntax(
    workflow: "WorkflowNewModel", sql_content: str, tool: str
) -> str:
    """Применить DQCR синтаксис параметров: заменить {{ var }} на формат dqcr.

    Использует param_syntax.py для правильного рендеринга в зависимости от domain_type.

    Args:
        workflow: WorkflowNewModel для получения domain_type параметров
        sql_content: SQL с параметрами в формате {{ var_name }}
        tool: целевой tool (oracle, adb, postgresql)

    Returns:
        SQL с параметрами в DQCR формате
    """
    import re
    from FW.macros.workflow.dqcr.param_syntax import render_param
    
    def replace_var(match):
        var_name = match.group(1).strip()
        domain_type = "UNDEFINED"
        param = None
        for p in workflow.parameters:
            if p.upper() == var_name.upper():
               param = workflow.parameters.get(p)
               break
        if param:
            domain_type = param.domain_type

        return render_param(var_name, domain_type=domain_type, tool=tool)

    result = re.sub(r"\{\{\s*([^}]+?)\s*\}\}", replace_var, sql_content)
    return result
