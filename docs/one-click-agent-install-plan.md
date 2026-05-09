# ListenKit 一键安装修订方案

## Summary

将“一键安装”精确定义为 **一键安装 Agent Instructions**，不承诺安装所有系统依赖。README 首屏拆成两条路：`Quick Try` 先让用户成功转录一次，`Install For Your AI Agent` 再处理持久安装。后续实施应按本文更新脚本与文档。

## Key Changes

- README 第一屏改成两段：
  - `Quick Try`：clone repo，安装 `yt-dlp`/`ffmpeg`，跑 `cli/generate-markdown.sh --help`，再跑一次示例转录。
  - `Install For Your AI Agent`：使用 `cli/install-agent-instructions.sh` 安装通用 agent 指令。
- 新增 `cli/install-agent-instructions.sh`，明确是 agent instructions installer：
  ```bash
  cli/install-agent-instructions.sh --target <file-or-directory>
  cli/install-agent-instructions.sh --target <file-or-directory> --force
  cli/install-agent-instructions.sh --target <file-or-directory> --dry-run
  cli/install-agent-instructions.sh --print
  ```
  `--target` 是持久安装模式；`--print` 是不知道 target 时的 fallback，将 instruction block 输出到 stdout，供用户贴到自己的 agent rules/context。
  `--dry-run` 只允许和 `--target` 搭配使用；`--print` 必须和 `--target`、`--force`、`--dry-run` 互斥。
- 新增 `adapters/agent/listenkit-agent-instructions.md` 作为唯一可安装指令源：
  - 正常转录只直接调用 `cli/generate-markdown.sh`
  - URL 用 `--url`，本地媒体用 `--input`
  - 必须提供 `--language` 和 `--output`
  - 默认使用 `--auto-init`
  - 产出同 stem 的 `.md` 和 `.json`
  - 不要把 `yt-dlp`、`ffmpeg`、低层 CLI、`tools/*` 当作 integration shortcut 直接调用
- 扩展 `LLM_INTEGRATION.md`，把 AI-first 安装和使用场景合并到现有 agent contract：
  - 区分 install request、use request、install + use request。
  - 不知道持久 rules/context target 时，先用 `--print` 或询问用户，不猜路径。
  - 询问 target 时使用固定模板：“I can install ListenKit instructions, but I need the path to your agent rules/context file or directory. If you only want to use it once, I can skip installation and run ListenKit directly.”
  - 明确说 `install-agent-instructions` 不安装 Homebrew、Python backend 或 ASR 模型。
  - 说明 `LLM_INTEGRATION.md` 是完整契约，`adapters/agent/listenkit-agent-instructions.md` 是可安装摘要。
  - 规则变更时先更新 `LLM_INTEGRATION.md` 作为 source of truth，再同步 `adapters/agent/listenkit-agent-instructions.md` 的关键 invariant，避免两者漂移。
- 文档架构重构为三个主入口：
  - `README.md`：人类和 AI 都先看这里，只保留最简使用指南、agent 安装入口和文档路由。
  - README 第一屏必须只包含一个最小可运行 URL 转录示例和一个最小 agent instructions 安装示例；可选参数、backend 解释、低层命令和故障细节分别移到 `docs/install.md` 或 `LLM_INTEGRATION.md`。
  - `docs/install.md`：只负责系统依赖、backend 初始化、故障排查和维护/debug 参考。
  - `LLM_INTEGRATION.md`：负责所有 AI/Agent 场景，包括 GitHub install/use、unknown target、`--print` fallback、公共入口契约、输出契约和 do-not-bypass 规则。
  - 删除 `QUICKSTART.md`，将必要的 Quick Try 内容合并到 README 第一屏。
  - 不新增独立 `AGENT_INSTALL.md`；把原计划中的 AI-first 安装内容合并进 `LLM_INTEGRATION.md`，避免 agent 文档入口分裂。
- 非 macOS 路径：
  - README 首屏保留 `brew install yt-dlp ffmpeg` 作为 macOS 最短路径。
  - 同段补一句：Linux users should install `yt-dlp` and `ffmpeg` with their package manager; details in `docs/install.md`。
- 验证流程：
  - 安装前/后可跑 `cli/generate-markdown.sh --help` 验证 CLI 可用。
  - `install-agent-instructions.sh` 成功后输出安装文件绝对路径。
  - `--dry-run` 显示 source 和 resolved target，不写文件。

## User Flows

- 人类用户快速试用：
  ```bash
  git clone <repo-url>
  cd ListenKit
  # macOS/Homebrew path. Linux users should install equivalent yt-dlp and ffmpeg packages with their package manager.
  brew install yt-dlp ffmpeg
  cli/generate-markdown.sh --help
  cli/generate-markdown.sh --url "https://example.com/video" --language Japanese --output work/sample.md --auto-init
  ```
- 人类用户不知道 agent target：
  ```bash
  cli/install-agent-instructions.sh --print
  ```
  然后把输出的 instruction block 贴到自己的 AI agent rules/context。
- 人类用户知道 agent target：
  ```bash
  cli/install-agent-instructions.sh --target <your-agent-rules-file-or-dir>
  ```
- AI agent 读 GitHub 并安装：
  - 先读 `LLM_INTEGRATION.md`
  - 检查 `yt-dlp`/`ffmpeg` 是否存在；缺失时提示安装或在用户允许时安装，不要改用低层 pipeline 绕过依赖
  - 知道 target 则跑 `--target`
  - 不知道 target 则用 `--print` 或询问用户
- AI agent 读 GitHub 并使用：
  - 可跳过持久安装，直接跑 `cli/generate-markdown.sh`
  - 如果用户没有指定 `--output`，默认使用 `work/<safe-source-stem>-transcript.md`；无法稳定取得 source stem 时，使用 `work/transcript.md`
  - 完成后告知这是当次使用，未必已持久安装

## Test Plan

- 新增 `tests/test_install_agent_instructions.py`：
  - `--help` 成功。
  - 缺少 `--target` 且未使用 `--print` 时失败。
  - `--print` 输出 instruction block 且不写文件。
  - `--print` 与 `--target`、`--force`、`--dry-run` 同时出现时失败。
  - `--dry-run` 缺少 `--target` 时失败。
  - target 是既有目录时生成 `listenkit-agent-instructions.md`。
  - target 是文件路径时生成指定文件。
  - 既有文件未加 `--force` 时拒绝覆盖。
  - 加 `--force` 时覆盖成功。
  - `--dry-run` 不创建、不修改文件。
  - 从 repo 外 cwd 执行仍能定位源指令文件。
  - 安装内容包含 `cli/generate-markdown.sh` 和禁止低层 shortcut 的关键规则。
- 文档检查：
  - README 前 60 行内能看到 `Quick Try` 和 `Install For Your AI Agent`。
  - `LLM_INTEGRATION.md` 覆盖 install/use/install+use/unknown target 四种场景。
  - `docs/install.md` 明确低层 backend 命令不是 agent 正常入口。
  - `QUICKSTART.md` 被删除，且 README 已包含其必要 Quick Try 内容。
  - 删除 `QUICKSTART.md` 后搜索全仓库面向用户的文档引用，排除本计划文档；所有引用必须被删除或改指向 README 对应段落。
- 回归测试：
  - 跑现有 unittest，确认 transcript 生成流程不变。

## Assumptions

- “一键安装”指一键安装 agent instructions，不是完整依赖安装器。
- `--target` 是高级/持久模式；`--print` 是最安全的新手和未知 agent fallback。
- 采用复制文件，不使用 symlink。
- AI agent 在当次使用场景中应优先选择稳定、可预测的 `work/*-transcript.md` 输出路径，除非用户明确指定其他路径。
