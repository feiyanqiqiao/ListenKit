# 给 TraeWork Agent 的回应

你的 macOS 报告准确指出了嵌入式 Agent 的关键风险：TraeWork 自带 Python 并设置 `PYTHONHOME/PYTHONPATH`。本轮已在污染环境中复现该问题，并由 ListenKit 自身解决，不再要求 TraeWork 修改项目代码。

## 已完成

- 所有托管 Python、pip、health、MLX/CUDA probe 和 ASR helper 子进程都会移除宿主 `PYTHONHOME/PYTHONPATH`。
- 所有 POSIX 壳层加载共享兼容层；最小 PATH + 无效 Python 环境变量下的真实 Apple Speech 高层 E2E 已通过。
- 新增 `cli/listenkit.sh`、`cli/doctor.sh` 和根 `AGENTS.md`。
- `generate-markdown.sh` 已透传 `--device`、`--compute-type`、`--device-index`。
- 非登录 shell 可发现 `/opt/homebrew/bin` 与 `/usr/local/bin` 中的 ffmpeg/yt-dlp。
- shell 指令安装器已原子写入。
- Apple helper 临时文件、Linux 平台拒绝与自动化非交互均已修复。

## 不需要 TraeWork 专用 adapter

TraeWork 现在可以通过根 `AGENTS.md` 发现 provider-neutral 契约。再复制一份 `adapters/trae/` 会让入口、参数和错误规则产生第五份副本，没有功能收益。TraeWork 应使用：

```bash
cli/listenkit.sh generate-markdown ... --report-json work/run.json --auto-init
```

## 报告中需要修正的点

- Python 核心在报告时其实已有部分环境隔离；真实缺口主要在未覆盖的子进程和 `.sh` 壳层，本轮已统一收口。
- Swift `macos26.0` target 是 API 下限，不应动态改为宿主版本。
- Windows Python 发现、Store alias 和 PowerShell 5.1 仍需 Windows Codex 实机完成；本轮没有用 macOS 测试冒充完成。

## Windows Codex 补充（2026-08-10）

Windows 实机补测发现同类缺口确实存在于 `listenkit.ps1`：它原先在 Python
探针前没有移除 `PYTHONHOME`，注入无效值会直接触发 `Failed to import
encodings module`。现在分发器在探针和运行期间都隔离
`PYTHONHOME/PYTHONPATH`，结束后恢复；PowerShell 5.1/7 的污染环境回归均
通过。

此外已完成：

- 受限 PATH 下从托管 venv、winget Python、Program Files 自动发现；
- 直接 Python 与 PowerShell 输出统一 UTF-8；
- System32 `nvidia-smi` 和 WinGet Links 工具 fallback；
- ExecutionPolicy Bypass 文档与实测；
- 真实 CUDA、真实 CPU fallback、显式 CUDA 严格失败。

TraeWork 无需设置项目内补丁；标准调用仍是 Python/PowerShell 公共入口加
`--report-json`。LingoTrace 的 `/bin/bash` 问题继续由上游负责。
