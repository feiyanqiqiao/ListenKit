# ListenKit Windows 兼容性加固与验收方案

- 日期：2026-08-10
- 实施分支：`codex/agent-compatibility-hardening`
- GitHub 权威基线：`03fb5e47cf7ccb92cc9efc2a3c7fb35e537ce164`
- 上一阶段交接：`windows-codex-handoff.md`
- 报告输入：同目录 5 个 Agent × macOS/Windows 共 10 份兼容性报告
- 本阶段目标：在不为每个 Agent 复制业务逻辑的前提下，完成 Windows 原生入口、受限宿主、UTF-8、工具发现、CUDA/fallback、执行报告和文档契约的实机闭环

## 1. 基线与证据原则

### 1.1 GitHub 与本地核对结果

1. GitHub 远端分支 `codex/agent-compatibility-hardening` 指向 `03fb5e4`，远端 `main` 指向 `6048fbb`。
2. 原本地分支指针停在 `c23f0a8`，但工作树包含大部分 macOS 改动，缺少远端已经提交的 `AGENTS.md`、`windows-codex-handoff.md` 和 5 份回应文档，并有少数提交前旧版本文件。
3. 本地 Git 有 3 个损坏的 Codex checkpoint ref，常规 `git fetch` 会报 `bad object`。为避免把损坏引用误判为 GitHub 状态，已通过独立临时克隆核验远端提交与文件内容。
4. 对齐前的本地状态已保存为 `stash@{0}: pre-windows-github-authoritative-sync-2026-08-10`；随后本地分支无损对齐到 `03fb5e4`。
5. 后续所有实现均以 `03fb5e4` 为父提交，不从旧本地内容或 `main` 重做。

### 1.2 证据分级

- A 级：本机 Windows 11、PowerShell 5.1/7、GTX 1660 SUPER 上的真实执行结果。
- B 级：Windows 自动化测试，包含真实子进程、临时 venv、中文/空格路径和字节级 UTF-8 检查。
- C 级：跨平台单元测试或静态审计；可证明控制流与契约，不能替代真实硬件/宿主验收。
- 报告中的陈述只有在 A/B 级证据或明确代码路径支持后才进入“已确认问题”；冲突结论不按多数票决定。

## 2. 当前 Windows 实机基线

### 2.1 环境

| 项目 | 实测值 |
|---|---|
| OS | Windows 11 `10.0.26220` / AMD64 |
| Windows PowerShell | 5.1.26100.9022 |
| PowerShell | 7.6.4 |
| CLI Python | 3.14.4，`%LOCALAPPDATA%\\Programs\\Python\\Python314\\python.exe` |
| 托管 ASR runtime | `%LOCALAPPDATA%\\ListenKit\\venvs\\cpython-314`，Python 3.14.4 |
| faster-whisper | 1.2.1 |
| GPU | NVIDIA GeForce GTX 1660 SUPER，compute capability 7.5，6144 MiB |
| NVIDIA driver | 581.80 |
| CUDA 库 | cuBLAS 12 / cuDNN 9 均可加载 |
| ffmpeg/ffprobe | WinGet Links |
| yt-dlp | 2026.07.04，WinGet Links |

### 2.2 已通过项

- `python -m compileall -q listenkit_cli cli tools tests`：通过。
- `python -m unittest discover -s tests -v`：146 tests，全部通过，76 个 POSIX/Bash 用例按 Windows 预期跳过。
- PowerShell 5.1 与 7 均通过：
  - `listenkit.ps1 --help`
  - `listenkit.ps1 doctor`
  - `generate-markdown.ps1 --help`
- 两个 PowerShell 宿主均报告同一托管 runtime、CUDA device 0、`float16` 与完整 CUDA 库状态。

### 2.3 已复现缺口

| ID | 证据 | 结论 |
|---|---|---|
| W1 | 注入无效 `PYTHONHOME/PYTHONPATH` 后，`listenkit.ps1 --help` 以 `Failed to import encodings module` 失败 | 分发器在解释器探针前没有隔离宿主 Python 环境；远端文档声称的隔离在 Windows 尚未成立 |
| W2 | 将 PATH 限制到 Windows PowerShell 目录后，健康托管 venv 已存在但 `listenkit.ps1 doctor` 报找不到 Python 3.10+ | CLI Python 发现没有托管 venv、winget Python 和 Program Files Python fallback |
| W3 | 直接 Python 的 `sys.stdout.encoding/sys.stderr.encoding` 为 `gbk`、`utf8_mode=0` | Antigravity 的编码担忧成立；直接 `python -m` 需要在入口层重配置 UTF-8，而不是要求每个 Agent 设置环境变量 |
| W4 | 受限 PATH 下直接 doctor 将 `yt-dlp/ffmpeg/nvidia-smi` 全报 missing，CUDA 核心探针却仍能发现设备 | 工具元数据和 driver 检测缺少 Windows 常见路径 fallback；会产生互相矛盾的诊断 |
| W5 | Git Bash 执行 `cli/listenkit.sh --help` 返回 0 并显示完整帮助 | `.sh` 在原生 Windows 上仍会造成“看起来支持”的误导，与远端公共契约不一致 |

## 3. 对 10 份报告的裁决

### 3.1 接受并实施

1. Windows PowerShell 分发器增强 Python 发现，并真实执行版本探针，排除 Store alias/stub。
2. Windows 分发器在探针前及实际运行期间移除 `PYTHONHOME/PYTHONPATH`，结束后恢复调用方环境。
3. 直接 Python 模块入口主动将 stdout/stderr 重配置为 UTF-8。
4. `nvidia-smi.exe`、WinGet Links 下 `ffmpeg.exe`/`ffprobe.exe`/`yt-dlp.exe` 增加受限 PATH fallback。
5. Git Bash/MSYS2/Cygwin 的 `.sh` 入口快速失败，明确指向 `python -m listenkit_cli` 或 `listenkit.ps1`。
6. 保留并完整验证 `--report-json` 成功、错误、路径冲突及原子写入契约。
7. 用真实 CUDA 推理和真实 CPU fallback 验证 `auto`/显式 `cuda` 语义。

### 3.2 已由 macOS 阶段解决，只做 Windows 回归

- Python 子进程移除宿主 `PYTHONHOME/PYTHONPATH`。
- `generate-markdown`、`transcribe-audio` 的 `--report-json`。
- doctor 四项版本/schema 握手。
- 根 `AGENTS.md` 与通用 Agent 契约。
- Apple backend 仅 macOS、BSD `mktemp` 并发安全、非交互 shell、POSIX 入口补齐。

### 3.3 不在 ListenKit 侧实施

1. 不修改 LingoTrace 的 `/bin/bash`、`resolve-listenkit` 或 `mlx` 参数问题；这些属于上游仓库。
2. 不为 WorkBuddy、TraeWork、QwenWork、Antigravity 分别复制业务 adapter。它们共同使用根 `AGENTS.md`、`LLM_INTEGRATION.md`、通用 adapter 和 execution report。
3. 不为“某 Agent 无法读取 PowerShell stdout”改写 ASR 流程；`--report-json` 是项目侧的兼容层。
4. 不降低托管 ASR runtime 的 Python 3.14/`cpython-314` 要求。CLI 宿主的 Python 3.10+ 与 ASR runtime 3.14 是两层要求，错误信息必须分别说明。
5. 不把 Git Bash `.sh` 宣布为长期支持面。虽然报告证明注入正确 venv 路径后部分脚本可以运行，但完整支持还需维护 MSYS 路径转换、bootstrap、工具发现、CI 和全部入口；收益小于重复支持成本。
6. 不修改 macOS 26 deployment target；SpeechAnalyzer API 下限不是本阶段问题。

## 4. 实施设计

### 4.1 PowerShell 分发器

目标文件：`cli/listenkit.ps1`。

候选顺序：

1. `LISTENKIT_CLI_PYTHON` 显式覆盖；无效时明确失败，不静默改用别的解释器。
2. `LISTENKIT_FASTER_WHISPER_VENV_DIR\\Scripts\\python.exe`，否则默认 `%LOCALAPPDATA%\\ListenKit\\venvs\\cpython-314\\Scripts\\python.exe`。
3. `%LOCALAPPDATA%\\Programs\\Python\\Python314\\python.exe`。
4. `%ProgramFiles%\\Python314\\python.exe`。
5. `py -3.14`、`python3.14`、`python`。

每个候选必须实际执行 `sys.version_info >= (3, 10)` 探针；文件存在或 `Get-Command` 命中不等于可执行。Store alias、0 字节 stub、启动异常和错误退出均跳过。

环境策略：

- 在候选探针之前保存并移除 `PYTHONHOME/PYTHONPATH`。
- 实际 CLI 只设置 `PYTHONPATH=<repo-root>`，不把宿主 `PYTHONPATH` 拼回去。
- 设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。
- PowerShell 输出编码设置为无 BOM UTF-8，并在 `finally` 中恢复。
- 保存并恢复 `LISTENKIT_POWERSHELL_VERSION` 及所有原环境变量。
- 失败文案同时说明：CLI host 需要 Python 3.10+；新建/修复 ASR runtime 需要 Python 3.14。

### 4.2 Python bootstrap 发现

目标文件：`listenkit_cli/runtime.py`。

- Windows bootstrap 候选加入 `%LOCALAPPDATA%\\Programs\\Python\\Python314\\python.exe` 和 `%ProgramFiles%\\Python314\\python.exe`。
- 继续严格要求实际探针为 Python 3.14。
- 捕获不可执行 alias/stub 的 `OSError`，继续检查后续候选。
- 不把待创建的目标 venv 当作 bootstrap；健康托管 venv由 `initialize_runtime` 直接复用，缺失/损坏目标不能自举自身。

### 4.3 Windows 工具发现

目标文件：`listenkit_cli/process.py`、`listenkit_cli/cuda_runtime.py`、`listenkit_cli/asr_device.py`。

- `find_command` 先遵循 PATH。
- Windows fallback：
  - `%SystemRoot%\\System32\\nvidia-smi.exe`
  - `%LOCALAPPDATA%\\Microsoft\\WinGet\\Links\\ffmpeg.exe`
  - 同目录 `ffprobe.exe`、`yt-dlp.exe`
- `nvidia_driver_available` 与 NVIDIA 元数据查询统一调用 `find_command(..., environment=env)`，避免一个字段 fallback、另一个字段仍只看宿主 PATH。
- 只接受真实文件；不扫描整个磁盘，不调用注册表，不修改 PATH 持久状态。

### 4.4 Python UTF-8 模块入口

目标文件：`listenkit_cli/__main__.py`。

- 在调用 `main()` 前，对支持 `reconfigure` 的 stdout/stderr 设置 `encoding='utf-8'`、`errors='replace'`。
- 该修复覆盖直接 `python -m listenkit_cli`；PowerShell 分发器仍设置环境变量，形成双层保证。
- 用字节捕获严格 UTF-8 解码测试含中文、日文、emoji 的错误路径，防止 GBK 或反斜杠转义冒充成功。

### 4.5 Git Bash/MSYS/Cygwin 行为

目标文件：`cli/_common.sh` 及 POSIX 入口测试。

- `uname -s` 为 `MINGW*|MSYS*|CYGWIN*` 时返回退出码 64。
- stderr 同时给出：
  - `python -m listenkit_cli <command>`
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\\cli\\listenkit.ps1 <command>`
- 守卫位于共享 `_common.sh`，确保 `--help`、doctor、init、generate、transcribe 等入口行为一致。
- WSL 的 `uname` 为 Linux，不受该拒绝逻辑影响。

### 4.6 文档与 Agent 契约

目标文件：`LLM_INTEGRATION.md`、`README.md`、`README.zh-CN.md`、`docs/install.md`、通用/Codex/Claude/Cursor adapter。

- 统一描述 Git Bash/MSYS/Cygwin 为原生 Windows，使用 Python/PowerShell，而非 `.sh`。
- 文档化 `LISTENKIT_CLI_PYTHON` 与自动发现顺序。
- 明确 CLI host 3.10+ 与 ASR runtime/bootstrap 3.14 的区别。
- 对受限执行策略给出 `-NoProfile -ExecutionPolicy Bypass -File .\\cli\\listenkit.ps1 ...`。
- 推荐 Agent 用 `--report-json` 读取结果，不要求其修改 ListenKit 或捕获 stdout。

## 5. 自动化测试计划

### 5.1 Windows 分发器

在 `tests/test_windows_runtime.py` 增加：

1. PowerShell 5.1/7 在无效 `PYTHONHOME/PYTHONPATH` 下仍能运行 `--help`。
2. 受限 PATH 下，通过临时 managed venv 自动发现 CLI Python。
3. `LISTENKIT_CLI_PYTHON` 支持含空格路径且优先级最高。
4. 含中文/日文/emoji 的错误输出可按 UTF-8 严格解码。
5. restricted PATH doctor 的 fallback 查找由独立单元测试覆盖，避免 CI 依赖本机实际 WinGet/GPU。

### 5.2 Python 核心

- Windows Python 3.14 常见安装位置进入 bootstrap 候选。
- 不可执行候选不会终止后续发现。
- Windows `find_command` fallback 命中临时构造的 System32/WinGet Links 文件。
- NVIDIA driver 与元数据查询使用传入 environment。

### 5.3 Git Bash 政策

- Windows 实机用 Git for Windows 的 bash 验证 `listenkit.sh --help` 退出 64。
- 输出必须包含 Python 与 PowerShell 两条替代入口。
- POSIX CI 保持现有 macOS/Linux 行为。

### 5.4 execution report

- 成功报告：`status=ok`、Markdown/transcript 路径、实际 engine/device/compute type。
- 缺文件：非 0、`status=error`、结构化 error。
- report 与 Markdown/transcript 同路径：在任何产物写入前拒绝；既有文件哈希不变。
- fallback：报告透传 transcript 的 `fallback_from/fallback_reason`。

## 6. Windows 实机 E2E 验收

### 6.1 正常 CUDA

1. 用 Windows SAPI 生成短英语 WAV，路径包含中文与空格。
2. 通过 PowerShell 公共入口运行 `generate-markdown --engine auto --device auto --report-json`。
3. 验证 `.md`、同 stem `.json`、execution `.json` 全部存在。
4. transcript/report 必须为 `faster-whisper`、`cuda`、本机支持精度（预期 `float16`）。
5. 核对文本非空、segments 存在、`timing_complete=true`。

### 6.2 制造 CUDA 失败后的真实 CPU fallback

1. 测试 helper 对 CUDA 尝试返回明确 CUDA 失败，对 CPU 分支委托真实 faster-whisper helper。
2. `device=auto` 必须依次尝试 CUDA 精度并最终在 CPU INT8 完成真实转写。
3. transcript 与 execution report 必须记录 `device=cpu`、`compute_type=int8`、`fallback_from`、`fallback_reason`。
4. 同一故障下显式 `device=cuda` 必须非 0，写 error report，且不得静默 CPU fallback。

### 6.3 宿主与路径矩阵

- Windows PowerShell 5.1。
- PowerShell 7。
- `-ExecutionPolicy Bypass`。
- 受限 PATH。
- 污染 `PYTHONHOME/PYTHONPATH`。
- 直接 `python -m listenkit_cli`。
- 中文、日文、emoji 与空格路径。
- stdout/stderr 捕获及重定向文件按 UTF-8 解码。

## 7. 完成标准

只有以下条件全部满足，Windows 阶段才标记完成：

1. 所有新旧单元测试通过；Windows skip 仅为 POSIX/Bash 专属用例。
2. `compileall` 通过。
3. PowerShell 5.1/7 公共入口及受限执行策略通过。
4. 受限 PATH 与污染 Python 环境通过。
5. Git Bash `.sh` 快速失败且替代指引可执行。
6. 中文/空格路径真实 CUDA E2E 通过。
7. 制造 CUDA 失败后的真实 CPU INT8 fallback 通过；显式 CUDA 不降级。
8. execution report 成功、错误、冲突、fallback 全部验证。
9. `windows-codex-handoff.md` 增补确切结果、命令、版本、设备与仍未验证边界。
10. 5 份 Agent 回应文档分别补充 Windows 结论，明确接受、驳回或转交上游的每项建议。
11. 最终 `git diff --check`、工作树审查与 GitHub 基线差异清单通过。

## 8. 风险与回滚

- PowerShell 兼容性：不得使用 PowerShell 7 专属语法；所有实现必须在 5.1 运行。
- 编码：UTF-8 设置必须限定在当前脚本进程并在 `finally` 恢复，避免污染调用方会话。
- Python 发现：显式 override 不得被静默忽略；自动候选必须逐个真实探针。
- CUDA：不得因自动 fallback 改变显式 `device=cuda` 的严格语义。
- Git：对齐前状态保留于 `stash@{0}`；实现提交以 `03fb5e4` 为父提交。损坏 checkpoint refs 不属于产品源代码，单独记录处理。
