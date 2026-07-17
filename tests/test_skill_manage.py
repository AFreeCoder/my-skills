#!/usr/bin/env python3
"""skill-manage 控制面的端到端测试。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REAL_REPO = Path(__file__).resolve().parents[1]
MANAGER = REAL_REPO / "skills" / "skill-manage" / "scripts" / "skill_manage.py"


class SkillManageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="skill-manage-test-")
        self.base = Path(self.temporary.name)
        self.repo = self.base / "my-skills"
        self.user_home = self.base / "home"
        self.project = self.base / "project"
        self.repo.mkdir()
        self.user_home.mkdir()
        self.project.mkdir()
        self.make_skill(self.repo / "skills" / "demo-skill", "demo-skill", "自建测试 Skill。")
        (self.repo / "external").mkdir()
        self.write_catalog({"third_party": []})
        self.write_readme()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_skill(self, directory: Path, name: str, description: str, body: str = "初始内容") -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(
            "\n".join(
                [
                    "---",
                    f"name: {name}",
                    f"description: {description}",
                    "---",
                    "",
                    f"# {name}",
                    "",
                    body,
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def write_readme(self) -> None:
        (self.repo / "README.md").write_text(
            "\n".join(
                [
                    "# My Skills",
                    "",
                    "当前共收录 `1` 个自建 Skill。",
                    "",
                    "| Skill | 说明 |",
                    "| --- | --- |",
                    "| `demo-skill` | 自建测试 Skill。 |",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def write_catalog(self, value: dict[str, object]) -> None:
        path = self.repo / "external" / "skills.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def read_catalog(self) -> dict[str, object]:
        return json.loads((self.repo / "external" / "skills.json").read_text(encoding="utf-8"))

    def run_manager(
        self, *args: str, expected: int = 0, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["SKILL_MANAGE_USER_HOME"] = str(self.user_home)
        result = subprocess.run(
            [sys.executable, str(MANAGER), "--repo", str(self.repo), *args],
            cwd=cwd or self.project,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != expected:
            self.fail(
                f"命令返回码不符：{args}\n期望：{expected}\n实际：{result.returncode}"
                f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def make_external_source(self, skill_name: str = "third-skill") -> Path:
        source = self.base / "external-source"
        self.make_skill(source / "skills" / skill_name, skill_name, "第三方测试 Skill。")
        return source

    def add_external_source(self, skill_name: str = "third-skill") -> Path:
        source = self.make_external_source(skill_name)
        self.run_manager(
            "external",
            "add",
            "test-source",
            str(source),
            "--description",
            "第三方测试来源",
        )
        return source

    def test_audit_and_list_inventory(self) -> None:
        result = self.run_manager("audit")
        self.assertIn("1 个自建 Skill，0 个第三方 Skill", result.stdout)
        result = self.run_manager("list")
        self.assertIn("demo-skill\tself-built", result.stdout)
        self.assertNotIn("scope", result.stdout.splitlines()[0])

    def test_init_project_and_user_topology(self) -> None:
        self.run_manager("init", "--project", str(self.project))
        project_link = self.project / ".claude" / "skills"
        self.assertTrue((self.project / ".agents" / "skills").is_dir())
        self.assertTrue(project_link.is_symlink())
        self.assertEqual(os.readlink(project_link), "../.agents/skills")
        self.run_manager("init", "--project", str(self.project))

        self.run_manager("init", "--scope", "user")
        user_link = self.user_home / ".claude" / "skills"
        self.assertTrue((self.user_home / ".agents" / "skills").is_dir())
        self.assertTrue(user_link.is_symlink())
        self.assertEqual(os.readlink(user_link), "../.agents/skills")

    def test_init_rejects_existing_claude_directory_without_partial_creation(self) -> None:
        (self.project / ".claude" / "skills").mkdir(parents=True)
        result = self.run_manager("init", "--project", str(self.project), expected=1)
        self.assertIn("Claude Skill 入口不是软链", result.stderr)
        self.assertFalse((self.project / ".agents").exists())

    def test_install_self_built_in_project_and_user(self) -> None:
        self.run_manager("install", "demo-skill", "--project", str(self.project))
        target = self.project / ".agents" / "skills" / "demo-skill"
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(), (self.repo / "skills" / "demo-skill").resolve())
        self.run_manager("install", "demo-skill", "--project", str(self.project))

        self.run_manager("install", "demo-skill", "--scope", "user")
        user_target = self.user_home / ".agents" / "skills" / "demo-skill"
        self.assertTrue(user_target.is_symlink())
        self.assertEqual(user_target.resolve(), (self.repo / "skills" / "demo-skill").resolve())

    def test_install_requires_fact_source_registration(self) -> None:
        result = self.run_manager(
            "install", "owner/repo", "--project", str(self.project), expected=1
        )
        self.assertIn("Skill 名称无效", result.stderr)
        result = self.run_manager(
            "install", "unknown-skill", "--project", str(self.project), expected=1
        )
        self.assertIn("Skill 未登记", result.stderr)

    def test_external_add_refresh_and_list(self) -> None:
        source = self.add_external_source()
        catalog = self.read_catalog()
        entry = catalog["third_party"][0]
        self.assertNotIn("scope", entry)
        self.assertEqual(entry["skills"][0]["name"], "third-skill")
        self.assertEqual(entry["skills"][0]["path"], "skills/third-skill")

        self.make_skill(source / "skills" / "new-skill", "new-skill", "刷新后新增 Skill。")
        self.run_manager("external", "refresh", "test-source")
        names = [item["name"] for item in self.read_catalog()["third_party"][0]["skills"]]
        self.assertEqual(names, ["new-skill", "third-skill"])
        result = self.run_manager("external", "list")
        self.assertIn("test-source", result.stdout)
        self.assertIn("\t2\t", result.stdout)

    def test_external_collision_rolls_back_catalog(self) -> None:
        source = self.make_external_source("demo-skill")
        result = self.run_manager(
            "external",
            "add",
            "conflicting-source",
            str(source),
            "--description",
            "冲突来源",
            expected=1,
        )
        self.assertIn("第三方 Skill 与自建 Skill 重名", result.stderr)
        self.assertEqual(self.read_catalog(), {"third_party": []})

    def test_external_install_update_and_uninstall(self) -> None:
        source = self.add_external_source()
        self.run_manager("install", "third-skill", "--project", str(self.project))
        target = self.project / ".agents" / "skills" / "third-skill"
        self.assertTrue(target.is_dir())
        self.assertFalse(target.is_symlink())
        self.assertIn("初始内容", (target / "SKILL.md").read_text(encoding="utf-8"))
        self.run_manager("audit", "--project", str(self.project))

        self.make_skill(
            source / "skills" / "third-skill",
            "third-skill",
            "第三方测试 Skill。",
            body="上游更新内容",
        )
        result = self.run_manager(
            "update", "third-skill", "--project", str(self.project), expected=1
        )
        self.assertIn("确认后使用 --yes", result.stderr)
        self.assertIn("初始内容", (target / "SKILL.md").read_text(encoding="utf-8"))
        self.run_manager(
            "update", "third-skill", "--project", str(self.project), "--yes"
        )
        self.assertIn("上游更新内容", (target / "SKILL.md").read_text(encoding="utf-8"))

        self.run_manager(
            "uninstall", "third-skill", "--project", str(self.project), expected=1
        )
        self.run_manager(
            "uninstall", "third-skill", "--project", str(self.project), "--yes"
        )
        self.assertFalse(target.exists())

    def test_uninstall_self_built_only_removes_expected_link(self) -> None:
        self.run_manager("install", "demo-skill", "--project", str(self.project))
        target = self.project / ".agents" / "skills" / "demo-skill"
        self.run_manager("uninstall", "demo-skill", "--project", str(self.project))
        self.assertFalse(target.exists())
        self.run_manager("uninstall", "demo-skill", "--project", str(self.project))

        target.mkdir()
        result = self.run_manager(
            "uninstall", "demo-skill", "--project", str(self.project), expected=1
        )
        self.assertIn("拒绝移除非权威源码软链", result.stderr)

    def test_external_remove_requires_confirmation_and_keeps_installation(self) -> None:
        self.add_external_source()
        self.run_manager("install", "third-skill", "--project", str(self.project))
        self.run_manager("external", "remove", "test-source", expected=1)
        self.run_manager("external", "remove", "test-source", "--yes")
        self.assertEqual(self.read_catalog(), {"third_party": []})
        self.assertTrue((self.project / ".agents" / "skills" / "third-skill").is_dir())

    def test_audit_rejects_forbidden_file_and_unknown_installed_skill(self) -> None:
        forbidden = self.repo / ".claude-plugin" / "marketplace.json"
        forbidden.parent.mkdir()
        forbidden.write_text("{}\n", encoding="utf-8")
        result = self.run_manager("audit", expected=1)
        self.assertIn("仓库包含非目标清单或状态文件", result.stderr)
        forbidden.unlink()

        self.run_manager("install", "demo-skill", "--project", str(self.project))
        self.make_skill(
            self.project / ".agents" / "skills" / "unknown-skill",
            "unknown-skill",
            "未登记 Skill。",
        )
        result = self.run_manager("audit", "--project", str(self.project), expected=1)
        self.assertIn("存在未登记 Skill", result.stderr)

    def test_multiline_upstream_description_is_discovered(self) -> None:
        source = self.base / "multiline-source"
        skill_dir = source / "skills" / "multiline-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: multiline-skill\ndescription:\n  第一行说明，\n  第二行说明。\n---\n",
            encoding="utf-8",
        )
        self.run_manager(
            "external",
            "add",
            "multiline-source",
            str(source),
            "--description",
            "多行说明测试来源",
        )
        description = self.read_catalog()["third_party"][0]["skills"][0]["description"]
        self.assertEqual(description, "第一行说明， 第二行说明。")


if __name__ == "__main__":
    unittest.main()
