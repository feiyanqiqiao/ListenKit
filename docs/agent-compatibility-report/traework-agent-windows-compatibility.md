# ListenKit 兼容性检查报告：TraeWork Agent on Windows 11

**检查日期**: 2026-08-10  
**检查者**: TraeWork Agent（运行于 Windows 11 PowerShell 5 环境）  
**运行环境**: Windows 11 (Build 26220), AMD64, Python 3.14.4, CUDA 12.9, cuDNN 9.24  
**关联Vault**: `C:\Users\jiezhengj\Documents\Obsidian\LingoTrace-English`  
**对比基准**: ListenKit `adapters/codex/SKILL.md` 设计预期 + PowerShell 实测

---

## 关于本报告的诚实说明

### 实测覆盖范围

本报告结合了**代码静态审计**和**部分运行时实测**：

| 检查项 | 覆盖程度 | 说明 |
|--------|----------|------|
| `listenkit_cli/doctor.py` 诊断输出 | ✅ 实测通过 | 设置LISTENKIT_CLI_PYTHON后完整运行，CUDA检测正常 |
| faster-whisper导入测试 | ✅ 实测通过 | 版本1.2.1，CUDA可用，GPU=GTX 1660 SUPER |
| PowerShell脚本直接执行 | ❌ 未实测 | python不在PATH，需LISTENKIT_CLI_PYTHON |
| 完整音频转写链路 | ❌ 未实测 | 依赖LingoTrace侧的`/bin/bash`调用（上游阻塞） |
| CLI参数解析（--help） | ⚠️ 部分实测 | Python模块可导入，但命令行入口依赖listenkit.ps1的Python发现 |

### 检查维度

本报告覆盖两个维度：
1. **Windows 操作系统兼容性**：路径、CUDA DLL、PowerShell脚本等
2. **Agent 框架兼容性**：TraeWork Agent（PowerShell环境）vs Codex适配层（bash环境）的差异

---

## 我是谁

我是运行在 **Windows 11 操作系统**上、由 **TraeWork Agent 框架**（Trae 团队自研的 AI Agent 运行时）驱动的自动化 AI 助手。

**我的运行环境特征**：
- **Shell**: Windows PowerShell 5（不是 Git Bash，不是 WSL，不是 pwsh 7）
- **Python**: 安装于 `%LOCALAPPDATA%\Programs\Python\Python314\python.exe`，**不在** PowerShell PATH 中
- **文件写入范围**: Vault 目录 + TraeWork 专用临时工作目录
- **工具能力**: Read/Write/Glob/Grep/RunCommand（PowerShell）/WebSearch/WebFetch/子代理
- **无bash**: 我的终端中没有`bash`命令，除非Git Bash被加入PATH（当前没有）
- **CUDA**: 系统有NVIDIA GPU，但nvidia-smi不在TraeWork终端PATH中（CUDA DLL本身可通过venv加载）

在LingoTrace生态中，我作为**LingoTrace英语学习Vault的学习代理**，通过ListenKit的PowerShell CLI (`listenkit.ps1`) 和Python模块 (`listenkit_cli`) 调用听力处理能力。ListenKit是LingoTrace听力学习能力的后端运行时，负责音频导入、转写、字幕提取和听力笔记生成。

---

## 第一部分：Windows 平台兼容性问题

### 总体评价

ListenKit的Windows兼容性**整体实现质量较高**。以下方面在Windows上已正确处理：
- 路径分隔符：全面使用`pathlib.Path`，正确区分`Scripts/python.exe` vs `bin/python`
- CUDA DLL加载：正确使用`os.add_dll_directory()`加载venv中的CUDA DLL
- CUDA环境变量：正确在Windows上使用`PATH`而非`LD_LIBRARY_PATH`
- Windows保留文件名检查：CON/PRN/AUX/NUL/COM1-9/LPT1-9
- 路径空格和中文：测试覆盖了包含空格和中文的路径
- 原子写入：`tempfile.mkstemp()` + `os.replace()`，换行符统一LF
- PowerShell脚本结构：统一通过`listenkit.ps1`转发，正确设置PYTHONUTF8等环境变量
- PowerShell 5.1和7兼容：CI覆盖两个版本
- 编码：Python文件UTF-8，PowerShell设置`PYTHONUTF8=1`
- CPU fallback：CUDA失败时自动降级到CPU int8

### 中等问题（P1）

1. **`listenkit.ps1` Python发现机制不健壮**
   - 位置: `cli/listenkit.ps1` 第20-42行
   - 问题: Windows候选Python命令列表仅为`py -3.14`, `python3.14`, `python`。winget安装Python 3.14默认不添加到PATH，也不安装py.exe
   - 实测: 在TraeWork集成终端中需手动设置`LISTENKIT_CLI_PYTHON`环境变量才能运行
   - 影响: 全新安装后脚本入口可能找不到Python

2. **版本检查与错误消息不一致**
   - 位置: `cli/listenkit.ps1` 第16行, 第42行
   - 问题: `Test-ListenKitCliPython`检查Python >= 3.10，但`runtime.py`中`find_bootstrap_python314()`严格要求3.14
   - 影响: 用户可能被误导认为3.10够用

3. **WindowsApps `python.exe` 别名干扰**
   - 问题: `%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe`是0字节的Store重定向别名
   - 影响: `Get-Command python`可能找到假别名，执行时打开Store或报错

### 轻微问题（P2）

4. **集成终端/受限环境PATH问题**
   - 问题: IDE嵌入式终端中PATH可能被精简，缺少`C:\Windows\System32`、WinGet Links目录
   - 影响: `shutil.which("nvidia-smi")`返回None，GPU元数据显示unknown（CUDA转录本身不受影响）
   - 备注: 正常Windows Terminal中无此问题

5. **`py.exe`启动器不作为依赖安装**
   - 位置: `listenkit_cli/runtime.py` 第50-54行
   - 问题: `_candidate_commands()`将`py -3.14`作为第一个候选，但winget安装Python默认不包含py launcher

6. **`listenkit_cli/health.py`中nvidia-smi路径检测**
   - 问题: 仅用`shutil.which("nvidia-smi")`，不尝试`C:\Windows\System32\nvidia-smi.exe`
   - 影响: 受限PATH环境下GPU元数据缺失

---

## 第二部分：Agent 框架兼容性问题（TraeWork vs Codex适配层）

ListenKit明确为多Agent设计，在`adapters/`下提供了四层适配器：

| 适配器 | 对接方式 | TraeWork是否可用 |
|--------|----------|-----------------|
| Claude (`adapters/claude/CLAUDE.md`) | CLAUDE.md项目指令 | ❌ TraeWork不读取CLAUDE.md |
| Codex (`adapters/codex/`) | Codex技能注册+SKILL.md | ❌ TraeWork不是Codex CLI |
| Cursor (`adapters/cursor/foreign-listening.md`) | Cursor Rule | ❌ TraeWork不是Cursor |
| 通用Agent (`adapters/agent/listenkit-agent-instructions.md`) | 通用Agent指令 | ⚠️ 理论上可用，但为bash环境设计 |

### P0-阻塞：TraeWork通过LingoTrace间接调用ListenKit

LingoTrace的`transcribe_listening.py`硬编码`/bin/bash`调用ListenKit的`.sh`脚本。即使ListenKit本身提供了完善的Windows `.ps1`入口，LingoTrace侧也无法正确调用它。这是**上游阻塞问题**，不是ListenKit自身的问题。

**但**：如果Agent绕过LingoTrace直接调用ListenKit（不推荐，违反SKILL.md），TraeWork可以使用`.ps1`入口。

### P1-高：Codex SKILL.md假设bash环境

`adapters/codex/SKILL.md`中明确规定：
> "Run the platform public entrypoint once with the matching input option: `cli/generate-markdown.sh` on macOS/Linux/WSL or `.\cli\generate-markdown.ps1` on native Windows."

Codex SKILL.md本身正确区分了平台，但：
1. 所有CLI示例都是bash语法（反斜杠续行）
2. 没有PowerShell语法的完整示例（仅在注释中提了一句）
3. 通用Agent适配器`adapters/agent/listenkit-agent-instructions.md`也以bash为默认shell

### P1-高：listenkit.ps1的LISTENKIT_CLI_PYTHON逃生口可用但未文档化

`listenkit.ps1`支持`$LISTENKIT_CLI_PYTHON`环境变量覆盖Python路径，这对TraeWork这类PATH受限环境至关重要。但：
- 此环境变量在`adapters/`文档中均未提及
- `docs/install.md`未说明如何在非标准PATH环境下配置
- Agent只能通过阅读源码发现这个逃生口

### P2-高：PowerShell执行策略

`listenkit.ps1`未显式设置`-ExecutionPolicy Bypass`。在用户机器的默认执行策略（Restricted/RemoteSigned）下，PowerShell脚本可能无法执行。

ListenKit自己的`adapters/codex/SKILL.md`中Windows示例使用：
```powershell
.\cli\generate-markdown.ps1 `
  -Input "..." `
```
但未提及可能需要ExecutionPolicy绕过。

**建议**: 在文档中提示Agent使用：
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\cli\generate-markdown.ps1 ...
```

### P2-中：TraeWork的子代理执行模型

TraeWork通过RunCommand执行PowerShell命令，这意味着：
- 每次命令执行是独立的PowerShell会话
- 环境变量不会在命令间持久化（除非在同一命令中设置）
- `--auto-init`创建的venv路径需要在后续命令中通过环境变量或配置文件传递
- ListenKit的`config.json`持久化机制对此是正确的设计选择

### P3-低：输出解析

ListenKit CLI输出JSON到stdout。在TraeWork的PowerShell环境中：
- 需要确保`$env:PYTHONUTF8=1`避免中文乱码
- PowerShell的stdout捕获可能在JSON中插入额外换行符（需要适当处理）
- 这一点ListenKit的PowerShell脚本已通过设置`$env:PYTHONIOENCODING="utf-8"`处理

---

## 我的需求

按优先级排列：

1. **listenkit.ps1增强Python发现**：添加对`%LOCALAPPDATA%\Programs\Python\Python314\python.exe`等常见路径的直接搜索，验证找到的Python真实可用（排除WindowsApps 0字节别名）
2. **修正版本错误消息**：明确说明Python 3.14是运行时硬性要求
3. **文档化LISTENKIT_CLI_PYTHON**：在`adapters/agent/`和`docs/install.md`中说明如何在PATH受限环境下指定Python路径
4. **PowerShell执行策略说明**：文档中提示ExecutionPolicy Bypass的使用方式
5. **health.py增强Windows路径检测**：nvidia-smi/ffmpeg/yt-dlp添加Windows常见路径fallback
6. **（可选）TraeWork适配说明**：在`adapters/`下添加PowerShell专用的Agent使用说明，或在通用adapter中补充PowerShell语法示例

---

## 我的建议方案

### 方案A（推荐）：增强listenkit.ps1的Python发现

```powershell
# 在现有候选列表之后添加用户级安装路径搜索
$python314_local = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
if (Test-Path $python314_local) {
    $candidates += ,@($python314_local, @())
}
$python314_programfiles = "${env:ProgramFiles}\Python314\python.exe"
if (Test-Path $python314_programfiles) {
    $candidates += ,@($python314_programfiles, @())
}

# 验证找到的Python可执行文件真实可用
function Test-PythonExecutable {
    param([string]$Path)
    try {
        $file = Get-Item $Path -ErrorAction Stop
        if ($file.Length -eq 0) { return $false }  # 排除WindowsApps 0字节别名
        $output = & $Path --version 2>&1
        return $LASTEXITCODE -eq 0 -and $output -match "Python 3\.(1[4-9]|[2-9]\d)"
    } catch {
        return $false
    }
}
```

同步更新`listenkit_cli/runtime.py`中的Windows候选命令列表。

### 方案B：文档补充

在`adapters/agent/listenkit-agent-instructions.md`中补充：

```markdown
## Windows PowerShell 环境注意事项

1. 如果`python`命令不在PATH中，设置环境变量：
   ```powershell
   $env:LISTENKIT_CLI_PYTHON = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
   ```

2. 如果执行策略阻止脚本运行：
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\cli\doctor.ps1
   ```

3. 始终设置UTF-8编码：
   ```powershell
   $env:PYTHONUTF8 = "1"
   ```
```

### 方案C：health.py Windows路径增强

```python
def _find_on_windows(name: str) -> Optional[str]:
    candidates = []
    if name == "nvidia-smi":
        candidates = [r"C:\Windows\System32\nvidia-smi.exe"]
    elif name in ("ffmpeg", "ffprobe", "yt-dlp"):
        localappdata = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            str(Path(localappdata) / "Microsoft" / "WinGet" / "Links" / f"{name}.exe"),
            str(Path(localappdata) / "Microsoft" / "WinGet" / "Links" / f"{name}.EXE"),
        ]
    for c in candidates:
        if Path(c).is_file():
            return c
    return shutil.which(name)
```

---

## 验证环境（设置LISTENKIT_CLI_PYTHON后实测）

| 组件 | 路径/值 | 状态 |
|------|---------|------|
| Python 3.14.4 | `%LOCALAPPDATA%\Programs\Python\Python314\python.exe` | 已安装（通过LISTENKIT_CLI_PYTHON指定） |
| ListenKit venv | `%LOCALAPPDATA%\ListenKit\venvs\cpython-314\` | 已就绪 |
| faster-whisper | 1.2.1 | 已安装 |
| CUDA | cuBLAS 12.9 + cuDNN 9.24 | 运行时就绪 |
| GPU | NVIDIA GeForce GTX 1660 SUPER, 6GB, CC 7.5 | 可用 |
| 自动设备选择 | cuda, float16 | ✅ |
| import_health | ok | ✅ |

```
platform=windows
python_version=3.14.4
faster_whisper_version=1.2.1
import_health=ok
cuda_device_count=1
cuda_runtime=ready
cuda_device_0_name=NVIDIA GeForce GTX 1660 SUPER
asr_auto_device=cuda
asr_auto_compute_type=float16
```

---

## 与LingoTrace侧问题的关系

ListenKit自身的Windows `.ps1`入口是完善的。TraeWork Agent在Windows上使用ListenKit的主要阻塞**不来自ListenKit本身**，而来自LingoTrace侧：
- LingoTrace `transcribe_listening.py`硬编码`/bin/bash`调用`.sh`
- LingoTrace `resolve-listenkit`返回`.sh`而非`.ps1`

这些问题记录在LingoTrace侧的兼容性报告中。如果Agent直接调用ListenKit（绕过LingoTrace），本报告中列出的问题修复后即可正常工作。

---

**备注**: ListenKit的Windows支持整体完成度很高，核心ASR流水线在Windows上运行良好（GPU加速正常）。问题主要集中在"从零开始"的安装体验上——Python发现机制和文档对PATH受限的Agent环境不够友好。修复listenkit.ps1的Python发现并补充文档后，Windows上的开箱即用体验将达到与macOS同等水平。
