# 工件格式规范

## PRD.md

PM 阶段的输出，Architect 阶段的输入。

### 必须包含的章节

```markdown
# 项目名称

## 项目概述
[一段话描述项目目标和价值]

## 目标用户
[用户画像和使用场景]

## 核心功能
| # | 功能 | 优先级 | 描述 |
|---|------|--------|------|
| 1 | xxx | P0 | xxx |

## 非功能需求
[性能、安全、可用性等要求]

## 验收标准
[项目完成的判定条件]
```

### 存储位置

项目根目录：`PRD.md`

---

## feature_list.json

Architect 阶段的输出，Builder 阶段的输入。

### 完整格式

```json
{
  "project_name": "项目名称",
  "tech_stack": {
    "language": "TypeScript",
    "framework": "Next.js",
    "test_framework": "Jest",
    "package_manager": "npm"
  },
  "design_md": true,
  "features": [
    {
      "id": "F-001",
      "title": "功能标题",
      "description": "详细描述",
      "category": "data_model",
      "priority": "P0",
      "depends_on": [],
      "acceptance_criteria": [
        "标准1",
        "标准2"
      ],
      "status": "pending",
      "complexity": "simple"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_name | string | 是 | 项目名称 |
| tech_stack | object | 是 | 技术栈信息 |
| tech_stack.language | string | 是 | 编程语言 |
| tech_stack.framework | string | 是 | 框架 |
| tech_stack.test_framework | string | 是 | 测试框架 |
| tech_stack.package_manager | string | 否 | 包管理器 |
| design_md | boolean | 否 | 是否有 DESIGN.md（UI 项目为 true） |
| features | array | 是 | Feature 列表 |
| features[].id | string | 是 | Feature ID，格式 F-XXX |
| features[].title | string | 是 | 功能标题 |
| features[].description | string | 是 | 详细描述 |
| features[].category | string | 是 | 分类：data_model/api/ui/config/docs/test |
| features[].priority | string | 是 | 优先级：P0/P1/P2 |
| features[].depends_on | array | 是 | 依赖的 feature ID 列表 |
| features[].acceptance_criteria | array | 是 | 验收标准列表 |
| features[].status | string | 是 | 状态：pending/in_progress/done/blocked |
| features[].complexity | string | 是 | 复杂度：simple/medium/complex |

### 存储位置

项目根目录：`feature_list.json`

---

## init.sh

Architect 阶段的输出，Builder 阶段的输入。

### 内容

项目初始化脚本，包含：

```bash
#!/bin/bash
# 项目初始化脚本
# 由 Architect 生成，Builder 执行

# 1. 安装依赖
npm install

# 2. 初始化项目结构
mkdir -p src/models src/routes src/components

# 3. 配置环境
cp .env.example .env

# 4. 数据库初始化（如需要）
# npm run db:init
```

### 存储位置

项目根目录：`init.sh`

---

## DESIGN.md

Architect/Prototyper 阶段的输出（UI 项目），Builder 阶段的输入。

### 格式（遵循 Google Stitch 规范）

```markdown
# Design System: [项目名称]

## 1. Visual Theme & Atmosphere
[产品的视觉风格和氛围描述]

## 2. Color Palette & Roles
- **Primary** (#hex): [用途]
- **Secondary** (#hex): [用途]
- **Neutral** (#hex): [用途]
- **Error** (#hex): [用途]

## 3. Typography Rules
- **Headline Font**: [字体名]
- **Body Font**: [字体名]
- **Label Font**: [字体名]

## 4. Component Stylings
- **Buttons**: [形状、颜色、行为]
- **Cards**: [圆角、背景、阴影]
- **Inputs**: [边框、背景、内边距]

## 5. Layout Principles
[间距策略、边距、网格对齐]

## 6. Depth & Elevation
[阴影系统、表面层级]

## 7. Do's and Don'ts
- Do: [推荐做法]
- Don't: [禁止做法]

## 8. Responsive Behavior
[断点、触控目标、折叠策略]

## 9. Agent Prompt Guide
[快速颜色参考、可直接使用的提示词]
```

### 存储位置

项目根目录：`DESIGN.md`

---

## progress.md

开发阶段的进度记录，Orchestrator 维护。

### 格式

```markdown
# Progress Log — [项目名称]

## Session: [日期]

### Feature: F-XXX [标题]
- **Status:** done / in_progress / blocked
- **Complexity:** simple / medium / complex
- **Feedback Rounds:** X / Y (上限)

- Actions taken:
  - [操作1]
  - [操作2]

- Files created/modified:
  - [文件1] (created/modified)

- Verification results:
  | 验证项 | 结果 | 备注 |
  |--------|------|------|
  | lint | ✅ | — |
  | typecheck | ✅ | — |
  | test | ✅ | X tests passed |
  | runtime | ✅/⏭️ | — |

- Key decisions:
  - [决策1]
  - [决策2]

---
```

### 滚动窗口

- 保留最近 10 个 feature 记录
- 超过归档到 progress_archive.md

### 存储位置

项目根目录：`progress.md`

---

## progress_summary.md

Orchestrator 自动生成的上下文摘要，注入 Builder。

### 格式

```markdown
# 项目进度摘要

## 当前状态
- 正在开发: F-XXX [标题]
- 进度: X/Y features 完成 (Z%)
- 通过率: X/Y (Z%)

## 最近 5 个 feature 决策摘要
| Feature | 关键决策 | 审查结果 |
|---------|---------|---------|
| F-001 | [摘要] | ✅ |
| F-002 | [摘要] | ⚠️ 2轮 |

## 未解决的阻塞项
- [阻塞项1]

## 反馈循环统计
- 总轮次: X
- 平均每 feature: X.X
- 退回次数: X
```

### 存储位置

项目根目录：`progress_summary.md`

---

## progress_archive.md

归档的进度记录，供人类复盘。

### 格式

按时间倒序排列的已完成 feature 记录（与 progress.md 格式相同）。

### 存储位置

项目根目录：`progress_archive.md`

---

## 工件依赖关系

```
PRD.md ──────→ Architect ──→ feature_list.json ──→ Builder
                    │                │                    │
                    ├──→ init.sh ────┘                    │
                    ├──→ DESIGN.md ──┘                    │
                    │                                     │
                    └─────────────────────────────────────┘
                                     │
                              progress.md ←── Orchestrator
                              progress_summary.md ←── Orchestrator
                              progress_archive.md ←── Orchestrator
```
