---
name: zuoge-crypto-query
description: Use this skill when the user wants to query crypto-trader account info, current positions, or trading review data in Simplified Chinese, including requests like `查下账户`, `看看持仓`, `当前有哪些仓位`, `复盘最近交易`, `复盘某策略`, or `看看最近为什么亏`.
---

# Zuoge Crypto Query

## Architecture Role

`zuoge-crypto-query` is the **eyes** of the trading system. It reads account state, positions, and review data. It does NOT generate or submit signals — that is the responsibility of `crypto-trader-workflow` (strategy brain) .

When a user asks to create, validate, improve, or submit a strategy/signal, route to `crypto-trader-workflow` skill knowledge — not this skill. This skill only answers data-read questions: "what are my positions?", "what's my balance?", "review recent trades", "why did this strategy lose money recently?".

## Overview

Use this skill when the user wants to inspect account information, current positions, or trading review data in Chinese.
This skill is query-only. It does not compose or submit trade signals.

Typical requests:

- `查下账户`
- `详细看下账户信息`
- `看看当前持仓`
- `当前有哪些仓位`
- `复盘最近交易`
- `复盘 workflow_distilled_funnel 最近 7 天`
- `看看最近为什么亏`

## Required Environment Variables

Before querying data, read these env vars from the runtime environment:

| Variable | Example | Purpose |
|---|---|---|
| `ZUOGE_CRYPTO_BASE_URL` | `http://127.0.0.1:18000` | API server base URL |
| `ZUOGE_CRYPTO_API_KEY` | `zg-6cd...8359` | Bearer token for agent auth |
| `ZUOGE_CRYPTO_DATABASE_URL` | `postgres://zuo:@localhost:5432/crypto_trader?sslmode=disable` | PostgreSQL URL for read-only review queries |

If `ZUOGE_CRYPTO_BASE_URL` is not set for account/position queries, reply with 暂无法获取账户信息.
If `ZUOGE_CRYPTO_DATABASE_URL` is not set for review queries, reply with 暂无法获取复盘数据.

## Authentication

All agent API calls require `Authorization: Bearer <ZUOGE_CRYPTO_API_KEY>` header.

## Data Source

For account and position queries, read from the API-key protected agent query endpoints with this priority:

- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/portfolio/snapshot` for account summary, current positions, and account-level risk overview
- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/positions` for the current position list; append `?strategy_id=<id>` when the user asks for one strategy's positions

When the user asks for one strategy's positions, every request must include that `strategy_id`. Do not answer a strategy-level position question from whole-account `/portfolio/snapshot`.

If the caller already has JSON context, summarize that directly and do not re-fetch.

Authenticate agent requests with `ZUOGE_CRYPTO_API_KEY` using `Authorization: Bearer <key>` header. Do not use WebUI session cookies for this skill, and do not call non-`/api/v1/agent/` routes.

For review/复盘 queries, read [references/review-data.zh-CN.md](references/review-data.zh-CN.md) and query PostgreSQL directly through `ZUOGE_CRYPTO_DATABASE_URL`. Do not use trading-context endpoints for review.

## Workflow

1. Read `ZUOGE_CRYPTO_BASE_URL` and `ZUOGE_CRYPTO_API_KEY` from env vars.
2. Decide whether the user wants account summary, position list, or review data.
3. If the user asked for positions, fetch `${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/positions`; if they specified a strategy, include `strategy_id`.
4. If the user did not ask for positions or review, fetch `${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/portfolio/snapshot` only.
5. If the user asked for review/复盘/performance attribution/loss reason, read [references/review-data.zh-CN.md](references/review-data.zh-CN.md), query PostgreSQL through `ZUOGE_CRYPTO_DATABASE_URL`, and summarize the result.
6. For non-review queries, start with [references/query-reply-quickstart.zh-CN.md](references/query-reply-quickstart.zh-CN.md).
7. Reply in Simplified Chinese.
8. If the live API returns any error (503/unauthorized/not-configured) or `ZUOGE_CRYPTO_BASE_URL` is not set, reply with `暂无法获取账户信息` and do not fabricate.
9. If the database query fails or `ZUOGE_CRYPTO_DATABASE_URL` is not set for review, reply with `暂无法获取复盘数据` and do not fabricate.

If the user did not specify a symbol, do not surface any symbol-specific results in the final answer.
If the user only asked for account info or account overview, do not expand the `positions` list unless they explicitly asked to see positions or a detailed account breakdown.

## Progressive Disclosure

Read only:

- [references/query-reply-quickstart.zh-CN.md](references/query-reply-quickstart.zh-CN.md)
- [references/review-data.zh-CN.md](references/review-data.zh-CN.md) only for review/复盘 requests

Avoid opening signal schema, payload template, OpenAPI, or signal-generation references in this skill.

## Output Rules

- Use Simplified Chinese.
- Translate `long/short` to `多头/空头`.
- Translate `cross/isolated` to `全仓/逐仓`.
- Format money and price fields as `$1234.56` or `-$48.60`.
- Format snapshot/update times as `YYYY-MM-DD HH:MM:SS` in Beijing time; never surface raw RFC3339/ISO timestamps like `2026-05-05T04:43:03.68039Z`.
- Do not force two decimal places onto quantities, leverage, counts, or ratios.
- Use `暂无数据` for missing fields.
- When the user asks only for `账户信息 / 账户快览 / 查下账户`, reply with account-level summary only. Do not append position details, symbol drill-downs, or optional next-step menus unless the user explicitly asks.
- For this user, keep the reply minimal and direct: one compact summary plus one concise risk sentence is preferred over extra explanation.
- **Never** include a "数据来源：" or "来源：" line in the reply. The response should look like it came directly from the trading system, not from an agent relay.

## Maintenance

After changing query templates or examples, run:

```bash
python3 scripts/validate_query_display_rules.py
```

### Consistency Check

当用户要求"重新学习"/"re-learn"此技能时，agent 必须调用 `skill_view()` 重新读取当前 SKILL.md 和引用文件的状态，不得从记忆或历史会话中摘要复述。技能内容可能已被用户就地修改（删除路由、裁剪 scope 等），agent 的记忆可能滞后。始终以 `skill_view()` 的实时返回为准。
