# Project Bootstrap

将项目目的转化为可执行项目的通用 AI Skill，适用于科研、软件、工程、数据分析等长期项目。

## 能做什么

- 澄清目标、范围、输入、约束和验收标准。
- 制定分阶段任务书与带依赖、输入和验收条件的工作单。
- 创建项目目录、精简 AGENTS.md、按需读取的上下文和本地记忆。
- 检查输入、工具与环境，并组织首个任务的执行验证。
- 用本地 Markdown、JSON 和 Git 保存来源、决定、经验及交接信息。

生成器提供通用框架；专业程序、环境安装和最终成果仍须由执行 AI 按项目任务书完成。框架检查通过不代表领域成果已验证。

## 安装与使用

下载本仓库，将 project-bootstrap 文件夹复制到支持本地 skills 的 AI 工具技能目录。Codex 可使用用户主目录下的 .codex/skills/。其他工具请按其自身的技能加载方式配置；跨工具兼容性需实际验证。

向 AI 输入：

```text
使用 $project-bootstrap。
项目目的：……
项目目录：……
已有资料或代码：……
请补齐影响执行的必要需求，搭建项目并验证首个任务的执行条件。
```

技能入口：[SKILL.md](project-bootstrap/SKILL.md)。生成器预览不会写入项目；确认配置后使用 --apply，已有文件碰撞会拒绝写入。

## 开发与验证

运行时使用 Python 3.10+ 标准库。可在独立虚拟环境中安装 requirements-dev.txt 所列的开发校验依赖。

```sh
python -X utf8 project-bootstrap/scripts/bootstrap_project.py --help
python -X utf8 project-bootstrap/scripts/test_bootstrap.py
```

测试使用模拟项目，不运行真实科研或生产任务。项目记忆和审批记录用于追溯，不能代替操作系统权限隔离或身份认证。

## 项目状态

首次公开整理版。未包含原始会话、本地安装记录、私人研究资料或旧开发仓库历史。暂未授予开源许可证；如需复用、修改或分发，请先联系仓库所有者确认许可。
