# Agent 运行兼容性报告：原生 Windows（ListenKit 侧）

- 报告日期：2026-08-10
- 报告范围：ListenKit 在原生 Windows 上被外部 Agent 调用时的可执行性，以及对「WorkBuddy Agent」（非原定目标 Codex）的兼容性
- 关联报告：`LingoTrace/docs/agent-compatibility-report/workbuddy-agent-windows-compatibility.md`

---

## 一、我是谁

**一句话身份：我是运行在 Windows（win32）操作系统之上的「WorkBuddy」Agent 框架中的 AI 助手，是 ListenKit 的下游集成方。**

- **Agent 框架 / 产品**：WorkBuddy —— 一个带工具调用的 LLM Agent 平台。我以「Agent Loop」方式运行：每轮观察上下文、选择工具、执行动作、回收结果并迭代，直至任务完成。框架为我提供 Bash、PowerShell、文件系统读写、MCP 连接器等工具，工作模式为 Craft（直接执行）。
- **宿主操作系统**：Windows（系统内部标识 `win32`，本机为 Windows 11，AMD64）。我的命令执行入口是 Git Bash（MinGW64，由 WorkBuddy 托管），独立的 PowerShell 工具也由框架提供。
- **与运行时的关系**：我不是 ListenKit 的直接用户，而是通过 LingoTrace 运行时间接调用本项目的下游集成方；我不依赖 `adapters/` 下的任何适配器，而是按 `LLM_INTEGRATION.md` 约定的公共入口接入。

我不是 ListenKit 的直接用户，而是它的**下游集成方**：

- 我的主职责是维护用户的 LingoTrace 英语学习 Vault；
- 当用户说「请把这段音频做成精听稿」时，LingoTrace 的 `SKILL.md` 要求我解析出 ListenKit 安装位置，并通过 ListenKit 的公共入口获取转写与音频切片；
- 我按 `LLM_INTEGRATION.md` 的约定行事，特别是「不要绕过公共入口去直接调用 `yt-dlp` / `ffmpeg` / `tools/*`」这一条。

关于适配器：本仓库的 `adapters/` 下有 `agent`、`claude`、`codex`、`cursor`，但没有 WorkBuddy 的。我不依赖这些适配器，而是通过 LingoTrace 运行时间接调用本项目，因此**无需为我新增适配器**。这里说明只是为了让你知道调用方是谁。

我的执行环境（本次实测）：

| 项目 | 实测值 |
| --- | --- |
| 操作系统 | Windows 11（10.0.26220），AMD64 |
| 默认 Shell | Git Bash（MinGW64） |
| PowerShell | Windows PowerShell **5.1**.26100.9022（无 PowerShell 7） |
| `py` 启动器 | **不存在** |
| Git Bash 中的 `python` | 3.13.14 |
| PowerShell 中的 `python` | 3.14.4 |
| 本仓库 Git 状态 | `main`，工作区干净，`origin` 为个人 fork、`upstream` 为官方 |

---

## 二、问题是什么

先说结论：**ListenKit 的原生 Windows 通道（`.ps1` + `listenkit_cli`）是健康的，我实测完全跑通。问题集中在两处：一是 `.sh` 通道是纯 macOS 形状且缺少平台分支，二是我作为 Agent 在 Windows 上访问 `.ps1` 通道存在实际障碍。**

### 2.1 已验证健康的部分

`.\cli\listenkit.ps1 doctor` 实测输出（节选）：

```
platform=windows
runtime_dir=C:\Users\jiezhengj\AppData\Local\ListenKit\venvs\cpython-314
runtime_python=...\Scripts\python.exe
python_version=3.14.4          abi_tag=cpython-314
faster_whisper_version=1.2.1   import_health=ok
yt_dlp_path=...\yt-dlp.EXE     ffmpeg_path=...\ffmpeg.EXE
cuda_runtime=ready             cuda_device_0_name=NVIDIA GeForce GTX 1660 SUPER
asr_auto_device=cuda           asr_auto_compute_type=float16
EXIT=0
```

另外我验证了一个设计上的优点：**运行时解析不依赖发起进程的解释器**。我用 Git Bash 里的 Python 3.13 执行 `python -m listenkit_cli doctor`，它依然正确指向 `cpython-314` 的托管 venv，没有因 ABI 不匹配去重建环境。这个隔离做得很好。

### 2.2 P1：`.sh` 通道是纯 macOS 形状，且会误导使用者

`LLM_INTEGRATION.md` 已经写明「原生 Windows 用 `.ps1`」，所以下面这些严格说不算违约。但它们会**主动产生错误结论**，而不是干净地拒绝执行——这是我认为值得修的原因。

**问题 a：`cli/check-runtime.sh:6` 无条件硬编码 macOS 路径，且没有环境变量逃生口**

```bash
python_executable="${HOME}/Library/Caches/ListenKit/venvs/cpython-314/bin/python"
```

在 Windows Git Bash 下的实际输出：

```
ListenKit runtime is missing: /c/Users/jiezhengj/Library/Caches/ListenKit/venvs/cpython-314/bin/python
Repair: .../cli/init-faster-whisper.sh
```

这句话有两个问题：第一，它是**假阴性**——真实的 Windows 运行时就在 `%LOCALAPPDATA%\ListenKit\venvs\cpython-314` 且完全健康；第二，它给出的修复建议会引导对方去跑 `init-faster-whisper.sh`，也就是在已有健康 CUDA 运行时的情况下**重复下载构建第二套环境**。

对比 `transcribe-audio.sh:181-182`，那里是有逃生口的：

```bash
runtime_dir="${LISTENKIT_FASTER_WHISPER_VENV_DIR:-${HOME}/Library/Caches/...}"
repo_venv_python="${LISTENKIT_FASTER_WHISPER_VENV_PYTHON:-${runtime_dir}/bin/python}"
```

`check-runtime.sh` 却没有，两者不一致。

**问题 b：`cli/init-faster-whisper.sh` 假定 Homebrew 布局**

第 31-32、94-96、149 行写死了 `/opt/homebrew/bin/python3.14`、`/usr/local/bin/python3.14`，报错文案也直接建议 `export LISTENKIT_FASTER_WHISPER_BOOTSTRAP_PYTHON=/opt/homebrew/...`。这在 Windows 上没有任何意义。

**问题 c：`--help` 能正常输出，掩盖了不可用性**

我实测 `bash cli/generate-markdown.sh --help` 在 Git Bash 下输出完整且正常。这会让集成方（包括我）产生「`.sh` 在 Windows 上可用」的错觉，直到真正执行时才在运行时解析阶段失败。**一个平台上不受支持的入口，最好在入口处就明确拒绝，而不是让帮助信息看起来一切正常。**

**问题 d（好消息）：`.sh` 通道其实差得不远**

我做了一次验证性实验——给 `.sh` 通道注入正确的 Windows 运行时路径：

```bash
LISTENKIT_FASTER_WHISPER_VENV_DIR=".../AppData/Local/ListenKit/venvs/cpython-314" \
LISTENKIT_FASTER_WHISPER_VENV_PYTHON=".../Scripts/python.exe" \
bash cli/transcribe-audio.sh --audio-path probe.wav --locale en \
     --engine faster-whisper --output probe.json
```

**成功了。** 产出 JSON：`engine=faster-whisper, device=cuda, compute_type=float16, model=small, locale=en`。

也就是说，`.sh` 通道在 Windows Git Bash 上的唯一障碍就是那几个 macOS 默认路径。脚本逻辑本身、参数传递、Windows 路径处理都没问题。把默认值改成平台感知，这条通道就能顺带支持 Git Bash 环境。

### 2.3 P1：我作为 Agent 访问 `.ps1` 通道存在实际障碍

这一条不是你们的 bug，但它直接影响我能否遵守你们的契约，所以必须如实说明。

`LLM_INTEGRATION.md` 要求原生 Windows 走 `.ps1`。但在我的沙箱里：

1. **我的 Bash 工具拒绝调用 PowerShell**，返回：
   `Command blocked for security: Invoking PowerShell from Bash bypasses PowerShell security checks`
2. **我的独立 PowerShell 工具在本机取不到 stdout**——执行成功、退出码 0，但返回内容为空。我最终是靠 `Out-File` 落盘再读文件，才拿到上面那份 `doctor` 输出的。

后果是：**你们唯一官方支持的 Windows 入口，对我来说是「能触发但读不到结果」的。** 而 `generate-markdown` 的返回值（`status`、`fallback` 诊断、实际使用的 engine/device）恰恰是我必须转述给用户的信息。这类沙箱限制在 Agent 环境里相当常见，不会只有我一个。

### 2.4 P2：PowerShell 5.1 与 `py` 缺失下的解释器解析

`cli/listenkit.ps1:20-27` 的候选顺序是 `LISTENKIT_CLI_PYTHON` → `py -3.14` → `python3.14` → `python`。本机 `py` 与 `python3.14` 均不存在，最终落到 `python`（3.14.4），校验 `>= 3.10` 通过——**这次是运气好**。

如果用户的 `PATH` 里 `python` 恰好是 3.9 或某个 Microsoft Store 别名 stub，就会直接抛 `Python 3.10 or newer is required`，而此时 `%LOCALAPPDATA%\ListenKit\venvs\cpython-314\Scripts\python.exe` 这个已知可用的解释器就摆在那里却不在候选列表里。建议把托管 venv 的解释器加入候选。

另外这套 `.ps1` 在 PowerShell 5.1 下工作正常，我确认它没有使用 `??`、`?.`、三元运算符等 7+ 语法，这点做得很稳妥。

---

## 三、我的需求

1. **`.sh` 通道要么支持 Windows，要么明确拒绝。** 目前它介于两者之间——`--help` 正常、执行失败、还给出会造成重复构建的错误建议。这是最坏的一种状态。我倾向于「支持」，因为 2.2(d) 的实验证明只差平台感知的默认路径。

2. **不要在已有健康运行时的情况下建议重建。** `check-runtime.sh` 当前的输出会引导用户/Agent 去下载第二套 CUDA 环境。对使用流量计费或磁盘紧张的用户，这是实质损害。

3. **一条不强依赖 PowerShell stdout 的 Windows 结果获取方式。** 我需要读到 `generate-markdown` 的执行结论。可行的方向：支持 `--report-json <path>` 把结构化结果落盘，这样任何沙箱受限的 Agent 都能通过读文件拿到结果，而不必依赖捕获 PowerShell 的标准输出。

4. **解释器候选中包含托管 venv。** 见 2.4。

5. **在 `LLM_INTEGRATION.md` 中给 Agent 一句明确的平台指引。** 现在的表述是「`.sh` 用于 macOS/Linux/WSL，`.ps1` 用于原生 Windows」。建议补上 Git Bash / MSYS 的归属判断——它既不是 WSL，也不是原生 PowerShell 环境，目前处于契约的灰区，而这恰恰是 Windows 上 Agent 最常见的 shell。

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

顺带给 `check-runtime.sh` 补上它现在缺失的两个环境变量逃生口，与 `transcribe-audio.sh` 保持一致。

理由：这是最小改动，且 2.2(d) 已证明只要路径对了，Windows Git Bash 上的转写就能跑通并正确使用 CUDA。

对 `init-faster-whisper.sh`：Windows 分支下不应再探测 Homebrew 路径，建议直接提示改用 `.\cli\init-faster-whisper.ps1`，并把错误文案中的 `/opt/homebrew/...` 换成平台对应的示例。

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

这解决的是 2.3 的根本矛盾：Agent 沙箱对子进程 stdout 的捕获能力千差万别，但**读文件是普适能力**。建议同时写入 `LLM_INTEGRATION.md`，作为推荐给 Agent 集成方的标准做法。

（补充：`generate-markdown` 已经会产出 `<output>.json` 转写文件，但那是转写内容，不含本次执行的 `status` 与 fallback 诊断，无法替代 `--report-json`。）

### 方案 D：解释器候选加入托管 venv

`cli/listenkit.ps1:20-27` 的候选列表前部插入：

```powershell
$managed = Join-Path $env:LOCALAPPDATA "ListenKit\venvs\cpython-314\Scripts\python.exe"
if (Test-Path $managed) { $candidates += ,@($managed, @()) }
```

放在 `LISTENKIT_CLI_PYTHON` 之后、`py -3.14` 之前。这样即使用户的系统 `python` 版本过低或是 Store 别名 stub，只要托管运行时已初始化就仍可用。

### 方案 E：文档补充 Git Bash 的契约归属

建议把 `LLM_INTEGRATION.md` 中那句改写为：

> Use `.ps1` on native Windows, including when your shell is Git Bash / MSYS2 / Cygwin.
> Use `.sh` on macOS, Linux, and WSL. Git Bash is **not** WSL: it runs Win32 binaries
> against Windows paths, so the POSIX runtime layout does not apply.

（若采纳方案 A，则改为说明 `.sh` 在 Git Bash 下亦受支持，并列出所需环境变量。）

### 建议的验证方式

1. 在 Windows Git Bash 下 `bash cli/check-runtime.sh` → 应识别到 `%LOCALAPPDATA%` 下的运行时并报告 ready，而非 missing；
2. 用 2 秒测试音频跑 `generate-markdown`，确认 `device=cuda`；
3. 在 macOS 上回归 `check-runtime.sh` / `transcribe-audio.sh`，确认默认路径未变；
4. 临时改名或清空 `PATH` 中的 `python`，确认 `.ps1` 仍能通过托管 venv 启动。

---

## 五、文档落位说明

本文件放在 `docs/` 下，与 `debugging.md`、`install.md`、`backends.md` 同级。

我没有修改本仓库任何代码，没有创建分支，也没有执行提交。本次检查产生的临时探针文件（测试音频与转写 JSON）已全部清理，仓库工作区保持干净（`git status --porcelain` 除本文件外无输出）。

需要说明的一点是：`docs/one-click-agent-install-plan.md` 等既有文档我未逐字比对，若本报告的建议与其中已有规划重复或冲突，以维护者的既定路线为准。

---

## 六、附录：WorkBuddy Agent 兼容性专项（相对原定目标 Codex 的对照）

> 本节把上一版嵌在「Windows 兼容性」里的 Agent 维度单独成轴。本报告从 ListenKit 视角书写；上游 LingoTrace 调用本项目时碰到的问题，回指其自身报告。

### 6.1 为什么需要这一节

两个运行时的目标 Agent 是 Codex，而非通用 Agent：

- 本仓库 `adapters/` 含 `codex/`（`SKILL.md` + `agents/openai.yaml`）、`claude/`、`cursor/`、以及通用 `agent/`；
- 我本次核对：`adapters/codex/SKILL.md` 与 `adapters/agent/listenkit-agent-instructions.md` 的**行为契约完全一致**（都是「Windows 用 `.ps1`、macOS/Linux/WSL 用 `.sh`」），区别只在**打包格式**（`openai.yaml` 是 Codex 的技能描述格式）。没有"Codex 专用逻辑"被我漏掉；
- 但"面向 Codex 的隐含前提"依然存在——它假设调用方是一个**能自由跑 shell 并捕获其子进程 stdout** 的 Agent。我（WorkBuddy）不满足这条。

### 6.2 双轴定义

- **轴一 · 操作系统兼容性（Windows vs macOS/Linux）**：路径分隔符、shell 解释器、平台专用入口（`.sh` vs `.ps1`）。本报告 §二已覆盖。
- **轴二 · Agent 框架兼容性（Codex 假设 vs WorkBuddy 实际）**：运行时对「调用方能自由执行 shell 并读 stdout」这一隐含前提是否成立。这与操作系统无关，却是本报告最容易被误读成"只是 Windows 问题"的地方。

### 6.3 对照表：Codex 能力假设 → WorkBuddy 实际限制

| # | Codex（原定目标）的能力假设 | WorkBuddy（实际调用方）的限制 | 对调用的影响 | 本报告位置 |
| --- | --- | --- | --- | --- |
| 1 | Agent 可自由执行 shell，包括从 bash 调用 PowerShell | 我的 Bash 工具**拒绝从 Bash 调用 PowerShell**（安全拦截） | 你们唯一官方 Windows 入口 `.ps1` 对我「能触发但读不到结果」 | 本报告 §2.3 |
| 2 | Agent 能捕获子进程 stdout | 我的 PowerShell 工具在本机返回**空 stdout**，需 `Out-File` 落盘再读 | `generate-markdown` 的执行结论（status/device/fallback）无法直接转述给用户 | 本报告 §2.3 |
| 3 | Agent 通过适配层（`adapters/codex` 等）接入 | 我无专属适配层，按 `LLM_INTEGRATION.md` 经 LingoTrace 间接调用本项目 | 接入可用，但契约文档未承认「任意遵循 AGENTS.md 的通用 Agent」路径 | 本报告 §一 |
| 4 | `resolve-listenkit`（上游 LingoTrace）返回的入口对当前 Agent 可用 | 它返回 `.sh`，而**本仓库契约禁止原生 Windows 走 `.sh`** | 跨运行时契约冲突落到了编排 Agent 头上（详见 LingoTrace 报告 §2.2 根因 2） | LingoTrace 报告 §2.2 |
| 5 | 解释器候选含常见位置 | 本机无 `py`、无 `python3.14`；仅在 `PATH` 有 `python`=3.14.4 时侥幸命中 | 健壮性依赖运气；建议把托管 venv 加入候选 | 本报告 §2.4 |

### 6.4 关键洞见：真正断点不在"Windows vs macOS"，而在"Codex 的 shell/stdout 能力 vs WorkBuddy 的沙箱约束"

即使你们把 `.sh` 通道修成平台感知（本报告 §四 方案 A），只要仍要求调用方**直接执行 `.ps1` 并读取其 stdout**，我在原生 Windows 上依旧受阻——因为第 1、2 行的限制与 Windows 无关，只与"我是 WorkBuddy"有关。

因此，让运行时对"任意 Agent 框架"而非仅 Codex 鲁棒的关键设计是：**所有面向 Agent 的入口都提供 `--report-json <path>` 落盘能力**（本报告 §四 方案 C）。读文件是普适能力，捕获子进程 stdout 不是。这是比"支持更多 shell"更治本的解法。

### 6.5 诚实缺口（未演示项）

本报告**真实执行了运行时**：`.\cli\listenkit.ps1 doctor` 完整跑通（CUDA 就绪），并用环境变量覆盖 macOS 默认路径后，经 `bash cli/transcribe-audio.sh` 完成了**一次真实 GPU 转写**（`device=cuda, compute_type=float16, model=small`）。但**没有演示一条由上游 LingoTrace 编排层直达本项目的端到端精听链路**——上游 `transcribe_listening.py:645` 硬编码 `/bin/bash`，在原生 Windows 上先于到达本项目就抛 `WinError 2`。

该 happy path 的"绿色演示"依赖上游先修复（LingoTrace 报告 §四 方案 A/B）。此缺口**不影响"本项目 Windows 通道健康"的结论**，但意味着"经 LingoTrace 全链路开箱即用"尚未被本 Agent 验证。我未在源码上打补丁去强行演示。

### 6.6 给维护者的补充建议（在 §四 之上）

若希望运行时对 Codex 之外的 Agent 也鲁棒：

1. 所有面向 Agent 的入口都提供 `--report-json` 落盘（不只转写内容，含本次执行的 `status` / `fallback` 诊断）；
2. 在 `LLM_INTEGRATION.md` 显式列出"支持的 Agent 接入方式"，承认「任意遵循 AGENTS.md 的通用 Agent」这一路径；
3. `resolve-listenkit` 等上游返回应**按调用方当前平台**给出可用入口，而非一律 `.sh`。
