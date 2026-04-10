"""DQCR workflow generator.

Генерирует XML документ DQCR формата.

Структура вывода:
    target/dqcr/<workflow_name>/<workflow_name>_<context>_<tool>.xml
    target/dqcr/<workflow_name>/<workflow_name>_main.xml
"""
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Set
from xml.etree.ElementTree import Element, SubElement, tostring

SCOPE_ORDER = {
    'flags': 0,
    'pre': 1,
    'params': 2,
    'sql': 3,
    'post': 4,
}


def _get_scope_order(scope: str) -> int:
    """Получить порядковый номер для step_scope."""
    return SCOPE_ORDER.get(scope, 99)


if TYPE_CHECKING:
    from FW.macros.env import WorkflowMacroEnv
    from FW.models.workflow import WorkflowModel
    from FW.models.step import WorkflowStepModel


def _element_to_string_with_cdata(elem: Element, indent: int = 0) -> str:
    """Преобразовать Element в XML строку с CDATA."""
    prefix = "  " * indent
    
    children = list(elem)
    if children:
        result = f"{prefix}<{elem.tag}"
        for attr_key, attr_val in elem.attrib.items():
            result += f' {attr_key}="{attr_val}"'
        result += ">\n"
        for child in children:
            result += _element_to_string_with_cdata(child, indent + 1)
        result += f"{prefix}</{elem.tag}>\n"
    else:
        result = f"{prefix}<{elem.tag}"
        for attr_key, attr_val in elem.attrib.items():
            result += f' {attr_key}="{attr_val}"'
        
        if elem.text:
            if "<![CDATA[" in elem.text:
                result += f">{elem.text}</{elem.tag}>\n"
            else:
                result += f">{elem.text}</{elem.tag}>\n"
        else:
            result += f"/>\n"
    
    if elem.tail:
        result += elem.tail
    
    return result


def _wrap_cdata(text: str) -> str:
    """Обернуть текст в CDATA."""
    if not text:
        return ""
    return f"<![CDATA[{text}]]>"


def _format_sql_for_xml(sql_text: str) -> str:
    """Отформатировать SQL для красивого вывода в XML с отступами."""
    if not sql_text:
        return ""
    lines = sql_text.split('\n')
    indent = " " * 16
    formatted_lines = [indent + line for line in lines]
    return "\n" + "\n".join(formatted_lines) + "\n"


def _escape_for_flag_comment(text: str) -> str:
    """Экранировать / и * для комментария в FlagSQL."""
    if not text:
        return ""
    return text.replace("/*", "\\*").replace("*/", "*\\")


def _create_doc_element() -> Element:
    """Создать корневой элемент doc."""
    return Element("doc")


def _add_params_section(doc: Element, workflow: "WorkflowModel", tool: str = "", context: str = "") -> None:
    """Добавить секцию params с параметрами workflow."""
    params = SubElement(doc, "params")
    
    title = workflow.target_table.name if workflow.target_table else workflow.model_name
    title_param = SubElement(params, "param")
    title_param.set("name", "Title")
    title_param.text = _wrap_cdata(title)
    
    desc_param = SubElement(params, "param")
    desc_param.set("name", "Description")
    base_desc = workflow.description or f"DQCR workflow: {workflow.model_name}"
    
    if tool or context:
        suffix_parts = []
        if context:
            suffix_parts.append(f"для контекста {context}")
        if tool:
            suffix_parts.append(f"для tool {tool}")
        desc_param.text = _wrap_cdata(f"{base_desc} ({', '.join(suffix_parts)})")
    else:
        desc_param.text = _wrap_cdata(base_desc)


def _add_flag_params(
    doc: "Element", 
    steps: List["WorkflowStepModel"],
    tool: str,
    context: str
) -> None:
    """Добавить параметры FlagSQL для флагов."""
    from xml.etree.ElementTree import SubElement
    
    def is_param_type(step) -> bool:
        """Проверить является ли step_type PARAM."""
        st = step.step_type
        if isinstance(st, str):
            return st == "param"
        if hasattr(st, 'name'):
            return st.name == "PARAM"
        return str(st) == "param"
    
    # Include both: steps matching context AND steps with context="all"
    flag_steps = [
        s for s in steps 
        if s.step_scope == "flags" 
        and is_param_type(s)
        and s.param_model 
        and s.param_model.rendered_sql
        and tool in s.param_model.rendered_sql
        and (s.context == context or s.context == "all")
    ]
    
    if not flag_steps:
        return
    
    params = doc.find("params")
    if params is None:
        params = SubElement(doc, "params")
    
    for step in flag_steps:
        if not step.param_model or not step.param_model.rendered_sql:
            continue
        flag_sql = SubElement(params, "param")
        flag_sql.set("name", "FlagSQL")
        sql_text = step.param_model.rendered_sql.get(tool, "").strip()
        if sql_text:
            param_desc = step.param_model.description
            if param_desc:
                escaped_desc = _escape_for_flag_comment(param_desc)
                comment = f"/* {escaped_desc} */\n"
                flag_sql.text = _wrap_cdata(comment + _format_sql_for_xml(sql_text))
            else:
                flag_sql.text = _wrap_cdata(_format_sql_for_xml(sql_text))


def _add_sql_object(
    content: "Element",
    step: "WorkflowStepModel",
    tool: str
) -> None:
    """Добавить object для SQL шага."""
    from xml.etree.ElementTree import SubElement
    
    if step.is_ephemeral:
        return
    
    if not step.sql_model or not step.sql_model.rendered_sql.get(tool):
        return
    
    obj = SubElement(content, "object")
    obj.set("type", "SQL")
    obj.set("name", step.name)
    
    desc_prop = SubElement(obj, "property")
    desc_prop.set("name", "Description")
    step_description = step.sql_model.description if step.sql_model.description else f"Step: {step.full_name}"
    desc_prop.text = _wrap_cdata(step_description)
    
    sql_prop = SubElement(obj, "property")
    sql_prop.set("name", "SQL")
    sql_text = step.sql_model.rendered_sql.get(tool, "").strip()
    sql_prop.text = _wrap_cdata(_format_sql_for_xml(sql_text))


def _add_param_object(
    content: "Element",
    step: "WorkflowStepModel",
    tool: str
) -> None:
    """Добавить object для PARAM шага (не flags)."""
    from xml.etree.ElementTree import SubElement
    
    if step.step_scope == "flags":
        return
    
    if not step.param_model:
        return
    
    rendered_sql = step.param_model.rendered_sql.get(tool, "").strip() if step.param_model.rendered_sql else ""
    
    if not rendered_sql:
        return
    
    obj = SubElement(content, "object")
    obj.set("type", "SQL")
    obj.set("name", step.name)
    
    desc_prop = SubElement(obj, "property")
    desc_prop.set("name", "Description")
    step_description = step.param_model.description if step.param_model.description else f"Step: {step.full_name}"
    desc_prop.text = _wrap_cdata(step_description)
    
    sql_prop = SubElement(obj, "property")
    sql_prop.set("name", "SQL")
    sql_prop.text = _wrap_cdata(_format_sql_for_xml(rendered_sql))
    
    # Add OUT property with attributes
    if step.param_model.attributes:
        out_attrs = [attr.get("name", "") for attr in step.param_model.attributes if attr.get("name")]
    else:
        out_attrs = [step.param_model.name]
    if out_attrs:
        out_prop = SubElement(obj, "property")
        out_prop.set("name", "OUT")
        out_prop.text = _wrap_cdata(";".join(out_attrs))

def _add_call(
    content: "Element",
    steps: List["WorkflowStepModel"],
    tool: str,
    context: str
) -> None:
    """Добавить один call со всеми step внутри."""
    from xml.etree.ElementTree import SubElement
    
    # Include both: steps matching context AND steps with context="all"
    non_flag_steps = [
        s for s in steps
        if s.step_scope != "flags"
        and not s.is_ephemeral
        and _step_has_sql_for_tool(s, tool)
        and (s.context == context or s.context == "all")
    ]
    
    if not non_flag_steps:
        return
    
    call = SubElement(content, "call")
    call.set("type", "MultiFunc")
    call.set("name", f"EXEC_{context}_{tool}")
    call.set("value", "")
    
    for step in non_flag_steps:
        step_elem = SubElement(call, "step")
        step_elem.text = step.name


def _step_has_sql_for_tool(step: "WorkflowStepModel", tool: str) -> bool:
    """Проверить есть ли SQL для данного tool."""
    if step.sql_model and step.sql_model.rendered_sql.get(tool):
        return True
    if step.param_model and step.param_model.rendered_sql.get(tool):
        return True
    return False


def _collect_tools_and_contexts(workflow: "WorkflowModel", steps: List["WorkflowStepModel"]) -> Dict[str, Set[str]]:
    """Собрать tools для каждого context с учетом tools, разрешенных в контексте.
    
    Учитывает:
    - workflow.context_name - если задан конкретный контекст, генерируем только для него
    - ContextModel.tools - для каждого контекста используем только разрешенные tools
    - Контексты с пустыми tools пропускаются
    """
    tool_context_map: Dict[str, Set[str]] = {}
    
    # Determine which contexts to use
    if workflow.context_name and workflow.context_name != "default" and workflow.all_contexts and workflow.context_name in workflow.all_contexts:
        contexts_to_use = [workflow.context_name]
    else:
        contexts_to_use = list(workflow.all_contexts.keys()) if workflow.all_contexts else ['default']
    
    # For each context, get allowed tools from ContextModel
    for context_name in contexts_to_use:
        context_model = workflow.all_contexts.get(context_name)
        if not context_model:
            continue
        
        context_tools = context_model.tools if context_model.tools else []
        
        # Skip contexts with empty tools list
        if not context_tools:
            continue
        
        # Add only tools that are in context_tools and exist in steps
        available_tools_in_steps = set()
        for step in steps:
            if step.is_ephemeral:
                continue
            
            if step.step_scope == "flags":
                if step.param_model and step.param_model.rendered_sql:
                    available_tools_in_steps.update(step.param_model.rendered_sql.keys())
                continue
            
            if step.sql_model and step.sql_model.rendered_sql:
                available_tools_in_steps.update(step.sql_model.rendered_sql.keys())
            
            if step.param_model and step.param_model.rendered_sql:
                available_tools_in_steps.update(step.param_model.rendered_sql.keys())
        
        for tool in context_tools:
            if tool in available_tools_in_steps:
                if tool not in tool_context_map:
                    tool_context_map[tool] = set()
                tool_context_map[tool].add(context_name)
    
    return tool_context_map


def _get_sorted_step_order(workflow: "WorkflowModel") -> Dict[str, int]:
    """Получить порядок шагов из topological sort графа."""
    if workflow.graph:
        graph_steps = list(workflow.graph.topological_sort())
        return {s.full_name: i for i, s in enumerate(graph_steps)}
    return {}


def _generate_xml(workflow: "WorkflowModel", steps: List["WorkflowStepModel"], all_steps: List["WorkflowStepModel"], tool: str, context: str) -> str:
    """Сгенерировать XML для конкретного tool и context."""
    from xml.etree.ElementTree import Element, SubElement, tostring
    
    doc = _create_doc_element()
    
    _add_params_section(doc, workflow, tool=tool, context=context)
    
    # Pass all_steps for flags, not filtered steps
    _add_flag_params(doc, all_steps, tool, context)
    
    content = SubElement(doc, "content")
    
    has_object = False
    for step in steps:
        if step.step_scope == "flags":
            continue
        if step.is_ephemeral:
            continue
        
        # Include both: steps matching context AND steps with context="all"
        if step.context != context and step.context != "all":
            continue
        
        if step.sql_model and step.sql_model.rendered_sql.get(tool):
            if has_object:
                prev_object = content[-1]
                prev_object.tail = "\n\n"
            _add_sql_object(content, step, tool)
            has_object = True
        
        if step.param_model and step.param_model.rendered_sql.get(tool):
            if has_object:
                prev_object = content[-1]
                prev_object.tail = "\n\n"
            _add_param_object(content, step, tool)
            has_object = True
    
    if has_object:
        prev_object = content[-1]
        prev_object.tail = "\n\n"
    
    _add_call(content, steps, tool, context)
    
    xml_str = tostring(doc, encoding="unicode")
    
    # Add XML declaration
    result = "<?xml version='1.0' encoding='windows-1251'?>\n"
    result += _element_to_string_with_cdata(doc)
    
    return result


def _generate_main_xml(workflow: "WorkflowModel", files_info: List[Dict[str, str]]) -> str:
    """Создать main.xml с include всех сгенерированных файлов."""
    from xml.etree.ElementTree import Element, SubElement, tostring
    
    doc = _create_doc_element()
    
    _add_params_section(doc, workflow)
    
    content = SubElement(doc, "content")
    
    for file_info in files_info:
        context = file_info["context"]
        tool = file_info["tool"]
        filename = file_info["filename"]
        
        # Build callif based on tool and context
        tool_upper = tool.upper()
        context_upper = context.upper() if context != "all" else "ALL"
        
        include = SubElement(content, "include")
        include.set("name", filename.replace(".xml", ""))
        include.set("src", filename)
        include.set("exec", "ON")
        include.set("callif", f"IS{tool_upper};{context_upper}")
    
    xml_str = tostring(doc, encoding="unicode")
    
    result = "<?xml version='1.0' encoding='windows-1251'?>\n"
    result += _element_to_string_with_cdata(doc)
    
    return result


def _generate_repsys_main_xml(
    workflow: "WorkflowModel",
    repsysname: str,
    model_name: str,
    files_info: List[Dict[str, str]]
) -> str:
    """Создать main_{repsysname}.xml с include main_{model_name}.xml."""
    from xml.etree.ElementTree import Element, SubElement, tostring
    
    doc = _create_doc_element()
    
    _add_params_section(doc, workflow)
    
    content = SubElement(doc, "content")
    
    # Find the main_{model_name}.xml file info
    main_model_filename = f"{model_name}_main.xml"
    for file_info in files_info:
        if file_info["filename"].endswith(main_model_filename):
            include = SubElement(content, "include")
            include.set("name", f"{model_name}_main")
            include.set("src", f"forms/{repsysname}/{model_name}/{main_model_filename}")
            include.set("exec", "ON")
            include.set("callif", f"BP_{model_name}")
            break
    
    xml_str = tostring(doc, encoding="unicode")
    
    result = "<?xml version='1.0' encoding='windows-1251'?>\n"
    result += _element_to_string_with_cdata(doc)
    
    return result


def generate_workflow(workflow: "WorkflowModel", env: "WorkflowMacroEnv"):
    """Генерировать DQCR XML документы.
    
    Для каждой пары (context, tool) создается отдельный файл.
    Также создается main.xml с include всех файлов.
    
    Args:
        workflow: Модель workflow
        env: Окружение для создания файлов
    """
    repsysname = workflow.project_properties.get('repsysname')
    if not repsysname:
        raise ValueError("repsysname must be specified in project properties")
    
    model_name = workflow.model_name
    
    model_folder = f"{repsysname}/{model_name}"
    
    # Use _all_steps which contains all steps
    all_steps = workflow._all_steps if hasattr(workflow, '_all_steps') and workflow._all_steps else workflow.steps
    
    if not all_steps:
        all_steps = env.get_all_steps()
    
    tool_context_map = _collect_tools_and_contexts(workflow, all_steps)
    
    files_info = []
    files_generated = 0
    
    for tool, contexts in tool_context_map.items():
        for context in contexts:
            # Get sorted step order from graph
            sorted_order = _get_sorted_step_order(workflow)
            
            # Filter and sort steps
            filtered_steps = [
                s for s in all_steps
                if not s.is_ephemeral
                and s.step_scope != "flags"
                and (s.context == context or s.context == "all")
                and _step_has_sql_for_tool(s, tool)
            ]
            
            # Sort by scope first, then by graph order, then by name
            filtered_steps = sorted(filtered_steps, key=lambda s: (
                _get_scope_order(s.step_scope),
                sorted_order.get(s.full_name, 999),
                s.full_name
            ))
            
            if not filtered_steps:
                continue
            
            xml_content = _generate_xml(workflow, filtered_steps, all_steps, tool, context)
            
            filename = f"{model_folder}/{workflow.model_name}_{context}_{tool}.xml"
            env.create_file(filename, xml_content)
            
            files_info.append({
                "context": context,
                "tool": tool,
                "filename": filename
            })
            
            files_generated += 1
            print(f"[DQCR] Generated: {filename} ({len(filtered_steps)} steps)")
    
    # Generate main_{model_name}.xml with includes
    if files_info:
        main_xml = _generate_main_xml(workflow, files_info)
        main_filename = f"{model_folder}/{workflow.model_name}_main.xml"
        env.create_file(main_filename, main_xml)
        
        files_info.append({
            "context": "main",
            "tool": "main",
            "filename": main_filename
        })
        
        files_generated += 1
        print(f"[DQCR] Generated: {main_filename} (includes {len(files_info)-1} files)")
        
        # Generate main_{repsysname}.xml with include of main_{model_name}.xml
        repsys_main_xml = _generate_repsys_main_xml(workflow, repsysname, model_name, files_info)
        repsys_main_filename = f"{repsysname}/main_{repsysname}.xml"
        env.create_file(repsys_main_filename, repsys_main_xml)
        files_generated += 1
        print(f"[DQCR] Generated: {repsys_main_filename}")
    
    if files_generated == 0:
        print("[DQCR] Warning: No files generated")
    else:
        print(f"[DQCR] Total files: {files_generated}")
