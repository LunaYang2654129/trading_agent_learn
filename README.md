# Trading Agent Learn

本项目是面向股票多智能体分析系统的学习与工程原型工作区。当前实现基于 LangGraph，支持完整多 Agent 分析图，也支持本周计划中的 technical 单链路跑通。

## 目录说明

- `src/`：项目核心代码在这里。
- `docs/`：生成的学习计划、架构设计、研究分析和数据库设计说明在这里。
- `database/`：MySQL 建库脚本、迁移脚本和种子数据。
- `scripts/`：MySQL 启动、停止和初始化脚本。
- `tests/`：基础测试和单链路测试。
- `papers/`：下载的论文 PDF。
- `papers/text/`：从论文 PDF 提取的文本。
- `code/`：外部开源项目参考代码，本项目不直接维护这些第三方仓库。
- `outputs/`：运行生成的报告和日志，默认不提交业务输出。
- `data/`：原始数据、处理数据、知识库和共享记忆目录，默认不提交业务数据。

## 核心能力

- 完整 LangGraph 流程：`Planner -> Company / Financial / News / Technical -> Decision -> Reflection -> Final Report`。
- 本周 technical 单链路：`Data Collection -> Data Ingestion Status -> Planner -> Technical -> Decision -> Reflection -> Final Report`。
- Technical Agent 支持 K 线、成交量、MA20/MA60/MA200、MACD、RSI、Bollinger Bands、ATR、PE/PB、支撑阻力和技术风险输出。
- Decision Agent 在完整图中汇总四类专业结果；在 technical 单链路中只基于技术指标形成保守风险判断。
- Reflection Agent 按链路模式校验缺失项、风险覆盖、置信度和 retry 补采任务。
- MySQL 可保存分析运行、Agent 输出、技术指标、行情 K 线、报告和审计日志。

## 环境准备

推荐使用 conda：

```powershell
conda env create -f environment_multiple_agent_finance.yml
conda activate multiple_agent_finance
pip install -e .
```

也可以直接使用 pip：

```powershell
pip install -r requirements.txt
pip install -e .
```

## 运行完整图

```powershell
python -m multiple_agent_finance.main --ticker AAPL --request "Analyze fundamentals, financials, news sentiment, and technical signals."
```

## 运行本周 technical 单链路

只跑链路并生成报告：

```powershell
python -m multiple_agent_finance.main --mode technical-chain --ticker AAPL
```

采集行情、入库并保存最终分析状态：

```powershell
python -m multiple_agent_finance.main --mode technical-chain --ticker AAPL --persist-data --save-db
```

生成报告会写入：

```text
outputs/reports/
```

## MySQL

本地开发数据库配置文件：

```text
database/my.ini
```

启动 MySQL：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_mysql.ps1
```

初始化数据库：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init_mysql_database.ps1
```

已有数据库迁移：

```powershell
mysql -u root -p < database/migrations/001_add_technical_indicators.sql
mysql -u root -p < database/migrations/002_add_market_bars.sql
```

停止 MySQL：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_mysql.ps1
```

## 重要文档

- `docs/weekly_technical_single_link.md`：本周 technical 单链路实现说明。
- `docs/langgraph_multi_agent_learning_plan.md`：LangGraph 多智能体学习计划。
- `docs/langgraph_trading_agent_blueprint.md`：交易 Agent 架构蓝图。
- `docs/meeting_based_improvement_plan.md`：基于会议纪要的改进计划。
- `docs/research_and_code_analysis.md`：论文和代码分析。
- `docs/mysql_database_design.md`：MySQL 数据库设计。
- `docs/environment_setup.md`：环境安装说明。

## 测试

```powershell
pytest -q
```

## 注意

本项目用于学习、研究和工程原型，不构成投资建议，不接 broker，不输出真实下单指令。任何实盘交易前都需要独立验证、风控、合规审查和长期模拟盘测试。
