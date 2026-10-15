"""Install the checked-in growth skills into this project's Claude skill path.

Existing modified skills or unrelated MCP entries are preserved. This script
does not install packages, call models, start workers or publish anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("mas-ai-growth-ops", "mas-ai-linkedin", "mas-ai-prospecting")


def tree_hashes(folder: Path) -> dict[str, str]:
    if folder.is_symlink():
        raise ValueError(f"Refusing a symlink skill directory: {folder}")
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Refusing a symlink in a skill: {path}")
        if path.is_file():
            result[path.relative_to(folder).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def install(root: Path, python_executable: str, configure_mcp: bool = False,
            remotion_source: Path | None = None) -> dict:
    root = root.resolve()
    source_root = root / ".agents" / "skills"
    claude = root / ".claude"
    destination = claude / "skills"
    if claude.is_symlink() or destination.is_symlink():
        raise ValueError("Refusing a symlink Claude configuration directory")
    receipt_path = claude / "mas-ai-skill-install.json"
    previous = load_json(receipt_path)
    plans = []
    sources = [(name, source_root / name) for name in NAMES]
    if remotion_source:
        sources.append(("remotion-best-practices", remotion_source.resolve()))
    installed = dict(previous.get("skills", {}))
    for name, source in sources:
        if not (source / "SKILL.md").is_file():
            raise ValueError(f"Missing source skill: {source}")
        expected = tree_hashes(source)
        target = destination / name
        current = tree_hashes(target) if target.exists() else None
        old = previous.get("skills", {}).get(name)
        if current is not None and current != expected and current != old:
            raise ValueError(f"Preserved locally modified skill: {target}. Reconcile it before installing.")
        if current != expected:
            plans.append((source, target))
        installed[name] = expected

    mcp_path = root / ".mcp.json"
    config = load_json(mcp_path) if configure_mcp else None
    server = {
        "type": "stdio", "command": python_executable,
        "args": [str(root / "scripts" / "growthops_mcp.py")],
        "env": {"CONTENTOPS_PROJECT_ROOT": str(root)},
    }
    if configure_mcp:
        if mcp_path.is_symlink():
            raise ValueError("Refusing a symlink MCP configuration")
        servers = config.setdefault("mcpServers", {})
        current = servers.get("contentops-growth")
        if current is not None and current != server and current != previous.get("mcp"):
            raise ValueError("Preserved existing contentops-growth MCP entry; reconcile it first")
        servers["contentops-growth"] = server

    # All conflict checks precede mutations.
    destination.mkdir(parents=True, exist_ok=True)
    for source, target in plans:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    if configure_mcp:
        temporary = mcp_path.with_suffix(".json.growth-tmp")
        temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        temporary.replace(mcp_path)
    receipt = {"skills": installed, "mcp": server if configure_mcp else previous.get("mcp")}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {"installed": [name for name, _ in sources], "changed": len(plans),
            "mcp_configured": configure_mcp, "root": str(root)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--configure-mcp", action="store_true")
    parser.add_argument("--python", default=sys.executable, dest="python_executable")
    parser.add_argument("--remotion-source", type=Path)
    args = parser.parse_args()
    print(json.dumps(install(args.root, args.python_executable, args.configure_mcp,
                             args.remotion_source), indent=2))


if __name__ == "__main__":
    main()
