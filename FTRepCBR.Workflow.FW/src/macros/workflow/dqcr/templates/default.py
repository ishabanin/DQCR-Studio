"""DQCR workflow template - default."""

from xml.etree.ElementTree import Element as ET_Element, SubElement as ET_SubElement
from FW.models.workflow_new import WorkflowNewModel

def generate_workflow(workflow : WorkflowNewModel, env):
    """Генерировать DQCR XML документы."""
    repsysname = workflow.project.project_properties.get("repsysname").get("value")
    model_name = workflow.model_name
    model_folder = f"{repsysname}/{model_name}"

    files_info = []
    files_generated = 0

    for context in workflow.graph:
        print(f"context: {context}")
        for tool in  workflow.graph[context]:
            print(f"tool: {tool}")
            steps = workflow.graph[context][tool]["steps"]
            xml_content = _generate_xml_doc(workflow, steps, tool, context)

            filename = f"{model_folder}/{workflow.model_name}_{context}_{tool}.xml"
            env.create_file(filename, xml_content, 'cp1251')

            files_info.append({"context": context, "tool": tool, "filename": filename})

            files_generated += 1
            print(f"[DQCR] Generated: {filename} ({len(workflow.graph[context][tool]["steps"])} steps)")

    if files_info:
        main_xml = _generate_main_xml_doc(workflow, files_info)
        main_filename = f"{model_folder}/{workflow.model_name}_main.xml"
        env.create_file(main_filename, main_xml, 'cp1251')

        files_info.append(
            {"context": "main", "tool": "main", "filename": main_filename}
        )

        files_generated += 1
        print(
            f"[DQCR] Generated: {main_filename} (includes {len(files_info) - 1} files)"
        )

        repsys_main_xml = _generate_repsys_main_doc(
            workflow, repsysname, model_name, files_info
        )
        repsys_main_filename = f"{repsysname}/main_{repsysname}.xml"
        env.create_file(repsys_main_filename, repsys_main_xml, 'cp1251')
        files_generated += 1
        print(f"[DQCR] Generated: {repsys_main_filename}")

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
                    rendered =  tool_data.get("rendered_sql")
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

def _generate_xml_doc(workflow : WorkflowNewModel, steps, tool, context):
    """Сгенерировать XML для конкретного tool и context."""
    doc = ET_Element("doc")

    steps = _get_sorded_steps(workflow.graph[context][tool]["edges"], steps) 

    _add_params_section(doc, workflow, tool=tool, context=context)

    _add_flag_params(doc, workflow, steps, tool, context)

    content = ET_SubElement(doc, "content")    

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

        if step_type == "sql":
            sql_obj = workflow.sql_objects[step["object_id"]]
            obj = ET_SubElement(content, "object")
            obj.set("type", "SQL")
            obj.set("name", (step["object_id"].split("/")[-1] if "/" in step["object_id"] else step["object_id"]).replace(".","_"))

            desc_prop = ET_SubElement(obj, "property")            
            desc_prop.set("name", "Description")
            
            desc = getattr(sql_obj, "description", None) if sql_obj else None
            if desc:
                desc_prop.text = _wrap_cdata(desc)
            else:
                desc_prop.text = _wrap_cdata(f"Step: {step["object_id"]}")

            sql_prop = ET_SubElement(obj, "property")
            sql_prop.set("name", "SQL")
            sql_prop.text = _wrap_cdata(_format_sql_for_xml(rendered_sql))
            has_object = True

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
                desc_prop.text = _wrap_cdata(f"Param: {step["object_id"]}")

            sql_prop = ET_SubElement(obj, "property")
            sql_prop.set("name", "SQL")
            sql_prop.text = _wrap_cdata(_format_sql_for_xml(rendered_sql))

            out_attrs = _get_param_attributes(workflow, step)
            if out_attrs:
                out_prop = ET_SubElement(obj, "property")
                out_prop.set("name", "OUT")
                out_prop.text = _wrap_cdata(";".join(out_attrs))

            has_object = True

    _add_call(doc, workflow, steps, tool, context)

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

def _add_flag_params(doc, workflow, steps, tool, context):
    """Добавить параметры FlagSQL для флагов."""
    flag_steps = [
        s
        for s in steps
        if s.get("step_scope") == "flag"
        and _is_param_type(s)
        and s.get("context")
        and _step_has_sql_for_tool(workflow, s, tool)
    ]

    if not flag_steps:
        return

    params = doc.find("params")
    if params is None:
        params = ET_SubElement(doc, "params")

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


def _add_call(doc, workflow : WorkflowNewModel, steps, tool, context):
    """Добавить call со всеми step внутри."""
    content = doc.find("content")
    if content is None:
        return

    non_flag_steps = [
        s
        for s in steps
        if s.get("step_scope") != "flag"
        and _step_has_sql_for_tool(workflow, s, tool)
        and s.get("context") == context
    ]

    if not non_flag_steps:
        return

    call = ET_SubElement(content, "call")
    call.set("type", "MultiFunc")
    call.set("name", f"EXEC_{context}_{tool}")
    call.set("value", "")

    for step in non_flag_steps:
        step_key = step["object_id"]
        step_elem = ET_SubElement(call, "step")
        step_elem.text = (step_key.split("/")[-1] if "/" in step_key else step_key).replace(".","_")


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
        include.set("src", filename)
        include.set("exec", "ON")
        include.set("callif", f"IS{tool_upper};{context_upper}")

    result = "<?xml version='1.0' encoding='windows-1251'?>\n"
    result += _element_to_string(doc)

    return result


def _generate_repsys_main_doc(workflow, repsysname, model_name, files_info):
    """Создать main_{repsysname}.xml с include main_{model_name}.xml."""
    doc = ET_Element("doc")

    _add_params_section(doc, workflow)

    content = ET_SubElement(doc, "content")

    main_model_filename = f"{model_name}_main.xml"
    for file_info in files_info:
        if file_info["filename"].endswith(main_model_filename):
            include = ET_SubElement(content, "include")
            include.set("name", f"{model_name}_main")
            include.set("src", f"forms/{repsysname}/{model_name}/{main_model_filename}")
            include.set("exec", "ON")
            include.set("callif", f"BP_{model_name}")
            break

    result = "<?xml version='1.0' encoding='windows-1251'?>\n"
    result += _element_to_string(doc)

    return result

def _apply_dqcr_param_syntax(workflow: "WorkflowNewModel", sql_content: str, tool: str) -> str:
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
        param = workflow.parameters.get(var_name)
        if param:
            domain_type = param.domain_type
        
        return render_param(var_name, domain_type=domain_type, tool=tool)
    
    result = re.sub(r'\{\{\s*([^}]+?)\s*\}\}', replace_var, sql_content)
    return result