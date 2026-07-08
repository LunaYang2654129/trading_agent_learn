# Weekly Technical Single-Link Implementation

This week's implementation focuses on making one executable link stable:

```text
Data Collection -> Data Ingestion Status -> Planner Agent -> Technical Agent -> Decision Agent -> Reflection Agent -> Technical Analysis Report
```

## Entry Points

- Graph: `src/multiple_agent_finance/graph/technical_chain.py`
- CLI: `src/multiple_agent_finance/main.py`
- Run command:

```powershell
python -m multiple_agent_finance.main --mode technical-chain --ticker AAPL
```

Run with market-bar persistence and final-state database persistence:

```powershell
python -m multiple_agent_finance.main --mode technical-chain --ticker AAPL --persist-data --save-db
```

## Chain Agents

### Data Collection Agent

File: `src/multiple_agent_finance/agents/data.py`

Inputs:

- `ticker`
- `as_of_date`
- `market_period`
- `persist_data`

Outputs:

- `market_data`: OHLCV bars, PE/PB, warnings, and sources.
- `data_ingestion_result`: rows collected, rows persisted, persistence status, and warnings.

### Planner Agent

File: `src/multiple_agent_finance/agents/planner.py`

In technical mode, Planner creates only single-link tasks:

- Confirm market-data collection and ingestion status.
- Analyze OHLCV, volume, moving averages, MACD, RSI, Bollinger Bands, ATR, PE/PB, and support/resistance.
- Instruct Decision to avoid real trading orders.
- Instruct Reflection to validate technical completeness and retry tasks.

### Technical Agent

File: `src/multiple_agent_finance/agents/technical.py`

Technical Agent prefers `state.market_data` and avoids duplicate data fetching. It falls back to yfinance only when state data is unavailable.

Output fields:

- `trend`
- `volume_signal`
- `macd_signal`
- `rsi_signal`
- `valuation_pe`
- `valuation_pb`
- `support_resistance`
- `market_snapshot`
- `technical_risks`
- `warnings`
- `sources`

### Decision Agent

File: `src/multiple_agent_finance/agents/decision.py`

In technical mode, Decision requires only `technical_indicators`. Company, Financial, and News outputs are not required for this chain.

Risk points come from:

- Weak trend.
- Bearish MACD.
- Overbought or oversold RSI.
- High ATR-driven volatility.
- Shrinking volume during an uptrend.
- Indicator or data-source warnings.

### Reflection Agent

File: `src/multiple_agent_finance/agents/reflection.py`

In technical mode, Reflection validates:

- `market_data`
- `data_ingestion_result`
- `technical_indicators`
- `trend / volume_signal / macd_signal / support_resistance / technical_risks`

When technical indicators are missing, the retry task is:

```text
Backfill technical_indicators: trend / volume_signal / macd_signal / support_resistance
```

## Database

New table:

- `market_bars`: stores OHLCV bars collected during the data collection stage.

New migration:

- `database/migrations/002_add_market_bars.sql`

## Tests

Covered behavior:

- The full graph still contains `technical_agent` and no parallel `risk_agent`.
- The technical single-link graph contains `data_collection_agent`.
- Technical tools compute MA, MACD, RSI, Bollinger Bands, and ATR.
- yfinance empty-data fallback does not interrupt the flow.
- Decision technical mode does not require Company, Financial, or News outputs.
- Reflection returns actionable retry tasks when technical indicators are missing.
- The technical single-link graph can run from mock market data to final report.

Run:

```powershell
pytest -q
```
