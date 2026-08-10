# Agent 运行兼容性报告（Windows · 千问办公）

审计日期：2026-08-10
审计对象：本仓库（ListenKit 运行时），由 LingoTrace 运行时经设备共享连接（`%LOCALAPPDATA%\LingoTrace\connections\listenkit.json`）解析使用，服务对象为学习 Vault `C:\Users\jiezhengj\Documents\Obsidian\LingoTrace-English`。

> 落位说明：本报告位于 `docs/agent-compatibility-report/qwenwork-agent-windows-compatibility.md`。同目录另有其他 Agent 的同日审计（workbuddy / traework 前缀，含两份 traework 变体）；仓库根目录可能留有 TraeWork 的早期报告。本文件是**千问办公（QwenWork）**的独立报告：对"入口契约应统一为跨平台 `python -m listenkit_cli`、`.sh` 不应在 Windows 被消费"的结论与其他审计一致；本报告额外聚焦上游集成面的版本化契约缺失（L2）与跨设备文件同步残留（L3）。

## 我是谁

我是千问办公（QwenWork），运行在用户这台 Windows 设备上的桌面智能体。我通过两条路径使用你：一是作为 LingoTrace 运行时听力链路（`tools/listening-transcribe-official/transcribe_listening.py` 与英语包 SKILL.md）的间接下游；二是必要时直接调用你的 CLI 完成转写、切片与诊断。

本次审计中我的执行环境：

- Windows 11（10.0.26220），shell 为 bash 风格（Git Bash），可另行调用 powershell.exe；
- Python 3.14.4（`C:\Users\jiezhengj\AppData\Local\Programs\Python\Python314\python.exe`，无 py launcher）；
- ffmpeg/ffprobe 9.0、yt-dlp 2026.07.04 在 PATH；GPU 为 GTX 1660 SUPER（6 GiB）。

## 结论摘要

你的跨平台 Python 核心名不虚传：`python -m listenkit_cli doctor` 在本机全绿，CUDA 就绪，Python 3.14.4 恰好满足硬性要求。**你本身对我基本兼容**；问题集中在入口契约的跨平台一致性和与上游 LingoTrace 的集成面上——其中一部分根因在 LingoTrace 侧（我已另行在其目录留下报告），但需要你在文档与防御性行为上配合收口。

## 审计方法与证据分级

**真实执行（实跑取得）**

- `python -m listenkit_cli doctor`：完整运行时体检，输出逐字段核对。
- **端到端转写真跑（2026-08-10 补测）**：用 Windows SAPI 合成 8 秒英语语音 WAV，在仓库根执行 `python -m listenkit_cli generate-markdown --input <wav> --language English --output <md> --auto-init`，全流程成功：`engine=faster-whisper`、`device=cuda`、`compute_type=float16`、`model=small`、`timing_complete=true`、2 个 segments，Markdown 与 JSON 产物齐全，转写文本与合成语音逐字一致。这不只是诊断绿灯，是真实 ASR 推理闭环。
- 针对性核对：`cli/transcribe-audio.sh` 的 macOS venv 硬编码、LLM_INTEGRATION.md 的 Windows 指引、EXPECTED_PYTHON ABI 校验。

**代码审计（未端到端执行）**

- URL → 字幕优先路径（yt-dlp 链路）、`export-audio-slices.py` 切片导出：只读了契约与代码，未实跑（本机 yt-dlp/ffmpeg 就绪，留待真实学习任务时验证）。
- `.ps1` 壳层：未通过 powershell.exe 实跑（我走的是 `python -m` 路径，该路径已充分验证）。

## 对我这个 Agent 的兼容性（Codex 出身盘点）

你是两个运行时里 agent-generic 做得最彻底的：README 明文 "Not tied to Codex. Codex is only one adapter."，`adapters/` 并列 agent（通用）/ claude / codex / cursor 四套，`LLM_INTEGRATION.md` 自称 external LLM agents 的 source of truth。对我而言：

**兼容面（我可以直接使用）**

- 通用适配器 `adapters/agent/listenkit-agent-instructions.md` 与我的接入方式匹配：只调公共入口、消费 md/json 产物、不绕过入口直调 ffmpeg/yt-dlp——这些我都能遵守（本次补测正是经公共入口完成）。
- provider 无绑定：你不要求任何模型厂商 API，转写完全本地——与我这种"宿主 agent 自带模型判断"的形态天然契合。
- 错误 payload 与 schema_version=1 契约清晰，doctor 输出可直接解析。

**缺口（正是 L1 的核心）**

- 通用 agent 指令给出的入口是 `.sh`（POSIX）/`.ps1`（Windows）二选一，没有把 `python -m listenkit_cli` 立为全平台一等入口——而对我这种 bash 风格 shell 的 agent，模块入口才是最稳的路径（已实跑证明）。
- 上游 LingoTrace 仍按 `.sh` + `/bin/bash` 集成你（根因其侧），说明你的对外稳定面缺少一个让下游"不得不走对"的强约束或显著文档。

## 问题清单

### L1（高）入口契约对跨平台 agent 不一致，bash 风格 agent 会踩中 .sh 陷阱

- `LLM_INTEGRATION.md` 第 49–59 行要求 Windows 走 `.ps1`，不要走 WSL——正确；但你的上游消费方 LingoTrace 的 `resolve-listenkit` 对外报告的入口是 `cli/generate-markdown.sh`，其转写工具甚至硬编码 `/bin/bash` 调用它。
- 我自己的 shell 是 bash 风格，天然倾向选择 `cli/*.sh`；而 `cli/transcribe-audio.sh` 第 181–182 行把运行时 venv 硬编码为 `${HOME}/Library/Caches/ListenKit/venvs/cpython-314/bin/python`（macOS 布局，Windows 应为 `%LOCALAPPDATA%\ListenKit\venvs\cpython-314\Scripts\python.exe`），在 Windows 的 Git Bash 里执行必然找不到运行时或在错误位置初始化。
- 实测的正确路径：在仓库根执行 `python -m listenkit_cli` ——doctor 全绿，且补测中完成了端到端真实转写（CUDA float16，转写逐字准确）。也就是说**存在一条对我可靠的入口，但它没有被立为跨平台首选**。
- 佐证：上游 LingoTrace 硬编码 `/bin/bash` 的调用在 Windows 上直接抛 FileNotFoundError（见 LingoTrace 仓库 `docs/agent-compatibility-report/qwenwork-agent-windows-compatibility.md` 的 P1）。

### L2（中）与 LingoTrace 的集成缺少版本化契约

- 你与 LingoTrace 之间没有任何发现/版本协商机制（全仓库无 LingoTrace/vault 相关代码，这是有意设计，我理解）。但上游 LingoTrace 实际依赖这些隐性假设：存在 `README.md` + `cli/generate-markdown.sh` 即视为可用；`--engine apple|faster-whisper`、`--language/--locale/--output/--format` 参数与转写 JSON 长期稳定。
- 这些假设目前只散落在 LLM_INTEGRATION.md 与 docs/backends.md 里，没有集中声明"对外稳定面"与变更政策。上游一旦改版，LingoTrace 与我都只能靠运行时失败来发现。

### L3（低）跨设备文件同步残留

- `listenkit_cli/__pycache__/cuda_runtime.cpython-314.sync-conflict-20260809-132937-H6N5CG2.pyc` 等 Syncthing 冲突文件存在于工作树（本仓库在 Mac 与 Windows 之间被文件同步）。
- 当前不影响运行（`__pycache__` 不参与契约），但若同步工具在 pip/git/venv 操作中途脱水或锁定文件，可能造成罕见且难诊断的故障。

## 我的需求

1. 一条在任何 shell 下都无歧义的 Windows 入口：我需要文档明确告诉我（以及 LingoTrace 这类下游）"任意平台首选 `python -m listenkit_cli`（仓库根执行）"。
2. 长耗时任务的可预期性：首次 `--auto-init` 安装依赖、首次下载模型、CPU/GPU 转写时长各是什么量级，调用时应预留多少超时或是否应后台执行。
3. 错误 payload 与转写 JSON schema（当前 schema_version=1）保持稳定，变更时给出迁移说明。

## 建议方案

1. **L1**：在 `LLM_INTEGRATION.md` 与 `adapters/agent/listenkit-agent-instructions.md` 顶部把 `python -m listenkit_cli`（仓库根执行，或配 PYTHONPATH）声明为全平台一等入口，`.sh`/`.ps1` 定位为可选壳；并让 `cli/*.sh` 在检测到 Windows 环境（如 OSTYPE 为 msys/cygwin，或运行时路径不存在）时快速失败并打印指向 `.ps1` / `python -m listenkit_cli` 的明确指引，而不是按 macOS 路径继续尝试。（这条入口我已实跑验证：端到端转写成功，见「审计方法」。）
2. **L2**：在 docs/backends.md 或 LLM_INTEGRATION.md 增加 "Downstream integrators" 一节，集中列出对外稳定面：CLI 子命令与关键参数、转写 JSON schema_version=1、错误 payload 形状、切片导出 manifest 格式，以及破坏性变更的预告方式。
3. **L3**：在 `docs/install.md` 增加一句提示——避免把仓库放在按需云同步目录（OneDrive/iCloud/Syncthing 脱水场景）；若已同步，故障排查时先检查 `sync-conflict` 残留文件。

## 已验证可用的部分（2026-08-10 实测，避免误解）

- **端到端真实转写闭环（补测）**：合成英语语音经 `python -m listenkit_cli generate-markdown` 转写成功——faster-whisper、CUDA、float16、small 模型、timing_complete=true，转写逐字准确，md/json 产物完整。你的核心能力在我这里不只是"应该能跑"，是"已经跑通"。
- `python -m listenkit_cli doctor` 全绿：platform=windows、运行时 venv `%LOCALAPPDATA%\ListenKit\venvs\cpython-314`（Python 3.14.4、faster-whisper 1.2.1、import_health=ok）、`acceleration_backend=cuda-or-optimized-cpu`、`cuda_runtime=ready`、`asr_auto_device=cuda`（float16）、`model_small_cache=ready`、ffmpeg/yt-dlp 均可发现。
- Python 3.14.4 恰好满足 ASR 运行时的硬性要求（EXPECTED_PYTHON=(3,14) + cpython-314 ABI 校验）；CLI 宿主 ≥3.10 的要求对我同样满足。
- Windows 原生支持的实际投入（原生 .ps1 全套、LOCALAPPDATA 路径布局、CI 的 windows-real-runtime job、中文/空格路径测试）我在审计中都看到了，方向正确——剩下的只是把跨平台入口讲清楚。

—— 千问办公（QwenWork），2026-08-10
