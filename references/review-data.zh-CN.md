# 复盘数据查询指南

## 用途

当用户要求 `复盘`、`交易回顾`、`策略表现`、`最近为什么亏`、`胜率/盈亏/拒绝原因`、`某策略最近 N 天表现` 时，使用本文件。

复盘只读数据库，不查 trading context，不提交信号，不修改任何数据。

## 连接方式

使用环境变量 `ZUOGE_CRYPTO_DATABASE_URL` 连接 PostgreSQL。只执行 `SELECT`。

推荐命令形态：

```bash
psql "$ZUOGE_CRYPTO_DATABASE_URL" -X -A -F $'\t' -v ON_ERROR_STOP=1 -c "<SQL>"
```

如果 `ZUOGE_CRYPTO_DATABASE_URL` 缺失或查询失败，回复 `暂无法获取复盘数据`。

## 复盘相关表

核心事实链：

- `signals`：策略信号与入场意图源头。关键字段：`signal_id`、`trace_id`、`venue`、`source`、`skill_name`、`symbol`、`side`、`confidence`、`signal_reason`、`status`、`created_at`、`expires_at`、`strategy_id`、`strategy_version`、`context_id`、`price_ref`、`quote_side`、`data_freshness_ms`、`max_data_age_ms`、`max_slippage_bps`。
- `signal_actions`：信号后的系统动作，适合复盘止盈、止损、反手、接管、平仓等动作。关键字段：`action_id`、`signal_id`、`symbol`、`position_side`、`action_type`、`action_source`、`status`、`trigger_type`、`trigger_rule_id`、`trigger_reason`、`risk_decision_id`、`runtime_id`、`position_id`、`guard_status`、`action_params_json`、`decided_at`。
- `risk_decisions`：风控结果。关键字段：`decision_id`、`signal_id`、`action_id`、`passed`、`action`、`risk_level`、`reasons_json`、`computed_order_notional`、`computed_position_size`、`checked_at`。
- `order_intents`：订单意图。关键字段：`intent_id`、`signal_id`、`risk_decision_id`、`symbol`、`side`、`position_side`、`order_type`、`quantity`、`reduce_only`、`leverage`、`margin_type`、`client_order_id`、`exchange_order_id`、`created_by`、`created_at`。
- `executions`：执行状态。关键字段：`execution_id`、`intent_id`、`signal_id`、`action_id`、`execution_status`、`error_code`、`error_message`、`requested_at`、`acknowledged_at`、`finished_at`。
- `fills`：成交与已实现盈亏。关键字段：`fill_id`、`execution_id`、`intent_id`、`signal_id`、`symbol`、`side`、`position_side`、`quantity`、`price`、`notional`、`commission`、`realized_pnl`、`leverage`、`margin_type`、`status`、`filled_at`。

复盘补充表：

- `strategy_signal_rejects`：信号入口拒绝，常用于统计未入库/未执行原因。关键字段：`strategy_id`、`signal_id`、`reason_code`、`reason`、`payload_json`、`rejected_at`。
- `strategy_decision_logs`：策略内部决策日志，适合分析为什么出/不出信号。关键字段：`decision_id`、`strategy_id`、`version`、`context_id`、`symbol`、`decision`、`side`、`score`、`reason`、`evidence_json`、`feature_quality`、`dependency_status_json`、`signal_id`、`created_at`。
- `strategy_decision_log_rollups`：策略决策日志聚合，适合快速看决策分布。关键字段：`bucket_start`、`bucket_minutes`、`strategy_id`、`version`、`symbol`、`decision`、`side`、`reason`、`count`、`signal_count`、`sample_context_id`、`sample_signal_id`。
- `position_plan_runtimes`：持仓计划运行状态，适合复盘入场、止盈、移动止损、冷却和接管。关键字段：`signal_id`、`root_signal_id`、`parent_signal_id`、`owner_strategy_id`、`owner_strategy_version`、`symbol`、`position_side`、`entry_filled_at`、`last_block_reason_code`、`last_block_reason`、`effective_stop_price`、`pending_take_profit_targets_json`、`hit_take_profit_indexes_json`、`trailing_activated`、`add_position_count`、`remaining_position_ratio`、`runtime_status`、`cooldown_until`、`updated_at`。
- `portfolio_snapshots`：账户权益曲线。关键字段：`venue`、`equity`、`available_cash`、`total_exposure`、`open_positions`、`updated_at`。
- `execution_position_basis`：当前持仓成本与名义价值，只代表当前状态，不代表历史成交。
- `strategy_feedback_reports`：已生成的复盘报告。关键字段：`strategy_id`、`version`、`symbol`、`period_start`、`period_end`、`metrics_json`、`dimensions_json`、`suggestions_json`、`created_at`。
- `historical_market_snapshots`：历史行情快照，适合补充行情背景。关键字段：`symbol`、`data_type`、`source_time`、`ttl_ms`、`status`、`payload_json`。
- `audit_events`：审计事件，适合按 `trace_id` 或资源反查一次交易链路中的系统事件。

策略生命周期相关表：

- `strategies`、`strategy_versions`、`strategy_candidates`、`strategy_reviews`、`strategy_backtest_runs`、`strategy_deployments`、`strategy_status`：用于解释某个策略版本、候选、回测、审批、部署状态。

配置与风险预算相关表：

- `strategy_risk_allocations`：策略级资金与仓位预算，适合解释某策略为什么被限额。关键字段：`strategy_id`、`venue`、`enabled`、`allocation_pct`、`max_order_notional_pct`、`max_symbol_exposure_pct`、`max_total_exposure_pct`、`max_positions`、`max_add_count`、`updated_at`。
- `risk_limit_configs`：全局风控配置历史，适合解释系统级限额变化。

## 查询参数规则

- 默认时间窗口：最近 7 天。
- 用户说“最近 N 天”时使用 `now() - interval '<N> days'`。
- 用户指定 `strategy_id` 时，所有核心查询都加 `s.strategy_id = '<id>'`；拒绝表用 `r.strategy_id = '<id>'`；决策日志用 `strategy_id = '<id>'`。
- 用户指定 `symbol` 时，对 `signals/fills/decision_logs/reject payload` 都按大写 symbol 过滤。
- 需要 version 时优先用 `signals.strategy_version`、`strategy_decision_logs.version`、`strategy_feedback_reports.version`。
- 时间输出前按北京时间格式化：`to_char(ts AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS')`。

## AI 复盘最小数据包

一次复盘至少给 AI 准备这些数据：

- 总览指标：信号数、执行数、拒绝数、成交数、胜率、已实现盈亏、手续费。
- 亏损明细：最近亏损成交，包含 `signal_reason`、风控动作、执行状态、价格、数量、手续费。
- 阻塞原因：`strategy_signal_rejects.reason_code/reason` 和 `risk_decisions.reasons_json` 的 Top 分布。
- 策略内部决策：`strategy_decision_logs` 或 `strategy_decision_log_rollups` 的 decision/reason/feature_quality 分布。
- 权益变化：`portfolio_snapshots` 在窗口内的首尾权益、最大/最小权益、敞口范围。
- 运行状态：`position_plan_runtimes` 的 active/cooldown/blocked 状态、止盈命中、剩余仓位比例。
- 配置背景：策略级 `strategy_risk_allocations`，必要时补全局 `risk_limit_configs`。

复盘结论优先基于已成交和已拒绝事实；不要把当前持仓成本表当成历史表现。

## SQL 模板

### 总览指标

```sql
WITH filtered_signals AS (
  SELECT *
  FROM signals s
  WHERE s.created_at >= now() - interval '7 days'
    AND ($$STRATEGY_ID$$ = '' OR s.strategy_id = $$STRATEGY_ID$$)
    AND ($$SYMBOL$$ = '' OR s.symbol = $$SYMBOL$$)
),
fill_stats AS (
  SELECT
    COUNT(*) AS fill_count,
    COALESCE(SUM(f.realized_pnl), 0) AS realized_pnl,
    COALESCE(SUM(f.commission), 0) AS commission,
    COUNT(*) FILTER (WHERE f.realized_pnl > 0) AS winning_fills,
    COUNT(*) FILTER (WHERE f.realized_pnl < 0) AS losing_fills,
    COALESCE(SUM(f.notional), 0) AS traded_notional
  FROM fills f
  JOIN filtered_signals s ON s.signal_id = f.signal_id AND s.venue = f.venue
)
SELECT
  COUNT(*) AS signal_count,
  COUNT(*) FILTER (WHERE status = 'rejected') AS rejected_count,
  COUNT(*) FILTER (WHERE status = 'executed') AS executed_count,
  ROUND((SELECT realized_pnl FROM fill_stats)::numeric, 6) AS realized_pnl,
  ROUND((SELECT commission FROM fill_stats)::numeric, 6) AS commission,
  (SELECT fill_count FROM fill_stats) AS fill_count,
  (SELECT winning_fills FROM fill_stats) AS winning_fills,
  (SELECT losing_fills FROM fill_stats) AS losing_fills,
  CASE WHEN (SELECT fill_count FROM fill_stats) > 0
    THEN ROUND((SELECT winning_fills FROM fill_stats)::numeric / (SELECT fill_count FROM fill_stats), 4)
    ELSE 0
  END AS fill_win_rate,
  CASE WHEN COUNT(*) > 0
    THEN ROUND(COUNT(*) FILTER (WHERE status = 'rejected')::numeric / COUNT(*), 4)
    ELSE 0
  END AS signal_rejection_rate
FROM filtered_signals;
```

把 `$$STRATEGY_ID$$` 和 `$$SYMBOL$$` 替换为 SQL 字符串字面量，例如 `''`、`'workflow_distilled_funnel'`、`'BTCUSDT'`。

### 最近成交明细

```sql
SELECT
  to_char(f.filled_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS filled_at,
  s.strategy_id,
  s.strategy_version,
  f.symbol,
  f.position_side,
  f.side,
  f.quantity,
  f.price,
  f.notional,
  f.commission,
  f.realized_pnl,
  s.confidence,
  s.signal_reason,
  rd.action AS risk_action,
  rd.risk_level,
  e.execution_status
FROM fills f
JOIN signals s ON s.signal_id = f.signal_id AND s.venue = f.venue
LEFT JOIN order_intents oi ON oi.intent_id = f.intent_id
LEFT JOIN risk_decisions rd ON rd.decision_id = oi.risk_decision_id
LEFT JOIN executions e ON e.execution_id = f.execution_id
WHERE f.filled_at >= now() - interval '7 days'
  AND ($$STRATEGY_ID$$ = '' OR s.strategy_id = $$STRATEGY_ID$$)
  AND ($$SYMBOL$$ = '' OR f.symbol = $$SYMBOL$$)
ORDER BY f.filled_at DESC
LIMIT 50;
```

### 拒绝原因

```sql
SELECT reason_code, reason, COUNT(*) AS count
FROM strategy_signal_rejects r
WHERE r.rejected_at >= now() - interval '7 days'
  AND ($$STRATEGY_ID$$ = '' OR r.strategy_id = $$STRATEGY_ID$$)
  AND ($$SYMBOL$$ = '' OR COALESCE(r.payload_json->>'symbol', '') = $$SYMBOL$$)
GROUP BY reason_code, reason
ORDER BY count DESC, reason_code ASC
LIMIT 20;
```

### 风控拒绝/降级原因

```sql
SELECT
  rd.action,
  rd.risk_level,
  rd.reasons_json,
  COUNT(*) AS count
FROM risk_decisions rd
JOIN signals s ON s.signal_id = rd.signal_id AND s.venue = rd.venue
WHERE rd.checked_at >= now() - interval '7 days'
  AND ($$STRATEGY_ID$$ = '' OR s.strategy_id = $$STRATEGY_ID$$)
  AND ($$SYMBOL$$ = '' OR s.symbol = $$SYMBOL$$)
GROUP BY rd.action, rd.risk_level, rd.reasons_json
ORDER BY count DESC
LIMIT 30;
```

### 策略决策分布

```sql
SELECT
  decision,
  side,
  reason,
  feature_quality,
  COUNT(*) AS count,
  MIN(to_char(created_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS')) AS first_seen,
  MAX(to_char(created_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS')) AS last_seen
FROM strategy_decision_logs
WHERE created_at >= now() - interval '7 days'
  AND ($$STRATEGY_ID$$ = '' OR strategy_id = $$STRATEGY_ID$$)
  AND ($$SYMBOL$$ = '' OR symbol = $$SYMBOL$$)
GROUP BY decision, side, reason, feature_quality
ORDER BY count DESC
LIMIT 30;
```

### 持仓计划运行状态

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
WHERE updated_at >= now() - interval '7 days'
  AND ($$STRATEGY_ID$$ = '' OR owner_strategy_id = $$STRATEGY_ID$$)
  AND ($$SYMBOL$$ = '' OR symbol = $$SYMBOL$$)
ORDER BY updated_at DESC
LIMIT 50;
```

### 策略风险预算

```sql
SELECT
  strategy_id,
  venue,
  enabled,
  allocation_pct,
  max_order_notional_pct,
  max_symbol_exposure_pct,
  max_total_exposure_pct,
  max_positions,
  max_add_count,
  to_char(updated_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS updated_at
FROM strategy_risk_allocations
WHERE $$STRATEGY_ID$$ <> ''
  AND strategy_id = $$STRATEGY_ID$$
ORDER BY updated_at DESC;
```

### 账户权益变化

```sql
SELECT
  to_char(updated_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS updated_at,
  venue,
  equity,
  available_cash,
  total_exposure,
  open_positions
FROM portfolio_snapshots
WHERE updated_at >= now() - interval '7 days'
ORDER BY updated_at DESC
LIMIT 200;
```

### 已生成复盘报告

```sql
SELECT
  report_id,
  strategy_id,
  version,
  symbol,
  to_char(period_start AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS period_start,
  to_char(period_end AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS period_end,
  metrics_json,
  dimensions_json,
  suggestions_json,
  to_char(created_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD HH24:MI:SS') AS created_at
FROM strategy_feedback_reports
ORDER BY created_at DESC
LIMIT 20;
```

## 回复结构

复盘回复保持紧凑：

```md
最近 {{days}} 天复盘如下：

- 信号数：{{signal_count}}，执行数：{{executed_count}}，拒绝数：{{rejected_count}}
- 成交数：{{fill_count}}，胜率：{{fill_win_rate}}，已实现盈亏：{{realized_pnl}}，手续费：{{commission}}
- 主要亏损来源：{{loss_source}}
- 主要拒绝/阻塞原因：{{reject_or_risk_reason}}
- 需要关注：{{review_note}}
```

不要输出原始 SQL，除非用户明确要求。
