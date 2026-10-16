#!/usr/bin/env python3
"""Check the restored global skeleton; visual acceptance remains a separate step."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[1]
BUILTIN = ROOT.parent / "01-内置命令"
HELP = BUILTIN / "Help-Agent使用指南"
GLOBAL_NAME = "target_slash_command_global_classes"
GLOBAL_SVG = ROOT / "设计图" / (GLOBAL_NAME + ".svg")
RELATIONS = (
    "RuntimeCommandCatalogController --> CommandCatalogService",
    "RuntimeCommandController --> CommandExecutionService",
    "CommandCatalogService --> AgentRuntimeManager",
    "CommandExecutionService --> RuntimeSessionRepository",
    "CommandExecutionService --> CommandResponseAssembler",
    'CompositeCommandRegistry o-- "1..*" CommandDefinitionSource',
    "CommandDefinitionSource ..> CommandDefinition",
    "BuiltinCommandDefinition ..|> CommandDefinition",
    'ResolvedCommandCatalog o-- "0..*" CommandDefinition',
    'BuiltinCommandSource o-- "8" BuiltinCommandContributor',
    "BuiltinContributors ..|> BuiltinCommandContributor",
    "BuiltinContributors --> BuiltinHandlers",
    "BuiltinHandlers ..|> CommandHandler",
    'BuiltinCommandDefinition *-- "1" CommandAdmissionPolicy',
    'BuiltinCommandDefinition *-- "1" CommandHandler',
    "BuiltinHandlers --> DomainServices",
    "BuiltinHandlers --> AgentHelpQueryService",
    "AgentHelpQueryService -[norank]-> AgentRuntimeManager",
    "DomainServices --> RuntimeSessionRepository",
    "DomainServices --> RuntimeExecutionCoordinator",
    "RuntimeExecutionCoordinator --> RuntimeExecutionPorts",
    "RuntimeExecutionPorts --> RuntimeSessionRepository",
)


def global_block():
    source = (ROOT / "设计图/diagram.puml").read_text(encoding="utf-8")
    return source.split("@startuml " + GLOBAL_NAME + "\n", 1)[1].split("@enduml", 1)[0]


def check_structure(block):
    for relation in RELATIONS:
        if relation not in block:
            raise ValueError("Missing global responsibility: " + relation)
    for obsolete in ("CommandHelpFormatter", "parallel work",
                     "Runtime execution / Repository", "6 Other Builtin Handlers"):
        if obsolete in block:
            raise ValueError("Superseded or collapsed structure: " + obsolete)
    if "CommandCatalogService --> RuntimeSessionRepository" in block:
        raise ValueError("Agent catalog must not read Session state")
    if "06bea56" not in block or "待实现" not in block:
        raise ValueError("Missing presentation baseline or 待实现 boundary")


def first_diagram(markdown):
    target = re.search(r"!\[[^\]]*\]\(([^)]+\.svg)\)", markdown.read_text(encoding="utf-8"))
    return (markdown.parent / target.group(1)).resolve()


class GlobalClassViewTest(unittest.TestCase):
    def test_restored_complete_skeleton(self):
        check_structure(global_block())

    def test_each_responsibility_is_required(self):
        for relation in RELATIONS:
            with self.subTest(relation=relation):
                with self.assertRaises(ValueError):
                    check_structure(global_block().replace(relation, "omitted"))

    def test_obsolete_help_and_collapsed_groups_are_rejected(self):
        for obsolete in ("CommandHelpFormatter", "parallel work",
                         "Runtime execution / Repository", "6 Other Builtin Handlers"):
            with self.subTest(obsolete=obsolete):
                with self.assertRaises(ValueError):
                    check_structure(global_block() + "\n" + obsolete)

    def test_slash_and_builtin_share_the_first_global_diagram(self):
        self.assertEqual(GLOBAL_SVG.resolve(), first_diagram(BUILTIN / "README.md"))
        self.assertIn("设计图/" + GLOBAL_NAME + ".svg", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertTrue(GLOBAL_SVG.exists())

    def test_help_is_a_supplement_not_another_global_definition(self):
        source = (HELP / "diagram.puml").read_text(encoding="utf-8")
        self.assertIn("@startuml target_help_metadata_classes", source)
        self.assertNotIn("@startuml target_help_global_classes", source)
        for node in ("CompositeCommandRegistry", "BuiltinCommandSource", "SkillCommandSource"):
            self.assertNotIn(node, source)
        self.assertEqual((HELP / "target_help_metadata_classes.svg").resolve(),
                         first_diagram(HELP / "README.md"))

    def test_retired_global_link_does_not_return(self):
        for document in (ROOT / "README.md", BUILTIN / "README.md",
                         HELP / "README.md", REPOSITORY / "README.md"):
            self.assertNotIn("target_help_global_classes.svg", document.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
