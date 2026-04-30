---
name: AI编排系统全局规则
description: |
  AI编排系统项目的全局行为约束。所有Agent必须遵守这些规则。
  适用于：所有参与AI编排系统开发的Agent。
---

# AI编排系统全局规则

## 工件通信

- Agent 间通过文件系统（工件）传递信息，不直接通信
- PRD.md → Architect 读取 → feature_list.json → Builder 读取 → progress.md → Auditor 读取
- 每个 Agent 只读写自己权限范围内的文件

## 禁止事项

- 不读取 PRD.md 的 Agent：Builder、Auditor（避免上下文浪费）
- 不修改代码的 Agent：Auditor（只审查，退回 Builder 修复）
- 不修改 feature_list.json 定义的 Agent：Builder（变更走人类确认）
- 不使用 Mock 数据：开发与生产环境严禁使用模拟数据

## Git 规范

- 每个 feature 一个 commit
- Commit message 格式：`feat(F-XXX): 简短描述`
- Tag 规范：`feat/F-XXX-start` → `feat/F-XXX-verified` → `feat/F-XXX-done`

## 模型约束

- Builder 和 Auditor 必须使用不同模型（避免同源偏差）
- Orchestrator 不依赖 AI 推理（纯代码状态机）

## 代码规范

- 不添加注释（除非用户要求）
- 遵循项目已有的代码风格
- 每个功能必须编写测试
- 测试覆盖正常路径 + 异常路径 + 边界条件
