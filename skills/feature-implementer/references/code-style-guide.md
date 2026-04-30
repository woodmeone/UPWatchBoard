# 代码风格指南

## 通用原则

1. 遵循项目已有的代码风格（通过阅读已有代码确认）
2. 遵循语言/框架的社区惯例
3. 不添加注释（除非用户要求）
4. 配置项提取为常量或环境变量，不硬编码

## TypeScript / JavaScript

### 命名
- 变量/函数：camelCase
- 类/接口/类型：PascalCase
- 常量：UPPER_SNAKE_CASE
- 文件：kebab-case（组件文件 PascalCase）
- 私有成员：不加前缀，用 `private` 关键字

### 导入
- 使用 ES Module（import/export）
- 第三方库在前，项目内模块在后
- 避免使用 `* as` 导入

### 格式
- 缩进：2 空格
- 分号：按项目配置
- 字符串：单引号（按项目配置）
- 行宽：按 eslint/prettier 配置

### 错误处理
- 异步操作用 try/catch
- 不要吞掉异常（空 catch 块）
- 错误信息要具体，不要只抛 "Error"

## Python

### 命名
- 变量/函数：snake_case
- 类：PascalCase
- 常量：UPPER_SNAKE_CASE
- 文件/模块：snake_case
- 私有成员：单下划线前缀

### 导入
- 标准库 → 第三方库 → 项目内模块，各组之间空一行
- 避免使用 `from module import *`

### 格式
- 缩进：4 空格
- 行宽：88 字符（black 默认）
- 字符串：双引号（按项目配置）

### 错误处理
- 使用具体异常类型，不要裸 `except:`
- 异常信息要具体
- 使用 `raise ... from err` 保留异常链

## Go

### 命名
- 导出：PascalCase
- 未导出：camelCase
- 接口：以 `-er` 后缀（如 Reader, Writer）
- 文件：snake_case

### 格式
- 使用 `gofmt` 格式化
- 缩进：Tab
- 行宽：无硬限制

### 错误处理
- 显式检查 `if err != nil`
- 使用 `fmt.Errorf("context: %w", err)` 包装错误
- 不要 panic（除非不可恢复）
