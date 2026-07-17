#!/usr/bin/env python3
"""管理 my-skills 清单以及项目级、用户级 Skill 安装。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
GITHUB_SHORTHAND = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SKIP_PARTS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
FORBIDDEN_REPO_FILES = (
    Path(".claude-plugin/marketplace.json"),
    Path(".claude-plugin/plugin.json"),
    Path(".codex-plugin/plugin.json"),
    Path("skills-lock.json"),
    Path(".skill-lock.json"),
)


class SkillManageError(RuntimeError):
    """可直接展示给用户的管理错误。"""


@dataclass(frozen=True)
class ScopePaths:
    root: Path
    agents_skills: Path
    claude_skills: Path


@dataclass(frozen=True)
class SkillRecord:
    name: str
    kind: str
    description: str
    source: str
    source_dir: Path | None = None
    source_entry: dict[str, Any] | None = None
    relative_path: str | None = None


def default_repo() -> Path:
    override = os.environ.get("MY_SKILLS_HOME")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[3]


def user_home() -> Path:
    override = os.environ.get("SKILL_MANAGE_USER_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home().resolve()


def validate_name(value: str, label: str = "名称") -> None:
    if not NAME_PATTERN.fullmatch(value):
        raise SkillManageError(f"{label}无效：{value}；只能使用小写字母、数字和连字符")


def strip_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise SkillManageError(f"无法读取 {path}：{exc}") from exc

    if not lines or lines[0].strip() != "---":
        raise SkillManageError(f"SKILL.md 缺少 frontmatter：{path}")
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise SkillManageError(f"SKILL.md frontmatter 未闭合：{path}") from exc

    frontmatter = lines[1:end]
    result: dict[str, str] = {}
    index = 0
    while index < len(frontmatter):
        line = frontmatter[index]
        match = re.match(r"^(name|description):\s*(.*?)\s*$", line)
        if not match:
            index += 1
            continue
        key, value = match.groups()
        if value in {">", "|", ">-", "|-"} or (key == "description" and not value):
            chunks: list[str] = []
            index += 1
            while index < len(frontmatter):
                continuation = frontmatter[index]
                if continuation and not continuation[0].isspace():
                    break
                stripped = continuation.strip()
                if stripped:
                    chunks.append(stripped)
                index += 1
            result[key] = " ".join(chunks)
            continue
        result[key] = strip_yaml_scalar(value)
        index += 1
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SkillManageError(f"缺少 JSON 文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SkillManageError(
            f"JSON 无法解析：{path}:{exc.lineno}:{exc.colno} {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise SkillManageError(f"JSON 顶层必须是对象：{path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def catalog_path(repo: Path) -> Path:
    override = os.environ.get("MY_SKILLS_EXTERNAL")
    if override:
        return Path(override).expanduser().resolve()
    return repo / "external" / "skills.json"


def discover_self_built(repo: Path) -> tuple[dict[str, SkillRecord], list[str]]:
    errors: list[str] = []
    records: dict[str, SkillRecord] = {}
    skills_dir = repo / "skills"
    if not skills_dir.is_dir():
        return records, [f"缺少自建 Skill 目录：{skills_dir}"]

    for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        name = skill_dir.name
        if not NAME_PATTERN.fullmatch(name):
            errors.append(f"自建 Skill 目录名无效：{name}")
            continue
        try:
            frontmatter = parse_frontmatter(skill_file)
        except SkillManageError as exc:
            errors.append(str(exc))
            continue
        if frontmatter.get("name") != name:
            errors.append(
                f"Skill 目录名与 frontmatter name 不一致：{skill_file}，"
                f"期望 {name}，实际 {frontmatter.get('name', '<缺失>')}"
            )
        description = frontmatter.get("description", "").strip()
        if not description:
            errors.append(f"Skill 缺少非空 description：{skill_file}")
        records[name] = SkillRecord(
            name=name,
            kind="self-built",
            description=description,
            source=str(skill_dir),
            source_dir=skill_dir.resolve(),
        )
    return records, errors


def validate_relative_skill_path(value: Any, label: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return f"{label} 必须是非空字符串"
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return f"{label} 必须是来源仓库内的安全相对路径：{value!r}"
    return None


def parse_external(
    repo: Path, self_built: dict[str, SkillRecord]
) -> tuple[dict[str, Any], dict[str, SkillRecord], list[str]]:
    errors: list[str] = []
    records: dict[str, SkillRecord] = {}
    path = catalog_path(repo)
    try:
        data = load_json(path)
    except SkillManageError as exc:
        return {}, records, [str(exc)]

    entries = data.get("third_party")
    if not isinstance(entries, list):
        return data, records, [f"third_party 必须是数组：{path}"]

    source_names: set[str] = set()
    sources: set[str] = set()
    for source_index, entry in enumerate(entries):
        prefix = f"third_party[{source_index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        alias = entry.get("name")
        source = entry.get("source")
        description = entry.get("description")
        ref = entry.get("ref")
        if not isinstance(alias, str) or not NAME_PATTERN.fullmatch(alias):
            errors.append(f"{prefix}.name 无效：{alias!r}")
        elif alias in source_names:
            errors.append(f"第三方来源别名重复：{alias}")
        else:
            source_names.add(alias)
        if not isinstance(source, str) or not source.strip():
            errors.append(f"{prefix}.source 必须是非空字符串")
        elif source in sources:
            errors.append(f"第三方来源重复登记：{source}")
        else:
            sources.add(source)
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{prefix}.description 必须是非空字符串")
        if ref is not None and (not isinstance(ref, str) or not ref.strip()):
            errors.append(f"{prefix}.ref 必须是非空字符串")
        if "scope" in entry:
            errors.append(f"{prefix} 不应保存安装范围 scope")

        skills = entry.get("skills")
        if not isinstance(skills, list):
            errors.append(f"{prefix}.skills 必须是数组")
            continue
        for skill_index, skill in enumerate(skills):
            skill_prefix = f"{prefix}.skills[{skill_index}]"
            if not isinstance(skill, dict):
                errors.append(f"{skill_prefix} 必须是对象")
                continue
            name = skill.get("name")
            relative_path = skill.get("path")
            skill_description = skill.get("description")
            if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
                errors.append(f"{skill_prefix}.name 无效：{name!r}")
                continue
            path_error = validate_relative_skill_path(relative_path, f"{skill_prefix}.path")
            if path_error:
                errors.append(path_error)
            if not isinstance(skill_description, str) or not skill_description.strip():
                errors.append(f"{skill_prefix}.description 必须是非空字符串")
            if name in self_built:
                errors.append(f"第三方 Skill 与自建 Skill 重名：{name}")
            if name in records:
                errors.append(f"第三方 Skill 名称重复：{name}")
                continue
            if isinstance(source, str) and isinstance(relative_path, str):
                records[name] = SkillRecord(
                    name=name,
                    kind="third-party",
                    description=skill_description if isinstance(skill_description, str) else "",
                    source=f"{source}#{relative_path}",
                    source_entry=entry,
                    relative_path=relative_path,
                )
    return data, records, errors


def load_inventory(
    repo: Path, *, strict: bool = True
) -> tuple[dict[str, SkillRecord], dict[str, SkillRecord], dict[str, Any], list[str]]:
    self_built, errors = discover_self_built(repo)
    external_data, third_party, external_errors = parse_external(repo, self_built)
    errors.extend(external_errors)
    if strict and errors:
        raise SkillManageError("库存校验失败：\n- " + "\n- ".join(errors))
    return self_built, third_party, external_data, errors


def normalize_scope(scope: str) -> str:
    return "user" if scope == "global" else scope


def project_root(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_dir():
            raise SkillManageError(f"项目路径不是目录：{path}")
        return path
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    return Path.cwd().resolve()


def scope_paths(scope: str, project: str | None) -> ScopePaths:
    scope = normalize_scope(scope)
    if scope == "user":
        if project:
            raise SkillManageError("用户级操作不能同时指定 --project")
        root = user_home()
        if not root.is_dir():
            raise SkillManageError(f"用户目录不存在：{root}")
    else:
        root = project_root(project)
    return ScopePaths(
        root=root,
        agents_skills=root / ".agents" / "skills",
        claude_skills=root / ".claude" / "skills",
    )


def symlink_destination(path: Path) -> Path:
    raw = os.readlink(path)
    target = Path(raw)
    if not target.is_absolute():
        target = path.parent / target
    return target.resolve(strict=False)


def topology_errors(paths: ScopePaths, *, require_exists: bool) -> list[str]:
    errors: list[str] = []
    agents = paths.agents_skills
    claude = paths.claude_skills
    if agents.exists() or agents.is_symlink():
        if agents.is_symlink() or not agents.is_dir():
            errors.append(f"规范目录必须是普通目录：{agents}")
    elif require_exists:
        errors.append(f"缺少规范目录：{agents}")

    if claude.is_symlink():
        if not claude.exists():
            errors.append(f"Claude Skill 入口是断链：{claude} -> {os.readlink(claude)}")
        elif symlink_destination(claude) != agents.resolve(strict=False):
            errors.append(f"Claude Skill 入口指向错误：{claude} -> {os.readlink(claude)}")
    elif claude.exists():
        errors.append(f"Claude Skill 入口不是软链：{claude}")
    elif require_exists:
        errors.append(f"缺少 Claude Skill 入口：{claude}")
    return errors


def ensure_topology(paths: ScopePaths) -> None:
    errors = topology_errors(paths, require_exists=False)
    if errors:
        raise SkillManageError("目录初始化冲突：\n- " + "\n- ".join(errors))
    paths.agents_skills.mkdir(parents=True, exist_ok=True)
    paths.claude_skills.parent.mkdir(parents=True, exist_ok=True)
    if not paths.claude_skills.is_symlink():
        paths.claude_skills.symlink_to("../.agents/skills")


def find_record(repo: Path, name: str) -> SkillRecord:
    validate_name(name, "Skill 名称")
    self_built, third_party, _, _ = load_inventory(repo)
    if name in self_built:
        return self_built[name]
    if name in third_party:
        return third_party[name]
    raise SkillManageError(
        f"Skill 未登记：{name}；第三方 Skill 必须先写入 external/skills.json"
    )


def resolve_git_source(source: str) -> str:
    if GITHUB_SHORTHAND.fullmatch(source):
        return f"https://github.com/{source}.git"
    return source


@contextmanager
def materialize_source(entry: dict[str, Any], parent: Path) -> Iterator[Path]:
    source = str(entry["source"])
    ref = entry.get("ref")
    checkout = parent / "checkout"
    local = Path(source).expanduser()
    if local.exists():
        if not local.is_dir():
            raise SkillManageError(f"第三方本地来源不是目录：{local}")
        shutil.copytree(local.resolve(), checkout, symlinks=True)
        yield checkout
        return

    command = ["git", "clone", "--depth", "1"]
    if isinstance(ref, str) and ref:
        command.extend(["--branch", ref])
    command.extend([resolve_git_source(source), str(checkout)])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "未知 Git 错误"
        raise SkillManageError(f"获取第三方来源失败：{source}\n{message}")
    yield checkout


def discover_upstream_skills(checkout: Path) -> list[dict[str, str]]:
    discovered: dict[str, dict[str, str]] = {}
    for skill_file in sorted(checkout.rglob("SKILL.md")):
        relative = skill_file.relative_to(checkout)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        frontmatter = parse_frontmatter(skill_file)
        name = frontmatter.get("name", "").strip()
        description = frontmatter.get("description", "").strip()
        validate_name(name, f"上游 {relative} 的 Skill 名称")
        if not description:
            raise SkillManageError(f"上游 Skill 缺少 description：{relative}")
        if name in discovered:
            raise SkillManageError(f"上游存在重复 Skill 名称：{name}")
        discovered[name] = {
            "name": name,
            "path": skill_file.parent.relative_to(checkout).as_posix(),
            "description": description,
        }
    if not discovered:
        raise SkillManageError("第三方来源中未发现有效 SKILL.md")
    return [discovered[name] for name in sorted(discovered)]


def discover_selected_skills(checkout: Path, relative_paths: list[str]) -> list[dict[str, str]]:
    """只登记用户明确选择的上游 Skill 路径。"""
    discovered: dict[str, dict[str, str]] = {}
    for index, relative_path in enumerate(relative_paths):
        path_error = validate_relative_skill_path(
            relative_path, f"--skill-path[{index}]"
        )
        if path_error:
            raise SkillManageError(path_error)
        skill_dir = (checkout / relative_path).resolve()
        try:
            skill_dir.relative_to(checkout.resolve())
        except ValueError as exc:
            raise SkillManageError(
                f"第三方 Skill 路径越出来源仓库：{relative_path}"
            ) from exc
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            raise SkillManageError(f"第三方 Skill 路径失效：{relative_path}")
        frontmatter = parse_frontmatter(skill_file)
        name = frontmatter.get("name", "").strip()
        description = frontmatter.get("description", "").strip()
        validate_name(name, f"上游 {relative_path} 的 Skill 名称")
        if not description:
            raise SkillManageError(f"上游 Skill 缺少 description：{relative_path}")
        if name in discovered:
            raise SkillManageError(f"选择的上游 Skill 名称重复：{name}")
        discovered[name] = {
            "name": name,
            "path": Path(relative_path).as_posix(),
            "description": description,
        }
    if not discovered:
        raise SkillManageError("至少需要一个 --skill-path")
    return [discovered[name] for name in sorted(discovered)]


def refresh_registered_skills(
    checkout: Path, configured: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """刷新已获准的 Skill 元数据，不自动扩大可信清单。"""
    refreshed: list[dict[str, str]] = []
    for skill in configured:
        name = str(skill["name"])
        relative_path = str(skill["path"])
        source_dir = validate_source_path(checkout, relative_path, name)
        description = parse_frontmatter(source_dir / "SKILL.md").get(
            "description", ""
        ).strip()
        if not description:
            raise SkillManageError(f"上游 Skill 缺少 description：{relative_path}")
        refreshed.append(
            {
                "name": name,
                "path": relative_path,
                "description": description,
            }
        )
    return sorted(refreshed, key=lambda item: item["name"])


def validate_source_path(checkout: Path, relative_path: str, expected_name: str) -> Path:
    source_dir = (checkout / relative_path).resolve()
    try:
        source_dir.relative_to(checkout.resolve())
    except ValueError as exc:
        raise SkillManageError(f"第三方 Skill 路径越出来源仓库：{relative_path}") from exc
    skill_file = source_dir / "SKILL.md"
    if not source_dir.is_dir() or not skill_file.is_file():
        raise SkillManageError(f"第三方 Skill 路径失效：{relative_path}")
    actual_name = parse_frontmatter(skill_file).get("name")
    if actual_name != expected_name:
        raise SkillManageError(
            f"第三方 Skill 名称变化：清单为 {expected_name}，上游为 {actual_name!r}"
        )
    for path in source_dir.rglob("*"):
        if path.is_symlink():
            try:
                path.resolve().relative_to(checkout.resolve())
            except (OSError, ValueError) as exc:
                raise SkillManageError(f"第三方 Skill 包含越出来源仓库的软链：{path}") from exc
    return source_dir


@contextmanager
def staged_third_party(record: SkillRecord, target_parent: Path) -> Iterator[Path]:
    if record.source_entry is None or record.relative_path is None:
        raise SkillManageError(f"第三方 Skill 清单不完整：{record.name}")
    temporary = Path(tempfile.mkdtemp(prefix=".skill-manage-", dir=target_parent))
    try:
        with materialize_source(record.source_entry, temporary) as checkout:
            source_dir = validate_source_path(checkout, record.relative_path, record.name)
            staged = temporary / "staged"
            shutil.copytree(
                source_dir,
                staged,
                symlinks=False,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            yield staged
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def file_manifest(root: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            manifest[relative] = f"link:{os.readlink(path)}"
        elif path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest[relative] = f"file:{digest}"
    return manifest


def describe_changes(old: Path, new: Path) -> str:
    old_manifest = file_manifest(old)
    new_manifest = file_manifest(new)
    old_keys = set(old_manifest)
    new_keys = set(new_manifest)
    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed = sorted(key for key in old_keys & new_keys if old_manifest[key] != new_manifest[key])
    lines = [f"新增 {len(added)}，删除 {len(removed)}，修改 {len(changed)}"]
    for label, values in (("新增", added), ("删除", removed), ("修改", changed)):
        if values:
            preview = ", ".join(values[:8])
            suffix = " …" if len(values) > 8 else ""
            lines.append(f"{label}：{preview}{suffix}")
    return "\n".join(lines)


def install_skill(repo: Path, name: str, scope: str, project: str | None) -> None:
    record = find_record(repo, name)
    paths = scope_paths(scope, project)
    target = paths.agents_skills / name

    if record.kind == "self-built":
        assert record.source_dir is not None
        if target.is_symlink():
            if target.exists() and target.resolve() == record.source_dir:
                ensure_topology(paths)
                print(f"已经安装：{target} -> {record.source_dir}")
                return
            raise SkillManageError(f"目标是其他软链：{target} -> {os.readlink(target)}")
        if target.exists():
            raise SkillManageError(f"目标已存在且不是预期软链：{target}")
        ensure_topology(paths)
        target.symlink_to(record.source_dir)
        print(f"已安装自建 Skill：{target} -> {record.source_dir}")
        return

    if target.exists() or target.is_symlink():
        raise SkillManageError(f"目标已存在；首次安装不会覆盖：{target}")
    ensure_topology(paths)
    with staged_third_party(record, paths.agents_skills) as staged:
        shutil.copytree(staged, target)
    print(f"已安装第三方 Skill：{name} -> {target}")


def update_skill(
    repo: Path, name: str, scope: str, project: str | None, confirmed: bool
) -> None:
    record = find_record(repo, name)
    paths = scope_paths(scope, project)
    errors = topology_errors(paths, require_exists=True)
    if errors:
        raise SkillManageError("目录拓扑无效：\n- " + "\n- ".join(errors))
    target = paths.agents_skills / name

    if record.kind == "self-built":
        assert record.source_dir is not None
        if not target.is_symlink() or not target.exists() or target.resolve() != record.source_dir:
            raise SkillManageError(f"自建 Skill 未按权威源码软链安装：{target}")
        print(f"自建 Skill 直接读取权威源码，无需更新安装项：{target}")
        return

    if target.is_symlink() or not target.is_dir():
        raise SkillManageError(f"第三方 Skill 目标不是可更新的普通目录：{target}")
    with staged_third_party(record, paths.agents_skills) as staged:
        if file_manifest(target) == file_manifest(staged):
            print(f"已经是最新内容：{target}")
            return
        summary = describe_changes(target, staged)
        print(f"待更新 {name}：\n{summary}")
        if not confirmed:
            raise SkillManageError("更新会替换现有目录；确认后使用 --yes 重新执行")
        backup = staged.parent / "backup"
        os.replace(target, backup)
        try:
            os.replace(staged, target)
        except Exception:
            os.replace(backup, target)
            raise
        shutil.rmtree(backup)
    print(f"已更新第三方 Skill：{target}")


def uninstall_skill(
    repo: Path, name: str, scope: str, project: str | None, confirmed: bool
) -> None:
    record = find_record(repo, name)
    paths = scope_paths(scope, project)
    target = paths.agents_skills / name
    if not target.exists() and not target.is_symlink():
        print(f"已经不存在：{target}")
        return

    if record.kind == "self-built":
        assert record.source_dir is not None
        if not target.is_symlink() or not target.exists() or target.resolve() != record.source_dir:
            raise SkillManageError(f"拒绝移除非权威源码软链：{target}")
        target.unlink()
        print(f"已卸载自建 Skill：{target}")
        return

    if target.is_symlink() or not target.is_dir():
        raise SkillManageError(f"拒绝移除非普通第三方 Skill 目录：{target}")
    skill_file = target / "SKILL.md"
    if not skill_file.is_file() or parse_frontmatter(skill_file).get("name") != name:
        raise SkillManageError(f"目标目录无法确认为 {name}：{target}")
    if not confirmed:
        raise SkillManageError(f"卸载会删除目录 {target}；确认后使用 --yes 重新执行")
    shutil.rmtree(target)
    print(f"已卸载第三方 Skill：{target}")


def readme_errors(repo: Path, self_built: dict[str, SkillRecord]) -> list[str]:
    path = repo / "README.md"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"缺少 README：{path}"]
    errors: list[str] = []
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
    return errors


def audit_scope(
    repo: Path,
    self_built: dict[str, SkillRecord],
    third_party: dict[str, SkillRecord],
    paths: ScopePaths,
) -> list[str]:
    errors = topology_errors(paths, require_exists=True)
    if errors or not paths.agents_skills.is_dir():
        return errors
    for target in sorted(paths.agents_skills.iterdir()):
        if target.name.startswith("."):
            continue
        name = target.name
        if name in self_built:
            source_dir = self_built[name].source_dir
            if not target.is_symlink() or not target.exists() or target.resolve() != source_dir:
                errors.append(f"自建 Skill 不是权威源码软链：{target}")
        elif name in third_party:
            if target.is_symlink() or not target.is_dir():
                errors.append(f"第三方 Skill 不是普通目录：{target}")
                continue
            skill_file = target / "SKILL.md"
            try:
                actual = parse_frontmatter(skill_file).get("name")
            except SkillManageError as exc:
                errors.append(str(exc))
                continue
            if actual != name:
                errors.append(f"第三方 Skill 目录名与 frontmatter 不一致：{target}")
        else:
            errors.append(f"存在未登记 Skill：{target}")
    return errors


def audit(repo: Path, scope: str | None, project: str | None) -> None:
    self_built, third_party, _, errors = load_inventory(repo, strict=False)
    errors.extend(readme_errors(repo, self_built))
    for relative in FORBIDDEN_REPO_FILES:
        path = repo / relative
        if path.exists() or path.is_symlink():
            errors.append(f"仓库包含非目标清单或状态文件：{relative}")
    if scope:
        errors.extend(audit_scope(repo, self_built, third_party, scope_paths(scope, project)))
    if errors:
        raise SkillManageError("审计失败：\n- " + "\n- ".join(errors))
    message = f"审计通过：{len(self_built)} 个自建 Skill，{len(third_party)} 个第三方 Skill"
    if scope:
        message += f"，{normalize_scope(scope)} 级目录拓扑有效"
    print(message)


def list_inventory(repo: Path) -> None:
    self_built, third_party, _, _ = load_inventory(repo)
    print("name\ttype\tsource\tdescription")
    for record in sorted((*self_built.values(), *third_party.values()), key=lambda item: item.name):
        print(f"{record.name}\t{record.kind}\t{record.source}\t{record.description}")


def external_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    entries = data.get("third_party")
    if not isinstance(entries, list):
        raise SkillManageError("external/skills.json 的 third_party 必须是数组")
    return entries


def external_add(
    repo: Path,
    alias: str,
    source: str,
    description: str,
    ref: str | None,
    skill_paths: list[str],
) -> None:
    validate_name(alias, "第三方来源别名")
    _, _, data, errors = load_inventory(repo, strict=False)
    if errors:
        raise SkillManageError("现有清单无法安全修改：\n- " + "\n- ".join(errors))
    entries = external_entries(data)
    if any(entry.get("name") == alias for entry in entries if isinstance(entry, dict)):
        raise SkillManageError(f"第三方来源已存在：{alias}")
    if any(entry.get("source") == source for entry in entries if isinstance(entry, dict)):
        raise SkillManageError(f"第三方来源地址已登记：{source}")
    entry: dict[str, Any] = {
        "name": alias,
        "source": source,
        "description": description,
        "skills": [],
    }
    if ref:
        entry["ref"] = ref
    with tempfile.TemporaryDirectory(prefix="skill-manage-source-") as temporary:
        with materialize_source(entry, Path(temporary)) as checkout:
            entry["skills"] = (
                discover_selected_skills(checkout, skill_paths)
                if skill_paths
                else discover_upstream_skills(checkout)
            )
    candidate = {"third_party": [*entries, entry]}
    candidate_path = catalog_path(repo)
    write_json(candidate_path, candidate)
    _, _, _, candidate_errors = load_inventory(repo, strict=False)
    if candidate_errors:
        write_json(candidate_path, data)
        raise SkillManageError("新增来源会破坏清单：\n- " + "\n- ".join(candidate_errors))
    print(f"已登记第三方来源：{alias}，发现 {len(entry['skills'])} 个 Skill")


def external_refresh(repo: Path, aliases: list[str], discover_new: bool) -> None:
    _, _, data, errors = load_inventory(repo, strict=False)
    if errors:
        raise SkillManageError("刷新前清单校验失败：\n- " + "\n- ".join(errors))
    entries = external_entries(data)
    by_name = {entry.get("name"): entry for entry in entries if isinstance(entry, dict)}
    selected = aliases or sorted(name for name in by_name if isinstance(name, str))
    missing = [name for name in selected if name not in by_name]
    if missing:
        raise SkillManageError(f"未知第三方来源：{', '.join(missing)}")

    candidate = json.loads(json.dumps(data))
    candidate_by_name = {entry["name"]: entry for entry in candidate["third_party"]}
    for alias in selected:
        entry = candidate_by_name[alias]
        with tempfile.TemporaryDirectory(prefix="skill-manage-source-") as temporary:
            with materialize_source(entry, Path(temporary)) as checkout:
                entry["skills"] = (
                    discover_upstream_skills(checkout)
                    if discover_new
                    else refresh_registered_skills(checkout, entry["skills"])
                )
        print(f"已刷新第三方来源：{alias}，发现 {len(entry['skills'])} 个 Skill")
    write_json(catalog_path(repo), candidate)
    _, _, _, candidate_errors = load_inventory(repo, strict=False)
    if candidate_errors:
        write_json(catalog_path(repo), data)
        raise SkillManageError("刷新结果会破坏清单：\n- " + "\n- ".join(candidate_errors))


def external_remove(repo: Path, alias: str, confirmed: bool) -> None:
    if not confirmed:
        raise SkillManageError("移除来源会修改可信清单；确认后使用 --yes 重新执行")
    _, _, data, errors = load_inventory(repo, strict=False)
    if errors:
        raise SkillManageError("移除前清单校验失败：\n- " + "\n- ".join(errors))
    entries = external_entries(data)
    remaining = [entry for entry in entries if entry.get("name") != alias]
    if len(remaining) == len(entries):
        raise SkillManageError(f"未知第三方来源：{alias}")
    write_json(catalog_path(repo), {"third_party": remaining})
    print(f"已移除第三方来源：{alias}；未修改任何已安装 Skill")


def external_list(repo: Path) -> None:
    _, _, data, errors = load_inventory(repo, strict=False)
    if errors:
        raise SkillManageError("清单校验失败：\n- " + "\n- ".join(errors))
    print("source-name\tsource\tskills\tdescription")
    for entry in sorted(external_entries(data), key=lambda item: item["name"]):
        print(
            f"{entry['name']}\t{entry['source']}\t{len(entry['skills'])}\t{entry['description']}"
        )


def add_scope_options(parser: argparse.ArgumentParser, *, optional: bool = False) -> None:
    parser.add_argument(
        "--scope",
        choices=("project", "user", "global"),
        default=None if optional else "project",
        help="安装范围；global 是 user 的兼容别名",
    )
    parser.add_argument("--project", help="项目目录；默认使用当前 Git 仓库根目录")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="管理 my-skills 与共享 Skill 安装目录")
    parser.add_argument("--repo", type=Path, default=default_repo(), help="my-skills 仓库路径")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="列出所有自建和第三方具体 Skill")

    init_parser = subparsers.add_parser("init", help="初始化共享 Skill 目录")
    add_scope_options(init_parser)

    install_parser = subparsers.add_parser("install", help="安装已登记 Skill")
    install_parser.add_argument("name")
    add_scope_options(install_parser)

    update_parser = subparsers.add_parser("update", help="更新已安装 Skill")
    update_parser.add_argument("name")
    update_parser.add_argument("--yes", action="store_true", help="确认替换第三方目录")
    add_scope_options(update_parser)

    uninstall_parser = subparsers.add_parser("uninstall", help="卸载指定 Skill")
    uninstall_parser.add_argument("name")
    uninstall_parser.add_argument("--yes", action="store_true", help="确认删除第三方目录")
    add_scope_options(uninstall_parser)

    audit_parser = subparsers.add_parser("audit", help="审计仓库和可选安装范围")
    add_scope_options(audit_parser, optional=True)

    external_parser = subparsers.add_parser("external", help="维护第三方 Skill 清单")
    external_subparsers = external_parser.add_subparsers(dest="external_command", required=True)
    external_subparsers.add_parser("list", help="列出第三方来源")
    external_add_parser = external_subparsers.add_parser("add", help="新增并扫描第三方来源")
    external_add_parser.add_argument("name")
    external_add_parser.add_argument("source")
    external_add_parser.add_argument("--description", required=True)
    external_add_parser.add_argument("--ref", help="可选 Git 分支或标签")
    external_add_parser.add_argument(
        "--skill-path",
        action="append",
        default=[],
        help="只登记指定的 Skill 相对路径；可重复传入",
    )
    external_refresh_parser = external_subparsers.add_parser("refresh", help="刷新第三方来源")
    external_refresh_parser.add_argument("names", nargs="*")
    external_refresh_parser.add_argument(
        "--discover-new",
        action="store_true",
        help="重新扫描来源中的全部 Skill，并扩大当前清单",
    )
    external_remove_parser = external_subparsers.add_parser("remove", help="移除第三方来源")
    external_remove_parser.add_argument("name")
    external_remove_parser.add_argument("--yes", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        print(f"skill-manage: 仓库目录不存在：{repo}", file=sys.stderr)
        return 2
    try:
        if args.command == "list":
            list_inventory(repo)
        elif args.command == "init":
            paths = scope_paths(args.scope, args.project)
            ensure_topology(paths)
            print(f"目录已就绪：{paths.agents_skills}")
            print(f"Claude 入口：{paths.claude_skills} -> ../.agents/skills")
        elif args.command == "install":
            install_skill(repo, args.name, args.scope, args.project)
        elif args.command == "update":
            update_skill(repo, args.name, args.scope, args.project, args.yes)
        elif args.command == "uninstall":
            uninstall_skill(repo, args.name, args.scope, args.project, args.yes)
        elif args.command == "audit":
            audit_scope_name = args.scope or ("project" if args.project else None)
            audit(repo, audit_scope_name, args.project)
        elif args.command == "external":
            if args.external_command == "list":
                external_list(repo)
            elif args.external_command == "add":
                external_add(
                    repo,
                    args.name,
                    args.source,
                    args.description,
                    args.ref,
                    args.skill_path,
                )
            elif args.external_command == "refresh":
                external_refresh(repo, args.names, args.discover_new)
            elif args.external_command == "remove":
                external_remove(repo, args.name, args.yes)
        return 0
    except SkillManageError as exc:
        print(f"skill-manage: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
