#!/usr/bin/env python3
"""校验 CampusClaw TDD Agent 设计资产和能力注册表。"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as element_tree
from pathlib import Path


ENFORCED_MATURITY = {"accepted", "frozen", "implemented"}
VALID_MATURITY = ENFORCED_MATURITY | {"proposed", "research"}
VALID_COVERAGE = {"covered", "partial", "unbound"}
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PUML_LINK_PATTERN = re.compile(r"diagram\.puml#L(\d+)")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--design-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="设计仓根目录",
    )
    parser.add_argument(
        "--code-root",
        type=Path,
        help="pi-mono-java 根目录；提供后校验源码证据",
    )
    parser.add_argument(
        "--strict-coverage",
        action="store_true",
        help="将已生效 P0 的 partial/unbound 覆盖视为失败",
    )
    return parser.parse_args()


def fail(errors: list[str], message: str) -> None:
    """记录一个校验错误。"""
    errors.append(message)


def design_path_exists(design_root: Path, relative_path: str, commit: str) -> bool:
    """校验工作树或所分析提交中是否存在设计路径。"""
    if (design_root / relative_path).exists():
        return True
    result = subprocess.run(
        ["git", "-C", str(design_root), "cat-file", "-e", f"{commit}:{relative_path}"],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def validate_registry(
    topic_root: Path,
    design_root: Path,
    code_root: Path | None,
    strict_coverage: bool,
    errors: list[str],
) -> list[str]:
    """校验注册表结构、引用和覆盖规则。"""
    warnings: list[str] = []
    registry_path = topic_root / "capability-registry.json"
    registry = json.loads(registry_path.read_text())
    capabilities = registry.get("capabilities", [])
    design_commit = registry["baselines"]["designRepository"]["commit"]
    if not capabilities:
        fail(errors, "capability-registry.json 不包含 capabilities")
        return warnings

    capability_ids: set[str] = set()
    requirement_ids: set[str] = set()
    for capability in capabilities:
        capability_id = capability.get("id", "")
        if capability_id in capability_ids:
            fail(errors, f"重复 capability id: {capability_id}")
        capability_ids.add(capability_id)
        maturity = capability.get("maturity")
        coverage = capability.get("coverageState")
        if maturity not in VALID_MATURITY:
            fail(errors, f"{capability_id} maturity 非法: {maturity}")
        if coverage not in VALID_COVERAGE:
            fail(errors, f"{capability_id} coverageState 非法: {coverage}")
        for design_ref in capability.get("designRefs", []):
            if not design_path_exists(design_root, design_ref, design_commit):
                fail(errors, f"{capability_id} 设计引用不存在: {design_ref}")
        validate_requirements(capability, requirement_ids, errors)
        validate_source_evidence(capability, code_root, errors)
        validate_test_selectors(capability, code_root, errors)
        if maturity in ENFORCED_MATURITY and capability.get("criticality") == "P0":
            if coverage != "covered":
                message = f"{capability_id} 是已生效 P0，但覆盖状态为 {coverage}"
                if strict_coverage:
                    fail(errors, message)
                else:
                    warnings.append(message)
    return warnings


def validate_requirements(
    capability: dict[str, object], requirement_ids: set[str], errors: list[str]
) -> None:
    """校验 requirement 到 case 和 selector 的绑定。"""
    capability_id = str(capability.get("id", ""))
    requirements = capability.get("requirements", [])
    if not isinstance(requirements, list) or not requirements:
        fail(errors, f"{capability_id} 缺少 requirements")
        return
    for requirement in requirements:
        if not isinstance(requirement, dict):
            fail(errors, f"{capability_id} requirement 必须是对象")
            continue
        requirement_id = str(requirement.get("id", ""))
        if requirement_id in requirement_ids:
            fail(errors, f"重复 requirement id: {requirement_id}")
        requirement_ids.add(requirement_id)
        maturity = capability.get("maturity")
        criticality = capability.get("criticality")
        selectors = requirement.get("testSelectors", [])
        if maturity in ENFORCED_MATURITY and criticality == "P0" and not selectors:
            fail(errors, f"{requirement_id} 是已生效 P0，但没有 testSelectors")


def validate_source_evidence(
    capability: dict[str, object], code_root: Path | None, errors: list[str]
) -> None:
    """在提供实现仓路径时校验源码证据文件。"""
    if code_root is None:
        return
    capability_id = str(capability.get("id", ""))
    for evidence in capability.get("sourceEvidence", []):
        evidence_path = str(evidence).split(":", maxsplit=1)[0]
        if not (code_root / evidence_path).exists():
            fail(errors, f"{capability_id} 源码证据不存在: {evidence_path}")


def validate_test_selectors(
    capability: dict[str, object], code_root: Path | None, errors: list[str]
) -> None:
    """在提供实现仓路径时校验基线测试选择器。"""
    if code_root is None:
        return
    capability_id = str(capability.get("id", ""))
    for requirement in capability.get("requirements", []):
        if not isinstance(requirement, dict):
            continue
        for selector in requirement.get("testSelectors", []):
            if selector.startswith("./") or " " in selector:
                continue
            if selector.endswith((".ts", ".java")):
                pattern = f"**/{selector}"
            else:
                pattern = f"**/{selector}.java"
            if not any(code_root.glob(pattern)):
                fail(errors, f"{capability_id} 测试选择器不存在: {selector}")


def validate_diagrams(topic_root: Path, design_root: Path, errors: list[str]) -> None:
    """校验 PlantUML、SVG 和 Markdown 图链接。"""
    puml_path = topic_root / "diagram.puml"
    puml_text = puml_path.read_text()
    try:
        puml_text.encode("ascii")
    except UnicodeEncodeError:
        fail(errors, "diagram.puml 包含非 ASCII 字符")
    blocks = re.findall(r"^@startuml\s+(\S+)$", puml_text, flags=re.MULTILINE)
    for block in blocks:
        svg_path = topic_root / f"{block}.svg"
        if not svg_path.exists():
            fail(errors, f"缺少生成图: {svg_path.name}")
            continue
        try:
            element_tree.parse(svg_path)
        except element_tree.ParseError as error:
            fail(errors, f"SVG 不是有效 XML: {svg_path.name}: {error}")

    readme_path = topic_root / "README.md"
    readme = readme_path.read_text()
    registry = json.loads((topic_root / "capability-registry.json").read_text())
    design_commit = registry["baselines"]["designRepository"]["commit"]
    if "```mermaid" in readme.lower():
        fail(errors, "README.md 包含 Mermaid")
    for link in MARKDOWN_LINK_PATTERN.findall(readme):
        path_part = link.split("#", maxsplit=1)[0]
        if path_part.startswith(("http://", "https://")):
            continue
        candidate = (topic_root / path_part).resolve()
        if candidate.exists():
            continue
        try:
            relative_path = str(candidate.relative_to(design_root))
        except ValueError:
            fail(errors, f"README.md 本地链接超出设计仓: {link}")
            continue
        if not design_path_exists(design_root, relative_path, design_commit):
            fail(errors, f"README.md 本地链接不存在: {link}")
    lines = puml_text.splitlines()
    for line_number in PUML_LINK_PATTERN.findall(readme):
        index = int(line_number) - 1
        if index < 0 or index >= len(lines) or not lines[index].startswith("@startuml"):
            fail(errors, f"PlantUML 行锚点无效: L{line_number}")


def main() -> int:
    """执行全部校验并返回进程退出码。"""
    args = parse_args()
    design_root = args.design_root.resolve()
    topic_root = Path(__file__).resolve().parent
    code_root = args.code_root.resolve() if args.code_root else None
    errors: list[str] = []
    warnings = validate_registry(
        topic_root,
        design_root,
        code_root,
        args.strict_coverage,
        errors,
    )
    validate_diagrams(topic_root, design_root, errors)
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print("CampusClaw TDD Agent 设计校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
