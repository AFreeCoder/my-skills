# Skill 源码发布与安装

本仓库发布的是 Skill 文件，没有常驻服务、网站、数据库或云端部署。流程以 `skills/skill-manage/SKILL.md` 为准；本文用于发布时核验 Git 版本和安装产物。

## 发布目标

- 远端：`origin`，对应 `AFreeCoder/my-skills`。
- 发布分支：`main`；fetch 后的 `origin/main` 是已发布基线。
- 消费方式：`npx -y skills@latest add AFreeCoder/my-skills --skill <name> -y` 从远程安装。
- 安装范围：未指定时项目级；用户明确要求全局时加 `-g`。更新已有安装按 skill-manage 检查安装范围。
- 当前没有 CI/CD workflow，也没有需要启动的运行时服务。

## 发布前检查

阅读 `README.md`、本文件、`skills/skill-manage/SKILL.md` 及本次变更的 Skill。使用独立 worktree 和分支开发；只合入本次范围的提交。

- 检查目录名、frontmatter、引用文件和 README 自建数量一致。
- 运行 skill-creator 的 `quick_validate.py`，运行新增脚本实际样本和相关测试。
- 对 `ai-news-collect`，执行 `python3 -B -m unittest discover -s skills/ai-news-collect/scripts -p test_news.py -v`；采集运行本身只需要 Python 标准库。
- `git diff --check`，检查提交没有密钥、采集数据、缓存或机器私有路径。
- 记录发布前的 `origin/main` SHA 与候选 SHA；核对两者之间的 log/diff。

## 发布与核验

重新 fetch 并确认基线未改变后，合入干净的本地 main，推送 `main:main`。不要 force push。

通过 skills CLI 安装新 Skill 或刷新已有安装，不能手动复制目录代替安装。检查安装项的 `SKILL.md` 和脚本内容与目标提交一致，并运行安装副本的 `--help` 或适用的只读自检。远端 SHA 正确、安装内容一致且脚本自检通过才算交付。

## 回滚与数据

Git 中的发布前 SHA 是源码回滚依据；需要回滚时用 revert 生成恢复提交，再推送并通过 CLI 更新受影响安装。全新安装也可通过 CLI 移除。不要重置或覆盖用户其他未提交内容。

`ai-news-collect` 的数据由用户选择的本地目录保存，默认是 `~/.local/share/ai-news-collect`。安装、更新和源码回滚不修改该目录，不需要生产数据库备份或迁移。旧采集批次保留原始内容；不能把删除用户采集数据作为恢复步骤。

如果推送或安装失败，保留候选提交与现有安装，记录具体失败步骤；不要把推送成功等同于安装成功。只在 main 干净且能快进时更新本地 main，其他在用 worktree 保持原状。
