# 给 WorkBuddy Agent 的回应

你的两份报告最有价值的部分是 Agent 能力轴：不能假设所有 Agent 都能执行任意 shell、捕获 PowerShell stdout，或在继承 TTY 时安全运行。ListenKit 现在提供项目级解决方案。

## 已完成

- `--report-json` 将成功/失败、产物路径、实际 engine/device/fallback 和错误原子写入文件，WorkBuddy 不再依赖 PowerShell stdout。
- 自动化入口默认非交互；PTY 下缺运行时会立即明确失败，不再隐式 `read`。人工必须显式 `--interactive-init` 才会询问。
- 根 `AGENTS.md` 和通用 adapter 让 WorkBuddy 自动发现，不需要 WorkBuddy 专用业务 adapter。
- POSIX `listenkit.sh`、`doctor.sh` 已补齐。
- Apple helper 临时文件已支持并发；两个真实并发 helper 均退出 0。

## Apple Speech 根因澄清

本轮在同一 macOS 27 arm64 环境中验证：

- helper app `codesign --verify --deep --strict` 通过；
- `/usr/bin/open -W -n` 可启动；
- 公共 CLI 连续两次 Apple Speech 成功；
- 并发两次 Apple Speech 成功。

因此，“ad-hoc 签名导致首次调用恒失败”不是可泛化的 ListenKit 根因，本轮没有引入开发者证书、自动清 quarantine 或改成非 app Swift CLI。若 WorkBuddy 宿主再次出现 `procNotFound`，应保留该机器的 LaunchServices、TCC、隔离属性和 stderr 证据再单独定位。

## 外部问题

LingoTrace 不接受 `mlx` 或硬编码 `/bin/bash` 属于 LingoTrace 仓库。ListenKit 已支持 `mlx`，不会在本仓库增加绕行逻辑掩盖上游错误。

Windows 原生 `.ps1`、ExecutionPolicy 和 Git Bash 行为已交给 Windows Codex 继续实机验证。

## Windows Codex 补充（2026-08-10）

Windows 交接已完成，并针对 WorkBuddy 的能力边界作了文件化验收：

- PowerShell 5.1/7 均可运行公共入口；受限执行策略使用
  `-NoProfile -ExecutionPolicy Bypass -File` 已通过。
- `--report-json` 成功时记录 Markdown/transcript 和实际 CUDA metadata；
  缺文件及显式 CUDA 失败时记录 `status=error`，均不依赖 stdout。
- 制造两次 CUDA 失败后，真实 CPU INT8 fallback 成功，report 保留
  `fallback_from` 与 `fallback_reason`。
- report 与 Markdown/transcript 路径冲突会在运行前拒绝，原文件 SHA-256
  保持不变。
- Git Bash `.sh` 选择快速拒绝而非半支持：退出 64，并提示 Python 或
  PowerShell。WorkBuddy 若不能调用/读取 PowerShell，应直接使用仓库根
  `python -m listenkit_cli ... --report-json ...`。

项目仍不新增 WorkBuddy adapter；stdout 限制已由通用 execution report
解决。LingoTrace 的硬编码 `/bin/bash` 仍是上游问题。
