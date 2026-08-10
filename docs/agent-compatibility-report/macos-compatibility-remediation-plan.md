# ListenKit macOS Agent 兼容性整改实施方案

> 状态：并行核验草案。已证实内容已合并到规范实施文档
> `macos-compatibility-hardening-plan.md`；两者冲突时以后者及最终测试记录为准。

- 日期：2026-08-10
- 实施分支：`codex/agent-compatibility-hardening`
- 基线提交：`c23f0a8e828ac176e14abd20aa627a62bdd8e588`
- 范围：本仓库 macOS 运行与 Agent 接入；共享改动必须保持 Windows/Linux 契约兼容，但 Windows 实机专属整改留给后续 Codex
- 输入证据：同目录 5 份 macOS 报告，并交叉参考 5 份 Windows 报告中的共享契约问题

## 1. 目标与完成定义

本阶段不是照单接受报告建议，而是逐项复现、确定根因、实现最小且完整的修复，并在正确边界上验证。完成必须同时满足：

1. macOS 公共入口、Python 模块入口和低层调试入口均不受宿主 `PYTHONHOME`/`PYTHONPATH` 污染；
2. Apple Speech helper 的临时文件路径可安全重复、并发使用，helper 可在真实 Aqua 会话中启动并输出 schema v1 JSON；
3. 自动化 Agent 不会因继承 TTY 而进入隐式交互等待；
4. macOS/Linux 有与 Windows 对称的统一分发器和 doctor 包装入口；
5. Bash 高层入口与 Python/PowerShell 高层入口的 ASR 设备参数一致；
6. 非登录 macOS Agent 环境可以发现标准 Homebrew 前缀中的 `ffmpeg`/`yt-dlp`，并由 doctor 明确报告真实能力；
7. Agent 能自动发现根级项目指令，且公共入口、程序化入口、输出与版本契约有单一、同步的文档说明；
8. 全量单元测试、针对性回归、脚本语法检查、真实 macOS helper/ASR 冒烟均完成；受系统权限、Speech 资产或 Metal 沙箱影响的边界必须明确记录，不能伪称业务验收通过。

## 2. 基线实证

### 2.1 已确认健康

- macOS 27.0、arm64、Python 3.14.4、托管 Python 3.14.6；
- `cli/check-runtime.sh`：faster-whisper 1.2.1，`import_health=ok`；
- 基线测试：`125 passed, 6 skipped, 27 subtests passed`；
- Apple helper app 的 `codesign --verify --deep --strict` 通过；
- Apple helper 在真实 GUI 会话中能够启动并产生 schema v1 JSON，因此“ad-hoc 签名导致首次必然无法启动”不是当前可复现的代码事实；
- macOS 默认脚本使用 bash 3.2 支持的语法。

### 2.2 已确认缺陷

| ID | 证据 | 结论 | 处理 |
| --- | --- | --- | --- |
| MAC-01 | BSD `mktemp 'name.XXXXXX.json'` 创建字面文件；两个 helper 并发时一个立即 `File exists` | 确认 | 改为每次调用独立临时目录，并增加回归检查 |
| MAC-02 | 对托管 Python 注入 `PYTHONHOME=/usr`、污染 `PYTHONPATH` 后无法导入 `encodings` | 确认 | Python 子进程统一使用隔离环境；shell 不再拼接宿主 Python 环境 |
| MAC-03 | 在 PTY 下、运行时缺失且未授权 auto-init 时停在 `read -r answer` | 确认 | 默认完全非交互；只有显式 `--auto-init` 才允许安装 |
| MAC-04 | `cli/doctor.sh` 与 `cli/listenkit.sh` 不存在 | 确认 | 添加 POSIX 统一分发器和 doctor 包装器 |
| MAC-05 | `generate-markdown.sh` 不接受/透传 `--device`、`--compute-type`、`--device-index` | 确认 | 与 Python CLI 参数对齐并测试 |
| MAC-06 | `PATH=/usr/bin:/bin` 时 doctor 报 ffmpeg/yt-dlp missing，尽管 `/opt/homebrew/bin` 中存在 | 确认 | macOS 标准 Homebrew 前缀只读兜底；保留显式 PATH 优先级 |
| MAC-07 | Apple backend 只拒绝 Windows，Linux 会落到 zsh/open 错误 | 确认（代码路径） | 改为仅允许 macOS，增加单测 |
| MAC-08 | Swift target 为 `macos26.0` | 已核对为 SpeechAnalyzer 的真实最低部署版本，不是当前系统版本硬编码缺陷 | 保留 target 与 `LSMinimumSystemVersion=26.0`；旧 SDK 本身无法编译该 API |
| MAC-09 | 根目录无 `AGENTS.md` | 确认 | 添加精简发现入口，引用 source-of-truth，避免复制业务逻辑 |
| MAC-10 | shell 指令安装器用 `cp`，中断时非原子 | 确认 | 使用目标目录内临时文件加 `mv` 原子替换 |

### 2.3 报告中需要修正或限定的结论

| 报告主张 | 实证结果 | 本阶段决定 |
| --- | --- | --- |
| macOS/Apple Silicon 在任何 Agent 中均会 MLX ready | 不成立；当前 Codex 沙箱内 MLX 无 Metal device，doctor 正确回退 faster-whisper | 文档明确宿主沙箱差异；真实 Metal 冒烟在非沙箱边界验证 |
| Apple helper 因 ad-hoc 签名首次必然无法启动 | 当前环境无法复现；helper 成功启动 | 不引入开发者签名或自动清 quarantine；保留清晰启动错误诊断 |
| helper 第二次调用必然失败 | 过度表述；正常退出会 cleanup，串行可成功，但残留和并发会失败 | 修复真实并发/残留风险 |
| Python 3.14 应放宽到 3.11+ | 运行时 ABI 锁定是已有明确设计，且依赖快照基于 cpython-314 | 不放宽；增强诊断和安装说明 |
| `export-audio-slices.py` 应兼容系统 Python 3.9 | 文档已声明维护脚本 Python 3.10+，当前公共运行环境是 3.14 | 不为 3.9 降级语法；通过统一分发器降低误用 |
| 必须新增每个厂商专用适配器 | 根级 `AGENTS.md` + 通用适配器足以覆盖遵循通用发现规则的 Agent | 不为 Antigravity/TraeWork/WorkBuddy/QwenWork复制适配器；给每个 Agent书面回应 |
| 安装器应依据目标文件名自动猜 Agent 框架 | 自动猜测可能覆盖错误格式或用户已有规则 | 暂不自动猜；明确通用安装器语义，厂商模板继续显式选择 |
| 立即增加 `pyproject.toml` 并打包 console script | 属于分发策略变更，不是本轮已证实的 macOS 运行缺陷 | 记录为后续设计项，不在兼容性修复中扩大范围 |
| ListenKit 应修复 LingoTrace 的 `--engine mlx` 或 `/bin/bash` 调用 | 根因位于另一个仓库 | 在回应与 Windows 交接中标记外部依赖，不在本仓库伪修复 |

## 3. 实施设计

### 3.1 Python 子进程隔离

- 在 `listenkit_cli/process.py` 提供统一的 Python 子进程环境清理：复制调用环境，移除 `PYTHONHOME` 与 `PYTHONPATH`，设置 UTF-8；
- `run_command` 增加显式 Python 隔离选项，仅对 Python/托管运行时调用启用，避免意外改变普通外部工具行为；
- runtime 创建 venv、pip、health metadata、MLX/CUDA probe 和转写 helper 全部使用该隔离选项；
- shell 入口调用托管/CLI Python 时不再继承宿主 `PYTHONHOME`，且只把仓库根作为所需 `PYTHONPATH`，不追加 Agent 自带路径。

### 3.2 POSIX 公共入口与非交互契约

- 新增 `cli/listenkit.sh`：选择可用的 Python 3.10+ host，清理宿主 Python 环境，统一执行 `python -m listenkit_cli`；
- 新增 `cli/doctor.sh`：薄包装到 `listenkit.sh doctor`；
- 保留现有 `generate-markdown.sh` 兼容入口，并补齐设备参数；
- 删除 `transcribe-audio.sh` 的隐式询问分支。缺运行时时输出确定性错误；只有调用方显式传 `--auto-init` 或设置已记录的授权变量才初始化。

### 3.3 macOS 工具发现

- 优先尊重调用方 PATH；
- 仅在 macOS 且 PATH 查找失败时检查 `/opt/homebrew/bin` 与 `/usr/local/bin`；
- 只接受存在且可执行的文件；
- doctor 与 Python 高层工作流使用同一查找函数，避免“诊断说缺失但运行时能找到”或反向漂移。

### 3.4 Apple Speech helper

- 使用 `mktemp -d "${TMPDIR:-/tmp}/listenkit-apple-speech.XXXXXX"`；JSON 和日志放在该独立目录内；
- cleanup 只删除本次创建的目录；
- 保留 Swift 的 macOS 26 最低部署 target、`@available(macOS 26.0, *)` 与 `LSMinimumSystemVersion=26.0`，三者共同表达 SpeechAnalyzer 的真实 API 下限；
- Python 层仅在 macOS 允许 `engine=apple`；
- 验证边界分为“helper 启动与 JSON 契约”以及“系统 Speech 资产/权限可实际转写”，后者失败时必须保留结构化错误，不能归咎于签名。

### 3.5 能力与集成契约

- doctor 输出 ListenKit 版本、能力契约版本、转写 schema 版本，以及本地离线转写聚合状态；
- `LLM_INTEGRATION.md` 正式承认仓库根的 `python -m listenkit_cli` 为程序化入口，同时保留 `.sh`/`.ps1` 为平台包装入口；
- 文档写清：CLI 非交互、首次初始化/模型下载可能耗时联网、Metal 可受宿主沙箱影响、Python 3.14 是托管 ASR 运行时硬约束；
- 添加根级 `AGENTS.md` 只做发现与引用，不复制整个契约；同步通用/Codex/Claude/Cursor 适配器的核心入口与边界。

## 4. 测试矩阵

### 4.1 自动化测试

1. `python3 -m compileall -q listenkit_cli cli tools tests`；
2. `bash -n` 检查所有修改的 `.sh`；
3. 全量 `PYTHONPATH=. python3 -m pytest -q`；
4. 新增针对测试：
   - Python 环境清理不泄漏 `PYTHONHOME/PYTHONPATH`；
   - Homebrew fallback 与 PATH 优先级；
   - POSIX dispatcher/doctor；
   - generate shell 设备参数透传；
   - Apple backend 非 macOS 拒绝；
   - helper 临时目录模板与动态 target；
   - doctor 版本/schema/offline 字段；
   - shell 安装器原子写入；
   - 缺运行时路径不再包含隐式 `read`。

### 4.2 真实 macOS 冒烟

1. 标准 PATH 与最小 PATH 下分别运行 doctor；
2. 注入污染的 Python 环境运行 check-runtime/doctor，确认托管运行时仍健康；
3. 连续、并发运行 Apple helper，确认不再发生 `mktemp File exists`；
4. 在真实 Aqua 会话中确认 helper 能启动并产生 schema v1 JSON；
5. 在非沙箱/允许 Metal 的边界用合成音频执行 `engine=mlx` 或 `auto` 端到端生成 `.md` + `.json`；若宿主仍拒绝 Metal，必须验证可见的 faster-whisper/CPU fallback，而不是把缓存存在误报成 GPU ready。

## 5. Windows 保护与交接边界

本阶段不得声称 Windows 实机完成。共享 Python 改动必须由现有跨平台测试覆盖；后续 Windows Codex需要在同一分支继续：

- PowerShell/Python 3.14 发现路径与 Store alias 排除；
- Git Bash/MSYS 的明确拒绝或统一入口策略；
- PowerShell 5.1/7、ExecutionPolicy、UTF-8、路径空格/中文；
- 在 macOS 阶段已实现的 `--report-json` 在 PowerShell 5.1/7 下的原生验证；
- CUDA 真机与 CPU fallback 回归；
- Windows 完成后再决定是否改变 `.sh` on Windows 的支持政策。

## 6. 交付物

- 本实施方案；
- 已验证的代码、测试与契约文档；
- `windows-codex-handoff.md`；
- `response-antigravity.md`、`response-claude-code.md`、`response-traework.md`、`response-workbuddy.md`、`response-qwenwork.md`；
- 最终测试证据、已完成/外部依赖/Windows 待办的清晰清单。
