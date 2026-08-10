# Agent 运行兼容性报告：原生 Windows（ListenKit 侧）

- 报告日期：2026-08-10
- 报告范围：ListenKit 在原生 Windows 上被外部 Agent 调用时的可执行性，以及对「Claude Code Agent」（非原定目标 Codex）的兼容性
- 报告者：Claude Code（Anthropic 的 Agent CLI），运行于 Windows 11，shell 为 Git Bash
- 关联报告：`LingoTrace/docs/agent-compatibility-report/claude-code-agent-windows-compatibility.md`

---

## 一、我是谁

**一句话身份：我是运行在 Windows（win32）操作系统之上的「Claude Code」Agent 框架中的 AI 助手，是 ListenKit 的下游集成方。**

- **Agent 框架 / 产品**：Claude Code —— Anthropic 官方的命令行 Agent CLI。我以「Agent Loop」方式运行：每轮读取指令与工具结果、选择工具、执行、回收输出并迭代。框架为我提供 Bash（Git Bash）、文件系统读写、Grep/Glob 检索、Web 检索等工具。**与 WorkBuddy 沙箱不同，我的 Bash 工具可以调用 PowerShell（`powershell`/`pwsh`）并完整读取其 stdout**——这一能力差异直接决定了本报告对 `.ps1` 通道的结论。
- **宿主操作系统**：Windows 11（系统内部标识 `win32`，Build 10.0.26220，AMD64）。命令执行入口是 Git Bash（MSYS2/MINGW64）。
- **与运行时的关系**：我通过上游 LingoTrace 运行时间接调用本项目。LingoTrace 的 `SKILL.md` 要求我解析出 ListenKit 安装位置，并通过 ListenKit 的公共入口获取转写与音频切片；我按 `LLM_INTEGRATION.md` 的约定行事（「不要绕过公共入口直接调用 `yt-dlp`/`ffmpeg`/`tools/*`」）。我不依赖 `adapters/` 下的任何适配器，因为本项目没有 Claude Code 专属适配器，也不需要——按 `LLM_INTEGRATION.md` 的公共入口接入即可。

我的执行环境（本次实测）：

| 项目 | 实测值 |
| --- | --- |
| 操作系统 | Windows 11（10.0.26220），AMD64 |
| 默认 Shell | Git Bash（MSYS2/MINGW64，`/usr/bin/bash`） |
| PowerShell | Windows PowerShell **5.1**.26100.9022（`powershell`，可从 Bash 调用并捕获 stdout） |
| PowerShell 7 | **pwsh 7.6.4** 可用（`shutil.which("pwsh")` 可解析） |
| `python`（真实） | 3.14.4（`%LOCALAPPDATA%\Programs\Python\Python314\python.exe`） |
| `python3` | **Microsoft Store 别名 stub**（`AppInstallerPythonRedirector.exe`，调用即 exit 49、无输出） |
| `py` 启动器 | **不存在** |
| `bash` 解析 | `shutil.which("bash")` → `C:\Program Files\Git\usr\bin\bash.EXE` |
| ffmpeg / ffprobe / yt-dlp | 均在 PATH（WinGet Links） |
| ListenKit 托管运行时 | `%LOCALAPPDATA%\ListenKit\venvs\cpython-314`，**健康**（CUDA float16、faster-whisper 1.2.1、model small 已缓存） |
| GPU | NVIDIA GeForce GTX 1660 SUPER（6 GB，CUDA 就绪） |
| 本仓库 Git 状态 | `main`；`origin` 为个人 fork、`upstream` 为官方；工作区有**先前就存在的 CRLF-only 改动**（详见 2.4），非本报告产生 |

---

## 二、问题是什么

**先说结论：ListenKit 的原生 Windows 通道（`.ps1` + `listenkit_cli`）是健康的，我在本机完整跑通；`listenkit_cli` Python 核心对 Windows 的适配（`platform_paths.py`、`process.py`、`asr_device.py`、`cuda_runtime.py`、`transcription.py`）是高质量的。问题集中在 `.sh` 通道是纯 macOS 形状、以及个别解释器解析假设。**

### 2.1 已验证健康的部分（实测通过）

**`.ps1` 通道对我（Claude Code）完全可用。** `.\cli\listenkit.ps1 doctor` 实测输出（节选，stdout 完整捕获）：

```
platform=windows
runtime_dir=C:\Users\jiezhengj\AppData\Local\ListenKit\venvs\cpython-314
runtime_python=...\Scripts\python.exe
python_version=3.14.4          abi_tag=cpython-314
faster_whisper_version=1.2.1   import_health=ok
cuda_device_0_name=NVIDIA GeForce GTX 1660 SUPER
cuda_runtime=ready             asr_auto_device=cuda  asr_auto_compute_type=float16
EXIT=0
```

更关键的：**我用官方 Windows 公共入口 `.\cli\generate-markdown.ps1` 完成了一次真实的端到端转写**（3 秒测试音频 → 转写），`EXIT=0`，产出同一前缀的 `.md` 与 `.json`：

```json
{"engine": "faster-whisper", "model": "small", "device": "cuda",
 "compute_type": "float16", "locale": "en-US", "timing_complete": true}
```

**这条结论与 WorkBuddy 的报告不同**：WorkBuddy 因沙箱「调用 PowerShell 返回空 stdout」而无法使用 `.ps1` 通道；我的环境可以，所以 `.ps1` 对我不是断点。这一差异只与 Agent 框架有关，与 ListenKit 本身无关。

另外验证了设计上的优点：运行时解析不依赖发起进程的解释器——用系统 Python 执行 `python -m listenkit_cli doctor` 依然正确指向 `cpython-314` 托管 venv。

### 2.2 P1：`.sh` 通道是纯 macOS 形状，且会误导使用者

`LLM_INTEGRATION.md` 已写明「原生 Windows 用 `.ps1`」，所以下面这些严格说不算违约。但它们会**主动产生错误结论**而不是干净地拒绝执行——这是我认为值得修的原因。

**问题 a：`cli/check-runtime.sh:6` 无条件硬编码 macOS 路径，且没有环境变量逃生口**

```bash
python_executable="${HOME}/Library/Caches/ListenKit/venvs/cpython-314/bin/python"
```

在 Windows Git Bash 下的实际输出（我实测）：

```
ListenKit runtime is missing: /c/Users/jiezhengj/Library/Caches/ListenKit/venvs/cpython-314/bin/python
Repair: .../cli/init-faster-whisper.sh
```

两个问题：第一，**假阴性**——真实的 Windows 运行时就在 `%LOCALAPPDATA%\ListenKit\venvs\cpython-314` 且完全健康（我实测 CUDA float16）；第二，修复建议会引导去跑 `init-faster-whisper.sh`，即**在已有健康 CUDA 运行时的情况下重复下载构建第二套环境**。对流量计费或磁盘紧张的用户是实质损害。

对比 `transcribe-audio.sh:181-182` 是有逃生口的：

```bash
runtime_dir="${LISTENKIT_FASTER_WHISPER_VENV_DIR:-${HOME}/Library/Caches/...}"
repo_venv_python="${LISTENKIT_FASTER_WHISPER_VENV_PYTHON:-${runtime_dir}/bin/python}"
```

`check-runtime.sh` 却没有，两者不一致。

**问题 b：`cli/init-faster-whisper.sh` 假定 Homebrew 布局**

`init-faster-whisper.sh:94-98` 与 `:149` 写死了 `/opt/homebrew/bin/python3.14`、`/opt/homebrew/opt/python@3.14/bin/python3.14`、`/usr/local/bin/python3.14`，报错文案也直接建议 `export LISTENKIT_FASTER_WHISPER_BOOTSTRAP_PYTHON=/opt/homebrew/...`。这在 Windows 上没有任何意义。

**问题 c：`--help` 能正常输出，掩盖了不可用性**

我实测 `bash cli/generate-markdown.sh --help` 在 Git Bash 下输出完整且正常。这会让集成方（包括我）产生「`.sh` 在 Windows 上可用」的错觉，直到真正执行时才在运行时解析阶段失败（`generate-markdown.sh` → `init-faster-whisper.sh` → Homebrew 路径，实测报错 `Set LISTENKIT_FASTER_WHISPER_BOOTSTRAP_PYTHON=/opt/homebrew/bin/python3.14`）。**一个平台上不受支持的入口，最好在入口处就明确拒绝，而不是让帮助信息看起来一切正常。**

**问题 d（好消息）：`.sh` 通道其实差得不远**

我做了一次验证性实验——给 `.sh` 通道注入正确的 Windows 运行时路径：

```bash
LISTENKIT_FASTER_WHISPER_VENV_DIR=".../AppData/Local/ListenKit/venvs/cpython-314" \
LISTENKIT_FASTER_WHISPER_VENV_PYTHON=".../Scripts/python.exe" \
bash cli/transcribe-audio.sh --audio-path probe.wav --locale en \
     --engine faster-whisper --output probe.json
```

**成功了。** 产出 JSON：`engine=faster-whisper, device=cuda, compute_type=float16, model=small`。

也就是说，`.sh` 通道在 Windows Git Bash 上的唯一障碍就是那几个 macOS 默认路径。脚本逻辑本身、参数传递、Windows 路径处理都没问题。把默认值改成平台感知，这条通道就能顺带支持 Git Bash 环境（但 `.ps1` 仍是官方推荐，见方案 A/B）。

### 2.3 P1：解释器解析假设与 Windows 常见安装不符

**问题 a：`cli/listenkit.ps1:24-25` 依赖 `py` 启动器 / `python3.14`**

```powershell
$candidates += ,@("py", @("-3.14"))
$candidates += ,@("python3.14", @())
```

本机 `py` 与 `python3.14` 均不存在，最终落到 `python`（3.14.4），校验 `>=3.10` 通过——**这次是运气好**。

**问题 b：`listenkit_cli/runtime.py:51-52` 同样的假设**

```python
PythonCommand("py", ("-3.14",)),
PythonCommand("python3.14"),
```

引导初始化时 `py`/`python3.14` 缺失被静默跳过，只有 `python` 兜底。若用户 `PATH` 里 `python` 是 3.9 或 Store stub，引导会失败，而托管 venv `%LOCALAPPDATA%\ListenKit\venvs\cpython-314\Scripts\python.exe` 就摆在那里却不在候选里。

**问题 c：托管 venv 不在候选列表**

`listenkit.ps1` 与 `runtime.py` 的候选都没有 `%LOCALAPPDATA%\ListenKit\venvs\cpython-314\Scripts\python.exe`。既然运行时解析「不依赖发起进程的解释器」是设计目标，把这个已知可用的解释器加入候选是最自然的补强。

### 2.4 P2：其他

**问题 a：`.sh` 链路其余 macOS 形状点**

- `transcribe-audio.sh:181-182`：macOS 默认路径（有逃生口，故 P2）；
- `extract-subtitles.sh:95` 与 `generate-markdown.sh:302,354`：依赖 `python3` 或 `#!/usr/bin/env python3`——本机 `python3` 是失败的 Store stub，Git Bash 下通常也只有 `python.exe`；
- `transcribe-audio.sh:162-176`：`--engine apple` 会去执行 `#!/bin/zsh` 的 Apple Speech helper（Windows 无 zsh）。Python 核心在 `transcription.py:100-108` 已在 Windows 上拒绝 apple，所以只有绕过核心直接走 `.sh` 才会踩到；
- 所有 `cli/*.sh` **都没有** MINGW/MSYS/CYGWIN 平台分支。

**问题 b：Agent 契约假设「调用方能执行 `.ps1` 并读取 stdout」**

四个适配器（`codex/SKILL.md`、`codex/agents/openai.yaml`、`agent/listenkit-agent-instructions.md`、`claude/CLAUDE.md`）的契约一致且正确：「原生 Windows → `.ps1`」。但它隐含假设调用方能执行 `.ps1` 并读到结果——这对 WorkBuddy 类沙箱不成立（其报告 §2.3 记录 stdout 为空）。对 Claude Code 成立。此外，**Git Bash / MSYS 既不是 WSL 也不是「原生 Windows 传统意义上的 PowerShell 环境」，契约没有点名它的归属**，而这是 Windows 上 Agent 最常见的 shell。建议在 `LLM_INTEGRATION.md` 补一句（见方案 E）。

**问题 c：无 `--report-json`**

`generate-markdown` 打印的是输出路径，执行结论（`status`、fallback 诊断、实际 engine/device）只在 `<output>.json` 转写内容里，不含本次执行的状态与 fallback 诊断。对无法捕获子进程 stdout 的沙箱 Agent，需要一个落盘的结构化结果通道（见方案 C）。

**问题 d：`.ps1` 自身不处理 `-ExecutionPolicy`**

各 `.ps1` 由用户/Agent 以 `powershell -ExecutionPolicy Bypass -File` 调用；`tests/test_windows_runtime.py` 也总是显式传 `Bypass`。但 agent 指令契约（`adapters/*`）没有提这一点，Restricted 策略机器上直接 `.\cli\generate-markdown.ps1` 会被拒。建议在契约文档补一句。

**问题 e：工作区状态说明**

本仓库工作区在我审计前就有若干 ` M` 文件，经核实是 `core.autocrlf=true` 下的 **CRLF-only 行尾差异**（`git diff` 为空、`--ignore-space-at-eol` 也为空，mtime 早于本次审计），非内容改动，也非本报告产生。`docs/agent-compatibility-report/` 为未跟踪目录（前几份报告的落位处）。本报告不修改任何代码或既有文件。

---

## 三、我的需求

1. **`.sh` 通道要么支持 Windows，要么明确拒绝。** 目前它介于两者之间——`--help` 正常、执行失败、还给出会造成重复构建的错误建议。这是最坏的一种状态。我倾向「支持」，因为 2.2(d) 的实验证明只差平台感知的默认路径；若选择拒绝，请在入口处硬拒绝。
2. **不要在已有健康运行时的情况下建议重建。** `check-runtime.sh` 当前的输出会引导用户/Agent 下载第二套 CUDA 环境。
3. **解释器候选中包含托管 venv。** 见 2.3(c)——这能把「运气好才跑通」变成「设计上必然跑通」。
4. **（对受限沙箱可选）一条不强依赖 PowerShell stdout 的结果获取方式。** 对我（Claude Code）不必须，但对 WorkBuddy 类沙箱是刚需；`--report-json <path>` 落盘是普适解法。
5. **在 `LLM_INTEGRATION.md` 给 Agent 一句明确的平台指引。** 补上 Git Bash / MSYS 的归属判断，并注明 `.ps1` 调用需要 `-ExecutionPolicy Bypass`。

---

## 四、我的建议方案

### 方案 A（推荐）：给 `.sh` 通道加平台感知的默认路径

抽出一个共享的运行时路径解析片段，供 `check-runtime.sh`、`transcribe-audio.sh`、`init-faster-whisper.sh` 复用：

```bash
# cli/_runtime-paths.sh
listenkit_default_runtime_dir() {
  case "$(uname -s)" in
    Darwin)
      printf '%s' "${HOME}/Library/Caches/ListenKit/venvs/cpython-314" ;;
    MINGW*|MSYS*|CYGWIN*)
      local base="${LOCALAPPDATA:-${HOME}/AppData/Local}"
      printf '%s' "$(cygpath -u "${base}")/ListenKit/venvs/cpython-314" ;;
    *)
      printf '%s' "${XDG_CACHE_HOME:-${HOME}/.cache}/ListenKit/venvs/cpython-314" ;;
  esac
}

listenkit_default_runtime_python() {
  local dir; dir="$(listenkit_default_runtime_dir)"
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) printf '%s' "${dir}/Scripts/python.exe" ;;
    *)                    printf '%s' "${dir}/bin/python" ;;
  esac
}
```

三个脚本改为：

```bash
runtime_dir="${LISTENKIT_FASTER_WHISPER_VENV_DIR:-$(listenkit_default_runtime_dir)}"
python_executable="${LISTENKIT_FASTER_WHISPER_VENV_PYTHON:-$(listenkit_default_runtime_python)}"
```

顺带给 `check-runtime.sh` 补上它现在缺失的两个环境变量逃生口，与 `transcribe-audio.sh` 保持一致。对 `init-faster-whisper.sh`：Windows 分支下不应再探测 Homebrew 路径，建议直接提示改用 `.\cli\init-faster-whisper.ps1`，并把错误文案中的 `/opt/homebrew/...` 换成平台对应的示例。

理由：这是最小改动，且 2.2(d) 已证明只要路径对了，Windows Git Bash 上的转写就能跑通并正确使用 CUDA。

### 方案 B（若不愿支持 `.sh` on Windows）：在入口处硬拒绝

在每个 `.sh` 顶部插入：

```bash
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    echo "ListenKit .sh entrypoints are not supported on native Windows shells." >&2
    echo "Use the PowerShell entrypoint instead: .\\cli\\$(basename "$0" .sh).ps1" >&2
    exit 64 ;;
esac
```

这样至少消除了「`--help` 看起来正常」的误导，也不会再给出会导致重复构建的修复建议。比现状好，但不如方案 A。

### 方案 C：为受限 Agent 提供落盘的结构化结果

给 `generate-markdown` 与 `transcribe-audio` 增加：

```
--report-json <path>    将执行结论写入 JSON：status、engine、device、
                        compute_type、fallback 诊断、输出文件路径、耗时
```

这解决的是 Agent 沙箱对子进程 stdout 捕获能力参差的问题——**读文件是普适能力，捕获 stdout 不是**。建议同时写入 `LLM_INTEGRATION.md`，作为推荐给 Agent 集成方的标准做法。

（补充：`generate-markdown` 已经会产出 `<output>.json` 转写文件，但那是转写内容，不含本次执行的 `status` 与 fallback 诊断，无法替代 `--report-json`。）

### 方案 D：解释器候选加入托管 venv

`cli/listenkit.ps1:20-27` 的候选列表前部插入：

```powershell
$managed = Join-Path $env:LOCALAPPDATA "ListenKit\venvs\cpython-314\Scripts\python.exe"
if (Test-Path $managed) { $candidates += ,@($managed, @()) }
```

放在 `LISTENKIT_CLI_PYTHON` 之后、`py -3.14` 之前。`listenkit_cli/runtime.py:49-54` 的 Windows 分支同理（可在 `python` 之后追加托管 venv，或在其前）。这样即使用户系统 `python` 版本过低或是 Store alias stub，只要托管运行时已初始化就仍可用。

### 方案 E：文档补充 Git Bash 的契约归属与 ExecutionPolicy

建议把 `LLM_INTEGRATION.md` 中那句改写为：

> Use `.ps1` on native Windows, including when your shell is Git Bash / MSYS2 / Cygwin.
> Use `.sh` on macOS, Linux, and WSL. Git Bash is **not** WSL: it runs Win32 binaries
> against Windows paths, so the POSIX runtime layout does not apply.
> Invoke `.ps1` with `powershell -NoProfile -ExecutionPolicy Bypass -File ...` when
> the host execution policy may be restricted.

（若采纳方案 A，则改为说明 `.sh` 在 Git Bash 下亦受支持，并列出所需环境变量。）

### 建议的验证方式

1. 在 Windows Git Bash 下 `bash cli/check-runtime.sh` → 应识别到 `%LOCALAPPDATA%` 下的运行时并报告 ready，而非 missing；
2. 用 2 秒测试音频跑 `generate-markdown`，确认 `device=cuda`；
3. 在 macOS 上回归 `check-runtime.sh` / `transcribe-audio.sh`，确认默认路径未变；
4. 临时改名或清空 `PATH` 中的 `python`，确认 `.ps1` 仍能通过托管 venv 启动。

---

## 五、文档落位说明

本文件放在 `docs/agent-compatibility-report/` 下，与 `debugging.md`、`install.md`、`backends.md` 同级，不修改任何仓库代码。

我没有修改本仓库任何代码，没有创建分支，也没有执行提交。本次检查产生的临时探针文件（测试音频、转写 `.md`/`.json`）全部位于系统临时目录，已可清理；仓库工作区除本报告与既有 `docs/agent-compatibility-report/` 未跟踪目录外，保持与审计前一致（含先前就存在的 CRLF-only 标记，见 2.4-e）。

需要说明：`docs/one-click-agent-install-plan.md` 等既有文档我未逐字比对，若本报告建议与其中已有规划重复或冲突，以维护者的既定路线为准。

---

## 六、附录：Claude Code Agent 兼容性专项（相对原定目标 Codex 的对照）

### 6.1 为什么需要这一节

两个运行时的目标 Agent 是 Codex（`adapters/codex/` 含 `SKILL.md` + `agents/openai.yaml`），而我实际是 **Claude Code**。操作系统兼容性与 Agent 框架兼容性是两个独立轴，不能混为一谈。

### 6.2 双轴定义

- **轴一 · 操作系统兼容性（Windows vs macOS/Linux）**：路径分隔符、shell 解释器（bash vs pwsh）、平台专用入口（`.sh` vs `.ps1`）。本报告 §二已覆盖。
- **轴二 · Agent 框架兼容性（Codex 假设 vs Claude Code 实际）**：运行时对「调用方能自由执行 shell 并读 stdout」这一隐含前提是否成立。这一层与操作系统无关。

### 6.3 对照表：Codex 能力假设 → Claude Code 实际

| # | Codex（原定目标）的能力假设 | Claude Code（实际调用方） | 结论 |
| --- | --- | --- | --- |
| 1 | Agent 可执行 `.ps1` 并读取 stdout | **成立**——我的 Bash 工具可调用 `powershell`/`pwsh` 并完整捕获输出（已实测 `listenkit.ps1 doctor`、`generate-markdown.ps1` 转写） | ✅ 无断点 |
| 2 | Agent 通过适配层（`adapters/codex` 等）接入 | 我走 Vault `AGENTS.md` / `LLM_INTEGRATION.md`，无专属适配层，也**不需要** | ✅ 接入可用 |
| 3 | 解释器候选含常见位置（`py`/`python3.14`） | 本机无 `py`、无 `python3.14`；`python3` 是失败的 Store stub | ⚠️ 依赖 `python`=3.14.4 的运气（见 2.3） |
| 4 | 上游 LingoTrace `resolve-listenkit` 返回当前平台可用入口 | 上游返回 `.sh`（ListenKit 契约禁止原生 Windows 使用） | ❌ 断点在**上游**，见 LingoTrace 报告 §2.2 |

### 6.4 关键洞见：对 Claude Code 而言，断点不在 ListenKit 而在上游编排层

我在本机实测**完整跑通了 ListenKit 的原生 Windows 通道**（`.ps1` 端到端 CUDA 转写）。`listenkit_cli` Python 核心对 Windows 的适配质量很高（`platform_paths.py` 用 `%LOCALAPPDATA%`+`Scripts\python.exe`、`asr_device.py` 用 `ctypes.WinDLL`+`os.add_dll_directory`、`cuda_runtime.py` 在 Windows 用 `PATH`、`transcription.py` 在 Windows 拒绝 apple 引擎）。

因此我的结论与 WorkBuddy 不同：**WorkBuddy 的断点（沙箱读不到 PowerShell stdout）对 Claude Code 不成立**；对我而言，让「经 LingoTrace 全链路开箱即用」成立的关键在**上游 LingoTrace 的平台感知入口选择**（返回 `.ps1`、`transcribe_listening.py` 不再硬编码 `/bin/bash`），而不是本仓库的适配。这也是本报告把需求 1、2、5 放在前面的原因——即使 `.sh` 通道维持现状，只要上游修好入口选择，我就能通过 `.ps1` 完成精听链路。

### 6.5 给维护者的补充建议（在 §四 之上）

1. 若希望运行时对 Codex 之外的 Agent 也鲁棒：所有面向 Agent 的入口提供 `--report-json` 落盘（不只转写内容，含本次执行的 `status`/`fallback` 诊断）；
2. 在 `LLM_INTEGRATION.md` 显式列出「支持的 Agent 接入方式」，承认「任意遵循公共契约的通用 Agent」这一路径，并点名 Git Bash 的归属；
3. `resolve-listenkit` 等上游返回值按调用方当前平台给出可用入口（这属于上游，但值得在此指出）。
