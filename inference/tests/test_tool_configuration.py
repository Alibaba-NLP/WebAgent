import json
import unittest

from prompt import build_system_prompt
from tool_configuration import resolve_tools


class FakeTool:
    name = "current_source"
    description = "Search a current source."
    parameters = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    def __init__(self, config=None):
        self.config = config

    def call(self, params):
        return params


class LegacyTool(FakeTool):
    name = "legacy"
    parameters = [
        {
            "name": "files",
            "type": "array",
            "array_type": "string",
            "description": "Files to parse.",
            "required": True,
        }
    ]


class ToolConfigurationTest(unittest.TestCase):
    def test_resolve_tools_honors_names_configs_and_instances(self):
        instance = FakeTool()
        registry = {"current_source": FakeTool, "legacy": LegacyTool}

        tools = resolve_tools(
            ["legacy", {"name": "current_source", "timeout": 5}], registry
        )

        self.assertEqual(list(tools), ["legacy", "current_source"])
        self.assertEqual(
            tools["current_source"].config, {"name": "current_source", "timeout": 5}
        )
        self.assertIsInstance(tools["legacy"], LegacyTool)

        tools = resolve_tools([instance], registry)
        self.assertIs(tools["current_source"], instance)

    def test_resolve_tools_rejects_unknown_names(self):
        with self.assertRaisesRegex(ValueError, "not registered"):
            resolve_tools(["missing"], {})

    def test_prompt_contains_only_enabled_tool_schemas(self):
        prompt = build_system_prompt([FakeTool(), LegacyTool()])

        tool_block = prompt.split("<tools>\n", 1)[1].split("\n</tools>", 1)[0]
        definitions = [json.loads(line) for line in tool_block.splitlines()]
        functions = [definition["function"] for definition in definitions]

        self.assertEqual(
            [function["name"] for function in functions], ["current_source", "legacy"]
        )
        self.assertEqual(functions[0]["description"], FakeTool.description)
        self.assertEqual(
            functions[1]["parameters"]["properties"]["files"]["items"],
            {"type": "string"},
        )
        self.assertEqual(functions[1]["parameters"]["required"], ["files"])


if __name__ == "__main__":
    unittest.main()
