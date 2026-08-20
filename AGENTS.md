# ListenKit 仓库规则

在使用 ListenKit 作为外部 Agent，或修改其公共集成行为前，必须先阅读 `LLM_INTEGRATION.md`。面向 provider-neutral Agent 的摘要是 `adapters/agent/listenkit-agent-instructions.md`。

## 文档语言

- 本项目维护的所有文档均使用中文，包括 README、规范、计划、任务、清单、架构说明、Agent 集成说明和变更说明。
- 代码、API 名称、命令、文件路径、协议字段、配置键、Markdown 输出节名和上游专有名词保留原文；必要时在中文说明中补充解释。
- Spec Kit 生成且由 manifest 管理的工具技能文件属于工具基础设施，不手工翻译或改写；其项目使用规则必须在本文件和中文项目文档中说明。

## Agent 使用

- 不得仅为绕过 Agent 的 sandbox、shell、stdout 捕获或 PATH 限制而修改 ListenKit 源码。优先使用项目提供的 Python 或平台分发器，并在需要时使用 `--report-json`。
- 自动化优先从仓库根目录运行 `python -m listenkit_cli <command>`。主机 Python 环境不确定时，macOS/Linux/WSL 使用 `cli/listenkit.sh <command>`，原生 Windows 使用 `cli/listenkit.ps1 <command>`。
- 正常 transcript 集成只调用 `generate-markdown`；不得重复实现导入、字幕选择、ASR fallback 或渲染。
- Agent-specific 文件只能描述共享契约，不得加入 provider-specific 业务逻辑。

## 工程约束

- 仓库变更必须保持 Python 3.14 运行时隔离、UTF-8 I/O、transcript schema 兼容、原子输出写入和非交互自动化行为。
- 正常集成不得直接调用 `yt-dlp`、`ffmpeg`、低层 `cli/*` 或 `tools/*` 绕过公共入口；低层接口只用于 ListenKit 自身调试和维护。
- 需要明确时间范围的下游音频片段使用 `cli/export-audio-slices.py`，不直接调用 `ffmpeg`。

## Spec Kit 工作流

- 实质性功能、行为变更、兼容性变更、迁移和复杂缺陷按 `constitution → specify → clarify → plan → checklist → tasks → analyze → implement → validate → converge` 推进。
- 代码、公共契约或平台行为变更必须把需求、实现范围、测试和收敛结果写入对应 Spec Kit 工件。
- 生成的 Spec Kit integration 文件以当前 CLI manifest 为准；不得手工复制全局技能或强制覆盖现有项目集成。

## 交付前验证

在交付代码或公共契约变更前运行：

```bash
python -m compileall -q listenkit_cli cli tools
python -m unittest discover -s tests -v
```

平台硬件和权限结论必须有匹配的真实设备验证。提交前还必须检查 `git status`、`git diff`、`git diff --check`、未跟踪文件和 `.gitattributes` 换行规则。
