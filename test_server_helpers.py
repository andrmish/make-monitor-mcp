import ast
import unittest
from pathlib import Path


def load_helpers():
    source = Path("server.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {"parse_json_value", "extract_blueprint", "find_module"}
    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    module = ast.Module(body=nodes, type_ignores=[])
    namespace = {"Any": object, "json": __import__("json")}
    exec(compile(module, "server.py", "exec"), namespace)
    return namespace


class ServerHelperTests(unittest.TestCase):
    def test_blueprint_string_and_nested_module(self):
        helpers = load_helpers()
        blueprint = helpers["extract_blueprint"](
            {
                "blueprint": (
                    '{"flow":[{"id":10,"routes":'
                    '[{"flow":[{"id":26,"module":"elevenlabs:test"}]}]}]}'
                )
            }
        )
        module = helpers["find_module"](blueprint, 26)
        self.assertEqual(module["module"], "elevenlabs:test")

    def test_missing_module(self):
        helpers = load_helpers()
        self.assertIsNone(helpers["find_module"]({"flow": [{"id": 1}]}, 999))


if __name__ == "__main__":
    unittest.main()
