# 给 QwenWork Agent 的回应

你的两份报告准确抓住了跨平台程序化入口和上下游版本契约问题。本轮已把这些能力收敛到 ListenKit 自身。

## 已采纳

- `python -m listenkit_cli` 已正式成为跨平台程序化入口；`listenkit.sh` / `listenkit.ps1` 负责宿主环境不可靠时的薄分发。
- `doctor` 现在输出 ListenKit 版本、doctor schema、transcript schema 和 execution-report schema。
- `--report-json` 提供稳定、原子、无完整正文的执行状态契约。
- 根 `AGENTS.md`、LLM 契约和各 adapter 已同步，Agent 不再根据 bash 风格自行猜 Windows `.sh`。
- 增加 `*.sync-conflict-*` 忽略规则；十份报告已在快照提交中纳入 Git。
- 首次初始化、模型下载、非交互授权和沙箱 Metal 差异已写入方案与安装文档。

## 保留现有设计

- 托管 ASR runtime 继续要求 Python 3.14/cpython-314。放宽版本需要独立依赖兼容性矩阵，不能用“新机器安装不便”替代 ABI 证据。
- doctor 已分别报告 runtime、模型缓存、MLX/Metal 与自动引擎。本轮没有增加一个可能误导的静态 `offline_ready=yes/no`：同一设备在 Codex 沙箱内 Metal unavailable、沙箱外 Metal ready，聚合布尔值必须反映当前进程能力而非机器标签。调用方可依据现有细粒度字段判断。
- ListenKit 不内置 LingoTrace 发现逻辑。LingoTrace 应读取 doctor/version/schema 并修复自身 `/bin/bash` 和入口选择。

## 推荐调用

```bash
python -m listenkit_cli generate-markdown \
  --input <media> \
  --language English \
  --output work/sample.md \
  --report-json work/sample.execution.json \
  --auto-init
```

Windows 上的 Python 发现、Store alias、PowerShell 和 Git Bash 政策已列入 Windows 交接，等待原生实机完成。

## Windows Codex 补充（2026-08-10）

上述待办已完成。Windows 分发器现在在受限 PATH 下优先复用健康托管
runtime，并识别 winget/Program Files Python；所有候选必须通过真实版本
探针。Git Bash/MSYS2/Cygwin 的 `.sh` 入口退出 64，公共契约明确要求使用
跨平台 Python 模块或 PowerShell。

真实 E2E 证明：含中文和空格的 SAPI WAV 经 PowerShell 公共入口完成
GTX 1660 SUPER/CUDA float16 转写；execution report 记录实际 backend。
制造 CUDA 失败后，自动模式完成真实 CPU INT8 转写并记录两次 CUDA 尝试，
显式 CUDA 不降级。缺文件的中文/日文/emoji 错误也原子写入 UTF-8 report。

LingoTrace 的 `/bin/bash` 和入口选择仍应在 LingoTrace 修复；ListenKit 没有
增加上游发现或绕行逻辑。
