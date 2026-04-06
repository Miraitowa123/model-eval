## Why

当前错误分布统计中将所有 HTTP 400 错误归为一类，过于宽泛，无法知道具体是什么类型的错误导致请求失败。实际上 DashScope API 会在 400 响应中返回具体的 `error.code` 字段标识错误类型，这些信息对分析问题很有价值，但目前被埋没在"HTTP_400"这个大类中无法体现。

## What Changes

- 修改 `draw-chart.py` 中的错误统计逻辑
- 对于状态为 `HTTP_400` 的响应，从原始响应 JSON 中提取 `error.code`
- 按不同的 `error.code` 分别统计计数
- 在错误分布堆叠图中，按具体错误 code 分开展示，替代原来单一的 HTTP_400

## Capabilities

### New Capabilities
- 无新增能力，只改进现有统计分析

### Modified Capabilities
- 无现有能力需求变更

## Impact

- `draw-chart.py`: 修改错误统计和绘图逻辑
