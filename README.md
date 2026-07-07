# Trading Agent Learn

本项目是一个面向股票多智能体分析系统的学习与工程原型工作区。当前实现围绕 LangGraph 构建 Planner、Company、Financial、News、Risk、Decision、Reflection 和 Final Report 节点，支持本地报告生成和 MySQL 落库。

## 目录说明

- `src/`：项目核心代码在这里。
- `docs/`：生成的学习计划、架构设计、研究分析和数据库设计说明在这里。
- `database/`：MySQL 建库脚本、种子数据、项目本地 MySQL 配置和数据目录。
- `scripts/`：MySQL 启动、停止和初始化脚本。
- `tests/`：基础测试。
- `papers/`：下载的论文 PDF。
- `papers/text/`：从论文 PDF 提取的文本。
- `code/`：外部开源项目参考代码，本项目不直接维护这些第三方仓库。
- `outputs/`：运行生成的报告和日志，默认不提交。
- `data/`：原始数据、处理数据、知识库和共享记忆目录，默认不提交业务数据。

## 核心能力

- LangGraph 多智能体股票分析流程。
- 并行 Agent 层：公司画像、财务指标、新闻舆情、风险分析。
- Decision Agent 汇总结构化结论。
- Reflection Agent 校验完整性、风险覆盖和置信度。
- Final Report 节点生成 Markdown 报告。
- MySQL 数据库保存分析运行、Agent 输出、报告和审计日志。

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

## 运行分析

```powershell
python -m multiple_agent_finance.main --ticker AAPL --request "综合分析基本面、行情、新闻和风险。"
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

运行并写入数据库：

```powershell
python -m multiple_agent_finance.main --ticker AAPL --save-db
```

停止 MySQL：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_mysql.ps1
```

## 重要文档

- `docs/langgraph_multi_agent_learning_plan.md`：LangGraph 多智能体学习计划。
- `docs/langgraph_trading_agent_blueprint.md`：交易 Agent 架构蓝图。
- `docs/meeting_based_improvement_plan.md`：基于会议纪要的改进计划。
- `docs/research_and_code_analysis.md`：论文和代码分析。
- `docs/mysql_database_design.md`：MySQL 数据库设计。
- `docs/environment_setup.md`：环境安装说明。

## 外部参考代码

`code/` 下保存了 FinRL、FinRL-Meta、FinRL-Trading、TradingAgents、LangGraph Supervisor 等外部项目的本地参考副本。它们用于学习和对比分析，不作为本项目源码的一部分提交和维护。

## 测试

```powershell
pytest -q
```

## 注意

本项目用于学习、研究和工程原型，不构成投资建议。任何实盘交易前都需要独立验证、风控、合规审查和长期模拟盘测试。
