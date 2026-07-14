# Project Skill Linker Design

日期：2026-07-14

## 背景

`my-skills` 已收敛为 4 个自建 Skill 的权威源码仓库。项目使用统一的
`.agents/skills/` 目录启用 Skill；Claude Code 通过
`.claude/skills -> ../.agents/skills` 复用同一组项目级 Skill。

当前每个项目需要手工创建 Claude 兼容入口，并为需要的自建 Skill 分别执行
`ln -s`。直接把第一步写进用户级 `AGENTS.md` 只能形成约定，不能提供真正的
自动化：Agent 只有在任务运行时才会读取规则，而且只读任务不应因此修改仓库。

本设计增加一个可版本管理、幂等且默认安全的 `my-skills` 命令，由全局
`AGENTS.md` 规定在“配置项目 Skill”场景中优先调用该命令。

## 目标

1. 用一个命令初始化项目级 Skill 目录和 Claude Code 兼容软链。
2. 用一个命令显式链接一个或多个自建 Skill。
3. 安全、幂等地移除项目中的自建 Skill 软链，不删除源码。
4. 将命令实现维护在 `my-skills` 仓库中，并通过用户 PATH 直接调用。
5. 不恢复任何用户级全局 Skill 安装。

## 非目标

- 不安装、更新或管理官方及第三方 Skill。
- 不实现 `sync`、profile、项目模板或 `--all`。
- 不在进入目录、Git checkout 或每次 Agent 启动时自动修改项目。
- 不自动修改项目 `.gitignore`，也不决定项目是否提交 `.agents/` 或 `.claude/`。
- 不覆盖已有普通目录、非预期软链或其他工具维护的 Skill。

## 方案选择

### 方案 A：只写用户级 `AGENTS.md`

实现成本最低，但规则只有在 Agent 任务中才可能执行，无法作为可靠的项目初始化
机制，也容易在只读任务中造成不必要的仓库变更。

### 方案 B：Shell alias 或 function

调用方便，但实现散落在个人 shell 配置中，缺少版本管理、测试和跨机器同步。

### 方案 C：仓库内 CLI + 用户级规则（采用）

命令跟随 `my-skills` 版本管理和测试；全局 `AGENTS.md` 只声明使用边界。用户仍然
显式决定何时修改项目，命令负责把具体操作做得一致、安全、幂等。

## 命令接口

脚本源码放在 `my-skills/bin/my-skills`，用户级入口为：

```text
~/bin/my-skills -> ~/project/my-skills/bin/my-skills
```

当前环境的 `~/bin` 已在 `PATH` 中。命令支持：

```bash
my-skills init [--project <path>]
my-skills link [--project <path>] <skill-name> [<skill-name>...]
my-skills unlink [--project <path>] <skill-name> [<skill-name>...]
```

默认项目路径按以下顺序确定：

1. 使用 `--project <path>` 时，以该目录为项目根目录。
2. 未指定时，如果当前目录位于 Git 仓库或 worktree 中，使用
   `git rev-parse --show-toplevel` 的结果。
3. 当前目录不属于 Git 仓库时，使用当前工作目录。

`MY_SKILLS_HOME` 可覆盖源码仓库位置。未设置时，脚本应解析自身真实路径，并以
`bin/` 的父目录作为 `MY_SKILLS_HOME`；即使通过 `~/bin/my-skills` 软链调用，也不能
错误地把 `~/bin` 当作源码根目录。

## 行为设计

### `my-skills init`

1. 确认项目路径存在且为目录。
2. 创建 `<project>/.agents/skills/` 和 `<project>/.claude/`。
3. 若 `<project>/.claude/skills` 不存在，创建相对软链：

   ```text
   .claude/skills -> ../.agents/skills
   ```

4. 若现有软链解析后已经指向同一项目的 `.agents/skills/`，视为成功且不重建。
5. 若该路径是普通文件、普通目录或指向其他位置的软链，拒绝覆盖并返回非零状态。

### `my-skills link`

1. 至少要求一个显式 Skill 名称，不提供全量链接选项。
2. Skill 名称只允许小写字母、数字和连字符，且不能以连字符开头。
3. 每个源目录必须为 `<MY_SKILLS_HOME>/skills/<name>/`，并存在 `SKILL.md`。
4. 创建 `<project>/.agents/skills/<name>` 到源目录的绝对软链。
5. 已存在且解析到同一源目录的软链视为成功，不重复创建。
6. 已存在的普通目录、普通文件或其他目标软链均视为冲突，禁止覆盖。
7. 多名称调用先完成全部源和目标预检，再执行创建，避免前几个成功、后一个冲突的
   部分链接状态。
8. 预检通过后自动执行 `init`，因此通常只需：

   ```bash
   my-skills link push-deploy webpage-clipper
   ```

### `my-skills unlink`

1. 至少要求一个显式 Skill 名称。
2. 目标不存在时视为成功，保持幂等。
3. 只允许删除解析后准确指向 `<MY_SKILLS_HOME>/skills/<name>` 的软链。
4. 普通目录、普通文件或指向其他位置的软链均拒绝删除。
5. 多名称调用先完成全部目标预检，再删除任何链接。
6. 不运行 `init`，避免移除操作反而创建新的目录或 Claude 入口。

## 用户级 `AGENTS.md` 约定

在 `~/.codex/AGENTS.md` 增加“项目级 Skill 管理”规则：

- 项目 Skill 的规范目录为 `.agents/skills/`。
- Claude Code 通过 `.claude/skills -> ../.agents/skills` 复用同一目录。
- 仅当用户要求配置项目 Skill，或当前任务明确需要把某个 Skill 接入项目时，使用
  `my-skills init|link|unlink`；不得因为进入项目或执行只读任务而自动修改仓库。
- 自建 Skill 不复制，使用 `my-skills link` 从权威源码仓库逐个链接。
- 不覆盖已有普通目录或冲突软链；遇到冲突必须停止并报告。
- 不把项目 Skill 安装到 `~/.codex/skills`、`~/.claude/skills`、
  `~/.agents/skills` 或 `~/.cc-switch/skills`。

该规则负责统一决策边界，脚本负责文件系统操作，两者不互相替代。

## 输出与错误处理

- 成功创建时输出创建的链接和目标。
- 已处于正确状态时输出 `already configured` 或 `already linked`，退出码为 0。
- 参数错误、源 Skill 不存在、目标冲突或项目路径无效时，把具体路径和原因输出到
  stderr，退出码非 0。
- 不使用 `rm -rf`，不自动修复冲突，不静默改变已有文件类型。

## 文件变更

仓库内：

```text
bin/my-skills
tests/test-my-skills.sh
README.md
docs/design/project-skill-linker/DESIGN.md
docs/plan/project-skill-linker/implementation-plan.md
```

用户级：

```text
~/.codex/AGENTS.md
~/bin/my-skills -> ~/project/my-skills/bin/my-skills
```

## 测试设计

`tests/test-my-skills.sh` 使用临时目录隔离测试，不接触真实项目：

1. `init` 创建两个目录和正确的相对软链。
2. 重复 `init` 保持幂等。
3. `init` 拒绝普通目录和错误软链。
4. `link` 支持单个、多个和重复调用。
5. `link` 拒绝不存在或缺少 `SKILL.md` 的源。
6. `link` 在任一目标冲突时不创建其他待链接项。
7. `unlink` 只删除正确软链，重复调用保持幂等。
8. `unlink` 拒绝普通目录和错误软链，批量预检失败时不做部分删除。
9. 默认 Git 根目录、非 Git 当前目录和 `--project` 三种项目定位均正确。
10. 通过 `~/bin` 风格软链调用时仍能解析真实的 `MY_SKILLS_HOME`。

实现完成后还需运行：

```bash
bash tests/test-my-skills.sh
shellcheck bin/my-skills tests/test-my-skills.sh
git diff --check
```

若本机没有 `shellcheck`，实施阶段应先检查是否已有可用版本；不为单次验证擅自安装
系统级依赖，改用 `bash -n` 并明确报告验证差异。

## 验收标准

1. 新项目执行 `my-skills init` 后得到规范的 Claude Code 兼容入口。
2. `my-skills link push-deploy webpage-clipper` 只链接明确指定的两个自建 Skill。
3. 所有正确状态的重复调用均安全成功。
4. 所有冲突均在覆盖或删除前被拦截。
5. 用户级全局 Skill 目录保持为空或仅保留宿主管理内容。
6. README、全局规则、CLI 实际行为与测试相互一致。
