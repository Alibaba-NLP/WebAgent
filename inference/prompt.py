import json
from typing import Iterable


SYSTEM_PROMPT_TEMPLATE = """You are a deep research assistant. Your core function is to conduct thorough, multi-source investigations into any topic. You must handle both broad, open-domain inquiries and queries within specialized academic fields. For every request, synthesize information from credible, diverse sources to deliver a comprehensive, accurate, and objective response. When you have gathered sufficient information and are ready to provide the definitive response, you must enclose the entire final answer within <answer></answer> tags.

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
__TOOL_DEFINITIONS__
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>

Current date: """


def _normalize_parameters(parameters):
    if isinstance(parameters, dict):
        return parameters

    properties = {}
    required = []
    for parameter in parameters:
        name = parameter["name"]
        schema = {"type": parameter.get("type", "string")}
        if schema["type"] == "array":
            schema["items"] = {"type": parameter.get("array_type", "string")}
        if parameter.get("description"):
            schema["description"] = parameter["description"]
        properties[name] = schema
        if parameter.get("required"):
            required.append(name)
    return {"type": "object", "properties": properties, "required": required}


def build_system_prompt(tools: Iterable) -> str:
    definitions = []
    for tool in tools:
        function = {
            "name": tool.name,
            "description": tool.description,
            "parameters": _normalize_parameters(tool.parameters),
        }
        definitions.append(
            json.dumps({"type": "function", "function": function}, ensure_ascii=False)
        )
    return SYSTEM_PROMPT_TEMPLATE.replace(
        "__TOOL_DEFINITIONS__", "\n".join(definitions)
    )


SYSTEM_PROMPT = build_system_prompt(())

EXTRACTOR_PROMPT = """Please process the following webpage content and user goal to extract relevant information:

## **Webpage Content** 
{webpage_content}

## **User Goal**
{goal}

## **Task Guidelines**
1. **Content Scanning for Rationale**: Locate the **specific sections/data** directly related to the user's goal within the webpage content
2. **Key Extraction for Evidence**: Identify and extract the **most relevant information** from the content, you never miss any important information, output the **full original context** of the content as far as possible, it can be more than three paragraphs.
3. **Summary Output for Summary**: Organize into a concise paragraph with logical flow, prioritizing clarity and judge the contribution of the information to the goal.

**Final Output Format using JSON format has "rational", "evidence", "summary" feilds**
"""
