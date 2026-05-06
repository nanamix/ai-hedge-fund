# Telegram Flow Alerts Design

Date: 2026-05-06

## Purpose

Build a small monitoring and notification workflow that checks portfolio and market flow during the day and sends concise Telegram summaries to the user. This is an investment decision support tool, not an auto-trading system.

The system must reinforce the user's operating rules:

- Long-only.
- No leveraged ETF re-entry.
- No FOMO buying.
- Model output is advisory only.
- Position bands, cash level, and risk limits override model recommendations.

## Scope

Initial scope is a scheduled summary alert, KST-based, five times per day:

- 09:00: Korea market open or early-session check.
- 12:30: Korea mid-session check.
- 16:00: Korea close check.
- 22:30: U.S. pre-market/open preparation check.
- 23:30: U.S. early-session check.

02:00 KST is explicitly excluded.

Out of scope for the first version:

- Automatic order placement.
- Direct Toss Securities trading integration.
- Intraday high-frequency monitoring.
- Personalized tax calculations.
- Full portfolio reconciliation from brokerage credentials.

## Architecture

Use a lightweight scheduled script first, with a path to grow into a background worker later.

Components:

- `flow_check`: gathers current market and portfolio signals.
- `rules_engine`: maps signals into user-safe labels such as `대기`, `보류`, `검토`, or `분할매수 후보`.
- `notifier`: sends the message through Hermes Agent when available, with direct Telegram Bot API as a fallback.
- `state_store`: keeps a small local JSON snapshot of the previous run so alerts can mention changes since the prior summary.
- `scheduler`: macOS `launchd` preferred, with cron as a fallback.

Configuration:

- Optional Hermes Agent endpoint or command configuration.
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- Optional watchlist and threshold settings

Secrets must live in `.env`, Hermes Agent configuration, or the user's existing local secret workflow. They must not be committed.

## Notification Transport

Preferred transport is Hermes Agent if it is already connected to Telegram in the user's environment. This keeps Telegram-specific credential handling out of the portfolio monitor and lets Hermes own delivery concerns.

Transport order:

1. Hermes Agent Telegram bridge.
2. Direct Telegram Bot API fallback.
3. Dry-run console output for local testing.

The monitor should build one normalized alert payload and pass it to whichever transport is enabled. If Hermes is configured, the monitor should not require direct `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID`.

Hermes integration needs one of these concrete interfaces before implementation:

- A local CLI command to send a message.
- A local HTTP endpoint to post a message.
- A file/dropbox style queue that Hermes watches.

If more than one is available, prefer the simplest interface that can be manually tested from the terminal.

Current status:

- User has requested Hermes Agent integration.
- Implementation is waiting on the concrete Hermes interface: CLI, HTTP endpoint, or file queue.
- Until that interface is confirmed, keep direct Telegram Bot API as a fallback path only.

## Watchlist

Start with the existing AI Hedge Fund MLX operating set:

- Core or comparison: `SPYM`, `SPY`
- Value/defensive complement: `SPYV`
- Growth tilt: `VUG`
- Individual stock: `AMZN`
- Theme/risk checks: `VOLT`, `TQQQ`
- Dollar parking: `SGOV`, optionally `BIL`, `TFLO`
- KRW parking and Korean ETFs: KOFR/CD money-market style ETFs, `KODEX AI반도체`, `RISE 미국AI클라우드인프라`

The first implementation may support U.S. tickers before Korean ETF symbols if data access for Korean ETFs is less reliable.

## Data Flow

1. Scheduler invokes the script at one of the five approved KST times.
2. Script loads configuration and user rules.
3. Script fetches prices and recent movement for the watchlist.
4. Script optionally runs or reads an `ai-hedge-fund` model summary when configured.
5. Rules engine classifies the current state:
   - `대기`: no action.
   - `보류`: model or price action is noisy or conflicting.
   - `검토`: worth reviewing, but no immediate order.
   - `분할매수 후보`: only if within target bands and not a chase.
6. Notifier sends one concise message through Hermes or Telegram fallback.
7. State store records the snapshot for next comparison.

## Message Format

Messages should be short and action-oriented:

```text
[AI Hedge Fund Flow] 2026-05-06 23:30 KST

요약: 미국장 초반 체크. 기본 판단은 보류.

주요 변화
- SPYM: ...
- VUG: ...
- AMZN: ...
- SGOV: ...

리스크 신호
- 레버리지 재진입 금지 유지
- AI/성장 테마 추격매수 주의

오늘 행동
- 신규 매수: 보류
- 대기자금: 유지
- 다음 체크: 내일 09:00
```

Do not send long model essays. The message should help the user act calmly.

## Rules

Hard rules:

- Do not recommend short positions.
- Do not recommend new leveraged ETF buys.
- Do not recommend immediate full reinvestment after selling.
- Do not recommend buying after sharp rises unless the planned split-buy rule still passes.
- If model opinions conflict, default to `보류`.
- If portfolio band data is missing, default to `검토` or `보류`, not `매수`.

Risk thresholds for the first implementation can be conservative and configurable:

- 1-day move over roughly 2% in core ETFs: mention.
- 1-day move over roughly 4% in growth/theme assets: mention.
- Any TQQQ watchlist rally: warn against FOMO, not a buy signal.
- Cash or parking allocation below target minimum: warn before any new equity purchase.

## Error Handling

- Missing Hermes and Telegram configuration: exit with a clear error and do not retry.
- Hermes delivery failure: use direct Telegram fallback if configured; otherwise fail visibly.
- Price API failure: send a degraded alert only if Telegram config works, clearly saying data was unavailable.
- Partial ticker failure: include only successful tickers and list missing symbols briefly.
- Rate limits: back off and keep the message short; avoid repeated notification spam.
- Duplicate run at same scheduled minute: state store should avoid sending identical alerts when possible.

## Testing

Unit tests:

- Message formatting.
- Rule classification.
- Missing config handling.
- State comparison.

Manual verification:

- Send a Hermes-routed Telegram test message when Hermes configuration is present.
- Send a direct Telegram test message only when fallback credentials are configured.
- Run one dry-run alert without network price fetch.
- Run one live alert with a small watchlist.
- Confirm no secrets are printed or committed.

## Implementation Notes

The first version should be a CLI script or module rather than a full app integration. It should be easy to run manually before enabling `launchd`.

Expected command shape:

```bash
python -m src.notifications.telegram_flow_check --dry-run
python -m src.notifications.telegram_flow_check
```

The schedule file should be created only after manual Telegram delivery works.

If Hermes Agent is used, the schedule file should be created only after a manual Hermes-to-Telegram delivery test works.

## Approval Status

Design approved by the user with this cadence:

- Use summary alerts, not hourly alerts.
- Exclude 02:00 KST.
- Proceed with the five daily KST checkpoints listed above.
- Prefer Hermes Agent for Telegram delivery when connected; keep direct Telegram as fallback.
- Hermes Agent integration has been requested and is pending interface confirmation.
