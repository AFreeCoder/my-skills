#!/usr/bin/env python3
"""只读审计 my-skills 的自建库存和第三方收藏清单。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def parse_args() -> argparse.Namespace:
    default_repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="审计 my-skills 清单一致性")
    parser.add_argument("--repo", type=Path, default=default_repo, help="my-skills 仓库路径")
    return parser.parse_args()


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"缺少 JSON 文件：{path}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"JSON 无法解析：{path}:{exc.lineno}:{exc.colno} {exc.msg}")
        return {}

    if not isinstance(value, dict):
        errors.append(f"JSON 顶层必须是对象：{path}")
        return {}
    return value


def parse_frontmatter(path: Path, errors: list[str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append(f"SKILL.md 缺少 frontmatter：{path}")
        return {}

    try:
        end_index = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        errors.append(f"SKILL.md frontmatter 未闭合：{path}")
        return {}

    result: dict[str, str] = {}
    for line in lines[1:end_index]:
        match = re.match(r"^(name|description):\s*(.+?)\s*$", line)
        if match:
            result[match.group(1)] = match.group(2).strip().strip("\"'")
    return result


def discover_self_built(repo: Path, errors: list[str]) -> set[str]:
    skills_dir = repo / "skills"
    if not skills_dir.is_dir():
        errors.append(f"缺少自建 Skill 目录：{skills_dir}")
        return set()

    names: set[str] = set()
    for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        name = skill_dir.name
        names.add(name)
        if not NAME_PATTERN.fullmatch(name):
            errors.append(f"自建 Skill 目录名无效：{name}")
        frontmatter = parse_frontmatter(skill_file, errors)
        if frontmatter.get("name") != name:
            errors.append(
                f"Skill 目录名与 frontmatter name 不一致：{skill_file}，"
                f"期望 {name}，实际 {frontmatter.get('name', '<缺失>')}"
            )
        if not frontmatter.get("description"):
            errors.append(f"Skill 缺少非空 description：{skill_file}")
    return names


def marketplace_names(repo: Path, errors: list[str]) -> set[str]:
    path = repo / ".claude-plugin" / "marketplace.json"
    data = load_json(path, errors)
    plugins = data.get("plugins", [])
    if not isinstance(plugins, list):
        errors.append(f"marketplace plugins 必须是数组：{path}")
        return set()

    names: set[str] = set()
    for plugin in plugins:
        if not isinstance(plugin, dict):
            errors.append(f"marketplace plugin 条目必须是对象：{path}")
            continue
        skill_paths = plugin.get("skills", [])
        if not isinstance(skill_paths, list):
            errors.append(f"marketplace skills 必须是数组：{path}")
            continue
        for skill_path in skill_paths:
            if not isinstance(skill_path, str) or not skill_path:
                errors.append(f"marketplace Skill 路径无效：{skill_path!r}")
                continue
            if not skill_path.startswith("./skills/"):
                errors.append(f"marketplace Skill 路径必须位于 ./skills/：{skill_path}")
            name = Path(skill_path).name
            if name in names:
                errors.append(f"marketplace Skill 重复注册：{name}")
            names.add(name)
    return names


def audit_readme(repo: Path, self_built: set[str], errors: list[str]) -> None:
    path = repo / "README.md"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"缺少 README：{path}")
        return

    count_match = re.search(r"当前共收录 `([0-9]+)` 个自建 Skill", text)
    if not count_match:
        errors.append("README 缺少自建 Skill 数量声明")
    elif int(count_match.group(1)) != len(self_built):
        errors.append(
            f"README 自建 Skill 数量不一致：声明 {count_match.group(1)}，实际 {len(self_built)}"
        )

    for name in sorted(self_built):
        if not re.search(rf"^\| `{re.escape(name)}` \|", text, re.MULTILINE):
            errors.append(f"README 当前收录表缺少自建 Skill：{name}")


def audit_external(repo: Path, self_built: set[str], errors: list[str]) -> int:
    path = repo / "external" / "skills.json"
    data = load_json(path, errors)
    entries = data.get("third_party", [])
    if not isinstance(entries, list):
        errors.append(f"third_party 必须是数组：{path}")
        return 0

    seen: set[str] = set()
    for index, entry in enumerate(entries):
        prefix = f"third_party[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} 必须是对象")
            continue

        name = entry.get("name")
        source = entry.get("source")
        scope = entry.get("scope")
        description = entry.get("description")

        if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
            errors.append(f"{prefix}.name 无效：{name!r}")
            continue
        if name in seen:
            errors.append(f"第三方 Skill 别名重复：{name}")
        seen.add(name)
        if name in self_built:
            errors.append(f"第三方 Skill 别名与自建 Skill 重名：{name}")
        if not isinstance(source, str) or not source.strip():
            errors.append(f"{prefix}.source 必须是非空字符串")
        if scope not in {"project", "global"}:
            errors.append(f"{prefix}.scope 必须是 project 或 global：{scope!r}")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{prefix}.description 必须是非空字符串")
    return len(entries)


def main() -> int:
    args = parse_args()
    repo = args.repo.expanduser().resolve()
    errors: list[str] = []

    if not repo.is_dir():
        print(f"审计失败：仓库目录不存在：{repo}", file=sys.stderr)
        return 2

    self_built = discover_self_built(repo, errors)
    registered = marketplace_names(repo, errors)
    missing = self_built - registered
    extra = registered - self_built
    if missing:
        errors.append(f"marketplace 缺少注册：{', '.join(sorted(missing))}")
    if extra:
        errors.append(f"marketplace 存在无对应目录的注册：{', '.join(sorted(extra))}")

    audit_readme(repo, self_built, errors)
    external_count = audit_external(repo, self_built, errors)

    if errors:
        print("Skill 清单审计失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Skill 清单审计通过：{len(self_built)} 个自建 Skill，{external_count} 个第三方收藏项。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
