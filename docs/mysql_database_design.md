# MySQL 数据库设计说明

数据库名：`multiple_agent_finance`

设计目标：

- 保存每一次 LangGraph 多智能体分析运行。
- 保存各 Agent 的结构化输出、审计日志和最终报告。
- 支持后续做历史回测、报告检索、知识库扩展和共享记忆。

核心表：

- `symbols`：股票基础信息。
- `analysis_runs`：一次用户请求对应的一次完整图运行。
- `agent_outputs`：各 Agent 原始结构化输出，便于排查和复盘。
- `market_snapshots`：行情价格和技术指标快照。
- `company_profiles`：公司画像。
- `financial_metrics`：财务指标。
- `news_items`：新闻条目与情绪标签。
- `risk_assessments`：风险分数、风险等级、风险点。
- `decision_summaries`：Decision Agent 的最终判断。
- `reflection_reviews`：Reflection Agent 的校验结果和重试建议。
- `final_reports`：最终 Markdown 报告。
- `audit_events`：节点级审计日志。
- `shared_memory_entries`：后续共享记忆写入点。
- `knowledge_documents`：后续知识库/RAG 文档索引。

关系设计：

- `symbols.ticker` 是股票主索引。
- `analysis_runs.id` 是一次运行的主键，使用 UUID 字符串。
- 运行相关表通过 `run_id` 外键级联删除，便于清理某次试验数据。
- 半结构化信息使用 MySQL `JSON` 字段保存，避免过早锁死 Agent 输出结构。

初始化脚本：

- [schema.sql](../database/schema.sql)
- [seed.sql](../database/seed.sql)
