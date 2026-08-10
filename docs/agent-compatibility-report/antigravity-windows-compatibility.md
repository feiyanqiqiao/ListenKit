# Antigravity Agent Windows 兼容性报告 (ListenKit)

## 身份声明
- **操作系统**: Windows 11
- **Agent框架**: Antigravity (Google Deepmind)
- **执行环境**: 原生 Windows PowerShell (pwsh)
- **模型**: Gemini 3.1 Pro (High)

## 兼容性测试摘要
我对 ListenKit 的代码库和适配器文档（`LLM_INTEGRATION.md`）进行了深入审计，并在原生 Windows 上成功执行了 `python -m listenkit_cli doctor` 命令。测试显示该运行时成功识别了 Windows 系统、Python 3.14.4 环境、我的 NVIDIA 显卡以及 yt-dlp 和 ffmpeg 等核心依赖。

## 发现的问题

### 1. Windows 平台兼容性问题
- **入口规范性良好，但编码隐患仍存**: `LLM_INTEGRATION.md` 非常清晰地规定了 macOS/Linux 使用 `.sh`，原生 Windows 必须使用 `.ps1`，且警告了不能使用 WSL，这是非常优秀的跨平台设计。然而，作为智能体，我在执行带中文字符输出的任务时，Windows PowerShell 默认的输出编码 (通常为 GBK) 仍然存在风险。如果不显式附加 `PYTHONUTF8=1` 环境前缀，可能导致处理非英语素材时抛出异常或截断输出。

### 2. Agent 框架兼容性问题 (Codex vs Antigravity)
- **不同 Agent 框架的专属适配差异**: 在 `adapters/` 目录下，存在对 `codex`、`claude`、`cursor` 和通用 `agent` 的适配文件。Codex 作为成熟的自主智能体生态系统，已有相关的接入规范。而像 Antigravity 这样同样具备高度系统集成度、能够自主调用终端（`run_command`）的 Agent，在工具集和默认操作行为上可能有所不同，目前的通用说明缺乏对此类 Agent 运行特性的针对性补充。
- **自动化流程的跨平台操作指引**: 尽管现有的通用 `.ps1` 入口工作良好，并且在 `LLM_INTEGRATION.md` 中明确了 Windows 下的调用方式，但文档可以更加明确地指导各类型的自主 Agent，在全自动化流程中应如何安全、无阻塞地调用这些入口，以及如何标准化地处理终端环境下的异常回传。

## 需求与建议方案

### 我的需求
1. **防止字符编码错误**: 作为在后台执行脚本的 Agent，我需要平台尽量保证调用的稳定。在 `listenkit_cli` 初始化时，最好能在 Python 层面主动校验并修复标准输出流的编码，确保不管运行在哪个宿主 PowerShell，都是强制 UTF-8，这样能省去每次执行都手动加装前置环境变量的麻烦。
2. **现代执行型 Agent 操作指导**: 我需要明确的条款，告知在拥有全量运行权限的前提下，我在 Windows 上的最佳实践——不仅是“用 `.ps1` 替代 `.sh`”，还包括应如何正确捕捉异步任务的结果，及如何优雅处理错误回传。

### 建议方案
- 建议在 `listenkit_cli/__main__.py` 等入口处增加防范性编码修正，将 Windows 环境下的默认打印流强行指定为 UTF-8。
- 增加专门面向原生可执行 Agent（如 Antigravity）的最佳实践指导（可以是 `adapters/antigravity/SKILL.md` 或是升级通用 `agent` 的说明），明确强调在使用 `pwsh` 调用 `.\cli\generate-markdown.ps1` 时，对于跨端全自动化环境的细节期望。
