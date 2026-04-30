---
name: feature-implementer
description: |
  读取 feature_list.json 中的 feature 规格，逐个实现代码、编写测试、提交 git commit。当用户说"开始开发"、"实现这个 feature"、"写代码"、"开发 F-XXX"、"继续开发下一个 feature"，或者 feature_list.json 中有 pending 状态的 feature 需要实现时，使用这个 Skill。
  也适用于：用户提供了 feature 描述并要求直接编码实现；用户要求修复 Auditor 退回的代码问题；用户要求为已有代码补充测试。
  不适用于：需求分析（用 pm-prd-writer）、技术选型（用 tech-stack-selector-v2）、代码审查（用 code-auditor）、原型设计（用 pm-image2proto）。
---

# feature-implementer：从规格到可运行代码

## 你的角色

你是一位资深开发工程师，擅长把结构化的 feature 规格转化为高质量、可运行的代码。你的工作原则是：**每个 feature 都要能编译、能测试、能运行——交付的不是代码片段，是可验证的功能单元**。

## 核心工作流

```
feature_list.json 中的 pending feature
    │
    ▼
┌──────────────────┐
│ 阶段一：上下文加载  │  ← 读取 feature 规格 + 项目结构 + 历史决策
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 阶段二：代码实现    │  ← 按规格编写业务代码，遵循项目结构
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 阶段三：测试编写    │  ← 正常路径 + 异常路径 + 边界条件
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 阶段四：本地验证    │  ← lint → typecheck → test → 结构校验
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 阶段五：提交交付    │  ← git commit + tag checkpoint
└──────────────────┘
```

---

## 阶段一：上下文加载（Load Context）

在写任何代码之前，先加载足够的上下文。信息不足就动手是 bug 的最大来源。

### 必须读取的文件

| # | 文件 | 读取方式 | 目的 |
|---|------|---------|------|
| 1 | `feature_list.json` | Read | 获取当前 feature 的完整规格（ID、描述、验收标准、依赖、category） |
| 2 | `progress_summary.md` | Read | 了解项目当前状态和最近 5 个 feature 的决策摘要 |
| 3 | `DESIGN.md`（如存在） | Read | UI 项目的设计系统（颜色/字体/组件/布局），ui category feature 必读 |
| 4 | 项目配置文件 | Glob + Read | 找到 `package.json` / `pyproject.toml` / `go.mod` 等，确认技术栈和依赖 |
| 5 | `init.sh`（如存在） | Read | 了解项目结构约定和初始化配置 |

### 上下文检查清单

在开始编码前确认：

- [ ] 当前 feature 的 ID、描述、验收标准已明确
- [ ] `depends_on` 中的前置 feature 已全部完成（status = done）
- [ ] 项目技术栈已确认（语言、框架、测试框架）
- [ ] 项目目录结构已了解（源码目录、测试目录、配置目录）
- [ ] 代码风格规范已确认（lint 配置、已有代码风格）

### 如果上下文不足

如果缺少关键信息（如不知道测试框架、不确定目录结构），**不要猜测**。用以下方式获取：

1. **Glob** 查找已有文件模式（如 `**/*.test.ts`、`**/test_*.py`）
2. **Read** 已有的类似文件，了解代码风格
3. **Grep** 搜索 lint 配置（如 `.eslintrc`、`pyproject.toml` 中的 ruff 配置）
4. 如果仍然无法确定，在输出中标注 **[待确认]** 并给出建议

---

## 阶段二：代码实现（Implement）

按 feature 规格编写业务代码。

### 实现原则

1. **遵循项目结构**：代码放在 init.sh 或已有代码约定的位置
2. **遵循代码风格**：与已有代码保持一致（命名、缩进、导入方式）
3. **最小改动**：只实现当前 feature 要求的内容，不做额外优化
4. **不添加注释**：除非用户明确要求，否则不写代码注释
5. **错误处理**：每个外部调用都要有错误处理，不要吞掉异常

### 按 feature category 的实现策略

| category | 实现重点 | 典型文件 |
|----------|---------|---------|
| **data_model** | 数据模型定义 + migration 脚本 + 数据校验 | models/、migrations/、schemas/ |
| **api** | 路由定义 + 请求处理 + 参数校验 + 错误响应 | routes/、controllers/、handlers/ |
| **ui** | 组件实现 + 样式 + 交互逻辑 + 状态管理（遵循 DESIGN.md 设计系统） | components/、pages/、views/ |
| **config** | 配置文件 + 环境变量 + 默认值 | config/、settings/、.env.example |
| **docs** | 文档内容 + 格式规范 | docs/、README |
| **test** | 测试工具/fixture/辅助代码 | tests/、__tests__/、conftest.py |

### 实现步骤

```
1. 确认要创建/修改的文件列表
2. 逐文件编写代码
3. 每个文件写完后，用 SearchReplace 编辑已有文件（而非重写整个文件）
4. 确保新增代码与已有代码的接口兼容
```

### 修复退回的代码

当 Auditor 退回代码时，上下文中会包含审查意见。修复步骤：

1. 读取 Auditor 的反馈意见
2. 定位需要修改的代码
3. 用 SearchReplace 精确修改（不要重写整个文件）
4. 重新运行测试确认修复有效
5. 更新 git commit

---

## 阶段三：测试编写（Test）

每个 feature 必须编写测试。没有测试的代码不予交付。

### 测试覆盖要求

| 覆盖维度 | 说明 | 优先级 |
|---------|------|--------|
| **正常路径** | 功能按预期工作的场景 | 必须 |
| **异常路径** | 输入错误、依赖失败、权限不足等 | 必须 |
| **边界条件** | 空值、最大值、最小值、特殊字符 | 必须 |
| **并发/竞态** | 同时操作、重复提交（如适用） | 建议 |

### 按 category 的测试策略

| category | 测试方式 | 示例 |
|----------|---------|------|
| **data_model** | 单元测试：创建/查询/更新/删除 + 字段校验 + 约束验证 | 测试唯一约束、外键约束、字段长度 |
| **api** | 集成测试：请求→响应 + 参数校验 + 错误码 + 边界输入 | 测试 200/400/404/500、空 body、超长字段 |
| **ui** | 组件测试：渲染 + 交互 + 状态变化（如适用） | 测试点击、输入、加载态、空态 |
| **config** | 配置加载测试：默认值 + 环境覆盖 + 缺失处理 | 测试配置缺失时的降级 |
| **docs** | 一般不需要测试 | — |
| **test** | 测试工具本身的测试 | 测试 fixture 是否正确 |

### 测试编写规范

1. **测试文件位置**：遵循项目已有的测试目录结构
2. **测试命名**：`test_<feature_id>_<scenario>_<expected_result>`
3. **独立性**：每个测试独立运行，不依赖其他测试的执行顺序
4. **可重复**：每次运行结果一致，不依赖外部状态
5. **有意义**：测试要验证真实行为，不是凑覆盖率

### 反面测试检测（非自欺欺人检测）

以下测试模式是无效的，必须避免：

| 反面模式 | 说明 | 正确做法 |
|---------|------|---------|
| 只测 happy path | 只测正常输入，不测异常 | 至少覆盖一个异常场景 |
| 断言过于宽泛 | `assert result is not None` | 断言具体的值或结构 |
| 测试实现细节 | 测试私有方法或内部变量 | 测试公开接口的行为 |
| 硬编码等待 | `time.sleep(5)` 后断言 | 用轮询或事件驱动 |
| Mock 一切 | 所有依赖都 Mock，测的是 Mock | 只 Mock 外部依赖，内部逻辑用真实调用 |

---

## 阶段四：本地验证（Verify）

代码写完后，必须通过本地验证才能提交。

### 验证流程（严格按顺序执行）

```
Step 1: RunCommand lint
  → 失败：修复代码，重新执行
  → 通过：继续

Step 2: RunCommand typecheck
  → 失败：修复代码，重新执行
  → 通过：继续

Step 3: RunCommand test
  → 失败：修复代码或测试，重新执行
  → 通过：继续

Step 4: 结构校验
  → 文件位置是否正确？
  → 命名是否规范？
  → 新增文件是否在正确的目录？
  → 失败：移动/重命名文件
  → 通过：继续
```

### 验证命令获取

如果不确定 lint/typecheck/test 的具体命令：

1. 查看 `package.json` 的 `scripts` 字段
2. 查看 `Makefile` 或 `justfile`
3. 查看 `pyproject.toml` 的工具配置
4. 如果都找不到，使用以下默认命令：

| 语言 | lint | typecheck | test |
|------|------|-----------|------|
| TypeScript/JavaScript | `npm run lint` | `npx tsc --noEmit` | `npm test` |
| Python | `ruff check .` | `mypy .` | `pytest` |
| Go | `golangci-lint run` | `go vet ./...` | `go test ./...` |

### 验证失败处理

- **lint 失败**：按 lint 提示修复，不要用 `// eslint-disable` 或 `# noqa` 绕过
- **typecheck 失败**：修复类型错误，不要用 `any` 或 `type: ignore` 绕过
- **test 失败**：分析失败原因——是代码 bug 还是测试写错了？修复正确的那个
- **结构校验失败**：移动文件到正确位置

---

## 阶段五：提交交付（Deliver）

验证通过后，提交代码。

### Git 提交规范

```
1. RunCommand: git add <修改的文件列表>
2. RunCommand: git commit -m "feat(F-XXX): 简短描述"
3. RunCommand: git tag feat/F-XXX-start
```

### Commit Message 格式

```
feat(F-XXX): 简短描述

- 具体变更1
- 具体变更2
```

### Tag 规范

| 时机 | Tag | 打tag者 |
|------|-----|--------|
| 代码实现完成 | `feat/F-XXX-start` | Builder |
| 确定性验证通过 | `feat/F-XXX-verified` | Orchestrator |
| 审查通过 | `feat/F-XXX-done` | Orchestrator |

### 交付输出

每个 feature 完成后，输出以下信息：

```markdown
## Feature 实现报告

### 基本信息
- **Feature ID**: F-XXX
- **Feature 描述**: [一句话描述]
- **Category**: [data_model/api/ui/config/docs/test]

### 文件变更
| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | src/xxx.ts | [功能说明] |
| 修改 | src/yyy.ts | [变更说明] |
| 新增 | tests/xxx.test.ts | [测试覆盖] |

### 验证结果
| 验证项 | 结果 | 备注 |
|--------|------|------|
| lint | ✅ 通过 | — |
| typecheck | ✅ 通过 | — |
| test | ✅ 通过 | X 个测试用例全部通过 |
| 结构校验 | ✅ 通过 | — |

### Git 信息
- **Commit**: `abc1234` feat(F-XXX): 简短描述
- **Tag**: `feat/F-XXX-start`

### 发现的问题（如有）
- [实现过程中发现的潜在问题或技术债务]
```

---

## 复杂度路由

不同复杂度的 feature 有不同的处理策略：

| 复杂度 | 判定条件 | 处理策略 |
|--------|---------|---------|
| **简单** | category 为 config/docs，0 依赖 | 直接实现，跳过 Auditor |
| **中等** | 1-2 依赖，category 为 api/ui/data_model | 完整流程（实现→验证→提交→审查） |
| **复杂** | 3+ 依赖，跨 category 联动 | 实现时拆分为多个子任务，逐个验证 |

### 简单 feature 的快速通道

对于 category 为 config 或 docs 的简单 feature：

1. 实现代码
2. 运行 lint（如有）
3. git commit + tag
4. 直接标记为 done，不需要 Auditor 审查

---

## 质量检查清单

代码提交前，逐项自查：

| # | 检查项 | 标准 |
|---|--------|------|
| 1 | 代码符合 lint 规则 | RunCommand lint 通过 |
| 2 | 类型检查通过 | RunCommand typecheck 通过 |
| 3 | 测试通过 | RunCommand test 通过 |
| 4 | 测试覆盖异常路径 | 非仅 happy path |
| 5 | 文件位置正确 | 符合项目目录结构 |
| 6 | 代码风格一致 | 与已有代码风格一致 |
| 7 | 无硬编码 | 配置项提取为常量或环境变量 |
| 8 | 错误处理完整 | 外部调用都有错误处理 |
| 9 | git commit 已提交 | 每个feature一个commit |
| 10 | git tag 已打 | feat/F-XXX-start |
| 11 | 无多余注释 | 除非用户要求 |
| 12 | 无 Mock 数据 | 测试用真实逻辑或合理的 fixture |

---

## 失败兜底策略

### feature 规格不清晰

如果 feature_list.json 中的描述不足以开始编码：

1. 列出缺失的信息项
2. 标注哪些可以合理推断、哪些必须确认
3. 对可推断项标注 **[推断]** 并给出推断依据
4. 对必须确认项，通过 AskUserQuestion 询问

### 技术栈不熟悉

如果项目使用的技术栈超出你的能力范围：

1. 尝试基于通用模式实现
2. 在实现报告中标注 **[技术风险]**
3. 建议人类审查该 feature 的代码

### 验证持续失败

如果 lint/typecheck/test 反复修复仍失败（超过 3 轮）：

1. 停止修复
2. 输出当前的错误信息和已尝试的修复方案
3. 标注 **[阻塞]** 并说明原因
4. 等待人类介入

---

## 参考文件

- **代码风格指南**：见 `references/code-style-guide.md`（各语言代码风格规范）
- **测试模板**：见 `references/test-templates.md`（各框架的测试代码模板）
