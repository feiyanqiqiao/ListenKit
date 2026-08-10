# ListenKit macOS Agent 兼容性加固实施方案

- 日期：2026-08-10
- 实施分支：`codex/agent-compatibility-hardening`
- 基线提交：`c23f0a8e828ac176e14abd20aa627a62bdd8e588`
- 范围：ListenKit 仓库自身的共享兼容层与 macOS 行为
- 后续范围：Windows 原生实机验证与 Windows 专属补强，见 `windows-codex-handoff.md`

## 1. 目标与原则

本轮不是逐份照抄十份兼容性报告，而是把报告当作待验证的问题线索。每项建议必须经过源码核对、自动化测试或当前 macOS 实机复现后，才能进入实现范围。

实现遵循以下原则：

1. ListenKit 提供稳定、通用的 Agent 接入面，避免要求 Antigravity、Claude Code、TraeWork、WorkBuddy、QwenWork 各自修改 ListenKit 源码。
2. 平台差异收敛在薄入口和平台探针中；转写、输出、错误和执行报告契约由共享 Python 核心负责。
3. 自动化入口默认非交互，不能因为继承 TTY 而等待人工输入。
4. 不把 Agent 沙箱限制、LingoTrace 上游缺陷或未经复现的推测改造成 ListenKit 的复杂兼容代码。
5. 保持现有 `generate-markdown.sh` 与 `.ps1` 入口兼容，同时增加对 Agent 更稳定的统一分发入口。

## 2. 基线证据

### 2.1 自动化基线

在未修改源码的基线提交上执行：

```text
python3 -m unittest discover -s tests -v
Ran 131 tests in 40.217s
OK (skipped=6)
```

6 个跳过项均为 Windows 原生 PowerShell 测试，符合 macOS 基线预期。

### 2.2 macOS 与运行时基线

当前设备为 macOS 27.0、arm64，系统 Python 为 3.14.4，ListenKit 托管运行时为 Python 3.14.6 / faster-whisper 1.2.1。

同一 `doctor` 命令得到两种结果：

- Codex 沙箱内：MLX 报 `No Metal device available`；
- 沙箱外：`mlx_runtime=ready`、`mlx_metal=ready`、`mlx_default_device=Device(gpu, 0)`。

因此，Metal 在当前 Codex 沙箱内不可见是宿主执行隔离，不是 ListenKit 的 macOS 缺陷。涉及真实 Metal 的验收必须在沙箱外执行。

### 2.3 Apple Speech 基线

使用 macOS `say` 生成本地 AIFF 后，沙箱外实际运行 `run-apple-speech-helper.sh`：

- helper app 可构建；
- `codesign --verify --deep --strict` 通过；
- `/usr/bin/open -W -n` 可启动 helper；
- 返回 `schema_version=1`、`engine=apple`、带时间段的真实 JSON；
- 退出码为 0。

所以 WorkBuddy 报告中“ad-hoc 签名导致首次调用恒失败”的根因判断在本机未被证实。本轮不得以该判断为依据改开发者签名、移除隔离属性或改写为 Swift CLI。

## 3. 报告结论核验矩阵

| 问题 | 核验结论 | 本轮处理 |
| --- | --- | --- |
| BSD `mktemp` 模板的 `X` 后仍有 `.json/.log` | 已实测复现；生成字面固定名 | 修复为尾部 `XXXXXX`，消除并发和异常残留冲突 |
| Apple helper 因 ad-hoc 签名无法启动 | 当前实机未复现，真实转写成功 | 不改签名架构；保留验证记录 |
| Swift target `macos26.0` 应按当前系统动态变化 | 建议不正确；SpeechAnalyzer 本身要求 macOS 26+ | 保留最低部署目标 26.0 |
| `--engine apple` 在 Linux 未被前置拒绝 | 源码已证实，只拒绝 Windows | 改为仅允许 macOS并增加测试 |
| `.sh` 会继承 Agent 的 `PYTHONHOME/PYTHONPATH` | 已用损坏环境实测复现 | 为所有 POSIX 壳层统一清理 Python 污染变量 |
| 非登录 shell 找不到 Homebrew 工具 | Python 核心已有兜底；`.sh` 高层入口已实测失败 | POSIX 公共层补 `/opt/homebrew/bin`、`/usr/local/bin` 兜底 |
| 缺少 `cli/listenkit.sh` 与 `cli/doctor.sh` | 已确认 | 新增与 PowerShell 对称的 POSIX 分发入口 |
| `generate-markdown.sh` 未透传设备参数 | 已确认 | 补 `--device`、`--compute-type`、`--device-index` |
| `transcribe-audio.sh` 在继承 TTY 时等待输入 | 已在 PTY 中复现 | 默认非交互失败；只有显式参数才允许询问 |
| 根目录缺少 `AGENTS.md` | 已确认 | 新增通用发现入口，指向唯一集成契约 |
| shell 指令安装器使用非原子 `cp` | 已确认 | 改用同目录临时文件加原子 `mv` |
| `python -m listenkit_cli` 未被承认为程序化入口 | 两端实测可用，且避开特定 shell 限制 | 文档化为跨平台程序化入口；保留平台包装器 |
| Agent 不能可靠读取 PowerShell stdout | 属 Agent 能力差异，但文件读取更普适 | 共享 Python CLI 增加 `--report-json` 执行报告 |
| 缺少版本化下游握手 | `__version__` 存在但 doctor 未暴露 | doctor 增加版本与能力/转写 schema 版本 |
| 为每个 Agent 新增专用 adapter | 没有功能必要，且会制造漂移 | 不新增五套逻辑；以根 `AGENTS.md` 和通用 adapter 解决 |
| LingoTrace 不接受 `mlx` 或硬编码 `/bin/bash` | 属另一个仓库 | 不在 ListenKit 绕行；回应文档明确上游责任 |
| Python 3.14 安装门槛 | 已在 `docs/install.md` 明确 | 改进诊断/入口提示，不降低已验证 ABI 要求 |
| `.DS_Store`、`sync-conflict` 文件 | 均被现有通用规则部分忽略，但同步冲突名可更明确 | 增加 `*.sync-conflict-*` 忽略规则；不操作 `.git` 内部残留 |

## 4. 设计方案

### 4.1 统一 POSIX 兼容层

新增 `cli/_common.sh`，集中提供：

- 清理 `PYTHONHOME`、`PYTHONPATH`；
- 设置 UTF-8 Python I/O；
- 在 macOS 非登录 shell 中补充标准 Homebrew 前缀；
- 从 `LISTENKIT_CLI_PYTHON`、`python3.14`、`python3`、`python` 中选择可运行 CLI 的 Python 3.10+；
- 保持 Bash 3.2 兼容，不使用 Bash 4 专属语法。

所有现有 `.sh` 入口加载该兼容层。这样解决的是宿主环境污染，而不是给每个 Agent 增加私有分支。

### 4.2 对称统一入口

新增：

```text
cli/listenkit.sh <subcommand> [arguments]
cli/doctor.sh
```

推荐关系：

- 自动化/Agent：`python -m listenkit_cli ...`，或不便管理 `PYTHONPATH` 时使用 `cli/listenkit.sh ...` / `cli/listenkit.ps1 ...`；
- 人工快捷使用：继续支持 `cli/generate-markdown.sh` / `.ps1`；
- 下层脚本仍只用于维护和调试。

### 4.3 非交互契约

`transcribe-audio.sh` 在缺失运行时时默认立即返回清晰错误。若人工确实希望在终端确认安装，必须显式传 `--interactive-init`。Agent 不再需要自行重定向 stdin 才能避免死锁。

### 4.4 执行报告

为 Python CLI 的 `generate-markdown` 和 `transcribe-audio` 增加：

```text
--report-json <path>
```

报告采用原子写入，包含：

- `schema_version`；
- `command` 与 `status`；
- UTC 开始/结束时间和耗时；
- Markdown、转写 JSON 等输出路径；
- 实际 engine/device/compute type/fallback 元数据；
- 失败时的错误类型和消息。

执行报告与同 stem 的转写 JSON 是不同契约：前者描述本次运行，后者描述转写内容。实现必须拒绝将报告路径设置为 Markdown 或转写 JSON 路径，避免覆盖产物。

### 4.5 Agent 发现与文档

新增根 `AGENTS.md`，内容只引用 `LLM_INTEGRATION.md` 和通用 adapter，不复制五套业务逻辑。同步更新 README、中文 README、安装文档、LLM 契约和通用 adapter，明确：

- 跨平台程序化入口；
- 平台包装器；
- 自动化默认非交互；
- `--report-json`；
- 首次初始化和模型下载需要网络且可能耗时；
- 物理 GPU、Speech 权限和 Windows PowerShell 必须分别实机验收。

## 5. 实施步骤

1. 添加执行报告模块、CLI 参数和单元测试。
2. 添加 POSIX 公共兼容层、`listenkit.sh`、`doctor.sh`。
3. 接入所有现有 `.sh`，修复环境污染和 Homebrew PATH。
4. 修复 `generate-markdown.sh` 参数透传和 `transcribe-audio.sh` 交互策略。
5. 修复 Apple helper 临时文件与非 macOS 拦截。
6. 增加版本/能力 schema 诊断字段及同步冲突忽略规则。
7. 更新公共契约与入口文档。
8. 执行自动化、壳层、真实 MLX 和真实 Apple Speech 验收。
9. 形成 Windows 交接和五个 Agent 回应文档。

## 6. 测试与验收

### 6.1 自动化验收

- `python3 -m compileall -q listenkit_cli cli tools`
- `python3 -m unittest discover -s tests -v`
- 新增的执行报告成功/失败/路径冲突测试；
- POSIX 入口在污染的 `PYTHONHOME/PYTHONPATH` 下仍可运行；
- 非登录 PATH 能发现 Homebrew 的 ffmpeg/yt-dlp；
- 设备参数从 `generate-markdown.sh` 完整透传；
- 缺运行时时默认不在 TTY 中等待；
- Apple 临时文件并发不重名。

### 6.2 macOS 实机验收

- 沙箱外 `doctor` 报 MLX/Metal ready；
- 使用 `say` 合成短音频；
- Python 统一入口完成 MLX/Metal 端到端生成 Markdown + JSON + report JSON；
- Apple Speech helper 连续和并发启动不发生临时文件冲突；
- Apple Speech 经公共 Python CLI 返回 schema v1 JSON；
- 非登录 PATH 下的高层入口不再误报 Homebrew 工具缺失。

### 6.3 明确不构成验收的内容

- macOS 单元测试不能证明 Windows PowerShell 5.1/7、Windows Store alias、CUDA DLL 或原生路径已通过；这些留给 Windows 实机阶段。
- 沙箱内 Metal 失败不能作为 macOS GPU 不兼容证据。
- Apple Speech 在当前设备已有授权后的成功，不证明全新用户首次权限弹窗体验；代码只能保证正确触发并返回明确授权错误。
- ListenKit 测试不能证明 LingoTrace 已修复 `/bin/bash` 或 `mlx` 参数问题。

## 7. 提交组织

建议在同一共享分支按可审阅提交组织：

1. 方案与核验记录；
2. 共享 CLI/执行报告契约；
3. POSIX/macOS 兼容修复；
4. 测试与公共文档；
5. Windows 交接和 Agent 回应。

Windows Codex 应在本分支最新提交上继续，不另起一套长期平台分支。

## 8. 最终实施与验证记录

### 8.1 已实施范围

截至 2026-08-10，本方案第 5 节的九项步骤均已完成：共享 Python
子进程隔离、POSIX 统一入口、非交互策略、结构化执行报告、Apple helper
并发安全、平台限制、设备参数透传、公共 Agent 契约、Windows 交接与五份
Agent 回应均已落地。实现没有为五个 Agent 复制私有业务 adapter；宿主能力差异
统一由 ListenKit 入口、文件化报告和根级指令吸收。

### 8.2 自动化结果

```text
python3 -m compileall -q listenkit_cli cli tools tests
result: pass

Bash 3.2 syntax: cli/**/*.sh
zsh syntax: tools/apple-speech-helper/**/*.sh
result: pass

python3 -m unittest discover -s tests -v
Ran 146 tests in 37.896s
OK (skipped=6 Windows-only)

python3 -m pytest -q
140 passed, 6 skipped, 29 subtests passed in 36.66s
```

新增回归覆盖：成功/失败/冲突/不可写的 execution report、污染 Python
环境、包含空格的解释器路径、最小 Homebrew PATH、统一 doctor、旧入口委派、
设备参数透传、PTY 非交互、Apple 非 macOS 拒绝和 BSD `mktemp` 模板。

### 8.3 macOS 真实能力结果

- 沙箱外 doctor 实测 `mlx=0.32.0`、`mlx-whisper=0.4.3`、Metal ready；
  同一机器沙箱内 Metal unavailable，证实报告中的部分 MLX 失败属于宿主边界。
- 真实 MLX 端到端通过：`engine=mlx-whisper`、`device=metal`、
  `compute_type=float16`、`timing_complete=true`；Markdown、transcript JSON 和
  execution report 均产生。
- Apple Speech 从公共统一 CLI 连续执行两次均成功，实际 report 为 `status=ok`、
  `engine=apple`、`timing_complete=true`。
- 两个 Apple helper 同时运行均退出 0，输出均为有效 JSON，未出现临时文件冲突。
- `PATH=/usr/bin:/bin` 且注入无效 `PYTHONHOME/PYTHONPATH` 时，公共高层入口仍
  完成真实 Apple Speech Markdown 端到端流程。
- helper 的 `codesign --verify --deep --strict` 和 `/usr/bin/open -W -n` 启动均通过；
  因此没有把未复现的“ad-hoc 签名必然失败”当作本项目缺陷处理。

### 8.4 完成边界

macOS 代码、自动化和本机真实 backend 验收已经完成。全新 macOS 用户首次
Speech 权限弹窗仍属于必须由该用户确认的系统交互边界。Windows PowerShell、
Python 发现、UTF-8、Git Bash 策略和真实 CUDA/fallback 不在 macOS 设备上伪验收，
具体接续步骤见 `windows-codex-handoff.md`。
