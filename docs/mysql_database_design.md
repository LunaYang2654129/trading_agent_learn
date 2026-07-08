# MySQL 数据库设计说明

数据库名：`multiple_agent_finance`

## 设计目标

- 保存每一次 LangGraph 多智能体分析运行。
- 保存各 Agent 的结构化输出、审计日志和最终报告。
- 支持本周 technical 单链路中的行情采集、K 线入库和技术指标结果追踪。
- 支持历史报告检索、知识库扩展、共享记忆和后续批量分析。

## 核心表

- `symbols`：股票基础信息。
- `analysis_runs`：一次用户请求对应的一次完整图运行。
- `agent_outputs`：各 Agent 原始结构化输出。
- `market_bars`：数据采集阶段写入的 OHLCV K 线记录，按 `ticker + bar_date + source` 去重。
- `market_snapshots`：分析运行中的行情价格和技术指标快照。
- `company_profiles`：Company Agent 的公司画像。
- `financial_metrics`：Financial Agent 的财务指标。
- `news_items`：News Agent 的新闻条目与情绪标签。
- `technical_indicators`：Technical Agent 的趋势、成交量、MACD、RSI、估值和支撑阻力输出。
- `risk_assessments`：Decision Agent 汇总后的风险分数、风险等级和风险点。
- `decision_summaries`：Decision Agent 的最终判断。
- `reflection_reviews`：Reflection Agent 的校验结果和 retry 建议。
- `final_reports`：最终 Markdown 报告。
- `audit_events`：节点级审计日志。
- `shared_memory_entries`：后续共享记忆写入点。
- `knowledge_documents`：后续知识库/RAG 文档索引。

## 关系设计

- `symbols.ticker` 是股票主索引。
- `analysis_runs.id` 是一次运行的主键，使用 UUID 字符串。
- 运行相关表通过 `run_id` 外键级联删除，便于清理某次试验数据。
- `market_bars` 不依赖 `run_id`，用于保存可复用的行情基础数据。
- 半结构化 Agent 输出使用 MySQL `JSON` 字段保存，避免过早锁死结构。

## 初始化与迁移

- 初始化脚本：[schema.sql](../database/schema.sql)
- 种子数据：[seed.sql](../database/seed.sql)
- Technical Agent 迁移：[001_add_technical_indicators.sql](../database/migrations/001_add_technical_indicators.sql)
- 单链路行情入库迁移：[002_add_market_bars.sql](../database/migrations/002_add_market_bars.sql)

## Technical 单链路写入顺序

1. `Data Collection Agent` 调用 yfinance 获取 OHLCV 和 PE/PB。
2. 如果 `persist_data=True`，写入 `market_bars`。
3. `Technical Agent` 优先消费 state 中的 `market_data`，计算技术指标。
4. `Decision Agent` 汇总技术风险，生成 `risk_assessments` 和 `decision_summaries`。
5. `Final Report` 生成报告，`save_analysis_state()` 写入分析运行相关表。
