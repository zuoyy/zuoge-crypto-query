# 每日复盘日报 SQL 查询集

用于定时任务（cron job）生成每日 08:00→次日 08:00（北京时间）的交易复盘。

## 时间范围

```sql
start_time := date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
end_time   := date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
```

所有 WHERE 条件统一使用：

```
xxx >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
AND xxx < date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
```

## 查询 1：总览指标（按 exchange_order_id 聚合）

核心规则：一个币安订单（exchange_order_id）可能产生多笔成交，按 exchange_order_id 聚合，每单算一笔"交易"。

```sql
WITH review_signals AS (
  SELECT * FROM signals s
  WHERE s.created_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
    AND s.created_at < date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
),
order_aggregated AS (
  SELECT
    MIN(f.signal_id) AS signal_id,
    oi.exchange_order_id,
    SUM(f.realized_pnl) AS order_pnl,
    SUM(f.commission) AS order_commission,
    SUM(f.notional) AS order_notional,
    MIN(f.filled_at) AS first_fill_at,
    MAX(f.filled_at) AS last_fill_at
  FROM fills f
  JOIN review_signals s ON s.signal_id = f.signal_id AND s.venue = f.venue
  LEFT JOIN order_intents oi ON oi.intent_id = f.intent_id
  WHERE f.filled_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
    AND f.filled_at < date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
  GROUP BY oi.exchange_order_id
),
executed_signal_ids AS (
  SELECT DISTINCT signal_id FROM order_aggregated
),
rejected_counts AS (
  SELECT COUNT(*) AS reject_count
  FROM strategy_signal_rejects r
  WHERE r.rejected_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
    AND r.rejected_at < date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
)
SELECT
  COUNT(*) AS signal_count,
  (SELECT COUNT(*) FROM executed_signal_ids) AS executed_signal_count,
  (SELECT reject_count FROM rejected_counts) AS rejected_count,
  COUNT(*) FILTER (WHERE order_pnl > 0) AS winning_orders,
  COUNT(*) FILTER (WHERE order_pnl < 0) AS losing_orders,
  COUNT(*) FILTER (WHERE order_pnl = 0) AS breakeven_orders,
  COUNT(*) AS total_orders,
  ROUND(COALESCE(SUM(order_pnl), 0)::numeric, 6) AS realized_pnl,
  ROUND(COALESCE(SUM(order_commission), 0)::numeric, 6) AS commission,
  ROUND(COALESCE(SUM(order_notional), 0)::numeric, 2) AS traded_notional,
  CASE WHEN COUNT(*) FILTER (WHERE order_pnl <> 0) > 0
    THEN ROUND(
      (COUNT(*) FILTER (WHERE order_pnl > 0))::numeric /
      (COUNT(*) FILTER (WHERE order_pnl <> 0)),
      4
    )
    ELSE 0
  END AS win_rate_ex_breakeven,
  CASE WHEN COUNT(*) > 0
    THEN ROUND(
      (COUNT(*) FILTER (WHERE order_pnl > 0))::numeric / COUNT(*),
      4
    )
    ELSE 0
  END AS win_rate_raw
FROM order_aggregated;
```

> **胜率说明**：win_rate_ex_breakeven（排除平推单）= 赢单数÷(赢单+亏单)，是主指标。win_rate_raw（含平推）= 赢单数÷总订单。

## 查询 2：成交明细（按订单聚合，展示每单净盈亏）

注意：signals 表没有 `position_side`，需要从 fills 聚合中获取。

```sql
WITH review_signals AS (
  SELECT * FROM signals s
  WHERE s.created_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
    AND s.created_at < date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
)
SELECT
  to_char(AGG.first_fill_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS first_filled_at,
  to_char(AGG.last_fill_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS last_filled_at,
  AGG.exchange_order_id,
  s.strategy_id,
  s.symbol,
  AGG.position_side,
  s.side,
  AGG.order_notional,
  AGG.order_commission,
  AGG.order_pnl,
  s.signal_reason
FROM (
  SELECT
    MIN(f.signal_id) AS signal_id,
    oi.exchange_order_id,
    SUM(f.realized_pnl) AS order_pnl,
    SUM(f.commission) AS order_commission,
    SUM(f.notional) AS order_notional,
    MIN(f.filled_at) AS first_fill_at,
    MAX(f.filled_at) AS last_fill_at,
    MAX(f.position_side) AS position_side  -- position_side 从 fills 取，signals 表没有此字段
  FROM fills f
  JOIN review_signals s ON s.signal_id = f.signal_id AND s.venue = f.venue
  LEFT JOIN order_intents oi ON oi.intent_id = f.intent_id
  WHERE f.filled_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
    AND f.filled_at < date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
  GROUP BY oi.exchange_order_id
) AGG
JOIN signals s ON s.signal_id = AGG.signal_id
ORDER BY AGG.order_pnl ASC
LIMIT 50;
```

## 查询 3：信号拒绝原因

```sql
SELECT reason_code, reason, COUNT(*) AS count
FROM strategy_signal_rejects r
WHERE r.rejected_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
  AND r.rejected_at < date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
GROUP BY reason_code, reason
ORDER BY count DESC, reason_code ASC
LIMIT 20;
```

## 查询 4：风控决策分布

```sql
SELECT
  rd.action,
  rd.risk_level,
  rd.reasons_json,
  COUNT(*) AS count
FROM risk_decisions rd
JOIN signals s ON s.signal_id = rd.signal_id AND s.venue = rd.venue
WHERE rd.checked_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
  AND rd.checked_at < date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
GROUP BY rd.action, rd.risk_level, rd.reasons_json
ORDER BY count DESC
LIMIT 20;
```

## 查询 5：账户权益变化

```sql
SELECT
  to_char(updated_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS updated_at,
  venue,
  equity,
  available_cash,
  total_exposure,
  open_positions
FROM portfolio_snapshots
WHERE updated_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
  AND updated_at < date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
ORDER BY updated_at ASC
LIMIT 500;
```

## 查询 5b：权益汇总（首尾、极值）

```sql
WITH snapshots AS (
  SELECT
    updated_at,
    equity,
    total_exposure
  FROM portfolio_snapshots
  WHERE updated_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai' - interval '1 day') + interval '8 hours'
    AND updated_at < date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') + interval '8 hours'
  ORDER BY updated_at ASC
)
SELECT
  to_char((SELECT updated_at FROM snapshots ORDER BY updated_at ASC LIMIT 1) AT TIME ZONE 'Asia/Shanghai', 'MM-DD HH24:MI') AS open_at,
  ROUND((SELECT equity FROM snapshots ORDER BY updated_at ASC LIMIT 1)::numeric, 2) AS open_equity,
  to_char((SELECT updated_at FROM snapshots ORDER BY updated_at DESC LIMIT 1) AT TIME ZONE 'Asia/Shanghai', 'MM-DD HH24:MI') AS close_at,
  ROUND((SELECT equity FROM snapshots ORDER BY updated_at DESC LIMIT 1)::numeric, 2) AS close_equity,
  ROUND((SELECT MIN(equity) FROM snapshots)::numeric, 2) AS min_equity,
  to_char((SELECT updated_at FROM snapshots WHERE equity = (SELECT MIN(equity) FROM snapshots) ORDER BY updated_at LIMIT 1) AT TIME ZONE 'Asia/Shanghai', 'MM-DD HH24:MI') AS min_eq_at,
  ROUND((SELECT MAX(equity) FROM snapshots)::numeric, 2) AS max_equity,
  to_char((SELECT updated_at FROM snapshots WHERE equity = (SELECT MAX(equity) FROM snapshots) ORDER BY updated_at LIMIT 1) AT TIME ZONE 'Asia/Shanghai', 'MM-DD HH24:MI') AS max_eq_at,
  ROUND((SELECT MIN(total_exposure) FROM snapshots)::numeric, 2) AS min_exposure,
  ROUND((SELECT MAX(total_exposure) FROM snapshots)::numeric, 2) AS max_exposure;
```

## 查询 6：当前持仓状态

```sql
SELECT
  owner_strategy_id,
  owner_strategy_version,
  symbol,
  position_side,
  runtime_status,
  add_position_count,
  remaining_position_ratio,
  trailing_activated,
  effective_stop_price,
  hit_take_profit_indexes_json,
  last_block_reason_code,
  last_block_reason,
  to_char(entry_filled_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS entry_filled_at,
  to_char(updated_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS updated_at
FROM position_plan_runtimes
WHERE runtime_status IN ('active', 'cooldown', 'blocked')
ORDER BY updated_at DESC
LIMIT 20;
```

## 复盘输出模板

```
📊 交易复盘 | {start_month}月{start_day}日 08:00 → {end_month}月{end_day}日 08:00

📈 总览
- 信号数：{signal_count}，有成交信号：{executed_signal_count}，拒绝数：{rejected_count}
- 订单数：{total_orders}，胜率：{win_rate_ex_breakeven}（含平推 {win_rate_raw}），盈亏：{realized_pnl}，手续费：{commission}
- 交易额：{traded_notional}
- 策略：{strategy_name}
- 起始权益：$X → 当前权益：$Y
- 日内最低：$X（时间）→ 最高：$Y（时间）
- 敞口范围：$X ~ $Y
- 日内损益：+$Z

🔍 亏损明细
（按订单聚合，列出最大亏损订单，含 symbol / side / pnl / reason）

⛔ 拒绝/风控 Top
- {reason_code}: {reason} × {count}
...

📌 当前持仓
（列出 active 持仓状态，如无则写"无 active 持仓"）

⚠️ 关注点
（总结值得注意的问题或机会，例如：某策略/某方向集中亏损、胜率分化、权益偏离、风控行为异常等）
```

## 注意点

1. 使用 `psql "$ZUOGE_CRYPTO_DATABASE_URL" -X -A -F $'\\t' -v ON_ERROR_STOP=1 -c "<SQL>"` 执行查询。
2. 所有时间按北京时间（Asia/Shanghai）输出。
3. 胜率优先使用 win_rate_ex_breakeven（排除平推单），括号备注 win_rate_raw（含平推）。
4. 权益变化可能远大于成交盈亏——差额来自跨周期未实现盈亏或前周期持仓退出，需单独说明。
