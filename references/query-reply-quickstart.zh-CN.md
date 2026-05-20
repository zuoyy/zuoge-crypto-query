# 查询回复快速指南

## 用途

当用户只是要查询账户或持仓列表时，只看这份文件即可。
默认不要继续读取信号生成 schema、OpenAPI、设计文档、few-shot 或大样例。
当用户要求复盘、策略表现、盈亏归因或拒绝原因时，改读 [review-data.zh-CN.md](review-data.zh-CN.md)。

## 环境变量

| 变量 | 示例 | 用途 |
|---|---|---|
| `ZUOGE_CRYPTO_BASE_URL` | `http://127.0.0.1:18000` | API 地址 |
| `ZUOGE_CRYPTO_API_KEY` | `zg-6cd...8359` | Bearer token |

认证方式：`Authorization: Bearer <ZUOGE_CRYPTO_API_KEY>`

## 数据来源

- 用户只问账户、账户快览、账户风险概况时，优先使用 `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/portfolio/snapshot`
- 用户问当前持仓、持仓列表、某个策略的持仓时，使用 `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/positions`
- 如果用户指定策略 ID，给持仓接口追加 `?strategy_id=<id>`，例如 `/api/v1/agent/positions?strategy_id=workflow_distilled_funnel`
- 所有请求使用 `ZUOGE_CRYPTO_API_KEY` 通过 `Authorization: Bearer <key>` 认证
- 如果调用方已经持有 JSON，就直接总结，不重复请求

## 先判定意图

- 用户只问账户：走 `账户快览`，除非明确要求详细
- 用户问持仓列表：走 `持仓列表标准版`，除非明确要求快速或详细；如果指定策略，只统计该策略名下持仓

## 严格边界

- 用户没有指定 `symbol` 时，只输出账户快览或账户概览，不要追加任何"探针结果""补一条某标的情况""顺手看下 BTCUSDT"之类内容
- 用户只说"查询账户信息""查询账户快览""查下账户"时，默认只输出账户级摘要；即使底层 `snapshot` 带有 `positions`，也不要展开持仓明细
- 只有用户明确要求"看看持仓""列出持仓""当前有哪些仓位""详细账户信息"时，才展开 `positions` 列表
- 不要调用或输出 trading context；如果用户明确要求 trading context，回复：`当前查询技能不再读取 trading context，可以改查账户、持仓或复盘数据。`
- 用户只给标的如 `查 BTCUSDT` 时，只能从当前持仓里筛这个标的；不要补行情、特征、上下文判断
- **不要输出"数据来源""来源"之类的行**，回复应该是纯交易系统风格

## 展示规则

- 金额和价格类字段默认按 `USDT` 展示成 `$1234.56`
- 负数金额写成 `-$48.60`
- 时间字段要格式化后再展示，默认写成 `YYYY-MM-DD HH:MM:SS`，按北京时间理解，不要直接输出后端原始 RFC3339/ISO 字符串，如 `2026-05-05T04:43:03.68039Z`
- `数量`、`杠杆`、`持仓数`、比例字段不强制两位小数
- `long/short` 译为 `多头/空头`
- `cross/isolated` 译为 `全仓/逐仓`
- 缺失字段写 `暂无数据`

## 账户快览模版

```md
当前账户快览如下：

- 账户权益：{{equity}}
- 可用资金：{{available_cash}}
- 总敞口：{{total_exposure}}
- 浮动盈亏：{{unrealized_pnl}}
- 当前持仓数：{{open_positions}}
- 账户快照时间：{{updated_at}}
- 风险提示：{{risk_note}}
```

## 持仓列表标准版模版

```md
当前持仓列表如下：

- 持仓数量：{{position_count}}
- 总持仓敞口：{{total_position_notional}}

持仓明细：

1. {{symbol}} | {{side}} | 数量 {{quantity}} | 均价 {{entry_price}} | 未实现盈亏 {{unrealized_pnl}} | 杠杆 {{leverage}} | 保证金模式 {{margin_type}}

结论：

- 主要持仓风险：{{risk_note}}
```

## 最小字段提示

- 账户快览：只需要 `equity`、`available_cash`、`total_exposure`、`unrealized_pnl`、`open_positions`、`updated_at`
- 持仓列表：使用 `/agent/positions` 的 `items`，只需要 `symbol`、`position_side`、`quantity`、`avg_entry_price`、`unrealized_pnl`、`leverage`、`margin_type`、`owner_strategy_id`

## 最小字段映射

- `账户权益` <- `snapshot.equity`
- `可用资金` <- `snapshot.available_cash`
- `总敞口` <- `snapshot.total_exposure`
- `浮动盈亏` <- `snapshot.unrealized_pnl`
- `当前持仓数` <- `snapshot.open_positions`
- `账户快照时间` <- `snapshot.updated_at`
- `上次更新时间` <- `snapshot.updated_at`

## 常见回复示例

### 账户快览

```md
当前账户快览如下：

- 账户权益：$10234.56
- 可用资金：$8450.12
- 总敞口：$1784.44
- 浮动盈亏：$125.40
- 当前持仓数：2
- 账户快照时间：2026-05-04 16:10:00
- 风险提示：当前账户已有在途风险敞口，新增仓位前应先确认总风险占用。
```

### 持仓列表标准版

```md
当前持仓列表如下：

- 持仓数量：2
- 总持仓敞口：$12660.00

持仓明细：

1. BTCUSDT | 多头 | 数量 0.12 | 均价 $63850.00 | 未实现盈亏 $125.40 | 杠杆 3 | 保证金模式 全仓
2. ETHUSDT | 空头 | 数量 1.8 | 均价 $3120.00 | 未实现盈亏 -$48.60 | 杠杆 2 | 保证金模式 逐仓

结论：

- 主要持仓风险：ETH 当前处于浮亏，且账户已有多个方向暴露，建议关注整体回撤风险。
```

### Trading Context 不再支持

```md
当前查询技能不再读取 trading context，可以改查账户、持仓或复盘数据。
```
