## Context

当前评估流程：
1. `eval-script.py` 调用模型 API，将结果保存到 `response_body.xlsx`
   - "状态" 列只记录 `HTTP_XXX` 状态码
   - "原始响应" 列存储完整 JSON 响应
2. `draw-chart.py` 按状态分类统计并绘制堆叠条形图展示错误分布

问题：所有 400 错误都统计在一起，无法区分具体错误类型。实际上 DashScope API 在 400 响应中返回了 `error.code`，包含具体错误类型信息。

## Goals / Non-Goals

**Goals:**
- 在错误分布图中按 `error.code` 对 400 错误细分展示
- 不改变原始数据结构，只在绘图统计时进行解析
- 保持原有其他错误分类不变（HTTP_429, no_tool_call, REQUEST_ERROR）

**Non-Goals:**
- 不修改评估脚本（eval-script.py）
- 不改变存储格式，不需要提前预处理数据
- 不合并其他错误类型

## Decisions

### 决策 1：在 draw-chart.py 统计阶段动态解析
**选择**: 在绘图统计时解析 `原始响应` 列提取 `error.code`，而不是修改评估脚本提前存储。
**理由**:
- 现有数据文件已经包含了所需信息，无需重新评估运行
- 对于没有 400 错误的数据文件也不会有影响
- 保持评估脚本和绘图脚本职责分离

### 决策 2：保持原有其他错误分类不变
**选择**: 只拆分 HTTP_400 分类，原来的 HTTP_429, no_tool_call, REQUEST_ERROR 保持不变。
**理由**:
- 这些分类已经比较明确，无需细分
- HTTP_429 本身就是明确的速率限制
- no_tool_call 和 REQUEST_ERROR 分类清晰

### 决策 3：处理异常情况
**选择**:
- 如果解析 JSON 失败，归类为 `parse_failed`
- 如果没有 `error.code`，归类为 `unknown_code`

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 解析会增加一点运行时间 | 数据量不大（几百行），影响可以忽略 |
| 原始响应为空或不是 JSON | 通过 try/except 捕获，归类到 fallback 分类 |
| 不同平台错误 code 格式不同 | 目前只针对 Dashscope 兼容模式，格式统一 |
