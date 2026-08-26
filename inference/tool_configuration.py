from typing import Dict, Iterable


def resolve_tools(function_list: Iterable, registry: Dict[str, type]) -> dict:
    tools = {}
    for specification in function_list:
        if isinstance(specification, str):
            name = specification
            config = None
            tool = None
        elif isinstance(specification, dict):
            name = specification.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("Tool configuration requires a non-empty name.")
            config = specification
            tool = None
        else:
            tool = specification
            name = getattr(tool, "name", "")
            config = None
            if not name or not callable(getattr(tool, "call", None)):
                raise TypeError("Tool instances require a name and call method.")

        if tool is None:
            if name not in registry:
                raise ValueError(f"Tool {name} is not registered.")
            tool = registry[name](config)

        tools[name] = tool
    return tools
