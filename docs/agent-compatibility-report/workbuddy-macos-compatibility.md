# ListenKit × WorkBuddy（macOS）兼容性报告

> 文件名体现：WorkBuddy（Agent 框架）+ macOS（操作系统）
> 生成日期：2026-08-10
> 报告人：WorkBuddy（见下方"我是谁"）

---

## 一、我是谁（身份声明）

- **Agent 框架**：WorkBuddy（腾讯出品的 AI 助手 / Agent 框架）。本仓库原本针对 **Codex**（OpenAI 的 Agent 框架）开发，本报告检查其对"macOS + WorkBuddy"的兼容性。
- **操作系统**：macOS 27.0（arm64，Apple Silicon），Aqua GUI 会话。
- **执行环境**：由 WorkBuddy Agent 沙箱执行命令；宿主进程 `com.workbuddy.workbuddy`。
- **本机 Python**：3.13.12（WorkBuddy 托管）/ 3.14.4（系统）；运行时检查用 `python3.14`（系统 3.14.6）。
- **双 ASR 约定**：`SKILL.md` 默认每个听力笔记用双 ASR 校验（主引擎 mlx-whisper 或 faster-whisper，次引擎 apple），除非显式 `--single-asr`。

本报告的检查方法：**既审计代码，也实际完整跑过运行时**（check-runtime、doctor、export-audio-slices、单元测试、端到端 `--engine` 实测）。

---

## 二、macOS 兼容性实测（实际跑过）

| 检查项 | 命令 | 结果 |
|---|---|---|
| 运行时自检 | `cli/check-runtime.sh` | ✅ OK（python 3.14.6，faster_whisper 1.2.1，import_health=ok） |
| 诊断 | `listenkit_cli/doctor.py`（核心模块直接跑） | ✅ OK，完整输出 macOS/arm64/MLX/Metal 信息 |
| 精听切片 | `cli/export-audio-slices.py` | ✅ 成功导出切片 S01/S02 为 m4a |
| 单元测试（10 个快速模块） | `python -m unittest test_cross_platform_core test_render_listening_note test_runtime_contract test_install_agent_instructions test_import_audio test_export_audio_slices test_extract_subtitles test_generate_markdown test_init_faster_whisper test_windows_runtime` | ✅ 115 测试全过；6 个 Windows-only 跳过（macOS 预期） |
| `transcribe_audio` 模块 | `python -m unittest test_transcribe_audio` | ⚠️ 前 13 个测试通过；第 14 个 `test_missing_faster_whisper_environment_without_auto_init_returns_clear_error` 在 tty 环境下挂起（>180s 被强杀）。根因为 `cli/transcribe-audio.sh` 的 `[[ -t 0 ]]` + `read -r answer` 死锁，见问题 F6。 |
| `--engine mlx`（generate-markdown.sh） | 实测 | ✅ 可用（LingoTrace 端到端已验证 mlx-whisper + Metal） |
| `--engine apple` | `bash cli/generate-markdown.sh --engine apple` | ❌ 失败，Apple Speech helper 无法启动，见问题 F1 |

**目录实证**（`cli/` 内容）：`doctor` 与统一分发器 `listenkit` **仅有 `.ps1`**（无 `.sh`）；其余 7 个命令（check-runtime / generate-markdown / extract-subtitles / import-audio / init-faster-whisper / install-agent-instructions / transcribe-audio）均为 `.sh` + `.ps1` 双全。说明 doctor/listenkit 缺失 `.sh` 是遗漏而非设计。

---

## 三、Agent 框架兼容性（相对 Codex）问题与需求

### 问题 F1（P0 — Apple Speech helper 无法启动，macOS 实测）
- `tools/apple-speech-helper/run-apple-speech-helper.sh:85` 通过
  `/usr/bin/open -W -n "${APP_DIR}" --args … --output-path "${OUTPUT_JSON}"`
  启动 `ListenKitAppleSpeechHelper.app`。
- 实测：`open` 返回
  `Unable to block on application (GetProcessPID() returned 18446744073709551016)`（procNotFound）；
  helper 进程根本未出现（`pgrep` = 0），6 秒内无任何 JSON 产出。
- `codesign --verify` 通过，但 `spctl -a` 显示 **rejected**（adhoc 未签名）；`LSMinimumSystemVersion=26.0`，本机 27.0 满足条件。
- **根因定性**：adhoc 签名的 app 在 LaunchServices 中启动即失败（procNotFound），并非 mktemp 模板缺陷，也非 Agent 沙箱限制（沙箱外重跑同样失败；Calculator 能正常 `open` 启动，排除 GUI 会话问题）。
- **重要区分（与既有报告不同根因）**：既有报告中描述的"`mktemp` 第二次调用崩溃"是**另一个独立 bug**（见 F2）。本 Agent 实测的是"**首次调用即完全无法启动**"，症状与根因均不同，二者需分别修复。
- **影响**：`SKILL.md` 默认双 ASR 的次引擎 apple 在 macOS 上恒为 `secondary_unavailable`，双 ASR 保障失效。

**需求**：macOS 上 `--engine apple` 必须能真正启动（修复 adhoc 签名 / 隔离属性 / 启动方式）。

### 问题 F2（mktemp BSD 模板缺陷，独立 bug）
- `run-apple-speech-helper.sh:74-76`：
  `mktemp '/tmp/listenkit-apple-speech-output.XXXXXX.json'`（及两个 `.log` 同类）
- 在 macOS（BSD `mktemp`）上：首次创建字面文件 `/tmp/listenkit-apple-speech-output.XXXXXX.json`；第二次调用 `mkstemp failed: File exists`。
- 已独立复现确认。
- **影响**：即使 F1 修复，此缺陷仍会在第二次调用崩溃。与 F1 是两个独立问题。

**需求**：mktemp 改用标准 BSD 用法 `mktemp -t lh.XXXXXX.json` 或 `mktemp "${TMPDIR:-/tmp}/lh.XXXXXX.json"`。

### 问题 F3（POSIX 入口缺失 — doctor / listenkit 仅 `.ps1`）
- `cli/doctor.sh` 与 `cli/listenkit.sh` 缺失，仅有 `doctor.ps1` / `listenkit.ps1`。
- macOS / Linux 无法用 `cli/doctor` 或 `cli/listenkit` 统一入口；只能用 `listenkit_cli/doctor.py` 核心模块或各子命令 `.sh`。
- 其余命令均 `.sh`+`.ps1` 双全，故这是遗漏。

**需求**：补齐 `cli/doctor.sh`（调用 `listenkit_cli/doctor.py`）与 `cli/listenkit.sh`（统一分发器，类似 `listenkit.ps1`），与 Windows 对齐。

### 问题 F4（`--engine` 契约不对称）
- ListenKit `.sh` 接受 `auto|faster-whisper|mlx|apple`；LingoTrace 仅接受 `auto|apple|faster-whisper`（缺 `mlx`）。
- 实测：LingoTrace 层传 `mlx` 被 argparse 拒绝；ListenKit 侧实际支持 `mlx`。

**需求**：与 LingoTrace 对齐（都含 `mlx`），或明确由 ListenKit 校验、LingoTrace 透传。

### 问题 F5（无根级 AGENTS.md）
- 仓库根无 `AGENTS.md`，仅有 `adapters/{codex,claude,cursor,agent}/`。
- 本 Agent（WorkBuddy）按 AGENTS.md 约定寻找项目入口；缺失根级 AGENTS.md，意味着 WorkBuddy 无标准项目说明可读取（虽有 `adapters/agent/listenkit-agent-instructions.md`）。

**需求**：新增根级 `AGENTS.md`，指向 `adapters/agent/listenkit-agent-instructions.md` 作为 WorkBuddy / 通用 Agent 入口。

### 问题 F6（Agent 调用死锁风险 — 交互式 read）
- `cli/transcribe-audio.sh:268-287`：当 faster-whisper 未初始化且非 auto-init 时，若 stdin 是 tty（`[[ -t 0 ]]`），执行 `read -r answer` 等待用户输入。
- **实测复现**：unittest 中 `test_missing_faster_whisper_environment_without_auto_init_returns_clear_error` 挂起（>180s）；用 `</dev/null` 重定向 stdin 后，**退出 1 干净**（输出预期的 "faster-whisper is not initialized" 等）。
- **根因**：自动化 Agent 调用脚本时若不重定向 stdin，stdin 继承控制终端（tty），脚本便阻塞在 `read`。这是 Agent 框架兼容性关键风险——可被轻易触发导致死锁。
- 本 Agent 在端到端测试中使用 `--engine mlx`（绕过 faster-whisper 缺失分支），故未触发；但默认 auto 引擎且无 faster-whisper 时必触发。

**需求**：`transcribe-audio.sh` 在非真正交互时必须自动降级为错误退出，不要依赖 `[[ -t 0 ]]` 判断是否交互；或文档强制要求所有调用方重定向 stdin（`</dev/null` 或 `stdin=subprocess.DEVNULL`）。

---

## 四、建议方案（按优先级）

1. **F1（P0）**：对 `ListenKitAppleSpeechHelper.app` 用开发者证书签名，或移除隔离属性 `xattr -dr com.apple.quarantine …` 并确保 `LSMinimumSystemVersion` 匹配；若 ad-hoc 仍被拒，改用非 `.app` 方式调用 Speech 框架（直接 Swift CLI 而非 `.app`）。启动侧可改用 `open` 不带 `-W`（非阻塞）+ 轮询输出文件，避免 `open -W` 在启动失败时长时间阻塞。
2. **F2**：`mktemp '/tmp/...XXXXXX.json'` → `mktemp -t lh.XXXXXX.json`（或 `mktemp "${TMPDIR:-/tmp}/lh.XXXXXX.json"`）。
3. **F3**：补 `cli/doctor.sh` 与 `cli/listenkit.sh`，与 Windows 的 `.ps1` 对齐。
4. **F4**：LingoTrace 增加 `mlx`；或 ListenKit 文档明确契约、LingoTrace 透传。
5. **F5**：新增根级 `AGENTS.md`，指向 `adapters/agent/listenkit-agent-instructions.md`。
6. **F6**：`transcribe-audio.sh` 改为——当 `auto_init=false` 且 `LISTENKIT_AUTO_INIT` 未设置时，直接非交互错误退出（不 `read`）；`read` 仅在显式 `--interactive` 标志下执行。双管齐下：脚本默认非交互失败 + 文档要求调用方重定向 stdin。

---

## 五、与 LingoTrace 报告的关系

本报告中"`--engine mlx` 契约不对称""Apple helper 启动失败导致双 ASR 降级"等问题，在 LingoTrace 侧的表现与修复协同见同目录下的 `workbuddy-macos-compatibility.md`（LingoTrace 报告）。两份报告应合并阅读。
