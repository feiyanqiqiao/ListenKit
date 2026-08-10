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
