# 收敛记录：项目文档与契约治理基线

**日期**：2026-08-21

**分支**：`codex/spec-kit-migration`

## 收敛结论

本地实现已经满足 `spec.md`、`plan.md` 和 `tasks.md` 规定的迁移范围；没有发现需要追加的代码任务。迁移只改变项目文档、Spec Kit 治理工件和重复/过时文档结构，没有改变 ListenKit 应用源代码或公共运行时行为。

## 需求到证据映射

| 范围 | 实现/文档 | 验证 |
|---|---|---|
| FR-001/FR-002 | `.specify/`、`.agents/skills/`、`.specify/memory/constitution.md` | `specify integration status --json` 返回 `status: ok` |
| FR-003/FR-009 | `AGENTS.md`、`README.md`、`docs/`、`adapters/`；删除 `README.zh-CN.md` 和历史一键安装计划 | 文档逐文件审查、重复入口搜索、Git diff |
| FR-004/FR-005 | `LLM_INTEGRATION.md`、`docs/output-format.md`、`docs/backends.md`、适配器摘要 | 安装器 invariant 测试、现有 schema/report/backend 测试 |
| FR-006/FR-007 | `spec.md`、`plan.md`、`research.md`、`data-model.md`、`quickstart.md`、`tasks.md`、checklist、validation | 工件完整性检查、需求/任务/证据映射 |
| FR-008 | `listenkit_cli/`、`cli/`、`tools/`、`tests/` 未被迁移修改 | `git diff main --` 源码范围为空，153 项测试通过 |
| FR-010/SC-007 | `validation.md`、本记录、分支交付流程 | 编译、unittest、integration status、Git 审查；GitHub 推送/PR 由 T028 完成 |

## 任务收敛

- T001-T027 已完成并在 `tasks.md` 标记为 `[x]`。
- T028 是外部交付任务，依赖 GitHub 凭据和网络权限；在推送分支并创建 PR 后标记完成。
- 本地没有 CRITICAL、HIGH、MEDIUM 或 LOW 的实现缺口，因此不追加 Convergence phase。

## 已知限制

- 当前验证运行在 macOS/Python 3.14.4；Windows-only 测试跳过，由 CI 的三平台矩阵负责。
- Apple Speech 权限、Apple Silicon Metal 和真实 NVIDIA 设备声明没有新增本地以外的支持承诺，仍需对应实机或 CI 证据。
- Spec Kit 生成技能中的英文文本属于 manifest 管理的工具基础设施，未手工改写；项目维护规则和说明均已中文化。
