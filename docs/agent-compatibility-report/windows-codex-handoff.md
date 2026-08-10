# ListenKit Windows Codex 交接文档

- 日期：2026-08-10
- 共享分支：`codex/agent-compatibility-hardening`
- 快照基线：`c23f0a8e828ac176e14abd20aa627a62bdd8e588`
- macOS 方案：`macos-compatibility-hardening-plan.md`
- 接手原则：在同一分支最新提交上继续，不创建另一条长期 Windows 优化分支
- 发布说明：macOS 阶段已在本地提交；若 `origin` 尚未出现该分支，需由用户明确授权后再推送，不能改从 `main` 重做

## 1. macOS 阶段已经完成的共享能力

以下内容已经实现并通过 macOS 自动化与实机验证，Windows Codex 应先回归而不是重新设计：

1. `listenkit_cli/process.py` 的 Python 子进程隔离会移除宿主 `PYTHONHOME`、`PYTHONPATH`，并覆盖托管运行时检查、pip、MLX/CUDA 探针和 ASR helper。
2. Python CLI 的 `generate-markdown`、`transcribe-audio` 支持原子 `--report-json`，成功时写产物和实际 backend 元数据，失败时写结构化错误。
3. `doctor` 暴露：
   - `listenkit_version`
   - `doctor_schema_version`
   - `transcript_schema_version`
   - `execution_report_schema_version`
4. `python -m listenkit_cli` 已正式成为跨平台程序化入口；平台分发器用于宿主 Python 环境不可靠的场景。
5. 根 `AGENTS.md` 和通用/Codex/Claude/Cursor 适配器已统一到共享契约，明确不得让各 Agent 自行修改 ListenKit 规避宿主限制。
6. macOS/Linux 新增 `cli/listenkit.sh`、`cli/doctor.sh`；现有 `.sh` 会清理 Python 环境、补标准 Homebrew PATH、默认非交互。
7. Apple backend 只允许 macOS；helper 临时文件可并发安全使用。
8. `generate-markdown.sh` 已补齐 device/compute/device-index 参数透传。
9. shell 指令安装器已改为同目录临时文件加原子替换。

## 2. macOS 完成证据

```text
python3 -m compileall -q listenkit_cli cli tools tests
所有修改过的 Bash/zsh 脚本语法检查通过
python3 -m unittest discover -s tests -v
Ran 146 tests in 37.896s
OK (skipped=6)

python3 -m pytest -q
140 passed, 6 skipped, 29 subtests passed in 36.66s
```

实机边界：

- 沙箱外 doctor：MLX 0.32.0、mlx-whisper 0.4.3、Metal ready；
- 真实 MLX E2E：`engine=mlx-whisper`、`device=metal`、`compute_type=float16`，Markdown、transcript JSON、execution report 全部生成；
- Apple Speech 公共 CLI 连续两次成功；
- 两个 Apple helper 并发运行均退出 0，无 `mkstemp failed`/`File exists`；
- 最小 PATH 且注入无效 `PYTHONHOME/PYTHONPATH` 时，高层入口仍完成 Apple Speech E2E。

不要用 macOS 结果声称 Windows PowerShell、CUDA 或路径行为已验收。

## 3. Windows 必做核验顺序

### 3.1 建立基线

```powershell
git fetch origin
git switch codex/agent-compatibility-hardening
# 仅当该分支已经发布到 origin 时执行：
git pull --ff-only
git status --short --branch
python -m compileall -q listenkit_cli cli tools tests
python -m unittest discover -s tests -v
```

工作区必须先干净。不要清理或覆盖 macOS 文档与回应文件。

### 3.2 PowerShell 入口矩阵

分别在 Windows PowerShell 5.1 与 PowerShell 7 执行：

```powershell
.\cli\listenkit.ps1 --help
.\cli\listenkit.ps1 doctor
.\cli\listenkit.ps1 generate-markdown --help
.\cli\generate-markdown.ps1 --help
```

受限执行策略额外执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\cli\listenkit.ps1 doctor
```

验收：两种宿主输出一致，中文和包含空格的路径不乱码，退出码可读。

### 3.3 `--report-json` 原生验证

用本地短 WAV 跑：

```powershell
.\cli\listenkit.ps1 generate-markdown `
  --input "C:\路径 with spaces\sample.wav" `
  --language English `
  --output "work\路径 with spaces\sample.md" `
  --report-json "work\路径 with spaces\sample.execution.json" `
  --auto-init
```

必须验证：

- `.md`、同 stem transcript `.json`、execution `.json` 三者均存在；
- report `status=ok`；
- transcript 与 report 均记录实际 `device`、`compute_type`；
- 人为制造缺文件错误时 report `status=error` 且退出码非 0；
- report 路径与 transcript 路径相同时安全拒绝，原文件不被覆盖；
- WorkBuddy 一类无法读取 PowerShell stdout 的 Agent 能直接读取 report 文件完成判断。

### 3.4 Python 发现机制

报告已证实的 Windows 风险尚未在 macOS 阶段修改：

- 无 `py.exe`；
- 无 `python3.14` 命令；
- winget Python 位于 `%LOCALAPPDATA%\Programs\Python\Python314\python.exe` 但可能不在 PATH；
- `WindowsApps\python.exe` 可能是 Store alias；
- 托管 venv 已健康但 `listenkit.ps1` 没有优先把它作为 CLI host 候选；
- Agent 可能注入自己的 `PYTHONHOME/PYTHONPATH`。

建议候选顺序：

1. `LISTENKIT_CLI_PYTHON` 明确覆盖；
2. 已存在且可运行的托管 runtime Python；
3. `%LOCALAPPDATA%\Programs\Python\Python314\python.exe`；
4. `%ProgramFiles%\Python314\python.exe`；
5. `py -3.14`、`python3.14`、`python`。

每个候选必须真实执行版本探针，不能仅依赖 `Get-Command`。排除不可执行/重定向 alias，并在启动共享 Python CLI 时隔离宿主 `PYTHONHOME/PYTHONPATH`。CLI host 可以是 3.10+；创建托管 ASR runtime 的 bootstrap 仍必须是 3.14。错误消息要明确区分这两个要求。

### 3.5 Git Bash/MSYS/Cygwin 政策

当前正式契约是：

- 原生 Windows 优先 `python -m listenkit_cli` 或 `.\cli\listenkit.ps1`；
- Git Bash/MSYS/Cygwin 不是 WSL；
- 现有 `.sh` 仍包含 POSIX/macOS 运行时默认形状，不能因为 `--help` 成功就视为 Windows 支持。

Windows 阶段应做明确决策并测试：

- 推荐最小路径：`.sh` 在 MINGW/MSYS/CYGWIN 入口快速失败，指向 Python/PowerShell；
- 只有在愿意长期维护 Git Bash 路径、Python 布局、依赖和 CI 时，才把 `.sh` 宣布为支持。

不要让 `.sh` 在健康 Windows runtime 已存在时误报 macOS Cache 路径并建议重复初始化。

### 3.6 Windows 工具路径与 UTF-8

需要验证并酌情实现：

- `nvidia-smi.exe` 的受限 PATH fallback；
- WinGet Links 中 `ffmpeg.exe`、`ffprobe.exe`、`yt-dlp.exe`；
- 直接 `python -m listenkit_cli` 在 Windows 控制台的 stdout/stderr UTF-8；
- PowerShell 分发器在调用前设置并在 finally 中恢复 UTF-8 与 Python 环境变量。

不要仅依据 Antigravity 的编码推测修改；使用中文路径、中文错误、重定向到文件和 Agent stdout 捕获分别验证。

### 3.7 真实 CUDA 与 fallback

在 GTX 1660 SUPER 设备上至少验证：

- doctor 检测设备、CUDA 库、支持 compute type；
- `device=auto` 选择 CUDA；
- 实际转写为可支持精度；
- 模拟/制造 CUDA 失败后 fallback 到 CPU INT8，并把原因写入 transcript 和 execution report；
- `device=cuda` 明确要求时不允许静默 CPU fallback。

## 4. 本阶段不要做的事

1. 不要把 LingoTrace 的 `/bin/bash`、`resolve-listenkit` 或 `mlx` 参数问题伪修在 ListenKit；应在 LingoTrace 仓库修改。
2. 不要新增 Antigravity/TraeWork/WorkBuddy/QwenWork 四套业务 adapter；根 `AGENTS.md` 与通用契约是有意设计。
3. 不要删除或改成动态 macOS 26 deployment target；它对应 SpeechAnalyzer API 下限。
4. 不要降低托管 ASR runtime 的 Python 3.14 ABI 要求，除非另有依赖兼容性项目和完整矩阵证据。
5. 不要声称单元测试或 JS/shell 帮助输出等价于 Windows 真实 CUDA、PowerShell 5.1、受限 ExecutionPolicy 和 Agent stdout 验收。

## 5. Windows 完成标准

只有同时满足以下条件，才能把 Windows 阶段标记为完成：

- Windows 全量测试通过，非 Windows skip 符合预期；
- PowerShell 5.1 与 7 公共入口通过；
- Python 发现覆盖 PATH、winget、本地路径、托管 venv和 Store alias；
- 中文/空格路径真实 E2E 通过；
- CUDA 与 CPU fallback 真实验证；
- execution report 成功/失败均验证；
- Git Bash 行为明确且不会误导；
- 更新本交接文档的结果区，列出确切命令、版本、设备和未完成边界；
- 重新跑跨平台 CI 后再提交或发 PR。
