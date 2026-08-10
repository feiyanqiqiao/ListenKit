# Agent 运行兼容性报告：macOS（ListenKit 侧）

- 报告日期：2026-08-10
- 报告范围：ListenKit 运行时在 macOS（Apple Silicon）上的可执行性，以及对「Claude Code Agent」（非原定目标 Codex）的兼容性
- 报告者：Claude Code（Anthropic 的 Agent CLI），运行于 macOS 27.0（arm64），shell 为 zsh
- 关联报告：`LingoTrace/docs/agent-compatibility-report/claude-code-agent-macos-compatibility.md`
- 用户给出的目标目录是 Windows 风格 `C:\Users\...\ListenKit\docs\agent-compatibility-report`；本机为 macOS，等价路径为 `~/Documents/Project/ListenKit/docs/agent-compatibility-report/`

---

## 一、我是谁

**一句话身份：我是运行在 macOS（darwin，arm64 / Apple Silicon）操作系统之上的「Claude Code」Agent 框架中的 AI 助手，是 ListenKit 转录/切片链路的实际调用方（经 LingoTrace 编排，或作为独立 Agent 直接使用），也是本仓库 `adapters/*` 与 `LLM_INTEGRATION.md` 的实际消费方。**

- **Agent 框架 / 产品**：Claude Code —— Anthropic 官方的命令行 Agent CLI（终端/桌面/IDE 均可运行）。我以「Agent Loop」方式运行：每轮读取指令与工具结果、选择工具、执行、回收输出并迭代。框架为我提供 Bash（zsh）、文件系统读写、Grep/Glob 检索、Web 检索等工具；我的 Bash 工具可以完整读取子进程 stdout/stderr。
- **宿主操作系统**：macOS 27.0（Build 26A5388g），`uname -m` = arm64（Apple Silicon）。命令执行入口是 zsh（macOS 默认 shell）。系统自带 `/bin/bash` 为 GNU bash 3.2.57，`/usr/bin/python3` 为 CLT 自带 3.9.6。
- **与运行时的关系**：我通过 `cli/generate-markdown.sh`（macOS/Linux/WSL 入口）或 `python -m listenkit_cli` 调用本运行时；LingoTrace 的听力链路（`tools/listening-transcribe-official/transcribe_listening.py`）在 macOS 上同样经 `cli/generate-markdown.sh` 调用我。

我的执行环境（本次实测）：

| 项目 | 实测值 |
| --- | --- |
| 操作系统 | macOS 27.0（26A5388g），arm64（Apple Silicon） |
| 默认 Shell | `/bin/zsh`（macOS 默认） |
| 系统 bash | `/bin/bash` = GNU bash 3.2.57 |
| `python3` | 3.14.4（`/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`） |
| `/usr/bin/python3` | Python 3.9.6（CLT 自带） |
| brew | Homebrew 6.0.15，`/opt/homebrew`（Apple Silicon 路径） |
| ffmpeg / ffprobe / yt-dlp | 均在 `/opt/homebrew/bin/` |
| 托管运行时 | `~/Library/Caches/ListenKit/venvs/cpython-314`，健康（Python 3.14.6、faster-whisper 1.2.1、mlx 0.32.0） |
| MLX/Metal | `mlx_runtime=ready`、`mlx_metal=ready`、`asr_auto_engine=mlx`、默认设备 `Device(gpu, 0)` |
| MLX 模型缓存 | `mlx-community/whisper-small-mlx` 已缓存 |
| Apple Speech helper | 已构建（`tools/apple-speech-helper/.build/` 存在） |

---

## 二、问题是什么

我把本运行时按「默认转写链路」与「Apple Speech 可选后端」两块分别做了代码审计与真实运行验证。

**结论先行：默认转写链路（`cli/generate-markdown.sh` → MLX/Metal 或 faster-whisper → Markdown/JSON）在 macOS 上端到端可用，我用 macOS `say` 生成的 4.3 秒英语音频实测转写成功，`mlx-whisper / metal / float16`，文本与原始语音 100% 一致。macOS 上没有「必然失败」的默认链路缺陷（P0=无），但存在一处 P1 级缺陷：可选后端 Apple Speech 的辅助脚本 `run-apple-speech-helper.sh` 用 BSD `mktemp` 模板时生成固定文件名，重复/并发调用会 `mkstemp failed` 崩溃。对 Claude Code 而言，本仓库已提供 `adapters/claude/CLAUDE.md` 主动适配，契约完整可执行，无新增适配需求。**

### 2.1 已验证可正常工作的部分（实测通过）

| 能力 | 结果 |
| --- | --- |
| `cli/generate-markdown.sh --help` | ✅ 正常显示完整参数 |
| `cli/check-runtime.sh` | ✅ 健康：`python_version=3.14.6`、`faster_whisper_version=1.2.1`、`import_health=ok` |
| `python -m listenkit_cli --help` | ✅ 9 个子命令（generate-markdown/import-audio/extract-subtitles/transcribe-audio/render/init-runtime/check-runtime/install-agent-instructions/doctor） |
| `python -m listenkit_cli doctor` | ✅ `platform=macos`、`architecture=arm64`、`mlx_runtime=ready`、`mlx_metal=ready`、`asr_auto_engine=mlx` |
| 端到端转写（本地音频） | ✅ `EXIT=0`，产出 `test.md` + `test.json` + `audio/test.m4a` |
| 转写引擎/设备 | ✅ `engine=mlx-whisper`、`device=metal`、`compute_type=float16`、`device_selection_reason="Apple Silicon with a ready MLX/Metal runtime"` |
| 转写文本准确度 | ✅ 与原始语音逐字一致 |
| 测试套件 `python -m pytest tests/` | ✅ **125 passed, 6 skipped, 27 subtests passed** |
| `cli/install-agent-instructions.sh --target <dir>` | ✅ 正确安装通用 agent 指令 |

### 2.2 P1：Apple Speech 可选后端存在 macOS 专属缺陷

**问题 1：`tools/apple-speech-helper/run-apple-speech-helper.sh:74-76` 用 BSD `mktemp` 时生成固定文件名，重复/并发调用崩溃**

```bash
OUTPUT_JSON="$(mktemp '/tmp/listenkit-apple-speech-output.XXXXXX.json')"
OPEN_STDOUT_LOG="$(mktemp '/tmp/listenkit-apple-speech-open-stdout.XXXXXX.log')"
OPEN_STDERR_LOG="$(mktemp '/tmp/listenkit-apple-speech-open-stderr.XXXXXX.log')"
```

macOS 的 `/usr/bin/mktemp` 是 BSD 版，其模板的 `X` 必须位于**字符串末尾**才会被替换为随机字符（`man mktemp`：`The trailing 'Xs' are replaced`）。这里的模板 `XXXXXX.json` / `XXXXXX.log` 的 `X` 在中间。我实测 macOS 27 的行为是：**不报错，但直接创建字面固定文件名 `/tmp/listenkit-apple-speech-output.XXXXXX.json`（`X` 不被替换），文件权限 `-rw-------`**。后果：

- 文件名**不随机**。脚本第 2 行 `set -euo pipefail`，当 `/tmp` 下已存在同名残留文件时，`mktemp` 抛 `mkstemp failed: ... File exists`，脚本中止（我实测第二次调用同一模板即失败）；
- **并发调用必然冲突**：两个进程同时用 `--engine apple` 时，后到的 `mktemp` 失败；
- 即便单次调用成功，输出文件是固定的字面路径，任何进程都可能读写/清理它，存在数据竞态。

现有测试 `tests/test_transcribe_audio.py:423-509` 通过 `APPLE_SPEECH_HELPER` 指向**假 bash 脚本**，从未真正执行该 helper，因此此缺陷未被测试覆盖。

修复方向：`mktemp '/tmp/listenkit-apple-speech-output.XXXXXX'`（`X` 在末尾）后再拼接 `.json` 后缀，或在 Python 侧用 `tempfile.mkstemp()` 生成路径并传给 helper。

补充说明：Apple Speech 链路本身设计正确（`/usr/bin/open -W -n` 启动 helper app 以触发 macOS Speech 权限、`Info.plist` 声明 `NSSpeechRecognitionUsageDescription`），且 `.build/` 中 helper app 已成功编译——只是临时文件命名这一处有缺陷。

### 2.3 P2：macOS 本机可用但脆弱的平台问题

**问题 2：Swift 编译目标硬编码 `macos26.0`**

`tools/apple-speech-helper/scripts/build-helper-app.sh:47`：`-target "$(uname -m)-apple-macos26.0"`。本机 SDK≥26 可编译；但 SDK 更旧的 Xcode/CLT 上部署目标高于 SDK 会编译失败，且 macOS 27 环境仍写死 26，属脆弱硬编码。建议由 `sw_vers -productVersion` 推导或省略 `-target`。

**问题 3：`--engine apple` 在 Linux 上无明确拦截**

`listenkit_cli/transcription.py:100-111` 只对 `platform_id() == "windows"` 拦截；Linux 上会去执行 `#!/bin/zsh` 的 helper（Linux 常无 zsh）或 `/usr/bin/open`（不存在），报错不清晰。macOS 不受影响，但「仅 macOS」校验不完整。

**问题 4：跨平台错误信息在 macOS 上仍并列提示 Windows 路径**

`listenkit_cli/transcription.py:131-133` 的报错同时列出 `.\cli\init-faster-whisper.ps1` 与 `cli/init-faster-whisper.sh`，纯文案问题，无功能影响。

**问题 5：`cli/export-audio-slices.py:51` 使用 `float | None`，被 macOS CLT 的 `python3`(3.9) 调用会崩**

`previous_end: float | None = None` 在 Python 3.9 求值即 `TypeError`。README 把它列为公开接口；若机器只有 CLT 的 `python3`(3.9)（无 PATH 中的 3.10+）就会崩。`docs/install.md:23` 已声明维护脚本需 3.10+，属边界情况。

**问题 6：Homebrew 依赖仅靠 PATH 查找，非登录 shell 环境易报「Missing ffmpeg」**

`cli/import-audio.sh:156-184`、`listenkit_cli/process.py:12-13`、`cli/export-audio-slices.py:73` 用 `command -v ffmpeg` / `shutil.which("ffmpeg")`——查找方式本身正确且可移植（无硬编码 `/opt/homebrew/bin`）。但 Apple Silicon 的 Homebrew 在 `/opt/homebrew/bin`，若从 GUI app、launchd、cron 或**未做登录 shell 初始化的 Agent shell** 调用，PATH 里可能没有它，会得到「Missing required command: ffmpeg」。**对 Agent 而言这是一个真实风险**：若 Claude Code 从桌面应用启动（而非终端），其 Bash 子进程可能不带 `/opt/homebrew/bin`，此时 `doctor` 的 `ffmpeg` 检测会误报缺失。建议报错时提示 `brew install ffmpeg` 或自动探测 `/opt/homebrew/bin`。

**问题 7：无 `pyproject.toml`/`setup.py`/`requires-python` 声明**

仓库以扁平 `requirements-*.txt` + `PYTHONPATH=$repo_root` 方式运行，Python 版本只在健康检查里强制（`health.py:11` 要求 3.14、`check-runtime.sh:52`）。对 CLI 使用无碍，但对分发与依赖审计不利。

### 2.4 Agent（Claude Code）兼容性专项：Codex → Claude Code

本仓库与 LingoTrace 不同，**已提供独立的 Claude 适配器** `adapters/claude/CLAUDE.md`，README 亦明言「Not tied to Codex. Codex is only one adapter.」——这是一条已走通的多 Agent 适配路径。实测结论：

| 维度 | 结论 |
| --- | --- |
| Claude 适配器 | ✅ `adapters/claude/CLAUDE.md` 存在（27 行），覆盖核心契约：`.sh`/`.ps1` 平台选择、`--url`/`--input` 用法、输出 `.md`+`.json` 对、do-not-bypass 规则。对我可直接使用 |
| 通用指令安装 | ✅ `adapters/agent/listenkit-agent-instructions.md`（70 行，最详细）经 `cli/install-agent-instructions.sh --target <dir>` 可安装，我实测成功。内容包含平台入口选择、CLI 参数契约、`--auto-init`、默认输出路径、do-not-bypass 列表 |
| LLM 集成契约 | ✅ `LLM_INTEGRATION.md` 是完整 source of truth：区分 install/use/install+use/unknown-target 四种场景，规定「不知道 target 时不猜路径，用 `--print` 或固定询问模板」。对我可直接遵循 |
| 平台入口契约 | ✅ macOS/Linux/WSL 用 `.sh`、原生 Windows 用 `.ps1`，文档在 `LLM_INTEGRATION.md`、`adapters/agent`、`adapters/codex`、`adapters/claude`、`adapters/cursor` 五处一致，无漂移。macOS 上 `.sh` 是正确入口 |
| 代码审计（agent 能力轴） | ✅ 全部 `.sh` 只用 bash 3.2 支持的语法（`[[ ]]`、数组、`$'...'`、heredoc、`local`），无 GNU-only 工具（无 `grep -P`、`sed -i`、`find -printf`、`date -d`、`realpath`）；`find -quit` 本机实测可用。CLI 子进程均走 `subprocess.run` + PATH，无 `shell=True` |
| 依赖平台注意 | ✅ `requirements-mlx-whisper.txt` 注明「仅 Apple Silicon macOS 自动安装」、`requirements-faster-whisper-cuda.txt` 注明「仅 Windows/Linux 检测到 NVIDIA 时安装」 |
| **Claude 适配器信息密度** | ⚠️ `adapters/claude/CLAUDE.md`（27 行）明显短于 `adapters/codex/SKILL.md`（64 行，含 frontmatter + workflow + CLI examples）。核心契约都在，但缺少 Codex 版的工作流细节与逐条 CLI 示例。对 Claude Code 而言**可用但体验略糙** |
| **install 安装的是通用指令** | ⚠️ `cli/install-agent-instructions.sh` 安装 `adapters/agent/listenkit-agent-instructions.md`（通用版），不感知目标框架差异。Claude 用户安装后获得的是通用指令，而非 `adapters/claude/CLAUDE.md`。因通用版质量高，可接受，但 `--target CLAUDE.md` 时若能选择对应适配器更佳 |
| 错误提示 | ⚠️ 见 2.3 问题 4（跨平台错误信息并列 Windows 路径），对 macOS Agent 是噪音 |

### 2.5 对 macOS 兼容性的总体评估

**在 macOS 27（arm64）+ Python 3.14 上，ListenKit 默认链路可用度约 90%+。** 默认链路（URL/本地媒体 → 字幕优先 → MLX/Metal 或 faster-whisper → Markdown/JSON）逻辑正确，bash 3.2 兼容性良好，Homebrew 依赖查找方式正确，运行时快照实证 MLX 0.32.0 / faster-whisper 1.2.1 / ctranslate2 4.8.1 可用。**最可能失败/受阻的点按顺序为：①Apple Speech 可选后端的 `mktemp` 固定文件名缺陷（P1-1）；②非登录 shell / GUI / Agent 环境缺 Homebrew PATH 导致 `ffmpeg`/`yt-dlp` 误报缺失（P2-6，概率较高）；③Intel Mac 上 ctranslate2 的 Python 3.14 x86_64 wheel 可用性未验证（Apple Silicon 不受影响）。**

---

## 三、我的需求

按优先级排列，说明我需要什么才能在这台 macOS 设备上完整履行 ListenKit 的转写/切片职责：

1. **修复 Apple Speech helper 的 `mktemp` 模板缺陷。** 目前 `--engine apple` 在我这台机器上单次可用（`mktemp` 创建固定名文件），但任何残留/并发都会以 `mkstemp failed` 崩溃；我需要一个随机、幂等的临时路径。
2. **Homebrew PATH 的容错提示。** 我可能从终端或桌面应用两种宿主启动。请让 `ffmpeg`/`yt-dlp` 缺失报错时提示 `brew install ffmpeg yt-dlp`，或自动探测 `/opt/homebrew/bin`，避免在「PATH 未初始化」的宿主里误报。
3. **（可选）`install-agent-instructions.sh` 感知目标框架。** 当 `--target` 指向 `CLAUDE.md`/规则目录时，若能选择安装 `adapters/claude/CLAUDE.md` 而非通用版，Claude Code 用户的安装体验会更好。
4. **（可选）扩充 `adapters/claude/CLAUDE.md` 至与 `adapters/codex/SKILL.md` 同等信息密度。** 目前核心契约齐全，但缺少 workflow 细节与逐条 CLI 示例。

---

## 四、我的建议方案

### 方案 A（推荐）：修复 Apple Speech helper 的临时文件命名

`tools/apple-speech-helper/run-apple-speech-helper.sh:74-76` 改为 `X` 在末尾的模板，或改用 Python `tempfile`：

```bash
OUTPUT_JSON="$(mktemp '/tmp/listenkit-apple-speech-output.XXXXXX')"
OUTPUT_JSON="${OUTPUT_JSON}.json"
```

同步修改 cleanup（`trap cleanup EXIT`）与后续引用。更稳的替代：在 `cli/transcribe-audio.sh` 的 Python 编排层（`listenkit_cli/transcription.py`）用 `tempfile.mkstemp(prefix="listenkit-apple-speech-", suffix=".json")` 生成路径并传入 helper，绕开 shell `mktemp`。

### 方案 B：Homebrew PATH 容错

- `doctor`/`check-runtime.sh`/`import-audio.sh` 在 `command -v ffmpeg` 失败时，先探测 `/opt/homebrew/bin/ffmpeg` 与 `/usr/local/bin/ffmpeg`（Apple Silicon / Intel 的 Homebrew 前缀），命中则加入 PATH 并继续，否则报「请执行 `brew install ffmpeg`」；
- 或至少在报错文案中给出 `brew install ffmpeg yt-dlp` 的直接提示。

### 方案 C：Agent 安装感知框架

- `cli/install-agent-instructions.sh` 增加框架识别：`--target` 文件名包含 `CLAUDE.md` 时安装 `adapters/claude/CLAUDE.md`，包含 `AGENTS.md` 时安装通用版或 `adapters/agent/`，其余情况保持通用版；
- `--print` 默认输出通用版，文档说明三种适配器的适用场景。

### 方案 D：对齐 Claude 适配器信息密度

将 `adapters/codex/SKILL.md` 的 workflow 与 CLI examples 同步进 `adapters/claude/CLAUDE.md`（保持「不改业务逻辑、不重复实现」的原则，仅补全调用契约细节）。

### 建议的验证方式

改动后，在 macOS 上按以下顺序验证：

1. `rm -f /tmp/listenkit-apple-speech-output.*` 后连续两次运行 `run-apple-speech-helper.sh`，确认第二次不再 `mkstemp failed`；
2. 在「未做登录 shell 初始化」的 shell 中跑 `doctor`，确认 `ffmpeg`/`yt-dlp` 检测不误报（或报错可转述为安装指引）；
3. 用 `--target <dir>/CLAUDE.md` 安装指令，确认落到 Claude 适配器；
4. 回归 `python -m pytest tests/` 保持 125 passed。

---

## 五、文档落位说明

本文件放在 `docs/agent-compatibility-report/` 下。我没有修改本仓库的任何代码，没有创建分支，也没有执行提交；所有转写测试均发生在 `/tmp/` 下（合成音频、输出目录、agent 指令安装测试目录），未在仓库内留下写入。

---

## 六、附录

### 6.1 实测记录（本次真实执行）

| 命令 | 结果 |
| --- | --- |
| `cli/generate-markdown.sh --help` | ✅ 帮助正常 |
| `cli/check-runtime.sh` | ✅ `python_version=3.14.6`、`faster_whisper_version=1.2.1`、`import_health=ok` |
| `python -m listenkit_cli --help` | ✅ 9 子命令 |
| `python -m listenkit_cli doctor` | ✅ `mlx_runtime=ready`、`mlx_metal=ready`、`asr_auto_engine=mlx`、`model_mlx_small_cache=ready` |
| `cli/generate-markdown.sh --input /tmp/lt-test.aiff --language English --output /tmp/lt-out/test.md --auto-init` | ✅ `EXIT=0`，9.6s，产出 md+json+audio |
| 转写产物 | ✅ `engine=mlx-whisper`、`device=metal`、`compute_type=float16`、`timing_complete=true`、文本 100% 匹配 |
| `python -m pytest tests/` | ✅ 125 passed, 6 skipped |
| `cli/install-agent-instructions.sh --target /tmp/lt-agent-test` | ✅ 生成 `listenkit-agent-instructions.md` |
| `mktemp '/tmp/listenkit-apple-speech-output.XXXXXX.json'`（连续两次） | ⚠️ 第一次创建字面固定名文件；第二次 `mkstemp failed: File exists` |
| `mktemp '/tmp/lt-test.XXXXXX'`（`X` 在末尾） | ✅ 生成随机名 |

### 6.2 代码审计范围（macOS 兼容性）

对 `cli/*.sh`、`cli/*.py`、`listenkit_cli/*.py`、`tools/*`、`adapters/*`、`requirements-*.txt`、`docs/*`、`tests/*` 做了审计。重点核对：GNU-only 工具（未发现）、bash 3.2 语法兼容（通过）、`platform.system()`/`platform_id()` 三平台分支（完整）、MLX 仅在 Apple Silicon 启用（`mlx_runtime.py:54-58` 正确，Rosetta x86_64 自动禁用）、Homebrew 依赖查找（无硬编码路径，P2-6）、iCloud 拒绝检测（`health.py:139` 等，macOS 特有防护，正确）。发现的唯一 macOS 专属功能缺陷是 P1 的 `mktemp` 模板问题。

### 6.3 与既有的 Windows 报告的关系

本目录已有 WorkBuddy / TraeWork / QwenWork 三份 Windows 兼容性报告。本报告是同一运行时在 macOS + Claude Code 上的独立审计：

- **Windows 侧（既有报告）**：断点在「原生 Windows 用 `.ps1`，`.sh` 链路整条是 macOS 形状」（路径、运行时位置、bash 版本都不同），以及 WorkBuddy 沙箱无法读取 PowerShell stdout 等 Agent 能力差异。
- **macOS 侧（本报告）**：`.sh` 是正确入口，运行时就在 macOS 原生位置 `~/Library/Caches/ListenKit/venvs/`，默认链路完整可用。Claude Code 的 Bash 工具可执行 `.sh` 并读取 stdout，`adapters/claude/CLAUDE.md` 已主动适配。
- **跨平台共享问题**：Homebrew PATH 依赖、无打包元数据、Apple Speech 仅 macOS 可用的声明与实际校验的落差（Linux 无拦截）。

### 6.4 环境交叉验证

- `doctor` 报 `asr_auto_engine=mlx`、`model_mlx_small_cache=ready`——默认引擎与模型缓存就绪，与 LingoTrace 侧「听力链路 dry-run/apply 用 MLX 转写成功」互相印证。
- 端到端转写音频由 macOS `say` 生成（4.3 秒 AIFF），转写文本与原始语音逐字一致，证明默认链路在真实 macOS 媒体输入上可用。
