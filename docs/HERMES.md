# Hermes Command Guide

Use this as a paste-friendly command sheet for Hermes Workspace. These commands are meant to steer Hermes toward the `hermes_trader` MCP tools instead of asking it to guess.

## Baseline Checks

```text
Use hermes_trader get_portfolio_state and summarize my paper account.
```

```text
Use hermes_trader get_open_positions and summarize open positions, side, quantity, entry, current value, and unrealized P/L.
```

```text
Use hermes_trader get_orders with status=open and explain whether any accepted orders have not filled yet.
```

```text
Use hermes_trader get_market_clock and explain whether paper market orders should fill now or wait for market open.
```

## Symbol Universe

```text
Use hermes_trader list_symbols with enabled=true and show the active trading universe.
```

```text
Use hermes_trader add_symbol for GOOGL in universe=core, enabled=true, validate_with_alpaca=true.
```

```text
Use hermes_trader disable_symbol for GOOGL with notes="disabled while reviewing short thesis quality".
```

```text
Use hermes_trader import_symbols for ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GOOGL"] into universe=core, enabled=true, validate_with_alpaca=true.
```

## Discovery And Scanning

```text
Use hermes_trader scan_trade_candidates with strategy=trend_following, max_symbols=5, qty=1, auto_size=true. Explain why each candidate ranked highly.
```

```text
Use hermes_trader scan_trade_candidates with strategy=breakout, max_symbols=5, qty=1, auto_size=true. Include trend regime, recent returns, and whether price is near highs.
```

```text
Use hermes_trader discover_trade_candidates with strategy=trend_following, max_symbols=3, qty=1, auto_size=true. Do not run a trade yet.
```

```text
Use hermes_trader discover_trade_candidates with strategy=random_baseline, max_symbols=3, qty=1, auto_size=true. Treat this as a baseline/debug result, not a real recommendation.
```

## Market Data And Reports

```text
Use hermes_trader get_market_bars for symbols=["AAPL", "MSFT", "NVDA"], timeframe=1Day, days=120, persist=true. Summarize trend and volatility.
```

```text
Use hermes_trader chart_symbol for symbol=GOOGL, timeframe=1Day, days=180, persist=true.
```

`chart_symbol` returns `assistant_response_markdown`, which already includes the PNG chart image and a short summary. Use it by default; do not ask separately for `chat_markdown_image`.

```text
Use hermes_trader get_symbol_report for symbol=GOOGL, timeframe=1Day, days=180, persist=true. Focus on whether long, short, or hold is better supported by the data.
```

```text
Use hermes_trader get_portfolio_report and summarize portfolio exposure, open orders, position concentration, and immediate risks.
```

## Backtesting

```text
Use hermes_trader run_backtest_seed with universe=core, days=180, horizon_days=5, label_threshold=0.0025, strategy=trend_following, persist=true. Summarize final value, win rate, drawdown, and per-symbol behavior.
```

```text
Use hermes_trader run_backtest_sweep with universe=core, days=180, strategies=["trend_following", "breakout", "mean_reversion_watch"], horizons=[1,3,5,10], label_thresholds=[0.0,0.0025,0.005], persist=false. Rank the best parameter sets.
```

```text
Use hermes_trader chart_backtest for the latest backtest run.
```

## Dry-Run Decisions

Dry runs persist the decision audit trail but should not submit paper orders.

```text
Use hermes_trader run_trading_tick with symbols=[], discover_if_empty=true, discovery_strategy=trend_following, max_symbols=3, qty=1, auto_size=true, dry_run=true, strategy_name="trend_following", intended_holding_period="3-10 trading days", strategy_plan={"thesis":"Only consider long trades aligned with multi-day trend strength.","exit_plan":"Review after horizon or if trend regime flips.","risk_notes":"Do not open shorts by default."}
```

```text
Use hermes_trader propose_trade_decision for symbol=NVDA, qty=1, auto_size=true, dry_run=true, strategy_name="trend_following", intended_holding_period="1-3 weeks", strategy_plan={"thesis":"Testing a long trend-following setup.","exit_plan":"Recheck after one week or if price closes below short moving average.","risk_notes":"Paper only; no override unless explicitly asked."}
```

## Paper Orders

Only use `dry_run=false` when you intentionally want to submit a paper order through the orchestrator. Include strategy context every time.

```text
Use hermes_trader propose_trade_decision for symbol=NVDA, qty=1, auto_size=true, dry_run=false, strategy_name="trend_following", intended_holding_period="1-3 weeks", strategy_plan={"thesis":"Paper test of a long setup selected from scanner.","exit_plan":"Hold until target horizon unless risk report says exposure is too high.","risk_notes":"Do not open or add to shorts."}
```

```text
Use hermes_trader run_trading_tick with symbols=["AAPL", "MSFT"], qty=1, auto_size=true, dry_run=false, strategy_name="trend_following", intended_holding_period="3-10 trading days", strategy_plan={"thesis":"Paper execution test against two DB-enabled symbols.","exit_plan":"Check orders immediately, then positions after fill.","risk_notes":"Policy must reject anything outside hard caps."}
```

## Order Follow-Up

```text
Use hermes_trader get_orders with status=open and explain which orders are pending, accepted, new, partially filled, or filled.
```

```text
Use hermes_trader get_order with order_id="<alpaca_order_id>" and explain its lifecycle status.
```

```text
Use hermes_trader cancel_order with order_id="<alpaca_order_id>" if the order is still open and should not remain queued.
```

## Safer Prompt Pattern

When asking Hermes for trading help, prefer this shape:

```text
Use only hermes_trader tools.
First get portfolio state, open positions, open orders, and market clock.
Then scan candidates using trend_following.
Then give me a dry-run plan with strategy_name, intended_holding_period, thesis, exit plan, and risk notes.
Do not submit paper orders unless I explicitly say dry_run=false.
```

## Tool Reference

- `run_trading_tick`: Run a policy-gated decision tick across explicit or discovered symbols.
- `discover_trade_candidates`: Pick eligible candidates from the DB symbol universe without running decisions.
- `scan_trade_candidates`: Rank DB-enabled symbols with a strategy-aware scanner.
- `list_symbols`: Show symbols controlled by Postgres.
- `add_symbol`: Add or enable a symbol, optionally validating with Alpaca.
- `disable_symbol`: Disable a symbol without deleting its history.
- `import_symbols`: Bulk-import symbols into a universe.
- `propose_trade_decision`: Propose one trade and persist the decision audit trail.
- `get_portfolio_state`: Fetch and persist current paper account state.
- `get_open_positions`: Fetch and persist current paper positions.
- `get_orders`: Fetch and sync paper orders.
- `get_order`: Fetch and sync one paper order.
- `cancel_order`: Cancel a pending paper order.
- `get_market_clock`: Fetch Alpaca market clock state.
- `get_market_bars`: Fetch and persist reusable market bars.
- `chart_symbol`: Create a candle chart artifact for one symbol.
- `chart_backtest`: Create an equity curve artifact for a backtest.
- `get_symbol_report`: Return recent bars, features, decisions, and chart artifact.
- `get_portfolio_report`: Return account, positions, open orders, and report artifact.
- `run_backtest_seed`: Backtest historical bars and persist labeled rows for training.
- `run_backtest_sweep`: Compare strategy and parameter combinations without placing orders.
