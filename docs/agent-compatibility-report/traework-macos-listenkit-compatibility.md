# TraeWork Agent 在 macOS 上的 ListenKit 兼容性报告

**报告日期**: 2026-08-10
**Agent 框架**: TraeWork (TRAE SOLO CN 内置 AI Agent)
**操作系统**: macOS 27.0 (arm64 / Apple Silicon)
**审计范围**: 代码静态审计 + CLI 入口实测 + 运行时环境验证

---

## 一、我是谁

我是 **TraeWork Agent**，运行在 **macOS (arm64)** 操作系统上，是 TRAE SOLO CN 桌面应用内置的 AI Agent 框架。我的执行环境具有以下特征：

1. **沙箱化运行环境**: 我在 TRAE 应用提供的隔离沙箱中执行命令，而非用户的登录 shell。
2. **内置工具链优先**: PATH 中优先使用 TRAE 内置的工具（包括内置 Python 3.10、内置 ffmpeg 等），而非用户系统安装的版本。
3. **环境变量污染**: TraeWork 会设置 `PYTHONHOME` 和 `PYTHONPATH` 环境变量指向内置 Python 环境，这会干扰外部 Python 解释器的正常启动。
4. **输出捕获能力**: 我可以可靠捕获 stdout/stderr 输出（这一点比 WorkBuddy 等沙箱 Agent 好）。
5. **文件系统访问**: 我可以访问用户授予的工作目录（当前 Vault 目录），以及系统标准路径。

---

## 二、兼容性问题汇总

### P0 - 阻塞性问题：Python 版本与环境污染

| 项 | 详情 |
|---|---|
| **问题描述** | TraeWork 默认 Python 是内置的 **Python 3.10.20**，而 ListenKit 要求 **Python 3.14**（托管 venv 基于 cpython-314）。TraeWork 设置的 `PYTHONHOME` 和 `PYTHONPATH` 环境变量会干扰 ListenKit 托管 Python 运行时的启动。 |
| **复现路径** | 1. 在 TraeWork 中运行 `PYTHONPATH=... python3 -m listenkit_cli doctor`<br>2. 基础 CLI 帮助可运行（argparse 在 3.10 上兼容）<br>3. `doctor` 显示 `runtime_python` 指向托管 venv 但 `import_health=failed`<br>4. 尝试调用托管 Python 时受 `PYTHONHOME` 污染 |
| **影响范围** | **部分阻塞**。基础 CLI 入口可运行（`--help` 正常），但托管 ASR 运行时健康检查失败；核心转录功能需要 Python 3.14 托管环境。 |
| **实测证据** | `doctor` 输出显示：<br>`runtime_dir=/Users/jiezhengj/Library/Caches/ListenKit/venvs/cpython-314`<br>`runtime_python=.../cpython-314/bin/python`<br>`import_health=failed`<br>`runtime_error=ListenKit runtime metadata check failed` |

### P1 - 高优先级问题

| # | 问题 | 文件/位置 | 影响 |
|---|---|---|---|
| 1 | **Apple Speech helper `mktemp` Bug**：`tools/apple-speech-helper/run-apple-speech-helper.sh:74-76` 使用 `mktemp '/tmp/xxx.XXXXXX.json'`，macOS BSD `mktemp` 要求 `X` 必须在末尾才替换随机字符，`.json` 后缀在 X 之后导致创建字面固定文件名，第二次调用 `File exists` 崩溃 | `tools/apple-speech-helper/run-apple-speech-helper.sh:74-76` | `--engine apple` 第二次调用必崩，并发调用必然冲突 |
| 2 | **macOS/Linux 缺少 `cli/doctor.sh`**：Windows 有 `cli/doctor.ps1`，但 macOS/Linux 没有对应的 shell 包装脚本，用户只能通过 `python -m listenkit_cli doctor` 运行诊断 | `cli/`（缺失文件） | 文档 `README.md:71` 只列出了 `cli/doctor.ps1`，与实际入口不一致 |
| 3 | **`cli/generate-markdown.sh` 未透传设备参数**：bash 版高层入口缺少 `--device`、`--compute-type`、`--device-index` 三个 ASR 设备控制参数，而 Python 核心和 Windows `listenkit.ps1` 都支持 | `cli/generate-markdown.sh:340-351` | macOS/Linux 用户通过高层入口无法控制 MLX/CPU 设备选择 |
| 4 | **缺少 `AGENTS.md` 入口文件**：项目根目录没有 `AGENTS.md`，这是通用 Agent 框架（包括 TraeWork）自动发现项目指令的约定文件名 | 项目根目录（缺失） | TraeWork 等通用 Agent 无法自动发现 `LLM_INTEGRATION.md` 和适配器指令 |

### P2 - 中优先级问题

| # | 问题 | 文件/位置 | 影响 |
|---|---|---|---|
| 5 | **非登录 Shell/Agent 环境 PATH 缺少 Homebrew**：`process.py` 和 `import-audio.sh` 依赖 `shutil.which("ffmpeg")` 查找工具。实测 doctor 显示 ffmpeg 来自 Trae 内置路径而非 Homebrew，若 Trae 未打包 ffmpeg 则会误报缺失 | `listenkit_cli/process.py:12-13`, `cli/import-audio.sh:156-184` | 桌面启动的 Agent（TraeWork/Claude Code 桌面版）可能找不到 Homebrew 安装的 ffmpeg/yt-dlp |
| 6 | **Swift 编译目标硬编码 `macos26.0`**：`tools/apple-speech-helper/scripts/build-helper-app.sh:47` 硬编码部署目标，在旧版 Xcode/CLT 上编译失败 | `tools/apple-speech-helper/scripts/build-helper-app.sh:47` | 旧 macOS 版本/Xcode 用户无法编译 Apple Speech helper |
| 7 | **`--engine apple` 仅拦截 Windows，Linux 上无清晰报错**：只检查了 `platform_id() == "windows"`，未拦截 Linux | `listenkit_cli/transcription.py:100-111` | Linux 用户尝试 Apple 引擎会得到不友好的 zsh/open 错误 |
| 8 | **`install-agent-instructions` 不感知目标框架**：bash/Python 安装器始终安装通用版指令（`adapters/agent/listenkit-agent-instructions.md`），不会根据目标框架安装 Codex/Claude/Cursor 专用版 | `cli/install-agent-instructions.sh`, `listenkit_cli/agent_install.py` | Claude/Codex/Cursor 用户安装后得不到框架特定指令内容 |
| 9 | **Claude 适配器信息密度低于 Codex**：`adapters/claude/CLAUDE.md` 仅 27 行，而 `adapters/codex/SKILL.md` 有 64 行，缺少 workflow 步骤和逐条 CLI 示例 | `adapters/claude/CLAUDE.md` vs `adapters/codex/SKILL.md` | Claude Code 用户体验略糙 |
| 10 | **bash 版 `install-agent-instructions.sh` 用 `cp` 非原子写入**：Python 核心使用 tempfile+rename 原子写入，但 bash 版用简单 `cp`，并发/中断场景可能产生半写文件 | `cli/install-agent-instructions.sh:125` | 极端情况下文件损坏 |

### P3 - 低优先级问题

| # | 问题 | 文件/位置 |
|---|---|---|
| 11 | 跨平台错误信息并列 Windows `.ps1` 路径，macOS 用户看到无关路径 | `listenkit_cli/transcription.py:131-133` |
| 12 | `cli/export-audio-slices.py` 使用 `float \| None` 语法（Python 3.10+），但文档已声明需 3.10+ | `cli/export-audio-slices.py:51` |
| 13 | 无 `pyproject.toml`/`requires-python` 声明，以扁平 requirements.txt + PYTHONPATH 方式运行 | 项目根目录 |
| 14 | 缺少 TraeWork 专用适配器文件（参考已有 `adapters/codex/`、`adapters/claude/`、`adapters/cursor/`） | `adapters/`（缺失） |

---

## 三、macOS 兼容性（平台层面）

ListenKit 在 macOS 上的平台兼容性**整体优秀**，有专门的 Apple Silicon 优化：

1. **运行时路径**：默认使用 `~/Library/Caches/ListenKit/venvs/cpython-314/`，正确遵循 macOS Cache 目录规范，非 iCloud 路径。
2. **iCloud 防护**：`runtime.py:117-120` 和 `health.py:139-142` 正确拒绝 `Library/Mobile Documents` 路径。
3. **MLX/Metal 加速**：仅在 Apple Silicon (`arm64`/`aarch64`) 上自动准备，Rosetta x86_64 自动禁用。
4. **Intel Mac 支持**：使用 CTranslate2 Apple Accelerate CPU 后端。
5. **CUDA 拒绝**：macOS 上明确拒绝 CUDA（`runtime.py:190-191`）。
6. **平台脚本分离**：`.sh`（macOS/Linux/WSL）与 `.ps1`（Windows）分离清晰。

**macOS 特有的问题**：
- Apple Speech helper 的 `mktemp` Bug 是 P1 级阻塞问题，第二次调用必崩。
- Swift helper 编译目标硬编码 `macos26.0` 对旧系统不友好。
- 缺少 `cli/doctor.sh` 入口。
- 非登录 shell PATH 问题（Homebrew 在 `/opt/homebrew/bin`）。

---

## 四、Agent 兼容性（框架层面）

### 4.1 好的设计

1. **LLM_INTEGRATION.md 作为契约 source of truth**：完整定义了 Agent 集成协议，覆盖安装场景、公开入口、输出契约、Do-not-bypass 规则。
2. **适配器目录结构**：有通用 (`adapters/agent/`)、Codex (`adapters/codex/`)、Claude (`adapters/claude/`)、Cursor (`adapters/cursor/`) 四级适配器，可扩展。
3. **平台选择规则清晰**：`.sh` vs `.ps1` 选择规则在多处文档中一致，无漂移。
4. **JSON 输出配对**：`.md` + 同 stem `.json` 输出契约明确。
5. **Do-not-bypass 规则**：禁止 Agent 直接调用 yt-dlp/ffmpeg/低层 CLI，必须通过公开入口。
6. **`LISTENKIT_CLI_PYTHON` 环境变量**：Windows 兼容性报告中提到的设计，允许 Agent 指定 Python 路径，这是很好的逃生口。
7. **原子写入**：Python 核心的 `agent_install.py` 使用 tempfile+rename 原子写入。
8. **已有多份兼容性报告**：`docs/agent-compatibility-report/` 已有 7 份各 Agent × 各平台报告，说明项目重视 Agent 兼容性。

### 4.2 对 TraeWork Agent 的核心障碍

**主要问题**：

1. **Python 版本与环境污染**：
   - TraeWork 内置 Python 3.10 无法满足 ListenKit 3.14 的要求。
   - `PYTHONHOME` 环境变量会干扰 ListenKit 托管 venv 的 Python 启动，导致 `import_health=failed`。
   - 基础 CLI argparse 层在 3.10 上可运行（`--help` 正常），但核心转录功能需要托管 3.14 环境。

2. **ffmpeg 路径问题**：
   - 实测 `doctor` 显示 ffmpeg 来自 Trae 内置路径 `/Users/jiezhengj/Library/Application Support/TRAE SOLO CN/.../ffmpeg`，而非 Homebrew。
   - 这恰好"工作"了，但如果 Trae 未来版本移除 ffmpeg 或版本不兼容，会出问题。
   - Agent 应该有机制显式指定 ffmpeg/yt-dlp 路径或确保 Homebrew PATH 正确。

3. **无 AGENTS.md 自动发现入口**：
   - TraeWork 等通用 Agent 会查找项目根的 `AGENTS.md`，但 ListenKit 没有。
   - Agent 只能通过用户手动安装指令或偶然发现 `LLM_INTEGRATION.md`。

4. **缺少 TraeWork 专用适配器**：
   - 有 Codex、Claude、Cursor 适配器，但没有 TraeWork 适配器。
   - TraeWork 不读取 `CLAUDE.md`、Codex `SKILL.md` 或 Cursor Rule，需要通用指令或专用适配器。

5. **bash 脚本在 Agent 沙箱中的执行问题**：
   - TraeWork 可以执行 bash 脚本，但环境变量（PATH、PYTHONHOME）与用户登录 shell 不同。
   - `cli/generate-markdown.sh` 调用链中每个子脚本都依赖正确的 PATH，可能找不到 python3/ffmpeg。

---

## 五、我的需求

为了让 ListenKit 能在 TraeWork Agent (macOS) 上正常工作，我需要：

1. **托管 Python 运行时必须可启动**：ListenKit 调用自己的托管 venv Python（cpython-314）时，需要清理 `PYTHONHOME`/`PYTHONPATH` 环境变量，避免 TraeWork 环境污染。
2. **Apple Speech helper 必须修复**：`mktemp` 模板 Bug 需要修复，否则 `--engine apple` 不可用。
3. **需要 `cli/doctor.sh`**：macOS/Linux 应有与 Windows `doctor.ps1` 对应的 shell 包装脚本。
4. **需要 `AGENTS.md` 入口**：项目根应有 `AGENTS.md`，让 TraeWork 等通用 Agent 可自动发现项目指令。
5. **`generate-markdown.sh` 应透传设备参数**：bash 版高层入口应支持 `--device`、`--compute-type`、`--device-index` 参数。
6. **PATH/工具查找应更健壮**：显式检查 Homebrew 路径（`/opt/homebrew/bin`、`/usr/local/bin`），或允许通过环境变量指定 ffmpeg/yt-dlp 路径。
7. **需要 TraeWork 适配器**（可选但推荐）：在 `adapters/` 下增加 `trae/` 目录，提供 TraeWork 特定的操作说明。

---

## 六、建议方案

### 方案 A：短期修复（优先级 P0/P1）

1. **修复子进程 Python 环境变量污染**：
   - 在 `listenkit_cli/runtime.py` 调用托管 Python 时，显式从子进程环境中移除 `PYTHONHOME`、`PYTHONPATH`，或构造一个干净的 `env` 字典。
   - 确保 `cli/*.sh` 脚本在调用 Python 前也清理这些变量。

2. **修复 Apple Speech helper `mktemp` Bug**：
   - 将 `mktemp '/tmp/xxx.XXXXXX.json'` 改为 `mktemp '/tmp/xxx.XXXXXX'` 后再 `mv "$tmp" "$tmp.json"`，或使用 `mktemp -t` 方式。
   - 正确写法：`OUTPUT_JSON="$(mktemp -t listenkit-apple-speech-output).json"` 或先创建不带后缀再追加。

3. **添加 `cli/doctor.sh`**：
   - 创建与 `cli/check-runtime.sh` 类似的 shell 包装，设置正确的 PYTHONPATH 后调用 `python -m listenkit_cli doctor`。

4. **添加项目根 `AGENTS.md`**：
   - 创建简单的 `AGENTS.md`，指向 `LLM_INTEGRATION.md` 和 `adapters/agent/listenkit-agent-instructions.md`。
   - 包含平台选择规则和 Do-not-bypass 要点。

5. **修复 `cli/generate-markdown.sh` 参数透传**：
   - 在 usage 和参数解析中增加 `--device`、`--compute-type`、`--device-index`，并传递给 `transcribe-audio.sh` 和 Python 核心。

### 方案 B：中期改进（优先级 P2）

6. **改进工具查找逻辑，增加 Homebrew 路径兜底**：
   - 在 `process.py` 的 `which()` 封装中，显式追加 `/opt/homebrew/bin`（Apple Silicon）和 `/usr/local/bin`（Intel）到查找路径。
   - 增加 `LISTENKIT_FFMPEG_PATH`、`LISTENKIT_YTDLP_PATH` 环境变量支持。

7. **修复 Swift helper 编译目标**：
   - 从 `sw_vers -productVersion` 推导部署目标，或省略 `-target` 让编译器自动选择当前系统版本。

8. **Linux 平台拦截 `--engine apple`**：
   - 在 `transcription.py` 中增加 Linux 平台检查，抛出清晰的错误信息。

9. **改进 Agent 指令安装器的框架感知**：
   - `install-agent-instructions` 增加 `--framework {generic,codex,claude,cursor,trae}` 参数。
   - 自动检测目标目录特征（如是否有 `CLAUDE.md`、`.codex/` 等）选择默认适配器。

10. **bash 安装器改用原子写入**：
    - 将 `cp` 改为与 Python 核心一致的 tempfile + `mv` 原子替换模式。

11. **补充 TraeWork 适配器**（可选）：
    - 创建 `adapters/trae/AGENTS.md` 或 `adapters/trae/SKILL.md`，提供 TraeWork 特定的操作说明。
    - 提到 PYTHONHOME 污染问题和清理方式。

### 方案 C：长期建议（优先级 P3）

12. **增加 `--report-json <path>` 落盘能力**：
    - 参考 WorkBuddy 兼容性报告的建议，为无法可靠捕获 stdout 的沙箱 Agent 增加 JSON 报告落盘选项。
    - TraeWork 可以捕获 stdout，但这是一个提高普适性的好设计。

13. **增加 `pyproject.toml`**：
    - 声明项目元数据和 `requires-python = ">=3.14"`。
    - 将 `requirements-*.txt` 整合为 optional dependency groups。

14. **错误信息平台感知**：
    - 根据当前平台只显示对应平台的命令路径，避免 macOS 用户看到 Windows `.ps1` 路径。

---

## 七、实测验证记录

| 测试项 | 结果 | 备注 |
|---|---|---|
| CLI 帮助信息 (`python3 -m listenkit_cli --help`) | ✅ 通过 | Trae 内置 Python 3.10 可运行基础 argparse，9 个子命令正常列出 |
| `doctor` 命令（Trae Python 3.10） | ⚠️ 部分通过 | 平台检测正常（macos/arm64），Homebrew yt-dlp 找到，但 runtime import_health 失败 |
| ffmpeg 路径检测 | ⚠️ 来自 Trae 内置 | 检测到 Trae 内置 ffmpeg 而非 Homebrew（偶然可用，但不可靠） |
| MLX/Metal 检测 | ✅ 通过 | `apple_silicon=yes`, `gpu_backend=mlx-metal`, `cpu_backend=apple-accelerate` |
| 运行时路径 | ✅ 通过 | 正确使用 `~/Library/Caches/ListenKit/venvs/cpython-314/` |
| Python 模块导入（Trae 3.10） | ✅ 基础导入通过 | `import listenkit_cli` 无 immediate ImportError |
| `install-agent-instructions --print` | ✅ 通过 | 可正确打印通用 Agent 指令 |
| 核心转录功能 | ❌ 未测试 | 需要修复 Python 环境后才能测试端到端转录 |

---

## 八、总结

ListenKit 的**Agent 集成协议设计是所有被审计项目中最完善的**：有清晰的 `LLM_INTEGRATION.md` 契约 source of truth、多框架适配器目录、Do-not-bypass 规则、原子写入、平台脚本分离、已有 7 份兼容性报告。这些都非常棒。

**TraeWork Agent 上的主要问题**：
1. **P0**: TraeWork 的 `PYTHONHOME` 污染导致 ListenKit 托管 Python 3.14 运行时 `import_health=failed`。
2. **P1**: Apple Speech helper `mktemp` Bug（第二次调用必崩）、缺少 `cli/doctor.sh`、缺少项目根 `AGENTS.md`、`generate-markdown.sh` 未透传设备参数。

核心修复工作量不大：
1. 子进程调用时清理 `PYTHONHOME`/`PYTHONPATH`
2. 修复 `mktemp` 模板 Bug
3. 添加 `cli/doctor.sh` 和根 `AGENTS.md`
4. bash 版参数透传补全

这些修复完成后，TraeWork Agent (macOS) 可以完整使用 ListenKit 的所有听力转录功能，包括 MLX/Metal 加速和 Apple Speech 引擎。
