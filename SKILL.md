---
name: zuoge-crypto-query
description: Use this skill when the user wants to query crypto-trader account info, current positions, or trading context in Simplified Chinese, including requests like `查下账户`, `看看持仓`, `当前有哪些仓位`, `查 BTCUSDT`, or `查 trading context`.
---

# Zuoge Crypto Query

## Architecture Role

`zuoge-crypto-query` is the **eyes** of the trading system. It reads account state, positions, and trading context from the API. It does NOT generate or submit signals — that is the responsibility of `crypto-trader-workflow` (strategy brain) and `zuoge-crypto-trade` (hands).

When a user asks about trading decisions, strategy analysis, signal quality, or pipeline health, route to `crypto-trader-workflow` skill knowledge — not this skill. This skill only answers data-read questions: "what are my positions?", "what's my balance?", "show me the trading context for symbol X".

## Overview

Use this skill when the user wants to inspect account information, current positions, or a symbol trading context in Chinese.
This skill is query-only. It does not compose or submit trade signals.

Typical requests:

- `查下账户`
- `详细看下账户信息`
- `看看当前持仓`
- `当前有哪些仓位`
- `查 BTCUSDT`
- `查 BTCUSDT 的 trading context`

## Required Environment Variables

Before querying the API, read these env vars from the runtime environment:

| Variable | Example | Purpose |
|---|---|---|
| `ZUOGE_CRYPTO_BASE_URL` | `http://127.0.0.1:18000` | API server base URL |
| `ZUOGE_CRYPTO_API_KEY` | `zg-6cd...8359` | Bearer token for agent auth |

If `ZUOGE_CRYPTO_BASE_URL` is not set, reply with 暂无法获取账户信息.

## Authentication

All agent API calls require `Authorization: Bearer <ZUOGE_CRYPTO_API_KEY>` header.

## Data Source

Read from the API-key protected agent query endpoints with this priority:

- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/portfolio/snapshot` for account summary, current positions, and account-level risk overview
- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/positions` for the current position list; append `?strategy_id=<id>` when the user asks for one strategy's positions
- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/executions/recent?strategy_id=<id>` for one strategy's recent fills/trades
- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/strategy-risk-allocations/<id>` for one strategy's risk budget settings
- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/strategy/context` only when the user explicitly asks for trading context
- `GET ${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/strategy/context/{symbol}` only when the user explicitly asks about a specific symbol

When the user asks for one strategy's positions, fills/trades, risk budget, or context, every request must include that `strategy_id`. Do not answer a strategy-level question from whole-account `/portfolio/snapshot` or unfiltered executions.

If the caller already has JSON context, summarize that directly and do not re-fetch.

Authenticate agent requests with `ZUOGE_CRYPTO_API_KEY` using `Authorization: Bearer <key>` header. Do not use WebUI session cookies for this skill, and do not call non-`/api/v1/agent/` routes.

## Workflow

1. Read `ZUOGE_CRYPTO_BASE_URL` and `ZUOGE_CRYPTO_API_KEY` from env vars.
2. Decide whether the user wants account summary, position list, or symbol trading context.
3. If the user asked for positions, fetch `${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/positions`; if they specified a strategy, include `strategy_id`.
4. If the user did not ask for positions and did not specify a symbol, fetch `${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/portfolio/snapshot` only.
5. If the user asked for strategy fills/trades or risk budget, require a strategy ID and use `/agent/executions/recent?strategy_id=<id>` or `/agent/strategy-risk-allocations/<id>`.
6. If the user explicitly specified a symbol or asked for trading context, fetch `${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/strategy/context?strategy_id=<id>` or `${ZUOGE_CRYPTO_BASE_URL}/api/v1/agent/strategy/context/{symbol}?strategy_id=<id>` when a strategy ID is in scope.
7. Start with [references/query-reply-quickstart.zh-CN.md](references/query-reply-quickstart.zh-CN.md).
8. Reply in Simplified Chinese.
9. If the live API returns any error (503/unauthorized/not-configured) or `ZUOGE_CRYPTO_BASE_URL` is not set, reply with `暂无法获取账户信息` and do not fabricate.

If the user did not specify a symbol, do not surface any symbol-specific results in the final answer.
If the user only asked for account info or account overview, do not expand the `positions` list unless they explicitly asked to see positions or a detailed account breakdown.

## Progressive Disclosure

Read only:

- [references/query-reply-quickstart.zh-CN.md](references/query-reply-quickstart.zh-CN.md)

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
