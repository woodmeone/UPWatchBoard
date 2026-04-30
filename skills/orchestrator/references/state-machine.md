# Orchestrator 状态机详细设计

## 状态定义

| 状态 | 说明 | 进入条件 | 退出条件 |
|------|------|---------|---------|
| INIT | 入口路由 | 用户启动项目 | 路由判断完成 |
| PM_PHASE | PM 阶段 | full_pipeline 模式 | PRD.md 确认 |
| ARCH_PHASE | Architect 阶段 | skip_pm 或 PM 完成 | feature_list.json 确认 |
| DEV_PHASE | 开发阶段 | pure_execution 或 Architect 完成 | 所有 feature done |
| COMPLETE | 项目完成 | 所有 feature done | — |

## 开发阶段子状态

| 子状态 | 说明 | 进入条件 | 退出条件 |
|--------|------|---------|---------|
| CHECKPOINT_RECOVERY | 断点恢复 | 进入新 feature | 断点确定 |
| SESSION_START | 会话开始 | 断点确定 | progress_summary.md 生成 |
| BUILD | 代码构建 | 会话开始 / 反馈退回 | Builder 交付 |
| DETERMINISTIC_VERIFY | 确定性验证 | Builder 交付 | 验证通过 |
| RUNTIME_VERIFY | 运行时验证 | 确定性验证通过 | 验证通过/跳过 |
| AI_REVIEW | AI 审查 | 运行时验证通过 | 审查完成 |
| FEEDBACK_LOOP_CHECK | 反馈循环检查 | 审查未通过 | 继续或仲裁 |
| HUMAN_ARBITRATION | 人工仲裁 | 反馈上限/终止信号 | 人类决策 |
| FEATURE_DONE | Feature 完成 | 审查通过/人类确认 | 下一个 feature |

## 状态转换规则

### 确定性验证失败 → BUILD

```
条件: lint / typecheck / test / 结构校验 任一失败
动作: 退回 BUILD，Builder 修复
轮次: 不计入反馈轮次
原因: 代码基本质量问题，不是设计分歧
```

### 运行时验证失败 → BUILD

```
条件: 运行时验证失败
动作: 退回 BUILD，Builder 修复
轮次: 不计入反馈轮次
原因: 功能性问题，不是设计分歧
```

### AI 审查未通过 → FEEDBACK_LOOP_CHECK

```
条件: Auditor 审查发现问题
动作: 检查反馈轮次
轮次: 计入反馈轮次
```

### FEEDBACK_LOOP_CHECK → BUILD

```
条件: 未达动态轮次上限 且 无终止信号
动作: 退回 BUILD，附带 Auditor 反馈
轮次: 轮次+1
```

### FEEDBACK_LOOP_CHECK → HUMAN_ARBITRATION

```
条件: 达到动态轮次上限 或 检测到终止信号
动作: 生成冲突摘要，等待人类决策
```

## 终止信号详细定义

| 信号 | 检测方法 | 阈值 |
|------|---------|------|
| 全部通过 | Auditor 返回 pass | N/A |
| 达到轮次上限 | 轮次计数 ≥ 动态上限 | 简单1/中等2/复杂3 |
| 改进幅度不足 | 对比连续两轮 Auditor 意见数量 | < 3% |
| 退化检测 | 新一轮出现上一轮没有的问题 | 任意1个新问题 |
| 信息停滞 | 对比连续两轮 Auditor 意见内容 | 变化量 < 10% |

## Architect 召回状态转换

```
DEV_PHASE → ARCH_PHASE (召回)
条件: 连续2个feature失败 / 人类要求 / 完成度低于预期
限制: 最多3次召回

ARCH_PHASE (召回) → DEV_PHASE
条件: Architect 调整完成 + 人类确认
动作: 重置连续失败计数
```

## 降级状态转换

```
L1 功能收缩:
  触发: 连续2轮无进展
  动作: feature acceptance_criteria 缩减为最小可用

L2 质量下降:
  触发: L1无效
  动作: 跳过非关键审查项

L3 人工接管:
  触发: L1+L2无效
  动作: 暂停所有Agent，等待人类
```
