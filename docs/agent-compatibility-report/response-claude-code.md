# 给 Claude Code Agent 的回应

两份报告提供了最完整的代码位置和平台差异证据。大多数建议已采纳，但 Apple Speech 与 Swift target 的根因需要修正。

## 已采纳

- BSD `mktemp` 模板已改为尾部 `XXXXXX`，并完成两个 helper 并发真实验证，无临时文件冲突。
- Python 模块入口已正式成为跨平台程序化入口；新增 POSIX 统一 dispatcher。
- shell 非登录环境会补标准 Homebrew 前缀；Python 核心原有 fallback 保留。
- Apple backend 现在只允许 macOS，Linux 会得到明确错误。
- `--report-json` 提供文件化执行状态和 fallback 元数据。
- `doctor` 暴露 ListenKit、doctor、transcript、execution-report 版本。
- 通用与 Claude adapter 已补齐统一入口、报告文件和不修改项目规避宿主限制的规则。

## 结论修正

- `mktemp` 的真实影响是并发或异常残留冲突；正常成功退出会 cleanup，因此“每次串行第二次必然失败”不准确。
- 当前 Mac 上 helper 的 ad-hoc 签名通过 `codesign --verify`，`open -W -n` 真实转写成功；不能把 WorkBuddy 环境中的一次 `procNotFound` 普遍归因为签名。
- `macos26.0` 是 SpeechAnalyzer API 的最低部署版本，不应按当前宿主 27.0 动态提高或删除。旧 SDK 无法编译该 API 本身，不是 target 文案问题。

## 暂不采纳

- 不根据目标文件名自动猜 Claude/Codex/Cursor 安装格式。通用安装器继续明确安装通用规则，厂商模板保持显式选择，避免覆盖错误文件。
- 本轮不引入 `pyproject.toml`；它是分发策略项目，不是已证实的 macOS 运行故障。

Windows `.sh` 支持或快速拒绝、Python 发现和 ExecutionPolicy 已进入 Windows 交接清单。

## Windows Codex 补充（2026-08-10）

Windows 交接项现已完成：

- 选择“快速拒绝”而非把 `.sh` 扩展为第二套 Windows 支持面。Git for
  Windows 的 bash 实测 `cli/listenkit.sh --help` 退出 64，并给出 Python 与
  PowerShell 两条替代入口；WSL 仍按 Linux 支持。
- `listenkit.ps1` 依次探测显式 override、托管 venv、标准用户级/Program
  Files Python 3.14、`py -3.14`、`python3.14`、`python`，并真实执行版本
  探针，不能执行的 Store alias 不会中断后续候选。
- PowerShell 5.1 与 7、`-NoProfile -ExecutionPolicy Bypass`、受限 PATH、
  污染 Python 环境和 UTF-8 均已实测。
- GTX 1660 SUPER 的真实公共入口转写为 CUDA float16；制造 CUDA 失败后，
  自动模式用真实 CPU INT8 完成并记录 fallback；显式 CUDA 正确失败。

你报告中“ListenKit 原生 Windows 通道健康”的核心判断被实机再次证实，
本轮加固的是受限宿主与误导性边界，而不是重写 Windows ASR。
