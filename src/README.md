# src

代码在这里。

主要目录：

- `multiple_agent_finance/agents/`：各 Agent 节点实现，包括数据采集、Planner、Company、Financial、News、Technical、Decision、Reflection。
- `multiple_agent_finance/graph/`：LangGraph 状态、路由、完整图和 technical 单链路图。
- `multiple_agent_finance/tools/`：公司、财务、新闻、行情采集、技术指标和兼容风险工具。
- `multiple_agent_finance/reports/`：最终 Markdown 报告生成。
- `multiple_agent_finance/storage/`：MySQL 落库逻辑。
- `multiple_agent_finance/config/`：项目配置。

本周单链路入口：

```powershell
python -m multiple_agent_finance.main --mode technical-chain --ticker AAPL --persist-data --save-db
```
