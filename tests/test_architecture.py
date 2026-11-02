"""Enforce the package dependency boundaries in architecture.md §4."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "rfp_eval"
ALLOWED = {
    "domain": set(),
    "tools": {"domain", "config", "security"},
    "db": {"domain", "config"},
    "security": {"domain", "config"},
    "llm": {"domain", "config", "security"},
    "agents": {"domain", "llm", "security"},
    "orchestration": {"domain", "tools", "agents", "db", "llm", "security"},
    "services": {"domain", "tools", "db", "agents"},
    "ui": {
        "domain",
        "tools",
        "db",
        "agents",
        "llm",
        "security",
        "orchestration",
        "services",
        "config",
    },
}


def test_import_boundaries() -> None:
    """Every package import follows the declared inward dependency direction."""
    violations: list[str] = []
    for path in ROOT.rglob("*.py"):
        layer = path.relative_to(ROOT).parts[0]
        if layer not in ALLOWED:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                if (module == "streamlit" or module.startswith("streamlit.")) and layer != "ui":
                    violations.append(f"{path}: Streamlit import")
                if not module.startswith("rfp_eval."):
                    continue
                target = module.split(".")[1]
                if target == layer:
                    if (
                        layer == "tools"
                        and path.stem in {"ranking_tool", "rounding", "weight_gate"}
                        and module != f"rfp_eval.tools.{path.stem}"
                    ):
                        violations.append(f"{path}: pure tool imports {module}")
                    continue
                if target not in ALLOWED[layer]:
                    violations.append(f"{path}: {module}")
                if (
                    layer == "tools"
                    and path.stem in {"ranking_tool", "rounding", "weight_gate"}
                    and target != "domain"
                ):
                    violations.append(f"{path}: pure tool imports {module}")
                if (
                    layer == "llm"
                    and target == "security"
                    and module != "rfp_eval.security.redaction"
                ):
                    violations.append(f"{path}: LLM imports {module}")
    assert not violations, "\n".join(violations)
