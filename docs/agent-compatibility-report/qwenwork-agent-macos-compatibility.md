# Agent 运行兼容性报告（macOS · 千问办公）

审计日期：2026-08-10
审计对象：本仓库（ListenKit 运行时），作为 LingoTrace 学习 Vault（`/Users/jiezhengj/Documents/Obsidian/LingoTrace-English`）听力链路的下游转写运行时，经 LingoTrace `resolve-listenkit` 解析绑定。

> 落位说明：本报告位于 `docs/agent-compatibility-report/qwenwork-agent-macos-compatibility.md`，是千问办公（QwenWork）在 macOS 上的独立审计报告，与同目录 `qwenwork-agent-windows-compatibility.md`（同一 Agent 的 Windows 报告）互补。本报告为纯新增文档，未修改任何代码，未提交任何 git 变更。本次审计在本机完成了 **MLX/Metal 端到端真实转写**（Python 模块入口与 `.sh` 壳层双路径），并全量跑通 131 个单测。

## 我是谁

我是千问办公（QwenWork），一个运行在用户这台 Mac 上的桌面 Agent 框架。我通过 LingoTrace 运行时的 `resolve-listenkit` 契约认识本仓库，并在用户请求听力学习任务时调用本仓库完成"音频 → 转写 JSON → Markdown 笔记"的本地转写环节。

本次审计中我的执行环境：

- macOS 27.0（arm64，Apple Silicon），默认 shell 为 zsh，我以子进程方式执行 bash/python3 命令并捕获 stdout/stderr；
- Python 3.14.4（python.org 安装）为默认 `python3`；托管运行时 venv 为 Python 3.14.6（`~/Library/Caches/ListenKit/venvs/cpython-314`）；
- yt-dlp、ffmpeg、ffprobe 均经 Homebrew 安装并在 PATH；
- 本机 MLX 运行时已就绪：MLX 0.32.0（Metal ready）、mlx-whisper 0.4.3、`whisper-small-mlx` 模型已缓存，`asr_auto_engine=mlx`。

我不是 OpenAI Codex CLI：没有 `~/.codex` 生态，不消费 `adapters/codex/agents/openai.yaml` 这类 Codex 技能打包格式。我走的是通用契约：`LLM_INTEGRATION.md` + `adapters/agent/listenkit-agent-instructions.md` + `cli/generate-markdown.sh`。

## 结论摘要

**总体结论：千问办公在 macOS（Apple Silicon）上对本仓库完全兼容，且本机即为最佳路径——MLX/Metal 加速是一等公民。** 两条调用路径（`python -m listenkit_cli` 与 `cli/generate-markdown.sh` 壳层）均已实跑端到端成功；`doctor`/`check-runtime` 全绿；131 个单测全部通过。源码零 Codex 依赖，Codex 出身仅体现在 `adapters/codex/` 的打包元数据上，对我无影响。问题均为契约与工程层面的改进项（L1–L6），无阻塞级。

## 审计方法与证据分级

**真实执行（2026-08-10 实跑取得，均在本机）**

- `python -m listenkit_cli --help`：9 个子命令全部列出。
- `doctor`：platform=macos / arch=arm64，托管 venv Python 3.14.6、faster-whisper 1.2.1、`import_health=ok`，MLX Metal ready、`asr_auto_engine=mlx`，yt-dlp/ffmpeg 就位，CUDA 正确显示 not-applicable。
- `check-runtime`（Python 入口与 `cli/check-runtime.sh` 壳层）：均通过。
- **端到端转写（Python 入口）**：用 macOS `say` 合成英语语音 → ffmpeg 转 wav → `transcribe-audio --engine mlx` 成功，输出 schema_version=1 JSON，`engine=mlx-whisper`、`device=metal`、`compute_type=float16`、`timing_complete=true`，转写文本准确。
- **端到端转写（壳层入口）**：`cli/generate-markdown.sh --input <wav> --language en --output ...` 完整流程成功，产出 Markdown + 同名 JSON（输出契约成立）。
- `render`：转写 JSON → Markdown 渲染正确。
- `install-agent-instructions --print`：输出通用 agent 指令（平台分流正确：macOS/Linux/WSL 走 `.sh`）。
- 全量单测：`python -m unittest discover -s tests`，**131 通过（6 个 skip 为 Windows 专属）**。

**代码审计（未端到端执行）**

- URL 路径（yt-dlp 下载 + 字幕优先策略）与 `init-runtime` 全新建 venv 路径未实跑（本机运行时已就绪，重建无必要且耗时；两者有单测覆盖）。
- Apple Speech 可选后端未构建（需 Xcode CLT 与 Speech 权限，超出兼容性审计必要范围）。

## 对我这个 Agent 的兼容性（Codex 出身盘点）

本仓库虽经由多个 `codex/*` 分支开发（git 历史可见），但对非 Codex agent 已做系统性解耦，我在 macOS 上无任何障碍：

**兼容面（我可以直接使用）**

- 源码（`listenkit_cli/`、`tools/`、`cli/`）零处 Codex 引用；agent 耦合仅在文档与 adapters 层。
- `README.md:96` 明文 "Not tied to Codex. Codex is only one adapter."；四套 adapter（agent/codex/claude/cursor）并列，我使用通用版 `adapters/agent/listenkit-agent-instructions.md` 即可。
- `LLM_INTEGRATION.md` 契约清晰且我已逐条验证：高层入口唯一（`generate-markdown`）、本地媒体用 `--input`、engine/device 保持 auto、输出 md+同名 JSON、"Do Not Bypass" 清单明确（唯一例外 `export-audio-slices.py`）。
- 子进程输出统一 UTF-8 强制（`process.py:26-67`），我捕获 stdout 无编码风险。
- `install-agent-instructions` 支持 `--target`/`--print`，对任意 agent 的规则文件布局都可适配。

**Codex 出身残留**

- 仅 `adapters/codex/agents/openai.yaml`（Codex 技能注册元数据）与 `adapters/codex/SKILL.md` 的文件名/格式；内容本身平台无关，我不消费，无影响。

## macOS 平台兼容性

macOS（尤其 Apple Silicon）在本仓库是一等公民：

- `platform_paths.py` 平台感知完整：venv 落 `~/Library/Caches/ListenKit/venvs/cpython-314`（正确 macOS 形状，且避开 iCloud：`runtime.py:117-120` 拒绝 `Library/Mobile Documents`）。
- 加速策略对 Apple Silicon 最优：自动探测并安装 mlx-whisper（`runtime.py:189-247`），MLX 失败回退 CTranslate2 Apple Accelerate CPU；Intel Mac 亦有 CPU 路径。
- CUDA 在 macOS 被正确拒绝并给出明确错误（`runtime.py:190-191`、`cuda_runtime.py:112-113`），不会误装 NVIDIA 依赖。
- Python 3.14 bootstrap 候选含 `/opt/homebrew/bin/python3.14` 等 arm64 Homebrew 路径（`runtime.py:49-61`）。
- `.sh` 壳层内硬编码的 venv 路径（如 `cli/transcribe-audio.sh:181-182`）在 macOS 上是正确布局（该硬编码只对 Windows Git Bash 是坑）。
- CI 矩阵含 `macos-latest`（GitHub 的 macos-latest 即 arm64），本机形已被覆盖；`docs/runtime-snapshot-python314.txt` 记录的参考机型（macOS 27.0 arm64 / Python 3.14.6 / MLX Metal）与本机一致。
- Apple Speech 可选后端为 macOS 专属加分项（需 Xcode CLT，未测）。

## 问题清单

### L1（契约）`python -m listenkit_cli` 未被文档立为一等入口

**现象**：`LLM_INTEGRATION.md` 与 README 首推 `.sh`/`.ps1` 壳层；`python -m listenkit_cli`（仓库根执行）实际是最稳定的跨平台程序化入口——LingoTrace 侧的听力脚本以子进程方式调用本仓库时，程序化入口比壳层更可控。我在 Windows 的报告中已提过此点（该报告 L1），macOS 上两条路径我都实跑成功，结论不变：壳层可用，但 Python 模块入口值得被文档正式承认。

**我的需求**：在面向 agent 的契约文档中，把"仓库根执行 `python -m listenkit_cli <子命令>`"列为与壳层并列的一等入口，注明两者等价性与适用场景。

**建议方案**：在 `LLM_INTEGRATION.md` 增加 "Programmatic entrypoint" 小节；中长期提供 `pyproject.toml` + `console_scripts`（`listenkit`），彻底摆脱"必须仓库根执行"的隐性前提。

### L2（安装门槛）托管运行时锁死 Python 3.14，全新机器为最大障碍

**现象**：`health.py:11` `EXPECTED_PYTHON=(3, 14)`，`health.py:122-131` 对版本与 `abi_tag == "cpython-314"` 双校验；`runtime.py:99-102` 在缺失时报错。本机恰好有 3.14（系统 3.14.4 + venv 3.14.6）故全绿，但全新 Mac 若无 3.14，`init-runtime`/`--auto-init` 即失败。

**我的需求**：在新机器上，agent 仅凭 `doctor` 输出就能知道"去哪里装 3.14、装完如何继续"，不需要读源码或试错。

**建议方案**：`doctor` 在 Python 3.14 缺失时输出明确的 bootstrap 指引（如 `brew install python@3.14`，与 `runtime.py:49-61` 的候选路径呼应）；或评估放宽为 ≥3.11 区间（若 faster-whisper/MLX 版本允许）。

### L3（首次运行）联网依赖对受限 agent 环境不透明

**现象**：首次运行需 pip 安装 mlx-whisper 并从 HuggingFace 下载模型（`mlx_runtime.py:109-113`、`transcription.py:425-427`）。本机模型已缓存故为离线成功；但沙箱、代理受限或无网络的 agent 环境会在转写中途失败。

**我的需求**：在发起转写前就能判断"当前是否离线可用"。

**建议方案**：`doctor` 已显示 `model_mlx_small_cache=ready/missing`（很好），建议进一步给出聚合的 `offline_ready=yes/no` 结论；并支持独立的"预准备"命令（如 `init-runtime --fetch-models`），让 agent 可在有网时一次性备齐。

### L4（上下游契约）与 LingoTrace 之间缺版本化握手

**现象**：LingoTrace 以 `cli/generate-markdown.sh` 是否存在作为 ListenKit root 可用性判据（LingoTrace 侧 `listenkit_connections.py:328-329`），两仓库间无版本/schema 握手。若未来壳层改名或 JSON schema（当前 schema_version=1）演进，上游只能在运行失败时发现。

**建议方案**：在仓库根提供轻量版本文件（如 `listenkit_cli.__version__` 已有 1.0.0，可加 `CAPABILITY_SCHEMA_VERSION`），并让 `doctor` 输出；LingoTrace 侧 `resolve-listenkit` 可据此做最小兼容性校验。

### L5（流程）兼容性报告的入库约定缺失

**现象**：`docs/agent-compatibility-report/` 与 `docs/agent-compatibility-windows-qwenwork.md` 长期处于 untracked 状态（本报告写入后同样如此）。各 agent 持续产出报告，但仓库未说明它们是应随 PR 入库，还是仅作本地交流件。

**建议方案**：在 README 或 docs 中写明报告的存放约定；若愿意入库，直接把该目录纳入跟踪即可（本仓库无白名单脚本障碍）。

### L6（卫生，轻微）工作树残留 sync-conflict 与 .DS_Store

`listenkit_cli/__pycache__/` 内存在 Syncthing 冲突残留 pyc（`*.sync-conflict-*.pyc`），另有 `.DS_Store`。不影响运行，但会干扰 agent 的文件枚举与搜索；建议清理并在 .gitignore 中补充 `*.sync-conflict-*`。

## 我的需求（汇总）

作为听力链路的调用方 agent，我在 macOS 上需要：一个被文档承认的程序化入口（L1）；新机器上可自助完成的运行时安装指引（L2）；发起转写前可判定的离线就绪状态（L3）；以及上下游可互相校验的版本契约（L4）。本仓库当前的公开契约（高层入口唯一、不绕过内部脚本、md+JSON 输出）我完全认可并会持续遵守。

## 附录：实跑结果速览

| 项目 | 命令 | 结果 |
|---|---|---|
| CLI 帮助 | `python -m listenkit_cli --help` | 9 子命令正常 |
| 诊断 | `doctor` | 全绿（MLX Metal ready、asr_auto_engine=mlx） |
| 运行时校验 | `check-runtime` / `cli/check-runtime.sh` | 均通过 |
| 端到端转写（Python 入口） | `transcribe-audio --engine mlx`（say 合成音频） | 成功，metal/float16，转写准确 |
| 端到端转写（壳层入口） | `cli/generate-markdown.sh --input ...` | 成功，md+同名 JSON 契约成立 |
| 渲染 | `render` | Markdown 输出正确 |
| 指令安装预览 | `install-agent-instructions --print` | 通用指令，平台分流正确 |
| 单测 | `python -m unittest discover -s tests` | 131 通过（6 skip 为 Windows 专属） |
